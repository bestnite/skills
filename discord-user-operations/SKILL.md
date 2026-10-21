---
name: discord-user-operations
description: "Use when operating Discord as a user: read, search, post."
---

# Discord User Operations

Read, search, and write on Discord as a regular user account (a "user token" session, no bot application). Typical work: browse servers and forum threads, read channel history, search messages, reply to threads, edit your own messages, add reactions, handle DMs.

Everything here is done through Discord's official REST API. This skill covers **what to do and which mechanics matter**; pick the concrete transport that fits your available tools (see Access Paths) — a shell HTTP client, a script, or a browser automation session all reach the same API. The skill ships no code: every choice that depends on your environment is written as a decision for you to make, not a script to run.

**Default posture: read-heavy, low frequency.** Writes that others can see (send / edit / delete / react / rename) require the user's explicit approval first: draft the exact content, get confirmation, then execute — and verify.

## Core Defaults

- Verify identity before anything else: `GET /users/@me`. This also proves the credential works.
- Prefer the REST API over UI interaction. Use the rendered page only for quick reads of what is already on screen.
- Keep requests at a human pace; treat `429` as a pacing signal, not a retry-forever loop.
- Never print or log the token, and never store it outside this skill's `.state/` directory (`references/session-persistence.md`). A user token is account-takeover-grade.
- Before editing or deleting, re-read the target and confirm its exact ID. Ambiguity → ask, never guess.
- If a call is forbidden or unauthorized (`401`/`403`), stop and surface it rather than silently probing alternatives.

## Access Paths

Two equally valid routes to the same API; pick per available tooling (mixing is fine).

### A. Direct HTTP (no browser)

