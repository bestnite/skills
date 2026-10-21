# The review panel and the draft server

Two shipped pieces carry a selection from the reviewer's pointer to the agent: `templates/draft-kit.js` (the panel, running in the page) and `scripts/draft_server.py` (serves the draft, writes what the panel posts). Neither is part of the draft.

## Attaching the panel

Copy `templates/draft-kit.js` into the draft directory, unchanged, and end `<body>` with:

```html
<script>window.DRAFT_KIT = { tokens: [...], states: [...] };</script>
<script src="draft-kit.js" defer></script>
```

Delete those two blocks (and the `draft-kit.js` file) and what remains is the draft. Whoever ports the draft must be able to tell the page from the panel at a glance; tooling mixed into the markup wastes their attention and gets migrated by accident.

The panel is one dependency-free file. It renders inside a shadow root, so the page's CSS cannot restyle it, and it never adds classes to the page's elements. It puts two nodes in the light DOM: the `<draft-kit>` host element that holds the shadow root, at the end of `<body>`, and one `<style id="draft-kit-page">` in `<head>` for the picking cursor (and the gutter, when one is configured). The audit skips the host. It needs nothing fetched from the network, so the draft still opens offline.

`templates/draft-kit.html` is a complete example.

## What the panel shows

A toolbar in a corner of the window: a drag grip, the picking toggle, the number of marks, a states menu, a warning sign when something is wrong, and the panel button. Next to a picked element, a note box: what was picked, its text contrast, a parent step and the mark button. The panel, opened from the toolbar: the readout of the selected element, the layer list with a parent step, the marks, an audit button and the sliders. Nothing else: everything else a reviewer might want — full selector, owning component, computed values, tag, text, moved sliders, the full audit — is in the snapshot and belongs to the agent, not to a control the human has to press. A copy button or a computed-values box only asks the reviewer to carry data the machine already has.

Behaviours it guarantees, because each one breaks a review when missing:

- **Picking is off by default.** Toggle with the toolbar button or `P` (keys are ignored while typing or with a modifier held); `Esc` closes the note box, and a second `Esc` leaves. In picking mode the page receives no pointer events at all — no menu opens, no link follows, no focus moves.
- **Hit-testing is point-accurate.** It builds the stack with `document.elementsFromPoint()` and picks the first element whose own box covers the point, so a cell under a stretched link is selectable. Elements reached only through another element's pseudo-element stay in the layer list, dashed: they are legitimate targets ("the whole row link"), just not what the eye sees.
- **Leaving picking mode keeps the readout.** The reviewer keeps talking about the element they just pointed at; only the hover outline goes. Numbered marks stay until the reviewer removes them.
- **The panel reads the page, it does not assume it.** Each slider seeds from the computed value of its property, trusted only in the slider's unit: a `0.5rem` radius never lands in a px slider as `0.5`; the row is marked "(not read)" and shows `def`. A page value outside `min`/`max` widens the slider instead of being clamped, and the slider's grid shifts so a measured value off the `step` grid (3.333 with step 0.5) is shown and kept as it is, not snapped.
- **Untouched sliders and state buttons re-read the page** after every click and keydown and every 500 ms, so a theme switched from the page's own menu shows up in the panel. A moved slider is marked `•` and keeps its inline value.
- **Reset removes inline overrides** rather than writing defaults, so the page's own values — including its theme block and its reduced-motion query — come back.
- **Marks carry several elements and the reviewer's words.** Pick an element: a note box opens next to it with the cursor in it; type the note and press Enter (or "mark"). Picking stays on, so the next element is one click away. Each mark gets a numbered badge on the page and an entry in the snapshot, so "this, this and that" is one request instead of three rounds. Marks survive the live reload that follows a patch (kept in `sessionStorage` per page; where storage is blocked they last one page load), so the reviewer can check each against the result. After a reload a mark is re-found by its selector; one that no longer matches is struck through and reported as `stale`.
- **The readout shows text contrast** — see "How contrast is measured" below.
- **"Audit this state" counts the page as rendered** — see below.
- **The kit floats; the page keeps its width.** By default nothing is reserved beside the page, so the layout is the one the window gives and the breakpoint the reviewer judges is the one they are on. The toolbar sits in a corner; drag its grip (`⠿`) to another one. The panel and the states menu open from the toolbar and float over the page; picking an element under the open panel moves the panel to the other side, and `⇄` in the panel's header does it by hand — also the way out when a fixed drawer or a corner button of the page sits under the kit. Where the toolbar sits and whether the panel is open are kept for the tab, across the live reload that follows a patch.
- **At a phone width the panel covers most of the page.** Close it to look: picking, the note box and the states menu all work with only the toolbar showing. The snapshot records the width each selection was made at.
- **A gutter is opt-in.** `gutter: 336` reserves that width beside the open panel at ≥1180px, for a reviewer who wants page and panel side by side. It narrows the layout — a 1280px window gives the page 944px, possibly a tablet layout — and `viewport.content` records what the page got.
- **`H` hides the kit completely** — toolbar, panel, badges, outline, note box, gutter — and shows it again; `draftKit.hide(true|false)` does the same for an agent. A closed panel still leaves the toolbar on screen, so use `H` for screenshots.

