# Giving the agent a browser tool (text guidance)

**This file is the instruction. Nothing here depends on code running** — this
skill ships only a signer, and the browser is set up by you, by hand. Adapt the
steps to the machine in front of you.

Source guide (the author's write-up, CC BY-NC-SA 4.0):
**<https://www.nite07.com/posts/agent-playwright-cloak/>**
— English mirror: <https://www.nite07.com/posts/agent-playwright-cloak/index.md>

## What you actually need

One capability, three parts:

1. **Navigate** a URL and get the rendered DOM.
2. **Evaluate JS** in the page (to run the extractor in `browser-search.md`).
3. **Inject cookies** into that browser session — any mechanism counts:
   a cookie-setting tool, a storage-state file, CDP `Network.setCookie`, or a
   profile the user pre-populated.

Nothing else about the implementation matters. If the environment already has a
tool with those three, skip this page and go straight to `browser-search.md`.

## Pick the shape that fits the machine

Resolve these four questions first — they decide which variant below applies:

| Question | Why it matters |
|---|---|
| Linux, macOS, or is the agent inside WSL? | Decides where the browser and its config live |
| Is the browser driven by an MCP server, or by code you write? | MCP → config file; code → a Playwright install |
| Is `npx` available? Is `uv`? | `npx` for Playwright MCP, `uv` for the CloakBrowser kernel |
| Does the agent's MCP config already have a browser entry? | Upgrade it rather than adding a second one |

## Variant A — CloakBrowser kernel behind Playwright MCP (recommended)

Why this one: CloakBrowser is an anti-detect Chromium build, so it survives
anti-bot checks that plain Playwright trips (`navigator.webdriver = true`, empty
plugin list, mismatched TLS fingerprint). Playwright MCP is the entry point the
agent talks to, and its `--caps=storage` flag is what supplies the cookie tools.

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
part that generalises to other clients:

```yaml
mcp_servers:
  playwright-cloak:
    enabled: true
    command: npx
    args:
      - "@playwright/mcp@latest"
      - "--caps=storage"     # ← the flag that provides the cookie tools
      - "--config"
      - "<path to the config file from step 2>"
      - "--headless"
```

`--caps=storage` adds the tools this skill depends on:

| Tool | Purpose |
|---|---|
| `browser_cookie_set` / `get` / `list` / `delete` / `clear` | manage individual cookies |
| `browser_storage_state` / `browser_set_storage_state` | save / restore cookies + localStorage |

Without `--isolated`, Playwright MCP keeps a persistent profile, which is the
preferred home for the session (`session-persistence.md`). With `--isolated` the
profile lives in memory and is gone at exit; then load the saved session from this
skill's state directory with
`--storage-state=<skill dir>/.state/storage-state.json`, where `<skill dir>` is
the directory this skill was loaded from — an absolute path only your install
knows.

**4. Verify** before touching Xianyu:

```bash
hermes mcp test playwright-cloak     # expect: ✓ Connected / ✓ Tools discovered
```

A server that connects but whose tool list lacks `browser_cookie_*` means
`--caps=storage` did not take effect — fix that before proceeding, because cookie
injection is the whole point.

## Variant B — Windows/WSL split

If the agent runs inside WSL but a Windows browser is the better citizen (no WSL
graphics/GPU/Turnstile pain), keep Playwright MCP and the browser on the Windows
side: put the config wherever the Windows-side client keeps its MCP configs,
point `executablePath` at the `chrome.exe` path that `cloakbrowser info` reports
when run on Windows, and let the WSL-side agent drive it. Do **not** point the agent's `command` straight at
`/mnt/c/Program Files/nodejs/npx` — child processes started that way can lose
their environment; use the wrapper form the guide prescribes.

## Variant C — no CloakBrowser: plain Playwright

Acceptable, with a caveat: a stock Chromium is more likely to be flagged by
Xianyu's anti-bot layer, so expect possible login walls or verification pages.
Use it when CloakBrowser cannot be installed at all:

```bash
uvx --with playwright playwright install chromium
```

Playwright then resolves its own browser — there is no path to configure. If you
want to point the skill's search path at a *specific* binary instead, ask
Playwright where its browser lives on this machine and export that, rather than
assuming an install location:

```bash
python - <<'PY'
from playwright.sync_api import sync_playwright
pw = sync_playwright().start()
print(pw.chromium.executable_path)   # export this as GOOFISH_BROWSER_EXECUTABLE
pw.stop()
PY
```

Either form works — what matters is that cookies reach the browser, not where the
binary lives. If the site starts rejecting the session anyway, that is the reason
(stock Chromium is easier to fingerprint) — say so instead of retrying.

## After the tool exists

1. Get the Xianyu session into it — the persistent profile already has it, or
   restore `.state/storage-state.json`, or inject a fresh jar with the cookie
   tools (then save it as `session-persistence.md` describes). Open
   `https://www.goofish.com` and check you see the account rather than a login
   wall — that is the only session check worth doing.
2. Follow `browser-search.md`: navigate to the search URL, scroll, evaluate the
   extractor it carries.
3. `body` / `risk_markers` showing 请先登录 / 验证码 / 安全验证 / 异常访问 means a
   login wall or risk-control page — a cookie or kernel problem, not a selector
   problem.
4. Everything else (item detail, own listings, chats) is **also** done in the
   browser: sign the URL on the host with `templates/mtop_request.py`, then run
   it with `fetch()` in the page. A host HTTP client works briefly and then trips
   `RGV587`; see `mtop-apis.md` for the measurement.

## If the setup fails

- **Report what you tried and where it stopped.** Do not fall back to fetching
  the search page over HTTP — it is client-rendered and login-walled, so the
  result is a shell page, and presenting that as data is worse than saying
  "no browser available".
- **Do not fall back to a host HTTP client for the JSON endpoints either.** It
  appears to work for about a dozen calls, then risk control lands; that reads
  like a dead session and sends you debugging the wrong thing.
- **Never invent kernel paths.** If `cloakbrowser info` cannot be run, leave the
  placeholder and ask the user for the path. Do not glob likely install
  directories: a guessed path fails later and looks like a bug in the skill,
  while "not configured" is an honest stop.
- **One browser is enough.** If the agent already has a cookie-capable browser
  tool (cloak, Playwright MCP, browser-use, a CDP-attached Chromium), use it and
  skip this page entirely.
