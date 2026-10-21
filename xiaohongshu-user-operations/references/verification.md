# Verification and Limits

What was verified, when, how, and what remains unknown. Read this before
presenting any endpoint as "supported" or any field as guaranteed.

## Date and environment

- **Verified on 2026-10-21 UTC** in an authenticated PC web session. The writing
  session date was 2026-10-22.
- Browser page: `https://www.xiaohongshu.com`, initialized app shell.
- Transport: the site's own initialized HTTP client, driven from the page. No
  host-side HTTP client was used for the endpoint checks.
- Authentication: a user-authorized browser session; credentials were handled by
  the user's browser tooling. This work wrote no cookie file.
- Login checks used an isolated, unauthenticated browser context (`1440` viewport)
  opened on `www.xiaohongshu.com`. The original authenticated context was left
  untouched and the isolated context was closed afterwards.
- Raw responses were not saved. No real user ids, note ids, comment ids,
  `xsec_token` values, request context ids, personal URLs, or cookies are part of
  this skill.

## Method

1. Open an authenticated `www.xiaohongshu.com` page.
2. Bootstrap the site's client by the webpack chunk/require route described in
   `browser-session.md`.
3. Call each endpoint through `client.get` / `client.post`, using target ids and
   tokens already present in the observed page context.
4. For each endpoint, confirm a **new network response** of HTTP 200 with
   `success: true`, then inspect the business payload.
5. For paginated endpoints, make at least one next-page request where a cursor
   existed, and record whether the page size matched `num`.
6. For the search host, confirm the `so` `baseURL` call reaches the endpoint from
   a page that is not the search results page.

All 16 endpoints were called at least once through the existing client/wrapper
surface, and each produced a new HTTP 200 response with `success: true` in the
observed session. That statement is about network success and payload shape; it
does not mean every field, every page, or every permission state was exhausted.

The availability of a client wrapper for an endpoint was used only as evidence
that the underlying client call contract is reachable. The skill does not depend
on wrapper exports or their names; it calls the client paths directly.

The QR login checks reused the same bootstrap in the isolated guest context: the
create and poll calls went through the same source-selected client, with no
hardcoded module id, export, or wrapper name, and without a `guest === false`
precondition.

## Endpoint coverage

| # | Endpoint | Observed call | Sample / limit |
|---|---|---|---|
| 1 | `GET /api/sns/web/v2/user/me` | No params | `guest: false`; identity fields present |
| 2 | `GET /api/sns/web/v1/user/selfinfo` | No params | Own profile, interactions, public tabs |
| 3 | `GET /api/sns/web/v1/user/otherinfo` | Target id + token + `pc_note` source | Public profile; `tabPublic.collection: false` in sample |
| 4 | `GET /api/sns/web/v1/user_posted` | `num: 10` + cursor | Self: 5, no next; other: 12 then 10; `num: 30` also succeeded but necessity unproven |
| 5 | `GET /api/sns/web/v2/note/collect/page` | `num: 30` + cursor | Self: 3, no next-page sample |
| 6 | `GET /api/sns/web/v1/note/like/page` | `num: 30` + cursor | Self: 10 + 10; page size ignored `num` |
| 7 | `POST /api/sns/web/v1/homefeed` | Observed context body | 27-item next batch; `cursor_score` copied; mixed item models |
| 8 | `POST /api/sns/web/v2/search/notes` | `so` host + active context ids | Pages 1 and 2; mixed note/recommendation items; 21/22-item pages |
| 9 | `GET /api/sns/web/v1/search/filter` | Keyword + `search_id` | Filter metadata; one filter combination exercised |
| 10 | `POST /api/sns/web/v1/feed` | Note id + note token | Image-text and video; `media_v2` JSON string; no subtitles |
| 11 | `GET /api/sns/web/v2/comment/page` | Note id + cursor | 10 then 2, `has_more: false` on page 2 |
| 12 | `GET /api/sns/web/v2/comment/sub/page` | Root id + cursor | 1 reply, `has_more: false`; no multi-page sample |
| 13 | `GET /api/sns/web/unread_count` | No params | Counts returned; direct reads did not clear them |
| 14 | `GET /api/sns/web/v1/you/mentions` | `num` 10/20 + cursor | Paged without overlap; `num: 5` not tested here |
| 15 | `GET /api/sns/web/v1/you/likes` | `num` 5/10/20 + cursor | Paged; numeric cursor precision trap confirmed |
| 16 | `GET /api/sns/web/v1/you/connections` | `num` 5/10/20 + cursor | Paged; `user` object observed; `userInfo` not established here |

## What the samples established

- **Bare fetch is not usable.** A plain in-page fetch to
  `https://edith.xiaohongshu.com/api/sns/web/unread_count` with
  `credentials: 'include'` returned HTTP 406 and `{code: -1}`. The same endpoint
  through the site's client returned HTTP 200 with `success: true` and carried
  `x-s`, `x-t`, `x-s-common` headers. The client generates them; no manual
  signing is documented or allowed here.
- **The client is reachable from the page types exercised.** It was called from
  pages other than each endpoint's business page, including a notification page
  for the search host call. That is not a blanket guarantee that every page type
  can serve every API. Search reads still need an existing search context from the
  user's normal search surface.
- **The client return is business data, not a transport response.** It is
  camelCased (`userId`, `hasMore`, `xsecToken`) and has no axios/`Response`
  wrapper. `.json()` is not applicable.