## Config

```js
window.DRAFT_KIT = {
  tokens: [{ key, min, max, step, def, unit, prop, label, suffix, apply }],
  states: [{ id, label, run(), on(), off() }],
  post: '/__select',     // snapshot endpoint; null disables posting
  gutter: 0,             // px reserved beside the open panel at ≥1180px; 0 floats it
  side: 'right',         // or 'left': the toolbar's first corner; the reviewer can drag it
  watch: true,           // false disables live reload
  ignoreClass: /…/,      // utility classes skipped when building selectors
};
```

- `prop` is the custom property read and written, default `--${key}`. For a draft extracted from a product, point it at the product's own property. `label` is display only, default `prop`.
- `unit` is the CSS unit the value carries (`'px'`, `'%'`, `'ch'`, `'ms'`; omit for unitless). `suffix` is what the readout prints instead (`--room: 3` reads `3×`). The readout shows as many decimals as `step` has.
- `def` is shown only when the page value cannot be read in `unit`.
- `apply(value, setVar)` is optional, for a token that writes several properties (a radius family). `value` is `null` when the slider is back at the page value; write through `setVar(name, valueOrNull)`, where `null` removes the inline property. Removing rather than writing the default matters: an inline default shadows the page's theme block.
- `states` become buttons for states the page cannot reach by itself. `run()` should flip something the draft already contains — a theme class, an attribute that shows a captured empty state, a call into the draft runtime — never implement behaviour, because the config is deleted at hand-off and the port would lose it. `on()` reports whether the state is active; it is re-read constantly, so keep it cheap. A click on an active state's button calls `off()`, or `run()` again when there is no `off()` — so a `run()` that only sets a state (`view('empty')`, `openDialog('invite')`) needs an `off()` that leaves it (`view('default')`, `closeOverlay('invite')`), or the reviewer is stuck in it; the panel warns when a state stays on after a click.
- `ignoreClass` defaults to Tailwind-style utility names (`flex`, `px-4`, `md:flex`, `text-sm`, …). A class it matches is skipped when naming a path segment; a draft whose meaningful classes look like utilities (`text-muted`) passes its own pattern.

### `data-levers`

An anchor may carry `data-levers="gap,ink,line"` — token `key`s that matter for that component. The panel highlights those sliders when something inside the component is selected, and the snapshot reports them, so the agent knows which levers the reviewer was shown. Keys are collected from every anchor above the selection, nearest first: an answer inside `faq/item#2` inside `faq` reports both anchors' keys. A key that names no token is reported in the warning line when the page loads. It is review tooling: strip it at hand-off — unlike `data-node`, which stays as the anchor map for the port.

## The snapshot

Every selection, mark change, slider change and resize (both debounced 400 ms), state button and audit posts the whole review state:

```json
{
  "page": "/pricing.html",
  "viewport": { "width": 1400, "height": 900, "content": 1385, "scrollbar": 15, "gutter": 0, "panel": "right", "dpr": 1 },
  "selection": {
    "target": "[data-node=\"pricing/row#1\"] > span.count",
    "component": "pricing/row#1",
    "levers": ["gap", "ink", "line"],
    "tag": "span",
    "text": "unlimited devices",
    "computed": {
      "font-size": "12.8px", "line-height": "19.8px", "font-weight": "400",
      "font-family": "ui-sans-serif, system-ui, sans-serif",
      "color": "oklch(0.06 0 0 / 0.65)", "background-color": "rgba(0, 0, 0, 0)",
      "padding": "0px 0px 0px 0px", "border-radius": "0px", "size": "105×20"
    },
    "contrast": { "ratio": 6.8, "required": 4.5, "passes": true, "against": "rgb(252 252 252)", "method": "stack" }
  },
  "marks": [
    { "n": 1, "note": "heading too heavy", "target": "[data-node=\"pricing/plan-card\"] > h2", "component": "pricing/plan-card", "...": "same fields as selection" },
    { "n": 2, "note": "should lead the row", "target": "[data-node=\"pricing/row#2\"] > span.count", "stale": true }
  ],
  "overrides": { "--gap": "20px" },
  "states": { "dark": false, "empty": false },
  "audit": null,
  "ts": "2026-10-21T09:14:03+00:00"
}
```

