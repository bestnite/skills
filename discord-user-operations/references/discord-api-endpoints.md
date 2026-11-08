# Discord REST API — Endpoints for User-Account Operations

Base: `https://discord.com/api/v10` (docs version; the web client uses `/v9` — both serve these routes).
Auth: `Authorization: <user token>` — raw token, no prefix. Writes: add `Content-Type: application/json`.
All IDs are snowflakes (strings — never numeric-parse). `204` = success, no body.

**Transport:** every call on this page is issued as an in-page `fetch()` from a
`discord.com` page in the user's logged-in browser session. Do not replay these
routes from a shell client or a local script — that is what gets the account
punished (`account-safety.md`).

Source: extracted from `olivier-motium/discord-user-mcp` (`src/client.ts`), 2026-09-11. Rows marked ✱ were added from live field verification the same day.

## Users

- `GET /users/@me` — current user; the standard auth/identity check.
- `GET /users/{user_id}` — user profile.

## Guilds & Members

- `GET /users/@me/guilds?with_counts=true` — servers the user is a member of.
- `GET /guilds/{guild_id}?with_counts=true` — server details (incl. `roles[]`, `member_count`).
- `GET /guilds/{guild_id}/channels` — all channels; filter by `type` / `parent_id`.
- `GET /guilds/{guild_id}/members/{user_id}` — one member (roles, nick, join date).
- `GET /guilds/{guild_id}/members/search?query={name}&limit={n}` — username → member; prefer exact match on `username` / `global_name` / `nick`, else first result.

## Channels & Messages

- `GET /channels/{channel_id}` — channel / DM / thread metadata (works for all three).
- `GET /channels/{channel_id}/messages?limit={n}&before={id}&after={id}&around={id}` — history. `limit` ≤ 100. `before`/`after`/`around` are mutually exclusive; page backward with `before=<oldest seen>`, forward with `after=<newest seen>`. Sort by id if you need chronological order across pages.
- `GET /channels/{channel_id}/messages/{message_id}` — single message.
- `POST /channels/{channel_id}/messages` — send. Body: `{"content": "..."}`; to reply: `{"content": "...", "message_reference": {"message_id": "..."}}`.
- `PATCH /channels/{channel_id}/messages/{message_id}` — edit your own message. Body: `{"content": "..."}`.
- `DELETE /channels/{channel_id}/messages/{message_id}` — delete your own message → `204`.

## Search

- `GET /guilds/{guild_id}/messages/search` — guild-wide message search. Query params:
  - `content` — substring match on text.
  - `author_id` — filter by author (resolve username → id first).
  - `channel_id` — limit the search to one channel.
  - `has` — one of `link` | `embed` | `file` | `sticker` | `sound`.
  - `min_id` / `max_id` — snowflake bounds (compute from dates).
  - `offset` — pagination (result pages of 25).
  - Response: `{"total_results": n, "messages": [[...], [...]]}` — the outer array contains *groups*; each group is an array of messages; take the group's middle message as the canonical hit.
- **403 fallback (search disabled in the server)**: scan a channel instead — walk `GET /channels/{c}/messages?limit=100&before=<cursor>` backward (first call: no `before`; cursor: oldest id seen), filter client-side by author / content substring, stop when past a `min_id` bound or at a page cap (e.g. 10 pages ≈ 1000 messages).

## Reactions & Pins

- `PUT /channels/{ch}/messages/{msg}/reactions/{emoji}/@me` — add your reaction. Emoji URL-encoded; custom emoji as `name:id`.
- `DELETE /channels/{ch}/messages/{msg}/reactions/{emoji}/@me` — remove your reaction.
- `GET /channels/{ch}/pins` — pinned messages.

## Threads & Forums

- `GET /channels/{ch}/threads/archived/public` — archived public threads of a channel.
- `GET /channels/{ch}/threads/archived/private` — archived private threads.
- ✱ Forum posts are threads: a forum channel's posts are thread channels; **the first message id of a thread equals the thread channel id**.
- ✱ `PATCH /channels/{thread_id}` `{"name": "..."}` — rename a thread / forum post title. **Max 100 characters** (102 → `400` 50035 `BASE_TYPE_MAX_LENGTH`; 95 → OK). A "renamed the thread" system message appears in-thread.

## DMs

- `GET /users/@me/channels` — list DM channels (with `recipients[]`).
- `POST /users/@me/channels` — open a DM with `{"recipient_id": "..."}`; returns the channel; send into it like any channel.

## Snowflakes & Dates

- `snowflake = (unix_ms − 1420070400000) << 22` (Discord epoch = 2015-01-01).
- `unix_ms = (id >> 22) + 1420070400000`.
- Examples (verified): `2026-09-01T00:00:00Z → 1544134695321600000`; `2026-09-10T00:00:00Z → 1547396186112000000`; `1547649194527948852 → 2026-09-10T16:45:21.907Z`.
- Compare IDs as strings / BigInt; zero-pad when comparing as numeric strings.

## Rate Limits & Errors

- `429` → body carries `retry_after` (seconds, may be fractional). Wait `retry_after` + small jitter; retry; max 3, then stop.
- Error body: `{"message": "...", "code": ..., "errors": {...}}`.
- Notable: `401` invalid token · `403` forbidden (permissions, or feature off for this route) · `404` unknown channel/message · `400` `code 50035` invalid form body — details in `errors.<field>._errors[].message`.

## Response Shape Cheatsheet

- **Message**: `id, channel_id, author{id, username, global_name}, content, timestamp, edited_timestamp, attachments[], embeds[], reactions[], message_reference{message_id}, referenced_message, type, flags`
- **Channel**: `id, type, guild_id?, name?, topic?, parent_id?, position?, last_message_id?, recipients[]?, thread_metadata{archived, auto_archive_duration, archive_timestamp, locked}?, message_count?, member_count?`
- **Guild**: `id, name, icon, owner, approximate_member_count?, description?, features[]` (+ `roles[]`, `member_count` on the detailed route)
- **Channel types**: `0` text · `1` DM · `2` voice · `3` group DM · `4` category · `5` announcement · `10` announcement thread · `11` public thread · `12` private thread · `13` stage · `15` forum.

## Recipes

Find replies to a message:

1. `GET /channels/{ch}/messages/{msg}` (original).
2. Page forward: `GET /channels/{ch}/messages?after={cursor}&limit=100`, cursor = last id of the previous batch; up to a page cap.
3. Keep messages whose `message_reference.message_id` equals the original; sort ascending by id; report chronologically.

Transport example — in-page `fetch()` from a logged-in `discord.com` page, which
is the only supported shape. A `curl` equivalent of this block is not a shortcut:
it is the account-flagging route (`account-safety.md`).

```js
// identity check
const me = await (await fetch('/api/v10/users/@me', { headers: { Authorization: token } })).json();
// read history
const r = await fetch('/api/v10/channels/' + CH + '/messages?limit=25',
  { headers: { Authorization: token } });
const msgs = await r.json();
// send
await fetch('/api/v10/channels/' + CH + '/messages', {
  method: 'POST',
  headers: { Authorization: token, 'Content-Type': 'application/json' },
  body: JSON.stringify({ content: 'hello' }),
});
```

## Out of Scope

- File attachments / uploads, webhooks, voice, gateway (websocket) events, OAuth2.
