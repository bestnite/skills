# UI Design Iteration

[English](./README.md) | [简体中文](./README.zh-CN.md)

A workflow skill that takes a UI from first draft to reviewed page: when there is no design yet, start from an existing, well-designed reference — reusing a template's open code where it publishes it, rebuilding from measurement where it does not — make it a live page, let a human point at any element, turn their words into a single-dimension patch, and verify the result.

It does not invent what the page looks like. The look comes from something already designed — a reference the user picked — from their own preferred sources first, otherwise from a starter catalogue (shadcn/ui, Tremor, TailAdmin, Cruip, Astro themes, Vercel templates; One Page Love, Recent, Mobbin) — a design skill or agent, the user, or the running product the draft was extracted from. This skill reuses or rebuilds that design and makes it reviewable; it never draws a page from a one-line brief.

The deliverable is a **static design draft**: a directory with one HTML entry page and its local CSS and JS, openable in a browser with no build step and no network, adjustable live, discussable element by element. Porting it into a framework or template language is deliberately out of scope — the draft plus its design contract is what a port starts from.

## What It Prevents

Agent-designed interfaces fail in two ways that have nothing to do with taste:

- **The unchangeable result.** The draft is one artifact. "Make the card tighter" triggers a rewrite of the whole block, so the user cannot see what changed, cannot keep what worked, and the next request drifts again.
- **Reviewing a screenshot.** A static picture cannot be judged for motion, feedback or state, so every decision about behaviour is made blind, and dialogs and empty states never exist at all.

The skill replaces both with structure: style is bound into a small set of tokens before any detail work, every element is addressable, every change is a patch with a named target, and every surface the page can show is reachable and selectable.

## The Loop

| Step | Goal | Output |
| --- | --- | --- |
| Draft from a reference (when there is no design) | a designed start, reused or rebuilt with the user's content | `<name>.html` with levers bound |
| Intake | the design on disk, tokens bound | `<name>.html`, one `:root` block, `design-contract.md` |
| Make it live | the draft behaves like the page | draft runtime plus review panel attached, server running |
| Iterate | changes become addressed and small | per-element patches, each read in a diff |
| Audit and hand off | limits met or waived in the contract, port-ready | draft directory, contract, anchor map |

## Installation

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s ui-design-iteration
```

The shipped code needs a browser to open the draft and Python 3 (standard library only) for the draft server. Nothing else is installed.

## When To Use It

- A design is settled (by a design skill, by the user, or by an existing product) and now needs review and iteration.
- An interface looks assembled — several individually fine components that do not add up to a product.
- A running app needs a static, inspectable copy of one screen to argue about.
- The user wants to adjust details by hand instead of describing them in words.
- There is no design yet, and the fastest good start is a page that already works.

With only a one-line brief, the skill starts from a reference rather than generating a page: it shortlists two or three, and the user picks.

## How To Use It

1. No design yet? Classify the page and write its argument — one claim per section, with the proof and imagery that really exist — shortlist references from the user's preferred sources (or the starter catalogue in `references/sources.md`), let the user pick, study and measure it, then reuse its open code or rebuild it with your content (never sampled proof), and compare the result with the reference before review (`references/drafting.md`). Otherwise bring the design in as one HTML page with real copy (`references/intake.md`).
2. Bind the thirteen levers into one `:root` block and replace the literals that duplicate them — or, for a draft extracted from a product, map the product's own custom properties.
3. Copy `templates/draft-kit.js` next to the draft and attach it with one config block and one script tag. Use the draft as a page: menus open, dialogs open, nothing navigates.
4. Start `scripts/draft_server.py <draft-dir> <port>` and open the draft through it.
5. Turn picking on (`P`) and click any element; the selection — CSS selector, owning component, computed values, text contrast, moved sliders, viewport width — is written to `selection.json` and the agent reads it from there. To point at several things at once, mark each with a note; the marks are numbered on the page and land in the same file.
6. Name one dimension per round — density, hierarchy or temperature — and the levers it may move.
7. Review the change, not the whole page: if the diff touches a sibling or a lever nobody asked about, send it back.
8. Before calling it done, run the audit at every state and reviewed width — limits, contrast, focus, keyboard — then hand over the draft without the review tooling.

## What's Inside

```text
ui-design-iteration/
├── SKILL.md
├── references/
│   ├── drafting.md     # starting from a reference: argument, shortlist, measure; reuse or rebuild; compare
│   ├── sources.md      # user's sources first, how to judge any source, a dated starter catalogue
│   ├── intake.md       # receiving a design: what to require, what to send back, mapping onto the levers
│   ├── tokens.md       # the thirteen levers, extracted products, external components, light and dark
│   ├── live-draft.md   # usable-draft rules, draft runtime, conditional surfaces, extraction, verification
│   ├── panel.md        # the panel: config, marks, contrast, audit, snapshot schema, server, live reload
│   ├── iteration.md    # using a selection and marks, rules for a round, vague-feedback triage
│   └── audit.md        # default limits, how to count, accessibility, widths, removal order
├── scripts/
│   └── draft_server.py      # serves the draft, writes selection.json (stdlib only)
├── templates/
│   ├── design-contract.md   # levers and their source, standing decisions, anchors, hand-off
│   ├── draft-kit.js         # the review panel: sliders, picking, marks, contrast, audit, live reload (no dependencies)
│   └── draft-kit.html       # example draft showing the lever block, anchors, runtime and panel
├── LICENSE
├── README.md
└── README.zh-CN.md
```

## The Limits It Checks

Two radii, two shadows, five type sizes, two families, no gradients, one card grid per page, one animated component, no eyebrow labels, no icon-topped feature rows. Five of them lean on an external study of 247 gallery-listed sites that this skill did not reproduce; `references/audit.md` marks which.

They are default exit conditions for iteration, not a style guide: a decision recorded in the design contract overrides any of them, and this skill reports a page that reads as assembled rather than redesigning it.

Accessibility is checked alongside and is not waivable: WCAG 2 AA text contrast (computed by the panel for every rendered text element), visible focus, keyboard operation and touch-target size, at every reviewed width.
