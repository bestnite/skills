# Session persistence

Where a login lives between runs, and how to save and restore it. This skill holds
an HTTP cookie set rather than a browser profile, so the rules below are the ones
that apply here; every skill in this repository that keeps a login follows the
same containment rules.

## Order of preference

1. **The user's own browser session, used while it lasts.** Ask for the cookies,
   use them for the task, and drop them. This holds no credential on disk at all
   and is the right default for a one-off lookup. The board can invalidate a
   copied session at any time (see `access-and-session.md`), so treat it as
   short-lived and never build a workflow that assumes it survives.
2. **The skill's `.state/` directory, when the user wants the login to persist.**
   Save the cookie set to `.state/session.json` inside this skill's directory,
   mode `0600`. Write session material nowhere else — not `/tmp`, not the home
   directory, not the working directory — so every credential the skill ever
   wrote sits in one place the user can inspect and delete.
3. **Credentials the user re-supplies per run.** Legitimate and the least
   surprising: nothing is stored, the user pastes a fresh cookie when it expires.
   Slower, and never wrong.

Do not scan the machine for browser cookie databases. A cookie store on disk is
the browser's, not yours, and reading it is a decision the user has to make.

## Ask at the moment the credential arrives

The question belongs in the same reply that acknowledges the credentials, not later and not silently:

> Session received. Keep it in this skill's `.state/` so the next run does not ask again, or use it once and drop it?

Asking afterwards — after the search, at the end of the task — is worse than useless: the user has already paid the cost of pasting it, and the next run asks again. Ask once, record the answer, and do not re-ask on every run while the session still works.

## Layout

- `<skill dir>` is the directory this skill's `SKILL.md` was loaded from. Resolve
  it at runtime; its absolute path differs per install.
- `<skill dir>/.state/session.json` — the cookie set, written only after the user said to keep it:

  ```json
  {"cookies": {"csrinru_phpbb3_u": "...", "csrinru_phpbb3_k": "...", "csrinru_phpbb3_sid": "..."},
   "user": "<account name, optional>",
   "saved_at": "<ISO 8601 timestamp, optional>"}
  ```

  Do not store `securitytoken` — it is bound to the client that minted it and
  expires daily; mint a fresh one on every run (`access-and-session.md`).
- The skill ships a `.gitignore` that ignores `.state/`, so a skill directory
  inside a git work tree does not stage it.

## Saving

- Ask once before the first write, because putting a live account session on disk
  is the user's decision. Say where the file goes (`<skill dir>/.state/`). The
  consent covers later refreshes of the same file; do not ask again on every run,
  and never save without that first consent.
- Create it restrictive from the start: directory `0700`, file `0600` on Unix, an
  owner-only ACL on Windows. Write to a temporary file inside `.state/`, then
  rename it over the target. Do not write a readable file and `chmod` it
  afterwards, because the session is exposed in between.
- Never route the value through the console, shell arguments, or a command line
  that ends up in shell history. Read it from the user's message into the file
  directly, or from an environment variable the user sets.
- Re-save over the same file after the user logs in again, so a later run does not
  load a dead session.

## Restoring

- Load the file, then run the session check before any real work: fetch
  `index.php` and look for `ucp.php?mode=logout` (logged in) versus
  `ucp.php?mode=login` (guest). Page content is the only reliable signal; the
  absence of an error is not.
- A failed check means the user supplies a fresh cookie. Do not retry the same
  cookie, and do not silently continue as an anonymous client while reporting
  masked links as if they were results.

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

- Deleting `.state/` does not end the session on the server. Revocation means the
  user logs out through the board's own session handling (or changes the
  password), then deletes `.state/`.
- Do not delete `.state/` without the user's permission.
