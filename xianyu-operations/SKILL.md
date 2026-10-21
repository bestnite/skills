---
name: xianyu-operations
description: "Use when reading or writing Xianyu/Goofish (闲鱼): search, item detail, own listings, chats, publish, message."
---

# Goofish / Xianyu Browsing

Access to Xianyu (闲鱼, Goofish), Alibaba's second-hand marketplace: keyword search,
item detail, your own listing list and IM chat list — and, under the rules in
"Writes", publishing listings, taking them down and sending messages.

There is **no official open API and no OAuth app registration**. Access is a
logged-in browser session, and **every request is issued by the browser you
already have open on the site** — never as a bare HTTP client from the agent's
machine. Two read shapes, both inside that one browser:

| Shape | How | Good for |
|---|---|---|
| Rendered DOM | navigate `https://www.goofish.com/search?q=…`, read cards out of the page | keyword search (the page is client-rendered) |
| In-page `fetch()` | sign the URL on the host, then call **`fetch()` inside the page** | item detail, own listings, chat list, any named internal endpoint, the publish/delete writes |

**Why the browser must issue the call, not the host.** Measured on a real
account (2026-09): the same signed read call, same session, same payload —

| Issued from | Result |
|---|---|
| host HTTP client (`urllib`/`curl`/`requests`) | 11 calls fine, then `FAIL_SYS_USER_VALIDATE` + `RGV587_ERROR::SM::哎哟喂,被挤爆啦` at call 12 |
| `fetch()` inside the open page | 12/12 `SUCCESS::调用成功` |

The mtop endpoint is not "unusable over HTTP" — it accepts a well-formed signed
request either way, which is exactly what makes the failure hard to read: the
block arrives a dozen calls in, as risk control, and looks like a session
problem. Driving the request from the page carries the browser's full fingerprint
and same-origin context, and it is the difference between the two rows above.
Signing is still host-side arithmetic; only the **send** moves into the browser.

**Language:** every string in this skill — instructions, examples, and the
wording suggested for asking the user — is English so the skill stays usable by
any audience. Talk to the user in their own language and translate as needed;
nothing here requires English output. The only Chinese kept verbatim is literal
site text (risk-control markers) and the platform's own name, because those must
match what the site prints.

## What ships here, and why it is only that

- `templates/mtop_request.py` — a copy-and-adapt template: session cookies + api +
  data in, **a signed URL and form body out** — ready to paste into `fetch()`
  inside the page. Standard library only, and nothing happens behind your back:
  it makes no network request at all, and it does not probe your environment.
- `templates/publish_item.py` — listing publication: the payload assembly for the
  publish call (title/desc/images/price/delivery + the category and location the
  server returns), because those ~20 nested field names must be exact.
- `templates/im_send_message.py` — chat messages, which travel over a WebSocket and
  not HTTP: the LWP frame sequence, with the parts only you can know marked.
- Everything else is text: which endpoint answers which question, where the
  response fields live, how to inject the session into your browser tool, how to
  search and fetch through that browser, how to tell a live session from a dead
  one, how to stand up a browser tool if the user has none, and the rules that
  govern writes.

The split is deliberate, and worth preserving when editing this skill: **code
only for the arithmetic that must be byte-exact every time; prose for everything
that depends on the environment or on judgement.** A script that probes the
machine, checks whether a browser exists, or verifies login state would be
usurping decisions the agent is better placed to make — it can see its own
tools, and it can open a page. Keeping the code narrow is what lets this skill
work on setups nobody anticipated.

It is a **template rather than a finished tool with parameters** for the same
reason. A fixed interface has to guess where your cookies live, which browser you
drive, and how you retry; a snippet you edit has to guess nothing. Copy it,
change the marked lines, run it.

## Workflow