Works with any HTTP client (curl, requests, a script's fetch).

- `https://discord.com/api/v10<path>`, header `Authorization: <user token>`.
- Writes additionally need `Content-Type: application/json`.
- Simplest for scripted and batch reads.

### B. Through a logged-in browser session

**Prerequisite:** a browser tool you can drive that reaches a logged-in Discord
session — it needs to navigate, evaluate JS, and either use the user's own
logged-in profile or inject their stored token. A browser with a persistent
profile keeps the session between runs; otherwise save and restore it via
`<skill dir>/.state/storage-state.json` (`references/session-persistence.md`).
**You can tell whether you have
one from your own toolset; do not probe the machine for it.** If you do not have
one, do not improvise: read `references/browser-tool-setup.md` (text instructions
you adapt locally, including how to stand up CloakBrowser behind Playwright MCP),
or ask the user for a browser tool. If the user can hand over their token instead,
Access Path A needs no browser at all and is usually the faster unblock.

When you drive a browser session that is already logged in as the user:

- Quick reads: query the rendered DOM (hooks in `references/browser-session-details.md`).
- Precise reads and **all writes**: issue `fetch()` from a page whose origin is `discord.com` (same-origin) with the `Authorization` header — you get the real API and JSON back.
- To get the token for headers, use your tool's context-level storage export (session / storage-state dump). Do **not** expect page JS to see `localStorage` — stealth/isolated contexts routinely hide it; this is a known dead end. If it can't be obtained cleanly, ask the user.
- Prefer API `fetch` over clicking UI controls for writes: hover-revealed menus rebuild constantly and detach between calls. Typing into the composer is a last resort, not the default.

## Mechanics

- **Auth**: `Authorization: <token>` — raw user token. No `Bot`/`Bearer` prefix (those belong to other auth schemes).
- **Version**: `/api/v10` per docs; the web client uses `/api/v9`; both serve the routes here.
- **Snowflakes**: IDs are 64-bit integers as strings — never numeric-parse (precision loss). For time filters: `snowflake = (unix_ms − 1420070400000) << 22`; reverse: `unix_ms = (id >> 22) + 1420070400000`. (Verified in field: message `1547649194527948852` ↔ 2026-09-10T16:45:21.907Z.)
- **Rate limits**: `429` bodies carry `retry_after` (seconds, may be fractional). Wait it plus a small jitter, retry — cap ~3 attempts, then report. Buckets are per-route; a busy route doesn't block others.
- **Statuses**: `2xx` ok; `204` no-body success (deletes). Errors: JSON `{message, code, errors?}`. `401` dead token → stop. `403` permission/feature missing (e.g. guild search disabled). `404` gone. `400` + `code 50035` = invalid form body → read `errors.<field>._errors[].message` (e.g. per-field max length).
- **Encoding**: URL-encode emoji in paths/query; custom emoji use `name:id`.

## Read Recipes

1. **Identify** — `GET /users/@me`; servers: `GET /users/@me/guilds`.
2. **Map a server** — `GET /guilds/{guild}/channels`; filter by `type` (0 text · 5 announcement · 15 forum · 11/12 threads · 4 category) and `parent_id`.
3. **Read history** — `GET /channels/{channel}/messages?limit=25` (≤100). Page back with `before=<oldest seen>`, forward with `after`, jump with `around`. Sort by id if chronological order matters. One message: append `/{message_id}`.
4. **Search** — `GET /guilds/{guild}/messages/search` with `content`, `author_id`, `channel_id`, `has`, `min_id`/`max_id`, `offset`. Date filters via snowflake conversion. Results are grouped and relevance-ordered. On `403` (search disabled): fall back to scanning the channel's messages and filtering locally.
5. **Usernames → IDs** — `GET /guilds/{guild}/members/search?query=…`; prefer an exact username / global-name / nickname match, else first result.
6. **Pins** — `GET /channels/{channel}/pins`.
7. **Threads & forum posts** — archived lists: `GET /channels/{channel}/threads/archived/public` (+ `/private`). A forum post **is** a thread channel: read it like any channel; its first message id equals the thread channel id.
8. **DMs** — `GET /users/@me/channels` to list; `POST /users/@me/channels {recipient_id}` to open; then treat as a channel.

Full endpoint catalog with params, bodies, and gotchas: `references/discord-api-endpoints.md`.

## Write Recipes

- **Send** — `POST /channels/{channel}/messages` `{"content": "…"}`; to reply add `"message_reference": {"message_id": "…"}`.
- **Edit own** — `PATCH …/messages/{message_id}` `{"content": "…"}` · **Delete own** — `DELETE …/messages/{message_id}` (→ `204`).
- **React** — `PUT …/messages/{message_id}/reactions/{emoji}/@me` (emoji URL-encoded); remove with `DELETE` on the same path.
- **Thread / forum title** — `PATCH /channels/{thread_id}` `{"name": "…"}`. Thread names cap at **100 characters** (over → `400`/50035). A "renamed the thread" system message appears in-thread — normal, not an error.
- **After any write**: re-read the target (GET it / reload the page) and confirm persistence and expected state (edited marker, new message visible) before reporting success.

## Worked Flow — reply into a forum thread

1. Resolve the thread: its channel id; first message id = channel id.
2. Read enough context that the reply fits the conversation.
3. Draft the exact text; get the user's approval.
4. `POST /channels/{thread}/messages` `{"content": "…"}`.
5. Verify by re-reading; report with the message id / link.

## Hard Stops

Stop and ask instead of improvising when:

- `401` — credential is dead. Don't hunt for alternative tokens.
- A public-facing write hasn't been approved — including "small" edits to something already published.
- Repeated `429` — back off and report; don't hammer.
- The primary route is `403` — surface it; use only the documented fallbacks.
- The target is ambiguous (which channel, user, message?) — confirm; never guess IDs.

## Compliance & Hygiene

- User-token automation ("self-botting") is against Discord's ToS. Keep it personal, low-frequency, read-mostly; no mass actions, no automated outreach, nothing spam-shaped.
- Token hygiene: never echo it into chat, logs, commits, or notes. If a Path A token is to be kept between runs, store it only in `<skill dir>/.state/token` (`0600`, after asking once); a browser session follows `references/session-persistence.md`. Deleting either does not invalidate the token — the user revokes it by logging out of that session or changing their password.

## Reference Routing

- `references/discord-api-endpoints.md` — the full endpoint catalog (extracted from `olivier-motium/discord-user-mcp` + field-verified additions).
- `references/browser-session-details.md` — tool-agnostic browser path: DOM hooks, composer fallback, storage pitfalls, virtualization.
- `references/browser-tool-setup.md` — what to do when you have no browser tool (or no way to load the session): text setup instructions, no hardcoded paths.
- `references/session-persistence.md` — where the session lives between runs: the browser's persistent profile first, `.state/` inside this skill otherwise.
- `.gitignore` — ignores `.state/`, the only place this skill writes session material.

## Provenance

Endpoint set extracted from `olivier-motium/discord-user-mcp` (`src/client.ts`), 2026-09-11; additions verified live the same day (thread rename limits, forum id equality, token retrieval paths, snowflake math).
