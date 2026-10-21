# xianyu-operations

[English](./README.md) | [简体中文](./README.zh-CN.md)

[Xianyu (闲鱼 / Goofish)](https://www.goofish.com) operations for AI agents:
keyword search, item detail, your own listings and IM sessions — plus publishing,
taking listings down and sending messages (writes, each one approved by the user).

Xianyu has no open API and no OAuth registration, so access is a logged-in
browser session. **Every request is issued by the browser** — the search page is
read from the rendered DOM, and the structured endpoints are reached with a
`fetch()` fired from inside a page already open on the site. Calling the API from
a host HTTP client is not a supported transport: it works for about a dozen calls
and then trips Alibaba's risk control (`RGV587`), which reads like a dead session.
Signing stays host-side arithmetic; only the send belongs to the browser.

## Install

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s xianyu-operations
```

Or copy the directory into your agent's skills folder.

## What is in here

Three templates and five reference documents:

| File | Role |
|---|---|
| `templates/mtop_request.py` | A copy-and-adapt snippet: signs an mtop request and prints the exact `fetch()` call to run in the page. **Standard library only**, no network at all |
| `templates/publish_item.py` | Payload assembly for publishing a listing (images, price, delivery, category, location) |
| `templates/im_send_message.py` | Chat messages over the WebSocket gateway: the LWP frame sequence (needs `websockets`) |
| `references/mtop-apis.md` | Verified endpoints, payloads, field paths, error codes, the in-page `fetch()` form, risk notes |
| `references/browser-search.md` | The search extractor and browser steps, as text |
| `references/write-operations.md` | Publish / take-down / message recipes, and the rules that govern writes |
| `references/browser-tool-setup.md` | How to stand up a browser tool when the machine has none |
| `references/session-persistence.md` | Where the session lives between runs: the browser's persistent profile first, `.state/` inside this skill otherwise |
| `.gitignore` | Ignores `.state/`, the only place the skill writes session material |

The narrow code is intentional, and it is a template rather than a tool: it
computes the one thing that must be byte-exact, and lets you edit where your
session lives, which browser you drive, and how you retry. Everything that
depends on the environment or on judgement stays in prose, so the agent adapts
instead of waiting for the skill to support its setup.

## Requirements

- Python 3 (any recent version). No third-party packages: not `requests`, not
  `playwright`.
- A logged-in Xianyu session (`unb` and `_m_h5_tk` are mandatory), loaded into
  the browser tool. A browser with a persistent profile keeps it between runs;
  otherwise the agent saves it, after asking once, to `.state/storage-state.json`
  inside this skill's directory and restores it from there.
- A browser tool with three abilities: navigate and read the rendered DOM,
  evaluate JS in the page, and inject cookies (any mechanism — cookie API,
  storage-state file, CDP, or a profile the user already logged into). If the
  environment has none, set one up per `references/browser-tool-setup.md`.

## Usage

```bash
cp templates/mtop_request.py ./mtop_request.py
$EDITOR mtop_request.py     # three marked blocks: session source, api/payload, fetch shape
python3 mtop_request.py
```

It prints the signed URL, the form body, and a ready-to-run `fetch()` snippet.
Run that snippet in a page already open on `www.goofish.com`; the browser issues
the call and returns the JSON. Then read `references/mtop-apis.md` for how the
response is shaped — item data lives under `data.itemDO`.

Keyword search is a browser job too: follow `references/browser-search.md`, which
carries the extractor and the steps.

## Writes

Publishing a listing, taking one down and sending chat messages are supported,
under three rules: **the user approves the exact content first**, writes stay at
roughly one per minute, and every write is verified by reading it back (a
`SUCCESS` ret means accepted, not live). No bulk actions and no automated
outreach — that is where accounts get limited.

## Security

A saved session is a live account session. The skill writes it only to
`.state/` inside its own directory (ignored by git, files `0600`) and never into
chat logs or the conversation. Reinstalling the skill can delete `.state/`, which
means logging in again. Deleting `.state/` does not end the session; to revoke
it, use the Xianyu app's "log out of all devices".

## Notes

Unofficial: it speaks the web client's internal endpoints, which can change
without notice. Verified against live responses in 2026-09; the request shapes,
field paths, and known response codes are documented in
[`references/mtop-apis.md`](./references/mtop-apis.md).
