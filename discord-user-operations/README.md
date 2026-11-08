# Discord User Operations

[English](./README.md) | [简体中文](./README.zh-CN.md)

Discord User Operations is a skill for reading, searching, and writing on Discord as a regular user account.

## What It Does

- reads servers, channels, forum threads, and message history
- searches server messages by content, author, channel, and date range
- replies to threads, edits and deletes your own messages
- adds reactions, reads pinned messages, and handles DMs
- works only through a logged-in browser session: every API call is emitted by the
  real browser, so the request carries the client identity Discord expects
- ships no direct-HTTP path, because calling the API with a copied token from a
  shell client gets the account flagged
- documents the REST API mechanics that matter: authentication, snowflakes, rate limits, and error semantics
- ships **no code**: every environment-dependent choice is written as a decision for the agent

## Installation

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s discord-user-operations
```

## Requirements

- **A browser session:** a browser tool you can drive that reaches a logged-in
  Discord session — navigate, evaluate JS, and either the user's own logged-in
  profile or a way to inject their stored session. The agent decides whether it
  has one from its own toolset; when it does not,
  [`references/browser-tool-setup.md`](./references/browser-tool-setup.md) explains
  how to stand one up (CloakBrowser kernel behind Playwright MCP, with the storage
  tools this path needs) — as instructions to adapt, not a script to run.
  **No HTTP client and no token-in-a-shell variant is supported**; see
  [`references/account-safety.md`](./references/account-safety.md) for why.
- **Authentication:** either log in inside that browser — best when the host can
  show a QR code and its egress looks ordinary — or, when the login screen is
  hostile (headless server, datacenter IP, CAPTCHA), log in on your own browser
  and hand over the token from an API request header. Either way the token is
  only ever used from a `discord.com` page; see
  [`references/token-handoff.md`](./references/token-handoff.md).
- **Keeping the session between runs:** a browser with a persistent profile keeps
  it. Otherwise the agent, after asking once, saves it to `.state/` inside this
  skill's directory (ignored by git, files `0600`) and restores it from there —
  see [`references/session-persistence.md`](./references/session-persistence.md).
  Session material is written nowhere else.

## When To Use It

Use this skill when you want to:

- browse Discord servers and forum threads as yourself
- read channel history or search for specific messages
- reply to a thread, or edit something you posted
- add a reaction, check pinned messages, or handle a DM
- handle small, personal Discord tasks through your own account

## How To Use It

1. Sort out authentication: log in inside the agent's browser, or hand over a
   token taken from your own browser's Network panel (never through the chat).
2. Provide a target:
   - a server, channel, or thread
   - a message to reply to or edit
3. Say what you want:
   - a read or a search
   - a drafted reply or edit
   - a reaction, a pin lookup, or a DM
4. For anything visible to others, review the exact content before it is sent.
5. After a write, re-read the target to verify the result.

## Example Requests

```text
Read the latest messages in this channel and summarize them.

Search this server for messages about the launch from the last week.

Draft a reply to this thread and post it once I confirm.

Edit my last message to fix the wording.
```

## Notes

- Built for personal, low-frequency, read-mostly use — not bulk actions or automated outreach.
- User-token automation sits in a gray area under Discord's Terms of Service: keep it considerate.
- Do not drive the API from a script or a shell client with a copied token. That
  route is not "faster": it lacks the browser's client identity and gets the
  account warned, locked behind a forced password reset, or worse. The browser
  session is the only supported transport.
- Anything visible to others requires explicit confirmation before it is sent.
- Treat your token like a password: never paste it into chats, logs, or commits.
- Deleting `.state/` does not invalidate a saved session; log out of that session in Discord to revoke it. Reinstalling the skill can delete `.state/`, which means logging in again.

## Credits

The REST endpoint catalog draws on [olivier-motium/discord-user-mcp](https://github.com/olivier-motium/discord-user-mcp) (MIT).

## License

MIT
