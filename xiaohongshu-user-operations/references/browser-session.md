# Browser Session, Bootstrap, and Transport

How to reach Xiaohongshu's read API from a browser that is already logged in, and
how to fail without damaging the session. Verified on 2026-10-21 UTC. API
catalog: `read-api.md`. Field coverage and gaps: `verification.md`.

## Contents

- [What the browser must provide](#what-the-browser-must-provide)
- [Why use the site's client](#why-use-the-sites-client)
- [Bootstrap: capture the site's client](#bootstrap-capture-the-sites-client)
- [Selecting the client without hardcoded ids](#selecting-the-client-without-hardcoded-ids)
- [Client call semantics](#client-call-semantics)
- [Search host exception](#search-host-exception)
- [Error model](#error-model)
- [Timeouts](#timeouts)
- [Page lifecycle](#page-lifecycle)
- [Using the template](#using-the-template)
- [Troubleshooting](#troubleshooting)
- [Secret handling in the transport](#secret-handling-in-the-transport)

## What the browser must provide

- A browser tool you can drive: navigate to a URL and evaluate JavaScript in the
  page. Decide from your own toolset whether you have one; do not probe the
  machine, look for browser binaries, or inspect profile directories.
- A tab on `https://www.xiaohongshu.com` in a user-authorized session. Login and
  credential handling are the user's browser tooling's responsibility.
- Main-world evaluation. The webpack runtime and the client live on the page's
  main world. An isolated content-script world can see the DOM but may not see
  `window.webpackChunkxhs_pc_web`; if it is absent while the page renders
  normally, switch to a page-context evaluation rather than concluding the site
  is broken.
- The site's app shell initialized. On the page types exercised here, one
  initialized `www.xiaohongshu.com` page served the calls; this is not a blanket
  guarantee for every page type. Search reads still need an existing search
  context from the user's normal search surface.

The skill does not read cookie files, export browser storage, or ask for a user
token. The credentials stay in the browser and are attached by the site's own
client.

## Why use the site's client

Measured in a logged-in tab:

```js
await fetch('https://edith.xiaohongshu.com/api/sns/web/unread_count', {
  credentials: 'include',
});
// HTTP 406, body {"code":-1,...}
```

The same endpoint through the page's initialized client returns HTTP 200 with
`success: true` and uses `x-s`, `x-t`, and `x-s-common` request headers that the
site generates from its own client state.

What the measurement supports:

- The site's client works for these APIs; a plain call was refused once.
- The refusal is not fully attributable to one cause. The response carried a
  readable JSON body, so CORS did not block reading it; do not record the
  measurement as proof that missing signatures are the sole cause.
- Do not generate, reverse-engineer, copy, or reuse the signature headers.
- Do not retry a refusal with different headers, a different `baseURL`, or a
  different token.
- `edith.xiaohongshu.com` and `so.xiaohongshu.com` are cross-origin relative to
  `www.xiaohongshu.com`; the page client handles that. This is a known topology,
  not a diagnosis of the refusal.

## Bootstrap: capture the site's client

The site is a webpack application that exposes its chunk array as
`window.webpackChunkxhs_pc_web`. Pushing an empty chunk is an additive way to
receive the runtime's `require` function without patching the site.

Run all of the following in one page evaluate call:

```js
const chunks = window.webpackChunkxhs_pc_web;
if (!Array.isArray(chunks)) throw new Error('chunk array missing');

let captured;
chunks.push([
  [`read-${Date.now()}-${Math.random().toString(36).slice(2)}`],
  {},
  (req) => { captured = req; },
]);
if (typeof captured !== 'function') throw new Error('require not captured');
```

- The chunk id only has to be unique; timestamp plus randomness is enough. It is
  not a secret and carries no account information.
- The chunk contains no modules. It does not modify existing modules, the HTTP
  client, `fetch`, or interceptors.
- The callback receives the webpack require function synchronously in the
  observed build. If it does not, stop; do not schedule later probes.

## Selecting the client without hardcoded ids

Module ids, export names, and wrapper function names are build artifacts. They
can move between builds and are not contracts. Locate the client by inspecting
module **source strings**, then require only the precise module the registration
call names.

1. Iterate `captured.m` and stringify each factory. Do **not** execute the
   factories during the scan.
2. Keep a factory only if its source contains both literal route fragments:
   `/api/sns/web/v2/user/me` and `/api/sns/web/v1/feed`. In the verified build
   this is the module that defines the read wrappers
   (`getApiSnsWebV2UserMe`, `postApiSnsWebV1Feed`, and similar).
3. Extract the registration call inside that factory:

   ```js
   const REGISTER = /registerHttp[^]*?\}\(\w+\((\d+)\)\.([A-Za-z_$][\w$]*)\)\}/;
   const match = source.match(REGISTER);
   // match[1] = module id, match[2] = export name
   ```

   The verified tail of the module looked conceptually like
   `function registerHttp(e){c=e}(r(<moduleId>).<export>)`; the regex captures the
   two variable parts and ignores the fixed text.
4. `captured(match[1])[match[2]]` is the initialized HTTP client. Validate that
   `get` and `post` are functions before using it.
5. If more than one factory matches, resolve each candidate and compare the
   resolved client objects. If exactly one unique client validates, use it; if
   several do, stop as ambiguous. Do not pick the first match, the shortest
   source, or the highest id.
6. Do not scan the runtime by calling every module. Requiring arbitrary modules
   executes them and can have side effects; the factory-string filter is what
   keeps the search safe.

A failed bootstrap is a hard stop. Report the observation for that build ("chunk
array absent", "route-bearing module not found", "registerHttp pattern absent",
"client validation failed", "multiple clients") and ask for a fresh page or a
newer observation. Do not fall back to guessing a global signing function, to
`__INITIAL_STATE__`, or to replaying headers from a captured request.

## Client call semantics

```js
client.get(path, { params });
client.post(path, body, options);
```

- `get` takes the path first and a request-options object second; query values go
  under `params`. There is no positional query argument.
- `post` takes the path, then the JSON body, then transport options.
- The return value is the business `data` object after the site's transform. It
  is camelCased; it is not an axios response, not a browser `Response`; do not
  call `.json()` and do not read `.data.data`.
- The raw wire payload uses `snake_case`; the client mechanically camelizes keys
  (`user_id` → `userId`, `has_more` → `hasMore`, `xsec_token` → `xsecToken`).
  `read-api.md` lists both sides where they differ.
- Query parameters accept wire snake_case and, in field testing, camelCase. Use
  the wire names shown in `read-api.md`.
- Do not mutate `client.defaults`, add interceptors, replace `fetch`, or wrap the
  client for logging. A patched client changes signing behavior and may leak
  headers.

The raw network envelope is:

```json
{ "code": 0, "success": true, "msg": "成功", "data": {} }
```

Judge the result by `success` and by the presence and shape of `data`, not by
`code === 0` alone. A recommendation response with `code: 1000` was observed to
be successful outside the documented main scope. A missing payload is a failure,
not an empty list.

## Search host exception

Search notes uses a different host and explicit transport options:

```js
const result = await client.post('/api/sns/web/v2/search/notes', body, {
  baseURL: 'https://so.xiaohongshu.com',
  withCredentials: true,
  transform: true,
});
```

This was exercised successfully from a notification page, so the page does not
have to be the search results page. The request still needs a valid search
context (`search_id`, `session_id`) obtained from the user's normal search
surface; those values are context, not something to invent. All other documented
reads use the default `edith` host.

## Error model

Classify before acting. Do not paste an entire error object into chat: it may
contain a request URL with tokens or context ids.

| Class | How it shows up | Action |
|---|---|---|
| Refusal | HTTP `401`, `403`, `406`; body often `{code: -1}` | Stop. No header edits, token swaps, or retries |
| Verification challenge | Captcha/verification page, `验证码`, risk-control text in the page or payload | Stop. Do not solve, bypass, or retry |
| Guest session | Identity payload has `guest: true` | Stop. The browser is not logged in |
| Business failure | `success: false`, or a client error thrown for a business reason | Report the fixed class; do not fabricate an empty result |
| Malformed/missing data | `success: true` but `data` is missing or not the expected shape | Treat as failure; stop that read |
| Transport failure | No HTTP status; network, timeout, DNS, socket, or abort text | Stop. Timeouts belong to the browser tool; do not auto-resend |
| Bootstrap failure | Missing chunk array, route module, registration pattern, or ambiguous client | Stop; report the build observation |

`msg` is present on success as well as failure, so it is not by itself a
rejection signal. A `406` was observed once for a plain call and the client
succeeded on the same endpoint; the refusal is not fully attributable to one
cause. The response is to stop and check that the call went through the site's
client, not to add headers.

A `403` can also be a legitimate privacy boundary (for example a non-public tab).
Respect it as a boundary; do not probe adjacent private endpoints to see whether
one answers.

## Timeouts

The browser tool owns network timeouts. The page client exposes no abort handle,
and a `Promise.race` timeout wrapper cannot cancel the in-flight request; it only
stops waiting while the request may still complete. Do not add a wrapper that
silently resends on timeout, and do not treat a timeout as a transient failure to
retry. Report it and stop.

## Page lifecycle

- Variables created in an evaluate call live for that call. A page navigation,
  reload, or tab replacement discards them, including the captured `require` and
  the resolved client.
- Re-bootstrap after every navigation. Do not cache the client in a host
  variable, a file, or `localStorage`.
- Do not navigate between the identity preflight and the task calls unless you
  re-run the preflight. A new page can be a different session.
- Close or leave the tab as you found it. Do not log out, clear storage, or
  "reset" the session.

## Using the template

`templates/browser-api-bootstrap.js` is a page-context snippet. Copy it into a
browser evaluate call, not into Node or a shell. It does the bootstrap, runs the
identity preflight, performs one read (by default the unread counts), and returns
an explicit projection. Its marked adaptation points are:

1. **Page/browser context** — run it on the authorized `www.xiaohongshu.com` tab
   in the main world. This differs per browser tool; that is why it is a template
   rather than a CLI.
2. **`TASK`** — replace the default read with the read the user authorized, using
   `read-api.md` for the path, params, body, and projection. For a list, loop one
   page at a time with a fixed page cap, copy the cursor unchanged, and keep any
   `xsecToken` inside the same evaluate block. The template does not guess targets
   and is not a generic call runner.

The template performs no environment detection, installs nothing, writes no
files, and uses no network transport of its own. It returns a small object:
`{ ok, identity: { guest }, task, data }` or `{ ok: false, stage, kind }`.

## Troubleshooting

| Symptom | Likely cause | Correct move |
|---|---|---|
| `window.webpackChunkxhs_pc_web` undefined | Isolated world, or page not initialized | Evaluate in the page main world; open/reload a site page once; stop if still absent |
| Route module not found | Build changed route strings, or page not the PC web app | Stop and record the build observation; do not widen the scan to all modules |
| `registerHttp` pattern absent | Build refactor | Stop; do not guess the client export |
| Multiple clients validate | More than one wrapper bundle | Stop as ambiguous; report both candidates' shapes without dumping source or ids |
| Plain call refused (406) | Not established; the site client succeeds on the same endpoint | Use the client; do not add headers or retry |
| Client exists but `get` is missing | Wrong export or partial module | Re-run selection; stop if not resolved |
| Calls work then fail after navigation | Captured state discarded | Re-bootstrap and re-run identity preflight |
| `guest: true` | Not logged in, or wrong tab/profile | Ask the user to authenticate; do not attempt login |
| 403 on another user's tab | Privacy boundary | Report; do not probe private endpoints |

## Secret handling in the transport

- The client object, its config, and its interceptors can expose cookies and
  signing state. Never serialize or return them.
- Return a fixed error class, not a raw error object: it can carry a request URL,
  headers, or tokens.
- `xsec_token`, search/session context ids, and signed URLs are scoped
  authorization material. Keep them in page variables for the next call in the
  same evaluate block; the result object contains only the projection.
- Do not persist raw responses or captured tokens. A user-requested export can be
  produced from projected fields and kept minimal and redacted.
