# Login and Session

How to authorize a Xiaohongshu browser session by QR code, and how to treat the
resulting session material. Login is an authentication exception to the read-only
business surface: it is an explicit state change the user authorizes, not a
business write, and not something to trigger automatically. The business reads in
`read-api.md` still require `guest: false`.

Observed on 2026-10-21 UTC (session date 2026-10-22) in an isolated guest browser
context, leaving the original authenticated context untouched. Live versus
source-only distinctions are in `verification.md`.

## Contents

- [Authorization and scope](#authorization-and-scope)
- [Bootstrap in a guest context](#bootstrap-in-a-guest-context)
- [Create a QR code](#create-a-qr-code)
- [Render the QR payload](#render-the-qr-payload)
- [Poll the QR state](#poll-the-qr-state)
- [Completion, geo routing, and handoff](#completion-geo-routing-and-handoff)
- [Polling budget and pending state](#polling-budget-and-pending-state)
- [Cookie and session strategy](#cookie-and-session-strategy)
- [Fallback: storageState in `.state/`](#fallback-storagestate-in-state)
- [Revocation](#revocation)
- [Secret handling](#secret-handling)
- [Verification status](#verification-status)

## Authorization and scope

- Login is an explicit authorized state change. If the user did not ask to sign
  in, ask before starting; do not trigger it from a business read failure.
- A business refusal (`401`, `403`, `406`) or a captcha is not a credential
  trigger. Do not switch into login, change headers, swap tokens, or retry because
  a business call failed.
- "No writes" in the skill covers business operations (publish, upload, comment,
  like, collect, reply). A login request is authentication, not one of those
  writes; it is still user-authorized and reported.
- If the browser is already logged in, reuse that session. Do not switch accounts,
  log out, clear storage, or replace the profile because a different account is
  requested.
- A different account gets a new dedicated browser context or profile. Keep the
  existing session intact.
- Default posture is one dedicated, user-authorized persistent profile for one
  account.
- The site's own login modal may poll by itself. Do not start a second infinite
  poll owner against it, and do not cancel the whole page's automatic flow. Keep
  at most one pending code per skill invocation or context.
- Associate every poll result with the `qrId` it belongs to. A manual code created
  while an older page code was still polling can observe the old code expire;
  never mix an old code's state with a new pair.

## Bootstrap in a guest context

The QR create and poll calls use the same webpack capture and registration
bootstrap as the business reads. A guest page does not need `guest === false`
first, and the route modules are the same. Do not hardcode module ids, export
names, or wrapper names; select the client by source string as in
`browser-session.md`.

- On a guest page the identity endpoint may return HTTP 200 with
  `code: -101, success: false`, or a later 200 with `success: true, guest: true`.
  That is the normal "no authentication yet" state, not a business `403` and not a
  reason to retry the identity call differently.
- Do not send the QR credentials or the pending code to the model as JSON. Keep
  the minimal pending state in the page namespace for the evaluate block, or in
  context-scoped state on the browser-tool side when the same evaluate call cannot
  wait for a human.
- Do not store credentials in globals across navigation.

## Create a QR code

```js
const qr = await client.post('/api/sns/web/v1/login/qrcode/create', {
  qr_type: 1,
});
```

Default `edith` host. Observed HTTP 200 with `success: true`.

Raw `data` fields: `qr_id`, `code`, `url`, `multi_flag`. Client-returned fields:
`qrId`, `code`, `url`, `multiFlag`. Check that `qrId`, `code`, and `url` are
present and are strings before using them.

- `url` is the QR **payload URL**, not a rendered image. Do not assign it to
  `img.src`, and do not call `page.goto(url)` expecting the page to display a QR.
- Keep `qrId`, `code`, and `url` out of logs, chat, commits, and any result
  object. They are short-lived login capability material.
- A QR image may be shown to the authorized user only as approved output; do not
  publish it to a shared or public host.
- If the code is refreshed, discard the old pair and treat the new code as a new
  epoch. Do not keep both.
- Do not fabricate or pre-send codes; a create call is the only source.

## Render the QR payload

The payload must be turned into a scannable image by an encoder that already
exists in the environment, or presented by the site itself.

- Preferred: a local QR encoder the user already has or has authorized. Do not
  add a third-party online QR service, and do not build a generic QR-encoder
  probe.
- Pure-interface flow is the priority: create the payload by API, render it with
  the environment's existing local QR encoder, then hand it to the user as a
  screenshot or attachment.
- Fallback: if the environment cannot render it, or the completion path is not
  verified, the site's official login QR is an explicit fallback. Show it in the
  same context and say that this is authentication presentation only, or ask the
  user to scan from the site. If the site owns the QR, use only its poll owner.
  Do not claim every environment is supported.
- A manual pair is independent: do not expect the site to auto-complete a
  manually created new pair.
- The site may already render the QR in its login modal. A screenshot of
  `.login-container .qrcode-img` is an **authentication presentation** exception,
  not business DOM scraping. It must show the same pair as the pending `qrId`; do
  not pair a site-rendered old code with a manually created new code.
- Write a temporary image only to an approved temporary location, and delete the
  exact owned artifact after expiry or completion.

## Poll the QR state

The live poll is not a GET status call. It is:

```js
const state = await client.post(
  '/api/qrcode/userinfo',
  { qrId: qr.qrId, code: qr.code },
  { transform: false, withCredentials: true },
);
```

Default `edith` host. The live call used camelCase `qrId` and `code`; preserve
those exact keys. Do not assume an alias such as `qr_id` is accepted.

- `transform: false` was the tested option; preserve it exactly. Its internal
  meaning was not verified, so do not state it as a fact and do not assume it
  changes response unwrapping. Treat the result as the actual client object; in
  loaded client source that business object is camelCase (`qrId`).
- The result is a business object with `codeStatus` and `result`.

| `codeStatus` | Meaning | Evidence |
|---|---|---|
| `0` | Waiting for scan | Live: polled successfully while pending |
| `1` | Scanned, awaiting mobile confirmation | Source only |
| `2` | Confirmed on the phone | Source only |
| `3` | Expired | Live: observed for an older page code still polling |

- `0` was observed live and is the normal pending state.
- `1` and `2` were only read from loaded client source; no real human scan was
  performed. Treat them as documented states, not as tested transitions.
- `3` was observed live for a stale code; when a poll returns it, discard that
  pair and stop polling it.

## Completion, geo routing, and handoff

A confirmed poll (`codeStatus: 2`) is not a completed login.

- If the source branch has a `geoZone`, it calls site geography routing and, when
  the current geo is suitable, a completion `GET /api/sns/web/v1/login/qrcode/status`
  with params `{ qrId, code }` and a `x-login-mode` header (for example the
  qrcode mode or an empty value). That completion path is **source-only**: it was
  not exercised over the network.
- When the source branch has no `geoZone`, its fallback emits `onLogin`; that is
  also source-only.
- Do not invent final cookie or "scanned success" values, do not substitute a
  country or `geoZone`, and do not create session token or cookie values.
- Recommended: after `2`, let the site's official flow complete activation and
  region routing (the UI owns the QR). A manual-only flow must be labeled as an
  authorized continuation that is not verified.
- On `geoZone`, activation, SMS, or captcha handoff, give control back to the
  user. Do not fake the result.
- After `2`, make a **new identity request in the same context** and require
  `guest: false` before reporting success. Do not announce a login from the poll
  state alone.
- No separate cookie export is needed to call business reads once the same
  context reports `guest: false`.

## Polling budget and pending state

- Poll no faster than every 2 seconds; this matches the observed UI source.
- Use a fixed client deadline (for example 4 minutes). That is a **client
  budget**, not a server TTL: no server expiry field was observed. Stop at the
  deadline; do not poll forever.
- Do not define every code as 4 minutes. A refresh needs explicit user
  permission, or a bounded reissue within the current task; a reissue discards the
  old pair and starts a new epoch.
- Associate state with the pair's `qrId` so a late result from an old code cannot
  be applied to the new one.
- Normal waiting for a human scan should pause the agent, not run a long busy
  loop. Use browser-side background polling or bounded multi-call checks, and
  yield to the user generically; do not bind the skill to a specific tool's
  "wait for user" name.
- Keep only minimal pending state. A local file is not the default transport for
  it, and QR credentials are never returned to the model as plaintext JSON.

## Cookie and session strategy

The shared rules — persistent profile first, `<skill dir>/.state/` otherwise,
consent, permissions, restore, revocation — are in `session-persistence.md`.
What follows is specific to Xiaohongshu.

Default: a user-authorized dedicated persistent browser profile, one account.

- The browser owns cookie and storage attributes: `Set-Cookie`, `Secure`,
  `HttpOnly`, `SameSite`, domain, path, and expiry are handled by the browser and
  the site's own JavaScript. Do not copy or reconstruct them by hand.
- `document.cookie` is neither complete nor recommended (it cannot see `HttpOnly`
  cookies). Do not rely on it as the session source.
- Do not manually copy session cookie values, and do not list sensitive cookie
  names unless truly necessary.
- A stable profile, kernel, and device environment can help session continuity,
  but this is not a binding guarantee and not anti-detection evasion.
- A profile may not survive every session cookie change or a site-side
  revocation. Run the identity check on every use; never promise a permanent
  login.

## Fallback: storageState in `.state/`

When the browser tool has no persistent profile, or the user explicitly asks for
a backup, export the session to `<skill dir>/.state/storage-state.json` as
`session-persistence.md` describes: ask once, create it `0600` from the start,
move it straight from the browser tool, never return its contents to the model.

- After a QR login that reached `guest: false`, that is the moment to save, so
  the next run restores instead of logging in again.
- On restore, the identity request with `guest: false` is the session check; a
  `guest: true` after restore means the user signs in again.
- Do not ship or run a host-side cookie parser or CLI; the browser tool writes
  and reads the file.

## Revocation

- A site logout invalidates the current session, and whether it invalidates the
  server side depends on the site.
- Deleting `.state/` or a local profile does **not** invalidate the server
  session. Revocation means the user logs out through the site's account/session
  or device management, then deletes `.state/`.
- Do not clear a shared browser profile or delete `.state/` without permission.
- Saving a session does not relax the ban on persisting raw responses. The
  `.gitignore` keeps `.state/` out of commits; it is not access control — the
  `0600` permissions are.

## Secret handling

- `qrId`, `code`, `url`, data URLs, cookies, and storage-state contents are
  credentials. Never log, print, commit, or return them as plaintext.
- A QR image may be shown to the authorized user as approved output only.
- Temporary QR images go to an approved temporary location and are cleaned up
  after expiry or completion.
- Do not export the session to call business reads; the same context is enough.

## Verification status

- Live: guest bootstrap, QR create with `success: true`, pending `codeStatus: 0`,
  expired `codeStatus: 3` on a stale page code.
- Source only: `codeStatus: 1`, `codeStatus: 2`, the `geoZone` branch, and the
  completion `GET /api/sns/web/v1/login/qrcode/status`.
- Not verified end to end: a real human scan, the full activation loop, SMS or
  captcha handoff, persistence across sessions, and a `.state/` storageState
  restore.
- Details and gaps: `verification.md`.
