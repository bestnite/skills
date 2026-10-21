# Before reporting done — the audit

The limits below are measurable, and they catch a page that reads as assembled faster than any aesthetic discussion. They are **defaults**: a decision recorded in `design-contract.md` overrides the matching limit, because this skill reports, it does not redesign. Audit the page against the limits the contract leaves standing, and list the waived ones in your report so the waiver is visible.

A draft built from a reference (Step 0, `references/drafting.md`) carries that reference's design language, and its devices — icon rows, badges, gradients, illustrations, shadows, extra radii — are standing decisions from the start, in copied and composed sections alike. The limits apply only to values and devices the design language does not contain; never remove one the main reference has to meet them. The accessibility checks further down are different: they are not defaults, and no contract waives them.

## Where the numbers come from

| Device | Share of higher-rated sites | Share of lower-rated sites |
| --- | --- | --- |
| Icon-topped feature rows | 1% | 28% |
| Pill or badge above a headline | 14% | 34% |
| Gradients | 22% | 52% |
| Shadows on things at rest | 24% | 48% |
| Tiny uppercase letter-spaced labels | 16% | 57% |

**Unverified here.** These shares come from an external study of 247 gallery-listed sites comparing pages rated 7.5+ with pages rated under 6.5. This skill did not reproduce it; treat the table as directional. Only these five rows were measured — the working limits below are heuristics built on them, not measurements.

## The working limits

1. **Two radii.** One main radius plus a pill, or one radius and nothing else. A box with some corners square (flush with an edge) still uses the main radius.
2. **Two shadows.** One for things at rest (often none) and one for genuinely floating surfaces (menus, dialogs).
3. **Five type sizes.** Two or three do the visible work; the rest should be candidates for removal.
4. **Two type families.** One is normal.
5. **No gradient** as a background, on a button, or in text. A flat scrim under text over a photograph is not a gradient.
6. **One card grid per page.** A second grid usually tells the same story twice.
7. **One animated component.** The page needs one focal motion; transitions on hover and press do not count.
8. **No eyebrow labels** — no small tracked label above a headline, no "New" chip. Put the information in the sentence.
9. **No icon-topped feature rows** — a row of equal items, each an icon above a title and a line. Lead with the claim and its proof instead.
10. **No ornamental rules.** A divider separates content that space alone cannot (rows of a list, a table); a line used as decoration (grid lines, a box around every section) is removed.
11. **Running text at full ink**, 16px or larger; reduced ink is for secondary notes only.

## How to count

**In the browser (preferred).** Run `window.draftKit.audit()` in a browser you drive, or ask the reviewer to press "audit this state" on the panel and read `audit` from `selection.json`. It counts computed values on rendered elements — radii, shadows, type sizes and families, gradients, animations — so it is exact whatever produced the styles (`references/panel.md`).

- It sees one state at one width. Run it for every state and every reviewed width (below), and merge the results before comparing with the limits: a radius used only inside the dialog still counts.
- Read the maps against the limits: more than two keys in `radii` or `shadows`, more than five in `fontSizes`, more than two in `fontFamilies`, any entry in `gradients`, more than one component in `animated`. On a draft built from a reference, tag every key with where it came from (the main reference, or this draft) — `examples` in the audit names an element that uses each key, so look at that element and the reference's measurements, not at a guess — and count only this draft's keys against the limits; report the reference's keys as standing decisions, not as excess.

**From the source (fallback, no browser).** With `rg` (substitute `grep -rhoE` if it is not installed):

```bash
# radii and shadows actually used
rg -oIN "border-radius:\s*[^;}]+" <page source files> | sort -u
rg -oIN "box-shadow:\s*[^;}]+" <page source files> | sort -u

# type sizes and families — the `font:` shorthand carries both
rg -oIN "font(-size|-family)?:\s*[^;}]+" <page source files> | sort -u

# gradients and their intended exceptions
rg -n "(linear|radial|conic)-gradient" <page source files>

# motion beyond hover/press transitions
rg -n "@keyframes|animation(-name)?:|requestAnimationFrame|setInterval" <page source files>
```

