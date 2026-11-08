# Browser Session Details (Tool-Agnostic)

How to operate Discord through a logged-in browser session using *whatever* browser automation your agent has. Read fast via the DOM; write via in-page `fetch` against the REST API (same-origin). API details: `discord-api-endpoints.md`.

## Session prerequisites

- The browser session must be authenticated (a logged-in persistent profile, or the storage state restored from `<skill dir>/.state/storage-state.json` — see `session-persistence.md`). Confirm by opening any `discord.com` page — the app shell shows the channel UI when logged in.
- Wait a few seconds after navigation before reading; the SPA renders asynchronously.

## Reading via the DOM (quick path)

Hooks that are stable enough in Discord web:

- Message rows: `li[id^="chat-messages-"]`
- Author line: `[id^="message-username-"]` (display name + role badges)
- Message body: `[id^="message-content-"]`
- Timestamps: `time[datetime]` (ISO 8601)
- A forum post / thread opens as its own channel — same structure as a text channel.

Pitfalls:

- The message list is virtualized: only what's near the viewport exists in the DOM. To load older content, scroll the message scroll container to top repeatedly with short waits (~0.5–1 s a time) until what you need appears or the top is reached.
- After any write, reload or re-query before reporting; never report from the optimistic UI.

## Getting the token (only needed for fetch headers)

- Page JS cannot read it. **Verified 2026-11-08** on an ordinary desktop browser at `discord.com/channels/@me`: `typeof localStorage` is `"undefined"` — absent, not merely empty. Don't spend calls probing storage.
- The token comes from the user, captured in their own browser: DevTools → **Network** → any `api/v9/...` request → **Request Headers** → `authorization`. Full procedure, handoff hygiene, and risk notes: `token-handoff.md`.
- A context-level storage export may still contain a legacy `token` or `tokens` entry (`tokens` is a JSON object keyed by user id; `token` may be JSON-quoted — unwrap it when `JSON.parse` yields a string). Treat that as a bonus, never as the expected path, and never as proof that the session is alive.
- Sanity check: a user token is three dot-separated segments.
- Handle it as a password: never print it, never paste it into chat or logs, and delete the handoff file when the work is done.

## Writing via in-page fetch (preferred)

- Run the `fetch` inside a page whose origin is `https://discord.com` (same-origin ⇒ no CORS complications), with `Authorization` and `Content-Type: application/json` headers.
- Sequence: token → read-only preflight (GET `/users/@me` or the target message) → write → re-read to verify.
- If your tooling loses context between tool calls (element handles detach, edit state drops), do the whole sequence **in one call / script** rather than stepwise.

## UI fallback (only if fetch is impossible)

- Composer: `div[role="textbox"][contenteditable="true"]` — several can exist (search bar etc.); pick the one in the message area.
- Clear: Ctrl+A, Backspace. Type. Enter sends.
- Edit mode hint text: "Enter to save • Esc to cancel".
- Expect fragility: hover-revealed controls are rebuilt every time; never loop a failing click — switch approach.

## Field notes

- Non-critical console noise is normal (e.g. an occasional `429` on a telemetry endpoint) — ignore anything that doesn't affect your task.
- Keep the working tab on the target channel; navigating away mid-flow can drop editor state.
- The Discord UI is localized (e.g. Chinese labels such as 编辑 / 删除 / 重命名帖子标题); match by stable ID attributes rather than visible label text where possible.
