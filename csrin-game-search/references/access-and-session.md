# Access and session

Verified against the live board on 2026-11-24.

## The gate is a cookie handshake, not a bot wall

There is no Cloudflare, no CAPTCHA, no JS challenge to solve. A request without the right cookie gets an HTTP 401 page titled `CS RIN - Security check`, whose script does two things:

```js
document.cookie = "securitytoken=<32 chars>; path=/; secure";
document.cookie = "securitytoken_expiration=<unix seconds>; path=/; secure";
location.replace(newURL.replace(location.pathname, "/securitycheck" + location.pathname));
```

`securitytoken_expiration` is about 24 hours ahead of the moment of issue. Sending those two cookies back is enough — the redirect through `/securitycheck/<path>` is not required, and every page (`viewforum.php`, `viewtopic.php`, `search.php`) answers 200 with just the two cookies present. Confirmed by request: challenge, then the target page with only `securitytoken` + `securitytoken_expiration` set.

So the whole "anti-bot" surface is:

1. `GET https://cs.rin.ru/forum/` → 401, read `securitytoken` and `securitytoken_expiration` out of the HTML.
2. Retry the real URL with `Cookie: securitytoken=<token>; securitytoken_expiration=<exp>`.

A browser is not needed, and reaching for one costs minutes and a profile you then have to keep. Use a browser only when the user asks you to drive their existing logged-in browser session.

None of this is a reason to start without credentials. The handshake gets you a *guest* session that reads pages; it does not get you links. Ask for an account first.

### The token is bound to the client that obtained it

A `securitytoken` minted by one client is rejected when replayed from another: a pasted cookie set containing someone else's `securitytoken` answered 401 from this machine. Mint your own token instead and carry over only the phpBB cookies (`csrinru_phpbb3_*`) from the user — that combination authenticated on the first request, then expired as described below.

## What a session changes

Anonymous access is a diagnostic, never an operating mode: use it to understand why a request fails, not to run a task. The skill's workflow asks for a session up front (step 0 in `SKILL.md`) and does not search while it waits.

| | Anonymous | Logged in |
|---|---|---|
| `viewtopic.php`, `viewforum.php` | 200 | 200 |
| Links in post bodies | replaced by `[[Please login to see this link.]]` | real anchors |
| `search.php` | works, flood-limited | works, larger quota |
| `f=22 Steam Content Sharing` | "Please register or log in to view this forum." | readable |
| `feed.php` | 200, links masked | 200, links masked |

`f=22` hides its whole subtree from anonymous clients, and `viewtopic.php?t=<id>` for a topic inside it answers `The requested topic does not exist` — the same answer a deleted topic gives, so the two are indistinguishable without a session. Do not conclude a game has no clean-files thread until you have looked with a session, and do not start a task without one: every link a guest sees is a placeholder, so the search has to be repeated afterwards.

## Logging in

Form: `POST https://cs.rin.ru/forum/ucp.php?mode=login`

| Field | Value |
|---|---|
| `username` | account name |
| `password` | password |
| `autologin` | `on` to get a persistent `_k` |
| `viewonline` | `on` to appear online; omit to stay hidden |
| `redirect` | `index.php` |
| `sid` | the `sid` from the login page, with a valid `securitytoken` cookie alongside |
| `login` | `Login` |

On success the response sets `csrinru_phpbb3_u`, `csrinru_phpbb3_k`, `csrinru_phpbb3_sid` and redirects to the index. On failure it returns the login page with an error and no new `_u`.

Registration is open in principle, but this skill never creates an account: rate limits, ban lists and account recovery are the user's business, and an account is a credential the skill would then have to store.

Login with a username and password was exercised end to end on 2026-11-25: those fields, no hidden form token, and the response set `csrinru_phpbb3_u/_k/_sid` with the next request showing `Logout`. The account ended up as the same user the pasted cookie was failing for — which is the point: a login creates a session in the client's own network context. If the form ever gains hidden fields, copy every one of them from the page instead of guessing.

## Cookie formats the user may hand you

1. **Header string** — `csrinru_phpbb3_u=...; csrinru_phpbb3_k=...; csrinru_phpbb3_sid=...`, usually pasted from the browser's cookie panel, semicolon-separated, unordered.
2. **`Cookie:` header dump** — same content, possibly with `securitytoken` and `securitytoken_expiration` included.
3. **Netscape cookie jar** (`cookies.txt`, tab-separated) exported by a browser extension.

Normalise all three to the same two things: your own fresh `securitytoken` pair, plus every `csrinru_phpbb3_*` value the user supplied. Drop anything else.

