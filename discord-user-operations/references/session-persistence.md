# Session Persistence

Where a logged-in session lives between runs, and how to save and restore it.
Every skill in this repository that drives a logged-in browser ships this same
text; when you change one copy, change all of them.

## Order of preference

1. **A browser tool with a persistent profile.** If your toolset has a browser
   whose profile survives restarts — a persistent context or user-data directory
   the tool manages, or the user's own logged-in browser — use it and let it keep
   the session. Write no credential file in this case, because the browser
   already owns the cookie attributes (`HttpOnly`, `SameSite`, domain, expiry)
   and picks up every token the site rotates; a copy on disk can only go stale.
2. **Otherwise, the skill's own `.state/` directory.** When the browser tool
   forgets the session between runs (an isolated or in-memory context), save the
   session with the tool's storage export into `.state/` inside this skill's
   directory, and restore it from there next time. Write session material
   nowhere else — not `/tmp`, not the home directory, not the working directory
   — so that every credential the skill ever wrote sits in one place the user
   can inspect and delete.
3. **No browser tool at all.** That is not a persistence question; follow the
   skill's browser-tool setup guidance or ask the user for a browser.

Decide between 1 and 2 from your own toolset and the tool's documentation. Do not
scan the machine for profiles or user-data directories.

## Layout

- `<skill dir>` is the directory this skill's `SKILL.md` was loaded from. Resolve
  it at runtime; its absolute path differs per install.
- `<skill dir>/.state/storage-state.json` — the browser tool's storage export
  (cookies and `localStorage`), in the format the tool writes and reads back. For
  Playwright-based tools that is `{"cookies": [...], "origins": [...]}`.
- Any other per-account state a skill names (a device id, a cached access token)
  also lives under `.state/`, one file per item, with the file name given in that
  skill's docs.
- The skill ships a `.gitignore` that ignores `.state/`, so a skill directory
  inside a git work tree does not stage it.

## Saving

- Ask once before the first write, because putting a live account session on
  disk is the user's decision. Say where the file goes (`<skill dir>/.state/`).
  The consent covers later refreshes of the same file; do not ask again on every
  run, and never save without that first consent.
- Create it restrictive from the start: directory `0700`, file `0600` on Unix,
  an owner-only ACL on Windows. Write to a temporary file inside `.state/`, then
  rename it over the target. Do not write a readable file and `chmod` it
  afterwards, because the session is exposed in between.
- Move the export straight from the browser tool to the file. If the tool can
  only write into its own output directory, move the file into `.state/` with a
  filesystem move. Never route the contents through the conversation, the
  console, or shell arguments: they are a live account session.
- If the browser runs on another host or filesystem (a container, a Windows
  browser driven from WSL), use the path under which that host sees the same
  `.state/` directory. If it has no such path, tell the user rather than picking
  a different location.
- Re-export over the same file after the session changes (a new login, a
  refreshed token), so a later restore does not load a dead session.

## Restoring

- Load the file with the tool's own restore mechanism (a set-storage-state tool,
  or a launch option such as Playwright MCP's
  `--isolated --storage-state=<skill dir>/.state/storage-state.json`), then run
  the skill's session check before any real work.
- A restore is not guaranteed. A storage export covers cookies and `localStorage`;
  it normally omits `sessionStorage`, includes IndexedDB only on some tool
  versions, and carries no device attributes. A failed session check after a
  restore means the user logs in again — do not retry the restore or edit the
  file.

## Keeping it contained

- Do not read, list, or quote `.state/` contents while exploring the skill; they
  are credentials, not documentation.
- Reinstalling or updating the skill can replace its directory and delete
  `.state/`; the user then logs in again. Say so if the user asks why a session
  disappeared.
- Some hosts sync skill directories across devices. On such a host `.state/`
  travels with the skill; mention it when you ask for consent if you know the
  host syncs.

## Revocation

- Deleting `.state/` or a browser profile does not end the session on the
  server. Revocation means the user logs out through the site's own session or
  device management, then deletes `.state/`.
- Do not delete `.state/` or clear a profile without the user's permission.