These patterns miss utility classes (`rounded-lg`, `text-sm`) and inline styles, and they count declarations, not what renders. When the styling is derived from tokens, count the tokens and the multipliers applied to them instead. Say in your report that the count came from the source.

## Accessibility

These are not taste and no contract waives them: a page that fails them is broken for some of its readers.

1. **Text contrast** — WCAG 2 AA: 4.5:1, or 3:1 for large text (≥24px, or ≥18.66px bold). `contrastFailures` in the audit lists every failing element with its ratio; `contrastUnknown` lists text over an image or gradient, which needs a look at a screenshot. `contrastApproximate` lists text the audit never saw on screen — inside a scroll container, or under a sticky header at every point — so its ratio comes from ancestors only: scroll each one into view and confirm it on a screenshot, or report it as unchecked. Check every theme: an accent that passes on white often fails on near-black. Read `transitions` in each result first: a result taken while a theme switch was still running is void, not failing.
2. **Focus is visible.** Tab through the page in a browser: every interactive element shows where focus is, and nothing removes the outline without replacing it. Screenshot two or three focused states.
3. **Everything works from the keyboard.** Menus, dialogs and drawers open with Enter or Space, close with Esc, and do not trap focus outside a dialog. In a draft these come from the draft runtime; name what it only approximates.
4. **Touch targets** on a phone width are at least 24×24px (WCAG 2.2 AA), comfortably 44×44px. Measure the area that takes the click, not the element's text box: a stretched link's clickable area is its `::after` (the whole row), so its own box understates it; padding counts. A smaller target passes under WCAG's spacing exception: a 24px-diameter circle centred on its bounding box intersects no other target and no other undersized target's circle. Check with the browser: for each link, button and input, take `getBoundingClientRect()` (or the row it stretches over) and compare.

Without a browser of your own, items 2–4 need the user: ask for them explicitly and report them as unchecked until done.

## Widths

A page that passes at one width can fall apart at another. Review — and audit — at a phone width (375px), a tablet width (768px) and the desktop width the design was made for, plus the widths where the layout changes:

- **Media-query breakpoints.** For each breakpoint the page actually uses, check the two widths on either side of the switch: just below and at a `min-width` breakpoint (767 and 768 for `min-width: 768px`), at and just above a `max-width` one (900 and 901 for `max-width: 900px`). Convert a `rem` or `em` breakpoint to pixels at the root font size first: `min-width: 50rem` at 16px is 800, so check 799 and 800. The layout changes between them, and the narrower side is the one most often broken. A framework's full breakpoint list (Tailwind's `sm` to `2xl`) only counts where the page uses it.
- **Container queries.** Components sized by `@container` rules change with their container, not the window — a KPI grid whose third card drops to its own row when the sidebar is open. Find the container rules (`@container` in the CSS, `@xl/name:`-style utility classes) and check the widths at which each container crosses its thresholds, including with sidebars open and collapsed.

At each width check overflow (no horizontal scroll, no descendant crossing its container's right edge), wrapping of headlines and buttons, and that nothing the reviewer must reach is hidden.

The snapshot's `viewport.content` says which width the reviewer was looking at; a finding made at 375px is not fixed by a change that only shows at 1280px.

## Removal order when a page exceeds a limit

Report first. Remove only what is drift — a value nobody decided — and ask before removing anything that looks like a design decision the contract does not mention.

1. Gradients and glows — the cheapest to remove and the most expensive to keep.
2. Shadows on things at rest.
3. Extra radii and type sizes: collapse each to the nearest token value; do not invent a new one.
4. Second and later card grids — a different composition is a design request, not an audit fix; send it back to the design source with the selection attached.
5. Icon-topped rows last, because removing them usually means rewriting a section, which is the user's decision.

## What to do instead of the removed device

Removing ornament leaves space, and space refilled with another ornament is the same problem. Refill it with scale (make the main thing larger), with the full content (the whole menu, every row, real numbers), with a picture made for this subject, or with a field of flat colour. Leave at most one area of the page deliberately empty.