- `target` is a valid CSS selector rooted at the nearest `data-node`: `document.querySelector(target)` returns the element. Only when no anchor sits above the element is it rooted at a stable `id`; ids that component libraries generate (`radix-…`, `base-ui-…`, React's `useId` forms) are never used, because they change on every render. Segments keep one meaningful class and add `:nth-child()` only when siblings share the tag. The panel's readout shortens long paths; the snapshot never does.
- `viewport.width` is the window, `scrollbar` the width a vertical scrollbar takes from it, `gutter` what a configured gutter reserves; `content` is what the layout actually got. To look at the page as the reviewer did, without the panel: hide the kit (`H`) and size the window to `content` plus the scrollbar width of *your* browser — `viewport.scrollbar` is the reviewer's, and a browser with overlay scrollbars (headless Chromium, most phones) takes 0. `panel` says where the panel was: open on the `right` or `left`, `collapsed` (toolbar only) or `hidden` (`H`).
- `selection` is `null` when nothing is selected or the selected node left the DOM. `contrast` is `null` for an element with no visible text of its own (including screen-reader-only text).
- `marks` are numbered as the badges on the page. A mark whose selector no longer matches is `stale` and carries only `n`, `note` and `target`: the markup it pointed at changed, so ask rather than guess.
- `audit` is the last audit the reviewer ran (below), or `null`.
- `overrides` are the sliders the reviewer moved, as CSS values. They live only in the browser until someone writes them into `:root` and the contract — the agent can do that from this field without asking.
- `ts` is added by the server, in UTC.

When an agent drives the page itself, `window.draftKit.snapshot()` returns the same object without `ts`.

## How contrast is measured

The WCAG 2 ratio of the text against what actually paints behind it, with the threshold that applies — 3:1 for large text (≥24px, or ≥18.66px at weight ≥700), 4.5:1 otherwise.

- **Hit-tested, not inherited.** At points along the element's own text, `elementsFromPoint()` gives every element painted there, top to bottom. The layers below the text — background colours, gradients, and backgrounds drawn by `::before` / `::after` — are composited onto white. A dark hero band drawn by a sibling or a pseudo-element is therefore seen even though no ancestor has a background (`"method": "stack"`).
- **Gradients.** A linear gradient contributes its colour at the text's position, interpolated between its stops. Any other gradient contributes every colour stop and the worst ratio is reported, with `"gradient": true` and the `range` across stops — a failure there is conservative: confirm it on a screenshot before acting.
- **Unknown.** An image behind the text, or gradient-filled text, has no ratio from styles: `ratio` is `null` with a `reason`. Measure it from a screenshot, by sampling the pixel next to the glyphs.
- **Approximate.** Text that is not on screen, or covered at every sample point (a sticky header over it), falls back to its ancestors' backgrounds (`"method": "ancestors"`); the readout says "approximate", and the audit lists the element under `contrastApproximate`.
- **Not covered.** Element `opacity`, `mix-blend-mode`, filters and text shadows are ignored. Measure the colours as they are, not mid-transition: after switching a theme, wait for its transitions to finish before auditing.

## Driving the panel from a script

Picking and marking have no API: they are the reviewer's acts. To simulate a reviewer, send real input — `P`, pointer press and release on the element (the note box opens with the focus in it), text into it, then click its "mark" button. Clicking is the reliable path; a synthesized Enter submits the note only when the key event carries its text (with the DevTools protocol, `Input.dispatchKeyEvent` with `type: "keyDown"`, `key: "Enter"` and `text: "\r"`). Read the result from `selection.json` or `snapshot()`.

## The audit

`window.draftKit.audit()` — or the panel's "audit this state" button, which puts the result in the snapshot — walks every rendered element and reports what the page actually uses:

```json
{
  "elements": 17,
  "viewport": { "width": 1400, "height": 900, "content": 1385, "scrollbar": 15, "gutter": 0, "panel": "right", "dpr": 1 },
  "states": { "dark": false, "empty": false },
  "radii": { "12px": 4, "pill": 2 },
  "shadows": { "rgba(0, 0, 0, 0.07) 0px 2px 14px 0px": 1 },
  "rings": { "oklab(0.145 0 0 / 0.1) 0px 0px 0px 1px": 4 },
  "fontSizes": { "16px": 7, "12.8px": 2, "31.3px": 1, "20px": 1 },
  "fontFamilies": { "ui-sans-serif": 11 },
  "examples": {
    "radii": { "12px": "[data-node=\"kpis/card#1\"]", "pill": "[data-node=\"kpis\"] > header > span" },
    "fontSizes": { "16px": "[data-node=\"kpis/card#1\"] > h3", "…": "…" },
    "…": {}
  },
  "gradients": [],
  "animated": [],
  "contrastFailures": [{ "target": "[data-node=\"kpis/card#2\"] > div:nth-child(2) > div:nth-child(2)", "ratio": 4.35, "required": 4.5 }],
  "contrastUnknown": [],
  "contrastApproximate": [],
  "hiddenText": 4,
  "transitions": 0
}
```

- Counts are of computed values, so they are exact whether the styles come from tokens, utility classes or inline styles. Each map is value → number of elements, most used first.
- `examples` names, for each key of `radii`, `shadows`, `rings`, `fontSizes` and `fontFamilies`, the first element that uses it. Read it to tell where a value came from — a section copied from the reference, or one this draft added — before counting it against a limit.
- Type sizes and families are counted only on elements with visible text of their own; screen-reader-only text is counted in `hiddenText` instead.
- `shadows` are shadows that draw; a zero-size one (`--shadow: 0`) is dropped, and a layer with no offset and no blur but a spread — an outline drawn with box-shadow, such as Tailwind's `ring-1` — is counted under `rings`. A radius is keyed by its distinct non-zero corner values, so a box rounded only on its top corners (`12px 12px 0 0`) counts as `12px`; a radius large enough to round any box (`rounded-full`) is counted as `pill`.
- Contrast is measured as described above. The audit scrolls the page one viewport at a time so every text can be hit-tested, and restores the scroll position; `contrastApproximate` lists the texts it could never see on screen (`target`, `ratio`, `required`), measured against their ancestors only. Content of a closed `<details>` or under `content-visibility: hidden` is not counted at all: it belongs to the open state, so audit that state too. `contrastFailures` entries over a non-linear gradient carry `gradient` and `range`.
- `transitions` counts the CSS transitions running when the audit read the page (the panel's own excluded). Above 0, colours were read mid-change — right after a theme switch the audit reports dark surfaces over white and contrast failures that are not there — so wait until the transitions end and run it again.
- It sees the current state only: elements hidden by an inactive state, a closed dialog or a breakpoint are not counted. Run it once per state and per width the reviewer signs off, and read `states` and `viewport` to know which one a result describes.
- It reports facts, not verdicts. Comparing them with the limits, and with the waivers in the contract, is the agent's job (`references/audit.md`).

## The server

```bash
python3 scripts/draft_server.py <draft-dir> <port> [--host <interface>]
```

- `POST /__select` writes the body to `<draft-dir>/selection.json` atomically; `GET /__selection` reads it back (404 until something is recorded). Every other path is a static file from `<draft-dir>`, sent with `Cache-Control: no-store` so a reload never shows a stale stylesheet.
- Unknown POST paths return 404 and malformed bodies 400. The panel shows any failure in its warning line (`not recorded (…)`) and on `file://` says selections are not recorded — never a silent success.
- The port is the user's or the environment's choice; `0` takes a free one and prints it. The host defaults to `127.0.0.1`. Pass `--host 0.0.0.0` only when the browser runs on another host or container, because that exposes the directory listing and the write endpoint to the network.
- Python 3 standard library only.

`selection.json` is generated: keep it out of any repository that ships the draft, and delete it at hand-off. It holds only the latest snapshot — any page with the kit attached and the server running overwrites it, including a browser you drive yourself only to screenshot or audit. Read it (or copy it) before you open the draft in another tab or session.

## Live reload

Served over HTTP, the panel polls the entry HTML and every same-origin stylesheet and script it links (except itself) every 1.2 s and reloads when one changes, so a file the agent writes is visible without touching the browser. Opened from `file://` the watcher stands down; the browser's own refresh is the mechanism.

If the reviewer has moved sliders, a reload would discard them, so the panel shows a notice with a reload button instead. Their values are already in the snapshot's `overrides`; write the ones the user wants to keep before they reload.

## Content-Security-Policy

The panel needs no `eval`. Under a strict policy it needs the inline `DRAFT_KIT` block allowed (or moved into a local file) and `draft-kit.js` served from the draft's own origin.
