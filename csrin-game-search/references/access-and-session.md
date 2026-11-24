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

### The token is bound to the client that obtained it

A `securitytoken` minted by one client is rejected when replayed from another: a pasted cookie set containing someone else's `securitytoken` answered 401 from this machine. Mint your own token instead and carry over only the phpBB cookies (`csrinru_phpbb3_*`) from the user — that combination authenticated on the first request, then expired as described below.

## What a session changes

| | Anonymous | Logged in |
|---|---|---|
| `viewtopic.php`, `viewforum.php` | 200 | 200 |
| Links in post bodies | replaced by `[[Please login to see this link.]]` | real anchors |
| `search.php` | works, flood-limited | works, larger quota |
| `f=22 Steam Content Sharing` | "Please register or log in to view this forum." | readable |
| `feed.php` | 200, links masked | 200, links masked |

`f=22` hides its whole subtree from anonymous clients, and `viewtopic.php?t=<id>` for a topic inside it answers `The requested topic does not exist` — the same answer a deleted topic gives, so the two are indistinguishable without a session. Do not conclude a game has no clean-files thread until you have looked with a session.

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

> End-to-end login with a username and password was not exercised in this verification run — the cookie path was. Treat the field list as read from the live form, and expect an extra hidden field (a form token) if the board ever hardens the login form; when that happens, read the form and copy every hidden input rather than guessing.

## Cookie formats the user may hand you

1. **Header string** — `csrinru_phpbb3_u=...; csrinru_phpbb3_k=...; csrinru_phpbb3_sid=...`, usually pasted from the browser's cookie panel, semicolon-separated, unordered.
2. **`Cookie:` header dump** — same content, possibly with `securitytoken` and `securitytoken_expiration` included.
3. **Netscape cookie jar** (`cookies.txt`, tab-separated) exported by a browser extension.

Normalise all three to the same two things: your own fresh `securitytoken` pair, plus every `csrinru_phpbb3_*` value the user supplied. Drop anything else.

## Sessions are short-lived; verify before promising

Observed in one run: the same pasted cookie set answered as a logged-in user on the first request and as a guest minutes later — the board had set `csrinru_phpbb3_u=1`, `_k=` (empty) and a new `_sid`, i.e. it discarded the session. Likely causes are server-side IP/browser validation or the user's own browser rotating the session, and neither is something the skill can control.

Consequences for the workflow:

- **Verify the session with the first request**: fetch `index.php` and look for `ucp.php?mode=logout` (logged in) versus `ucp.php?mode=login` (guest). Do not infer the state from the absence of an error.
- If the first request is already a guest, the cookie is stale — say so and ask for a fresh one instead of silently degrading to anonymous and reporting masked links.
- Do not retry a dead cookie. A session that answered as a guest will keep answering as a guest.

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
