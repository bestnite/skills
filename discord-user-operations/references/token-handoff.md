# Token Handoff — A Session Without Logging In

Sometimes the agent's browser cannot log in at all: it runs on a headless server,
from a datacenter IP, behind a host that cannot display a QR code to the user's
phone, or the login form answers with a CAPTCHA the agent cannot solve reliably.
In that situation the user logs in **on their own browser** and hands the agent a
token, which the agent then uses from inside its own browser page.

This page covers that handoff: how to obtain the token, how to move it without
leaking it, how to use it, and what it costs in account risk.

## Why the obvious export no longer works

**Verified 2026-11-08** on a normal desktop browser, logged in at
`discord.com/channels/@me`: page JavaScript sees no storage API at all.

```js
typeof localStorage   // → "undefined"   (not empty — absent)
```

So the long-standing recipe — read the `token` key out of
`https://discord.com`'s localStorage — returns nothing on the current web client,
and any tool that only exposes page JS is blind to it. A context-level storage
dump may still contain a legacy `token` or `tokens` entry from an older login; do
not rely on it, and never treat its absence as "not logged in".

## Getting the token

**Primary: the `authorization` request header.** Every API call the web client
makes carries the token in that header, and DevTools shows it.

1. Log in at `https://discord.com/channels/@me` in the user's own browser.
2. DevTools → **Network** → filter `api/v9`.
3. Trigger traffic (switch a channel, open a message).
4. Pick any `api/v9/...` request → **Headers** → **Request Headers** →
   `authorization`. The value is the user token: three dot-separated segments.

**Fallback: a context-level storage dump.** If the browser tool can export
storage state, look for a `token` or `tokens` entry under the
`https://discord.com` origin. `tokens` is a JSON object keyed by user id; `token`
may be a JSON-quoted string — unwrap it with `JSON.parse` when the parsed result
is a string. Only trust this when the dump came from a session that is currently
valid.

Do not extract the token from the desktop app's LevelDB unless the web route is
unavailable; it is slower, version-sensitive, and the header is always there.

## Handing it over

- **Never through the conversation.** Chat transcripts are persisted to session
  logs on disk and may be synced or cached by the host. A token in a transcript
  outlives the task that needed it. If the user offers to paste it, ask for a
  file instead, and say why once.
- Have the user write it to a file readable only by them:

  ```bash
  read -rs T && printf '%s' "$T" > ~/discord-token.txt && chmod 600 ~/discord-token.txt
  ```

  (`read -s` keeps it off the terminal echo; the file is `0600`.)
  `~/discord-token.txt` is a placeholder — any writable path the user can delete
  afterwards will do; the location is their decision, not the skill's.
- Move that file to wherever the automation actually runs — the same machine, a
  container, a remote host — with a filesystem copy, not by echoing it through a
  shell argument, an environment variable, or a tool call argument.
- Delete every copy when the task is finished. Deleting a copy does **not** end
  the session; see Revocation.

## Using it

The token authenticates an API call; it does not log the web app in. Do not try
to inject it into storage and hope the client picks it up — current builds read
no localStorage, so a restored storage state can leave the app on a login screen
while the token is still perfectly valid for the API.

Issue the call from a page whose origin is `https://discord.com`, so the request
inherits the browser's real client identity while the header supplies the
identity:

```js
// inside a page on https://discord.com
const me = await (await fetch('/api/v10/users/@me', {
  headers: { Authorization: token },
})).json();
```

Verify with `GET /users/@me` before anything else, then proceed with the normal
read recipes. Writes take the same shape with `Content-Type: application/json`.

**Pass the token per call.** Automation sandboxes commonly isolate each snippet:
`globalThis` does not survive between calls, and some expose neither `require`
nor `fs`. A token cached in a variable silently becomes `undefined` on the next
call, which surfaces as a confusing `401`. Inline it in the call that uses it, or
have the wrapper read it from the file at that moment — and do not print it.

## Account risk

A token minted on the user's home network and replayed from a datacenter host is
still a new device to Discord. It does not fail the way a shell HTTP client does
— the request comes from a real browser — but the account may receive a
verification email, a "new login" notice, or a challenge on a later call.

- Keep the work read-mostly and low-frequency, especially in the first hours.
- On any challenge, CAPTCHA loop, or forced reset: stop all activity and hand the
  account to the user (`account-safety.md`). Do not retry.
- A token bypasses 2FA by design. Treat the file as the account.

## Revocation

Deleting files and browser profiles does not end anything server-side. The user
revokes the token by changing their password (which invalidates every session) or
by logging out that session from Discord's device list. Say so when you ask for
the token, and remind them once the work is done.

## When logging in inside the agent's browser is the better path

If the agent's browser runs where a real login is plausible — the user's own
machine, or a host whose egress looks ordinary — logging in there is cleaner than
a handoff: the session is minted for that browser, nothing secret changes hands,
and a persistent profile keeps it. QR login exists for exactly this, but it is
time-boxed (a couple of minutes) and datacenter IPs frequently answer it with a
CAPTCHA. Choose the handoff when the login screen is hostile, and the login when
it is not.
