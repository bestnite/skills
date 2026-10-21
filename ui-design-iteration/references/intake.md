# Intake — receiving a design you did not make

The design source decides. This file is the handoff: what to require, what to send back, and where this skill's authority stops. A draft copied from a reference in Step 0 (`references/drafting.md`) arrives here like any other design; its main reference is its design source.

## What the input must be

| Requirement | Why it fails otherwise |
| --- | --- |
| One HTML entry page with its CSS inline or in local files beside it | Unbundled SCSS or a component tree cannot be opened, and a draft that cannot be opened cannot be reviewed |
| Real copy in real lengths | Placeholder text hides the two failures that matter: a headline that does not fit, a section with nothing to say |
| The levers bound in one `:root` block (or, for an extracted product or a reference's copied code, its own custom properties mapped) | Literal values scattered through the CSS make every later request a rewrite instead of a number |
| The states the view can reach, at least enumerated | A dialog nobody wrote is a dialog the reviewer cannot judge |
| No build step, nothing fetched from the network | A draft must open offline, from disk, months later |

If the design arrived as prose, materialize it once into that file. Materializing is mechanical: same composition, same type scale, same palette, same copy. Do not improve anything on the way in — an improvement at intake is a design decision made by the wrong agent, and it is the one the user cannot attribute later.

## What to send back

Send the design back to its source (or ask the user) when — for a draft from Step 0, "its source" means the main reference's other pages and section library; where neither covers the surface, compose it from the reference's parts (`references/drafting.md`, "Plan the page") and tell the user it is composed, and ask the user only when composing needs something the design language does not have:

- a surface the page needs has no rule at all — empty state, error, loading, long-content overflow;
- two sections would use the same composition, and the design gives no reason for the repetition;
- the palette has no working pair for a state (a destructive action with no warning colour, a disabled control with no dim);
- the design depends on imagery nobody has.

Fill in mechanically when the answer is already in the product: a dialog that exists in the running app, a table row pattern from another view, a token that already appears elsewhere in the CSS. Copy, do not design.

## Translating a design system into the levers

A design source usually returns scale and spacing as prose or as its own variables. Map them; do not re-derive them. The "if absent" column matches `templates/draft-kit.html`, so a draft built from defaults and the example panel agree.

| Lever | Take from the design | If absent |
| --- | --- | --- |
| `--gap` | its default gap between related elements (on a 4/8pt grid, usually 16px) | `16px` |
| `--fs` | its body size | `16px` |
| `--ratio` | its type step (1.2 / 1.25 / 1.333) | `1.25` |
| `--measure` | its line-length rule | `60ch` |
| `--radius` | its main corner radius | `12px` |
| `--hue` | its accent, as an OKLCH hue angle; lightness and chroma stay at the point of use, e.g. `oklch(58% .15 var(--hue))` | none — ask; an accent is a design decision. A reference with no accent stays without one: leave the lever unbound rather than invent a colour for the slider |
| `--ink` | its text colour, reduced to an OKLCH lightness | `6%` |
| `--surface` | its paper colour, as an OKLCH lightness | `99%` |
| `--line` | its divider colour, as an OKLCH lightness | `91%` |
| `--edge` | its border width | `1px` |
| `--shadow` | `0` if nothing floats at rest, `1` if it does; a multiplier on one shadow recipe | `0` |
| `--room` | its section spacing, as a multiple of `--gap` | `3` |
| `--dur` | its transition duration | `160ms` |
| `--ease` | its curve, declared once and never a slider | `cubic-bezier(.2,0,0,1)` |

Then replace every literal that duplicates a lever: `padding: 24px` → `calc(var(--gap) * 1.5)`; `border-radius: 12px` → `var(--radius)`; a heading two steps up the scale → `calc(var(--fs) * var(--ratio) * var(--ratio))` (`pow(var(--ratio), 2)` also works in current evergreen browsers). Any value that survives as a literal must be one the reviewer should never tune, or it is a leak the next round will argue about.

Record every mapping in `design-contract.md`, with the design's own name next to the lever, so a later session knows which numbers came from the design and which from a default.

## Where this skill's authority stops

| Question | Who answers |
| --- | --- |
| What the page looks like, section order, type, palette, copy | the design source |
| Whether the page exceeds the default limits | this skill (`references/audit.md`) — it reports; the contract can waive a limit |
| How a change is scoped, addressed and reviewed | this skill |
| Whether a request needs a new direction rather than a patch | the user, with one question — "is this a tweak or a different idea?" |

A request that changes composition is not a patch. Hand it back to the design source with the selection and computed values attached; that is the most useful bug report a draft can produce.