**1. Establish the session — in the browser.** Xianyu needs a logged-in browser
session; the credentials are the site's own session cookies (`unb` and
`_m_h5_tk` at minimum). A browser tool with a persistent profile keeps them
between runs; otherwise restore `.state/storage-state.json` (see "Handling the
session cookies"), or put a fresh jar into the browser via whatever mechanism it
has (a cookie-setting tool, a storage-state file, CDP `Network.setCookie`, or a
profile the user already logged into). Then confirm by
**looking at the page**, not by calling an endpoint: open
`https://www.goofish.com` and check for the account's own nickname.

A **read-only mtop call is the reliable session test** when the page is
ambiguous (the site's header can keep rendering a `登录` control even with valid
cookies injected, so "the header says log in" is not proof either way). Sign any
read call and run it in-page; `SUCCESS::调用成功` means live, and the strings in
`references/mtop-apis.md` mean expired or risk-blocked.

**2. Search through the page.** Navigate to the search URL and read the cards
from the DOM — `references/browser-search.md` carries the extractor and the
steps.

**3. Everything else: sign on the host, fetch in the page.** Take the signed URL
and body from the template (or write the two lines yourself — the algorithm is
below), then execute it with `fetch()` inside a page you already have open on
`www.goofish.com`. Same cookies, same origin, no CORS question, and the browser's
fingerprint comes along. `references/mtop-apis.md` lists the endpoints, their
payloads, the field paths, and the exact `fetch()` form.

**4. If you do not have a browser tool**, say so and ask the user for one rather
than improvising. `references/browser-tool-setup.md` is written as instructions
you can hand over or follow — including a CloakBrowser + Playwright MCP recipe,
and what to report when it does not work. Do **not** fall back to calling the API
from the host: see the measurement above for what that costs.

## Signing a request

Copy `templates/mtop_request.py` next to your work, adapt the three blocks marked
`# EDIT` — where the cookies are, which api and payload, and the in-page `fetch()`
snippet it prints — then run it with whatever Python is available. Read it before
running it: it is a starting point, not an interface, and the parts you change are
the parts only you can know.

If you would rather write the call yourself, the whole algorithm is two lines:

```
sign = md5( <_m_h5_tk up to the first "_"> & t & 34839810 & data )
```

- `t` = millisecond timestamp string; `34839810` is the Xianyu web appKey.
- `data` = the JSON payload, serialised compactly (no spaces) — that exact string
  is what gets signed.
- `_m_h5_tk` is `<token>_<timestamp>`; only the part before the first `_` is
  signed.

**Which `_m_h5_tk` to sign with — read it from the browser, not from a file.** A
jar can hold **more than one** `_m_h5_tk` for the same API host (the site sets
them on both `.goofish.com` and `.taobao.com`, and both are sent to
`h5api.m.goofish.com`). Only one is the live signing token; signing with the
other returns `FAIL_SYS_ILLEGAL_ACCESS::非法请求`. So:

- take the token from the browser's own cookie jar for the API host — i.e. the
  cookies the browser will actually attach — not from a hand-assembled string;
- `ILLEGAL_ACCESS` means wrong token, **not** risk control. Try the other
  `_m_h5_tk` before concluding anything about the session or the account.

**Token rotation:** the server hands out a fresh `_m_h5_tk` on most responses.
Read it from the browser's live jar every time — never cache the token in your own
state. If a call returns a token-expired `ret`, the same response already carried
the replacement: update the jar and retry once, then stop.

## Writes

Publishing a listing, taking one down, and sending chat messages are all covered —
`references/write-operations.md` carries the recipes and `templates/` carries the
two payload/socket builders. Three rules come with them, and they are not
optional:

1. **Explicit user approval for the exact content before every write.** Draft the
   title/description/price, or the message text, show it to the user, wait for a
   yes. Nothing visible to others goes out because you decided it should.
2. **Human pacing — roughly one write per minute, and at most one session writing
   at a time.** The upstream project ships exactly that as its default limiter plus
   a 10-minute circuit breaker on risk-control keywords; treat it as the floor.
3. **Verify by reading back.** A `SUCCESS` ret or an ack `code=200` means the
   server accepted the request, not that the listing is live or the message was
   delivered. Re-read, then report what you actually see.

Never blind-retry a write: a failed attempt may have half-landed (images uploaded,
listing created without a price, message sent with a late ack). Read first.

## When to Use

- Look up Xianyu item details or prices by item id.
- Search listings by keyword (market prices, competitor listings, "is anyone
  selling this service" checks).
- Read your own listings or chat/session list.
- Any task where the answer lives in Xianyu's data and the user provides a session.

**Don't use for:**

- Writes without the user's explicit approval for the exact content. Publishing
  and messaging are supported — see "Writes" — but nothing visible to others goes
  out on your own judgement, and nothing here does bulk or automated outreach.
- Anything without a logged-in session: Xianyu gates search and detail behind
  login, and anonymous requests get a login wall instead of data.

## Handling the session cookies

Required: **`unb`** and **`_m_h5_tk`**. Missing either means every request is
treated as signed-out. Useful extras: `cookie2`, `_tb_token_`, `sgcookie`, `cna`.

Where the jar lives between runs follows `references/session-persistence.md`:

1. **A browser tool with a persistent profile** keeps it — write no file, because
   that profile is exactly what the in-page `fetch()` sends.
2. **Otherwise** save the tool's storage export to
   `<skill dir>/.state/storage-state.json` (after asking once) and restore it from
   there next run. Nothing session-related is written outside `.state/`.

Other per-account state goes in the same directory: the IM device id in
`.state/device-id` and a cached IM access token in `.state/im-token` (see
`templates/im_send_message.py`).

**Security:** the jar is a live account session. Keep it out of chat logs and out
of the conversation; files under `.state/` are `0600`, created that way. Deleting
`.state/` does not end the session — tell the user they revoke it from the Xianyu
app ("log out of all devices").

## Pitfalls

- **A host-side HTTP client is not a supported transport.** Under a burst it gets
  `RGV587` while the same call in-page does not (measured, see the table at the
  top). If you catch yourself reaching for `curl`/`requests` because it is easier,
  that is the failure mode this skill exists to prevent.
- **`ILLEGAL_ACCESS` is a signing/token error, not risk control.** The jar can
  carry two `_m_h5_tk` values for one host; the wrong one produces exactly this.
  Do not report "blocked" or "session dead" on an `ILLEGAL_ACCESS` — retry with
  the other token.
- **The header's `登录` control is not a session indicator.** With valid cookies
  injected via a tool, the page's own header can still render the logged-out
  control. Verify with a read call's `ret`, or by a surface that truly gates on
  login, rather than by that text.
- **`baxia` in the page source is not a risk-control hit** — it is Alibaba's
  anti-bot JS library and appears on every page. Real markers:
  `哎哟喂`, `RGV587`, `FAIL_SYS_USER_VALIDATE`, `/punish`, or visible page text
  like 验证码 / 安全验证 / 异常访问 / 请先登录.
- **Field paths are nested deeper than expected.** Item data lives under
  `data.itemDO` (title, soldPrice in yuan, desc, itemStatus, `skuList[].price` in
  fen), the seller under `data.sellerDO.nick`. `data.trackParams` carries only
  `itemId` — reading `trackParams.title` yields nulls.
- **Search selectors are internal class names** (`row1-wrap-title`,
  `row2-wrap-cpv`, `price-wrap`) and drift between releases. When a search returns
  zero cards, check the page text for a login wall or a verification page before
  blaming the selectors.
- **Search pages by clicking the right arrow, not by changing the query
  parameter** — the page owns its pagination. Scrolling and re-extracting is the
  release-stable approach.
- **Rate and risk limits:** the IM-token endpoint
  (`mtop.taobao.idlemessage.pc.login.token`) is the most heavily guarded; the
  upstream project's own notes say frequent calls trigger `RGV587`. Read-type item
  and search calls are far more forgiving, but keep everything human-paced.
- **Writes are where accounts get limited or banned.** They are supported here,
  but only under the approval/pacing/read-back rules above. The IM token endpoint
  (`mtop.taobao.idlemessage.pc.login.token`) is the single most guarded call in the
  API surface — fetch it once and cache it rather than per message.

## Files

- `templates/mtop_request.py` — copy, adapt, run: signs an mtop request and emits
  the in-page `fetch()` snippet.
- `references/mtop-apis.md` — verified endpoints, payloads, response fields,
  error codes, the `fetch()` form, and account-risk notes.
- `references/browser-search.md` — the search extractor and the browser steps, as
  text, for whichever browser tool you have.
- `references/write-operations.md` — publish / delete / message recipes, the
  WebSocket sequence, and the rules that govern them.
- `references/browser-tool-setup.md` — how to stand up a browser tool when the
  environment has none.
- `references/session-persistence.md` — where the session lives between runs: the
  browser's persistent profile first, `.state/` inside this skill otherwise.
- `.gitignore` — ignores `.state/`, the only place this skill writes session
  material.
- `templates/mtop_request.py`, `templates/publish_item.py`,
  `templates/im_send_message.py` — copy, adapt, run.

API names, request shapes, and the search extractor were cross-checked against the
upstream project
[`fancyboi999/goofish-cli`](https://github.com/fancyboi999/goofish-cli) (Apache-2.0);
this skill does not depend on it at runtime.
