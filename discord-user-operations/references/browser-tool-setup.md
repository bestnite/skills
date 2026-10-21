# Giving the agent a browser tool (text guidance)

Access Path B in this skill assumes you can drive a browser that is logged into
Discord. This page is for when you cannot — either because you have no browser
tool at all, or no way to get the user's session into it.

**Nothing here depends on code running.** It is instructions to adapt to the
machine in front of you, because only you can see its constraints (OS, WSL or
not, what is installed, which MCP client is in play).

Source guide (the author's write-up, CC BY-NC-SA 4.0):
**<https://www.nite07.com/posts/agent-playwright-cloak/>**
— English mirror: <https://www.nite07.com/posts/agent-playwright-cloak/index.md>

## What Path B actually needs

Three things, no more:

1. **Navigate** to a `discord.com` URL and get the rendered page.
2. **Evaluate JS** in that page (the DOM reads, and the same-origin `fetch` that
   does all the writes).
3. **A session**: a profile already logged in as the user, or a way to inject the
   stored Discord token / storage state — a cookie-and-storage tool, a
   storage-state file, CDP, or the user's own logged-in profile.

Any implementation with those three works. Decide from your own toolset: if you
already have such a tool, skip this page. If you do not, do **not** improvise —
set one up (below) or ask the user for one.

## Variant A — CloakBrowser kernel behind Playwright MCP (recommended)

Discord web is tolerant, but a stock automation browser still shows the usual
signals (`navigator.webdriver = true`, empty plugin list, mismatched TLS
fingerprint). CloakBrowser is an anti-detect Chromium build; Playwright MCP is
the entry point, and its `--caps=storage` flag is what provides the
cookie/storage tools Path B relies on.

**1. Install the kernel.** The exact path matters later, so read it back:

```bash
uv tool install cloakbrowser      # or: pipx install cloakbrowser
cloakbrowser install              # downloads the browser binary
cloakbrowser info                 # prints the kernel path — copy it
```

If `uv`/`pipx` are unavailable, any install route works as long as
`cloakbrowser install` runs and reports a path.

**2. Point Playwright MCP at it.** Config file — write it wherever *your* client
keeps MCP configs; check its docs rather than assuming. (Example only: a Hermes
install reads its own config from `~/.hermes/playwright-mcp/config.json` — do not
copy that path if you are not on Hermes.) Note the path you chose for step 3:

```json
{
  "browser": {
    "browserName": "chromium",
    "launchOptions": {
      "executablePath": "<path reported by cloakbrowser info>"
    }
  },
  "outputDir": "<any writable directory>"
}
```

Both values are placeholders on purpose — where the browser and its output live
is this machine's decision, not the skill's. Fill them from `cloakbrowser info`
on Linux, the app bundle on macOS, `...\chrome.exe` on Windows.

**3. Register the MCP server with the agent.** Hermes example — the flags are the
part that generalises:

```yaml
mcp_servers:
  playwright-cloak:
    enabled: true
    command: npx
    args:
      - "@playwright/mcp@latest"
      - "--caps=storage"     # ← the flag that provides the storage tools
      - "--config"
      - "<path to the config file from step 2>"
      - "--headless"
```

Without `--isolated`, Playwright MCP keeps a persistent profile, which is the
preferred home for the session (`session-persistence.md`). With `--isolated` the
profile lives in memory; then also pass
`--storage-state=<skill dir>/.state/storage-state.json`, where `<skill dir>` is
the directory this skill was loaded from — an absolute path only your install
knows.

`--caps=storage` adds what Path B needs:

| Tool | Purpose |
|---|---|
| `browser_storage_state` / `browser_set_storage_state` | save and restore the session (this is how the Discord token arrives) |
| `browser_cookie_set` / `get` / `list` / `delete` / `clear` | manage individual cookies |

**4. Verify** before touching Discord:

```bash
hermes mcp test playwright-cloak     # expect: ✓ Connected / ✓ Tools discovered
```

A server that connects but exposes no storage/cookie tools means `--caps=storage`
did not take effect — fix that first, because loading the session is the point.

## Variant B — Windows/WSL split

If the agent runs inside WSL but a Windows browser is the better citizen (no WSL
graphics/GPU/Turnstile pain), keep Playwright MCP and the browser on the Windows
side: put the config wherever the Windows-side client keeps its MCP configs,
point `executablePath` at the `chrome.exe` path that `cloakbrowser info` reports
when run on Windows, and let the WSL-side agent drive it. Do **not** point the agent's `command` straight at
`/mnt/c/Program Files/nodejs/npx` — child processes started that way can lose
their environment; use the wrapper form the guide prescribes.

## Variant C — no CloakBrowser: plain Playwright

Acceptable when CloakBrowser cannot be installed at all:

```bash
uvx --with playwright playwright install chromium
```

Playwright then resolves its own browser — there is no path to configure. If you
do want an explicit binary, ask Playwright where its browser lives on this machine
rather than assuming a location:

```bash
python - <<'PY'
from playwright.sync_api import sync_playwright
pw = sync_playwright().start()
print(pw.chromium.executable_path)
pw.stop()
PY
```

Either form works — what matters is that the session reaches the browser, not
where the binary lives.

## After the tool exists

1. Load the user's Discord session into it: a logged-in persistent profile, or
   the storage state saved in `.state/storage-state.json` (it holds the `token`
   entry for the `https://discord.com` origin). Where to save it after a fresh
   login: `session-persistence.md`. Unwrapping details:
   `browser-session-details.md`.
2. Open `https://discord.com` and confirm you see the app shell rather than a
   login screen — that is the session check; no code needed.
3. Continue with `browser-session-details.md` (DOM reads, same-origin `fetch` for
   writes).

## If the setup fails

- **Report what you tried and where it stopped.** Do not silently fall back to a
  half-working path: reading the page without a session yields a login screen, and
  presenting that as data is worse than saying "no browser session available".
- **The direct-HTTP path still works.** If the user can supply their token, Access
  Path A needs no browser at all — that is often the faster unblock, and it is
  worth offering before spending turns on browser setup.
- **Never invent kernel paths.** If `cloakbrowser info` cannot be run, leave the
  placeholder and ask the user for the path. Do not glob likely install
  directories: a guessed path fails later and looks like a bug in the skill,
  while "not configured" is an honest stop.
- **One browser is enough.** If the agent already has a cookie-capable browser
  tool (cloak, Playwright MCP, browser-use, a CDP-attached Chromium), use it and
  skip this page entirely.
