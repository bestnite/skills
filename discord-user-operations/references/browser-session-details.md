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

- Do **not** try to read `localStorage` from page JS first: many stealth / isolated browser setups don't expose it at all (`window.localStorage` is `undefined`). Known dead end — don't burn calls on it.
- Instead use your tool's **context-level storage export** (the session / storage-state dump): look for the `token` entry under the `https://discord.com` origin's localStorage.
- The stored value may be JSON-encoded (a quoted string). Unwrap: `JSON.parse` it; if the result is a string, use it — otherwise use the raw value. Sanity check: a user token is three dot-separated segments.
- Manual alternatives (when designing a flow for a human operator): DevTools → Network → any request → copy the `Authorization` header; or extract from the desktop app's LevelDB storage.
- Handle the token like a password: never paste it into chat or logs, and never write it anywhere but `.state/` (`session-persistence.md`).

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
