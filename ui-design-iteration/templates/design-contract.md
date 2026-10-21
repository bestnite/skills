# Design contract — <page or project name>

Filled in at intake, kept next to the draft it describes, and handed over with it. A new session reads this before touching the UI; without it, every session re-decides the palette. Every `<…>` below is a placeholder to replace.

## The page in one sentence

<what this page is, who it is for, and the one thing it must make the reader do>

## Source

- Designed by: <the main reference, design skill, agent or person that settled composition, type and palette — or "extracted from <product and route>">
- Main reference: <name and URL of the template or site — or "none">
- Taken as code: <parts reused from published code, with block name or repository — or "none">
- Taken by measurement: <parts rebuilt from a demo, site or screenshot — or "none">
- Supporting references: <URL — what was taken from it, e.g. "pricing table layout"; or "none">
- Alternatives rejected: <directions the design source considered and dropped, one line of reason each; "none recorded" if it did not say>
- Copy deck: <where the final headlines and body text live>

## The levers

Mark each value with where it came from: `design` (the design source said so, or it was measured on the main reference), `product` (read from the template's or product's own CSS), `default` (this skill's fallback — a candidate to confirm), `tuned` (moved during review, with the round).

```css
:root {
  --gap:     <px>;                 /* design | product | default | tuned */
  --fs:      <px, body>;
  --ratio:   <1.2 | 1.25 | 1.333>;
  --measure: <ch, line length>;
  --radius:  <px>;
  --hue:     <OKLCH hue angle, 0–360>;
  --ink:     <% lightness, text>;
  --surface: <% lightness, paper>;
  --line:    <% lightness, borders and dividers>;
  --edge:    <0 | 1px | 2px>;
  --shadow:  <0–1, multiplier on the at-rest shadow>;
  --room:    <multiple of --gap, between sections>;
  --dur:     <ms, 0ms disables motion>;
  --ease:    <cubic-bezier(...), declared once — no slider>;
}
```

A lever the design or template has no single property for is not bound. Write it as a comment instead of inventing a value, so a later session does not mistake the gap for a decision:

```css
  /* --hue: not bound — the template's accent is a full colour (--primary), no hue scalar */
```

### Mapping to the design's own names

| Lever | Design or product name | Note |
| --- | --- | --- |
| <`--radius`> | <`--radius-lg`> | <e.g. product uses rem; panel reads it with unit `rem`> |

## Standing decisions

Answers that are not re-litigated in a later session. A decision here overrides the matching default limit in the audit.

- <e.g. no gradient anywhere>
- <e.g. hero is left-aligned, never centred>
- <e.g. hairline dividers between pricing rows are deliberate>
- <e.g. the pricing section keeps a table, not cards>

## Samples that must be confirmed

<sample product names, prices, figures, dates used to reach full density — each one the user must replace or approve before launch>

## Anchors

`data-node` values in use, so a request can name its target and a porter can find the parts:

```
<hero>
<hero/cta>
<pricing/row#1>
<pricing/plan-card>
```

## Hand-off

- Draft runtime files: <`<name>-runtime.js`, `<name>-runtime.css`, `<name>-fragments.js`, `<name>-patches.css` — or "none">
- Changes made in the template's source vs. only in the draft's CSS: <for route A — which patches exist in component source, which only in `<name>-patches.css`>
- Approximations: <behaviour the draft only imitates — e.g. focus trap, scroll lock, form submission>
- Widths reviewed: <the design's breakpoints, or 375 / 768 / <desktop> px>
- Accessibility: <contrast — audit clean at every state and width / exceptions; focus visible; keyboard; checked by agent or by user>
- Intentionally absent: <data wiring, routing, states not captured>
- Review tooling removed: <yes / no — the `DRAFT_KIT` block, `draft-kit.js`, `data-levers`, `selection.json`>
