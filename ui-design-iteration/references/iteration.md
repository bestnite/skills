# Iterate

Iterative UI work with an agent feels like a lottery not because of model quality but because of **reference failure**: "the card", "that block", "a bit tighter" all point at something the model has to guess. A selected element turns each of those into a precise request.

## What a change costs

Two different latencies, and it matters which one you promise the user:

| Change | Mechanism | Cost |
| --- | --- | --- |
| any bound token | the custom property reassigned in the document | next frame, no reload, no build |
| markup, copy, structure, CSS | file written, page reloaded by the panel's watcher | one file write plus a reload |
| porting to another stack | not this skill | see `SKILL.md`, Step 4 |

- Token changes never need a reload. Do not regenerate the draft to change a number.
- Never promise "instant" for a structural change. Say "a file write and a reload".
- A reload discards sliders the reviewer moved. The panel asks before reloading in that case; write the values the user wants to keep first (`overrides` in the snapshot).

## Anchor everything

- Every section root and every component instance carries a stable `data-node` attribute (`pricing/plan-card#1`), named from its role, not its order in the file (`references/live-draft.md`, rule 4).
- Anchors exist before the first adjustment. A missing anchor on a section is a defect to fix, not an inconvenience.
- In the draft the markup *is* the source, so an attribute is enough: no mapping layer, no instrumentation, no build step.
- Keep the anchor list in `design-contract.md` current; it is how a later request names its target and how the porter finds the parts.

## Using a selection

The agent does not watch the page. The panel posts a snapshot and the server writes it to `selection.json` in the draft directory (schema in `references/panel.md`). When the reviewer says "change this" — or "see my marks" — read the file:

- **`selection.target`** is a CSS selector; find the element in the source by its anchor and the segments after it. If the selector no longer matches the markup, the selection is stale — ask the reviewer to pick again rather than guessing.
- **`selection.computed`** is the current state. State the change against it ("font-size 12.8px → 16px"), so the reviewer can check you understood which value they meant.
- **`marks`** are the reviewer's numbered notes on several elements. Answer them by number, one patch per mark, and say which ones you did not act on and why. Each mark is still one dimension: when two marks pull in different directions (one asks for more air, another for more on screen), ask which wins before patching either. A `stale` mark points at markup that changed; ask the reviewer to re-mark it.
- **`viewport.content`** is the width the reviewer was looking at. Reproduce a finding at that width before fixing it, and check that the fix does not break the other reviewed widths.
- **`selection.contrast`** is the text contrast where it matters. A request that lowers it below `required` ("make the grey lighter") is worth one sentence of warning before you apply it.
- **`overrides`** are values the reviewer already tried on the sliders. A request like "keep it like this" means: write those into `:root` and the contract.
- **`ts`** tells you whether this is the selection the reviewer is talking about. Re-read after every change round; a selection made two rounds ago describes markup that may no longer exist.

The words still come from the reviewer. What the tool supplies is the reference — selector, component, current values — which is the part the model would otherwise guess at. Do not ask the reviewer to paste what is already in the file.

## Turning vague feedback into one dimension

"I don't like it" is not actionable, and asking "what exactly?" produces more words, not more signal. Map the complaint onto one of three axes yourself, propose it to the reviewer in one sentence, and move only that axis's levers once they agree.

| Axis | How it sounds | Levers to move |
| --- | --- | --- |
| Density | "cramped", "too airy", "everything is on one screen" | `--gap`, `--room`, `--measure` |
| Hierarchy | "I can't tell what matters", "the title doesn't lead" | `--fs`, `--ratio`, `--ink`, weight, the number of competing accents |
| Temperature | "cold", "loud", "cheap", "washed out" | `--hue`, accent chroma, surface tint, `--shadow`, `--radius` |

Two axes in one round is a redesign; one axis is an adjustment.

## Rules for a round

- **One dimension per round.** Three dimensions at once and nobody can attribute the outcome, so the next round is blind too.
- **Return a patch, not a file.** A change that rewrites the component wholesale cannot be reviewed, and unreviewable changes accumulate.
- **Read the diff yourself before showing it.** If it touches a sibling, a paragraph or a lever nobody asked about, revert that part and say so.
- **Screenshot before and after, with the kit hidden (`H`)**, at the width the request was made at: size the window so the layout gets `viewport.content` from the snapshot — that width plus your own browser's scrollbar, which is 0 with overlay scrollbars (headless Chromium), not the reviewer's `viewport.scrollbar`. The screenshot is the only regression test a visual change has.
- **Size the screenshots to the change's reach.** A patch to one element needs that element's section. A change to a lever, a shared class or a component used in several places reaches every element that uses it: screenshot the whole page at every reviewed width, before and after, and compare all of it. A lever patch checked only where it was requested is how a heading two sections away wraps unnoticed.
- **Tell expected movement from regressions.** A change moves what it touches and what flows around it: a larger number makes its card taller, and the row and the cards below follow. That is the change working. A regression is something that moved without a path from the change to it, or that broke — wrapping, overflow, overlap, a lost alignment. If either appears, the round failed regardless of the requested change landing.
- **A mark on one instance of a repeated pattern raises one question:** "this one, or all of them?" — a footer line in one of three identical cards, a row in a table. Ask before patching, and patch at the level the answer names: the instance, or the shared class or component.
- **Say what you did not change.** It tells the user the request was bounded, which is the thing they were missing.
- **Update the contract** when a lever value or a standing decision changed.

## When the user wants to do it by hand

- Bind a slider instead of asking for descriptions. Prose has no scale; a slider does.
- An adjustment session should end as a few changed lines in `:root`, not a rewritten stylesheet.
- Slider values live in the browser until written down. Write the ones the user keeps — from `overrides` — into the draft's `:root` and `design-contract.md`.

## Order of work when a page needs many changes

Type and scale, then colour, then spacing and rhythm, then states (hover, focus, empty, error), then the components imported from libraries. Each earlier step changes the reading of everything after it; doing them in reverse means redoing the later work.