## The session cookie rotates on every response

The board sets `csrinru_phpbb3_u`, `_k` and `_sid` on **every** response, and `_sid` changes each time — three consecutive guest requests produced three different session ids. A browser keeps working because it stores each rotation. A client that pastes one cookie header and ignores `Set-Cookie` authenticates on its first request and answers as a guest from the second on. That looks exactly like an expired cookie and is not: it is the client dropping the rotation.

So keep a jar and merge every `Set-Cookie` into it (`scripts/csrin_session.py` does this in `_absorb`). With the rotation followed, a live session stays live; without it, one request is all you get.

A pasted cookie can still be stale — the user's own browser rotated it after copying. Verify on the first response:

- `ucp.php?mode=logout` present → logged in.
- `ucp.php?mode=login` present, and the response set `csrinru_phpbb3_u=1` → the session row is gone; the cookie is dead.

If it is dead, ask for a fresh copy and use it immediately. Do not retry a dead set, and do not silently continue as an anonymous client while reporting masked links as results.

`memberlist.php?mode=viewprofile&u=<id>` also needs a session: anonymous clients get the login form. The join date and post count you need for judging an uploader are already in each post's author cell, so profile pages are an optional extra, not the primary source.

## A pasted cookie set often cannot be replayed

Three bindings were observed, and only one of them is the familiar "the cookie expired":

1. **The security token did not survive the move.** A token minted in the user's browser answered 401 from this host under four different user agents, while the same browser kept working with it. Something ties the token to the client that obtained it — the network address, or a one-shot handshake — and either way a pasted token is worthless from elsewhere.
2. **Guest sessions rotate `_sid` on every response** — three consecutive guest requests produced three different session ids. Any multi-request run must follow `Set-Cookie`, or it will look logged in once and anonymous afterwards.
3. **The replayed phpBB session was answered as a guest**: every attempt with the pasted `csrinru_phpbb3_*` set came back with `csrinru_phpbb3_u=1` and no error, under both the original and a fresh security token. A stale copy and a client-binding rule look identical from outside, and both produce the same guest page.

Consequence: cookie import is not portable. It works when the agent's requests leave from the same network as the browser, and it fails when they do not — a VPS, another VPN node, a container egress. In the failing case the run must say so rather than degrading to anonymous and reporting placeholders as results.

The reliable paths, in order:

1. **Credentials login from the client that will make the requests** (`ucp.php?mode=login`). The session is then born in the right network context, and the login form is the only path that does not depend on where the user's browser sits.
2. **Route the agent's requests through the browser's egress** (the user's proxy or VPN endpoint), then import the cookies.
3. **Have the user fetch the page themselves** and hand over the HTML — slow, but it needs no session at all.

Cheap test before promising anything: request `/forum/` with only the pasted `securitytoken`. A 401 means the token will not work from here — spent, expired, or minted elsewhere; retrying the full set will not help, and the answer is a login, not another paste.

## Session material lives in `.state/`

Write the cookie set to `.state/session.json` inside this skill directory, mode `0600`, and read `references/session-persistence.md` before the first write — it carries the full rules (ask once, gitignore, never print the value, deletion is the user's call).

## Mirrors and routing

- `https://csrin.org/` 301-redirects to `https://cs.rin.ru/forum`; it is an alias, not a separate site. Links inside feeds and pages are rendered against `csrin.org`.
- The board advertises a Tor onion service (`onion-location` header, `alt-svc` entry). Relevant only when the plain domain is unreachable; the same URLs and the same cookie names apply.
- The forum's own downtime thread (`t=93439`) is the authority on alternative domains. Read it rather than hunting for mirrors, because unofficial mirrors are exactly the malware risk the staff warn about.

## Failure decision table

| Symptom | Meaning | Action |
|---|---|---|
| 401 `CS RIN - Security check` | no valid `securitytoken` | run the two-step handshake |
| 401 after the handshake | token minted by another client, or expired | mint a new token |
| `ucp.php?mode=login` in the toolbar | not logged in | ask for a fresh cookie or credentials; do not report masked links as results |
| `Please register or log in to view this forum` | login-only forum (`f=22` etc.) | same |
| `The requested topic does not exist` | deleted topic, or one in a hidden forum | check with a session before reporting it gone |
| `Sorry but you cannot use search at this time` | search flood control | wait minutes; see `references/search-recipes.md` |
| Post links read `[[Please login to see this link.]]` | anonymous | the session is the fix; the link is not recoverable |
