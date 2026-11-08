# Account Safety — Why Calls Must Come From the Browser

Discord enforces against user-token automation. The transport you choose decides
how much of the account's real identity the request carries, and that is what
gets an account flagged. This page states the rule, the field evidence, and the
recovery when an account is already caught.

## What was observed

**Verified 2026-11-08.** Driving `discord.com/api` from a standalone HTTP client
with the account's user token drew a Terms-of-Service violation warning in the
Discord client and a forced password reset — the account was locked into the
reset flow, not merely warned. Treat that as the expected outcome of the route
rather than an unlucky draw. Which individual calls triggered it was not
isolated, so the rules below cover the whole route, reads included. That is why
this skill has no direct-HTTP path.

## The mechanism

A browser request to Discord carries, on every call:

- `X-Super-Properties` — base64 client metadata: client version, OS, browser and
  version, device class, release channel.
- Real `User-Agent`, `X-Discord-Locale`, `X-Discord-Timezone`, plus the origin,
  referer and cookie context that belong to the app shell.
- The browser's TLS ClientHello and HTTP/2 fingerprints, which are not settable
  from a script.
- An authenticated gateway (WebSocket) presence for the same session.

A shell client has none of these, or has invented values. A token whose requests
suddenly arrive with no super-properties, a scripting `User-Agent`, a mismatched
fingerprint, no gateway presence and machine-regular timing is not ambiguous to
the backend: it reads as credential replay. Rate limiting is not the enforcement
mechanism here — identity mismatch is.

An in-page `fetch()` from a `discord.com` page emits the request through the very
browser engine the site already trusts, so headers, fingerprint, cookie jar and
timing all match the logged-in client. That is the whole reason this skill reads
the API and not the UI while still being safe: the request is genuinely the
browser's.

## Rules

- **Never run a standalone HTTP client against Discord with a user token.** Not
  for a quick read, not "just this once", not to unblock a missing browser. The
  token's origin is the failure.
- **Never ask the user to paste a token into a shell, a script, an environment
  variable, or a request body.** The single acceptable destination for a
  user-supplied token is the browser session's own storage, so the browser — not
  a process you spawned — emits the calls. Their session in a browser is what
  makes the work possible.
- Do not route the browser's token into a sidecar process either — a local script
  holding it and proxying calls is the same failure with an extra hop.
- Driving the real browser removes the identity mismatch. It does not remove
  behavioural detection: bursting requests, hot-loop polling, uniform intervals
  and mass writes still get an account flagged. Keep the pace human and the
  posture read-mostly.
- A UI click and an in-page `fetch()` are equally safe from this angle. Choose
  between them on reliability, not safety.

## If the account is already flagged

1. **Stop all automation immediately**, including reads. Say plainly what was
   being attempted and which transport was used.
2. The user completes the forced password reset themselves. Do not attempt to
   continue around a challenge, solve it for them, or retry the old session.
3. A password reset invalidates sessions server-side, so a saved
   `.state/storage-state.json` is dead. Expect the next run to hit a login
   screen; the user logs in again and the storage state is re-exported
   (`session-persistence.md`).
4. Do not relaunch the failed approach after the reset. The account is now
   watched more closely, and the same mismatch is more likely to escalate.

## If a browser session cannot be obtained

That is a stop, not a reason to fall back. Options to offer the user: give the
agent a browser tool (`browser-tool-setup.md`), or run Discord themselves and
have the agent draft the exact content and API calls for them to execute. An
honest "no browser session available" costs a turn; the shortcut costs the
account.