- **Search needs its own host and context.** `so.xiaohongshu.com` with
  `baseURL`, `withCredentials: true`, `transform: true` worked. `search_id` and
  `session_id` came from an active search context.
- **Cursors are not uniform.** String cursors exist, `strCursor` exists on the
  notification lists, and a numeric `likes` cursor was observed to differ from
  its string form. Do not normalize or parse any of them.
- **`num` is a hint.** Observed page sizes were 5, 10, 12, 21/22, and 27. A
  request for 30 did not guarantee 30.
- **Home-feed cursors are strings.** `cursor_score` was copied as an opaque
  string; no arithmetic was performed.
- **Mixed item arrays.** Home feed and search return non-note models. Filter by
  `modelType === 'note'` and dedupe.
- **Comment and notification lists can be incomplete at first glance.** A
  comment's `subComments` may embed one reply; it is not the full thread.
  Notification entries may be deleted/illegal; that is not an empty list.
- **Identity is not privacy-safe by default.** The account payload contains
  profile fields and a token. The template returns only `guest` and the projected
  read fields.
- **Counts and identifiers have different types.** IDs and cursors are strings;
  counts may be numbers. The template accepts a finite number or a decimal string
  for the four unread counts and rejects anything else.

## Login and QR evidence

- **Guest identity is a normal state.** In the isolated context, the identity
  endpoint answered HTTP 200 with `code: -101, success: false`, or later 200 with
  `success: true, guest: true`. That is missing authentication, not a business
  refusal.
- **Create was live.** `client.post('/api/sns/web/v1/login/qrcode/create',
  { qr_type: 1 })` on the default `edith` host returned HTTP 200 with
  `success: true`; the payload carried `qr_id`, `code`, `url`, and `multi_flag`
  (client: `qrId`, `code`, `url`, `multiFlag`).
- **Pending poll was live.** `client.post('/api/qrcode/userinfo', { qrId, code },
  { transform: false, withCredentials: true })` returned `codeStatus: 0` while
  waiting.
- **Expiry was live for a stale code.** `codeStatus: 3` was observed for an older
  page code that was still polling in the background while a new manual code
  existed. Poll results must be associated with their own `qrId`.
- **Scanned and confirmed are source-only.** `codeStatus: 1` and `codeStatus: 2`
  were read from loaded client source; no real human scan was performed.
- **Geo and completion are source-only.** The `geoZone` branch, the site
  geography routing, and the completion `GET /api/sns/web/v1/login/qrcode/status`
  with an `x-login-mode` header were read from source, not exercised over the
  network.
- **The close of the loop was not verified.** No post-confirmation identity call
  returning `guest: false`, no final cookie/session creation, and no persistence
  across sessions were tested. The skill must re-check identity in the same
  context before claiming a login.
- **Session persistence and restore were not tested.** The dedicated persistent
  profile and the `.state/` storageState export/restore are documented strategy,
  not measured outcomes.

## What remains unverified

These are explicit gaps, not hidden assumptions:

- Another user's private collection/liked list or private profile tab. A public
  profile sample had `tabPublic.collection: false`; private access was not
  tested and must not be probed by trying adjacent endpoints.
- Location filters (`同城`, `附近`), `geo` semantics, and any coordinate
  encoding. Do not fabricate a location.
- Video subtitles. No subtitle track appeared in the sampled video; no schema is
  documented.
- Multi-page comment replies. Only a single-reply `has_more: false` sample
  exists.
- Multi-page collected-note pagination. Only a one-page `has_more: false` sample
  exists.
- Creating a brand-new search context without visiting/using a search page.
  `search_id`/`session_id` generation is not documented.
- A minimal home-feed body for a fresh context. The observed body carried
  session values and was not reduced to a proven minimum.
- Exact enum completeness for search filters. One real UI selection and one
  client-side combination succeeded; not every combination was tried.
- Notification read-marking and the `POST /api/sns/web/v1/message/read` write.
  That write was observed in client source only, with no network call in this
  session. It is unverified and outside scope.
- All business writes: publish, upload, comment, like, collect, reply, and
  notification reply. (QR login is separated above; reset is not covered.)
- A real human QR scan, the confirmed-to-authenticated transition, geo/activation
  completion, SMS or captcha handoff, and any final cookie creation.
- Persistent-profile survival across sessions and a `.state/` storageState restore.
- Long-run rate limits and account-risk behavior. Only bounded, low-frequency
  reads were exercised; no safe threshold is claimed.
- Build durability. Module ids, wrapper names, and the registration pattern are
  build artifacts. The documented source-string scan is a method, not a promise
  that a future build keeps the same internals.

## How to re-check safely

If a future session needs to confirm that the surface still works:

1. Open the authenticated site in the browser tool you already have.
2. Bootstrap the client using `templates/browser-api-bootstrap.js`.
3. Run only the identity preflight first; stop if `guest` is not false.
4. Run one read for the specific task, at human pace, with a page cap.
5. If bootstrap, signing, or status behavior differs, record the observation
   (date, page type, error class, whether a new network response occurred) and
   update the docs. Do not add captured ids, tokens, URLs, or headers.
6. Do not re-test by probing private endpoints, retrying a refusal, or
   automating a captcha. Those are boundaries, not test cases.

## Documentation checks

The endpoint facts above were observed in the independent browser session
described here. The original read facts were not replayed during packaging. The
QR research for this update was independently observed before the documentation
was written. The final static checks themselves (Markdown links, JavaScript syntax,
secret/absolute-path scans) made no network request.
