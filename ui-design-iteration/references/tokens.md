# Bind the levers

Binding the levers exists for one reason: after it, "make it feel lighter" is a number, not a redesign.

## The levers

Thirteen sliders plus one declared value. A lever earns its place only if one `calc()` can replace every literal of its kind across the page — if it can only move one component, it is a patch, not a token.

| Lever | Controls | Typical range | What breaks without it |
| --- | --- | --- | --- |
| `--gap` | every padding, margin and inline gap, as a multiple of it | 12–24px | each block invents its own rhythm |
| `--fs` | body text size; on a page whose layout is in `rem`, the type sizes, not the root font size | 15–18px | per-block font sizes appear |
| `--ratio` | type scale step; headings are `fs × ratio^n` | 1.2 / 1.25 / 1.333 | heading sizes stop relating to each other |
| `--measure` | line length of running text | 45–75ch | long lines make every paragraph look unfinished |
| `--radius` | the main radius; other radii derive from it or are a pill | 0 / 8–16px | mixed radii read as mixed systems |
| `--hue` | accent hue angle in OKLCH | 0–360 | a second accent creeps in |
| `--ink` | text lightness | 2–20% light / 88–97% dark | grey body text makes the page look unbuilt |
| `--surface` | page and panel background lightness | 96–100% light / 2–10% dark | every section invents its own background |
| `--line` | border and divider lightness | 86–94% light / 16–26% dark | dividers and card edges drift apart |
| `--edge` | border width used everywhere | 0 / 1px / 2px | thin and heavy borders coexist |
| `--shadow` | multiplier on the one at-rest shadow recipe | 0–1, usually 0 | every card floats and nothing is primary |
| `--room` | space between sections, as a multiple of `--gap` | 3–8 | section rhythm and block rhythm become one number, so "more air" hits both |
| `--dur` | every transition and animation duration; `0ms` disables motion | 0–300ms | motion is a per-component literal, so one fast block sets the page's pace |
| `--ease` | the one easing curve — declared, **not a slider** | `cubic-bezier(.2,0,0,1)` | every component brings its own curve |

`--ease` has no slider on purpose: a curve has no "a bit more" in it, and picking one is a design decision, not a tuning pass. Declare it once and use it everywhere.

`--ink`, `--surface` and `--line` are lightness scalars, not colours: one number each is what makes them sliders. If the design has a tinted paper, keep its chroma and hue at the point of use (`oklch(var(--surface) 0.01 80)`) rather than adding a second lever.

The ranges are where these values usually sit, not limits: when the design's value is outside one, the design wins and the panel widens its slider to fit (`references/panel.md`).

## Derive everything

```css
:root{
  --gap: 16px; --fs: 16px; --ratio: 1.25; --measure: 60ch;
  --radius: 12px; --hue: 24;
  --ink: 6%; --surface: 99%; --line: 91%;
  --edge: 1px; --shadow: 0; --room: 3;
  --dur: 160ms; --ease: cubic-bezier(.2,0,0,1);
}
h1            { font-size: calc(var(--fs) * var(--ratio) * var(--ratio) * var(--ratio)) }
p             { max-width: var(--measure) }
.card         { padding: calc(var(--gap) * 1.25);
                border: var(--edge) solid oklch(var(--line) 0 0);
                border-radius: var(--radius);
                box-shadow: 0 calc(2px * var(--shadow)) calc(14px * var(--shadow)) rgb(0 0 0 / .07) }
section + section { margin-top: calc(var(--gap) * var(--room)) }
.btn          { transition: transform var(--dur) var(--ease) }
.muted        { color: oklch(var(--ink) 0 0 / .65) }
@media (prefers-reduced-motion: reduce) { :root { --dur: 0ms } }
```

A literal `padding: 28px` anywhere is a value that will drift. Anything that survives as a literal must be something the reviewer should never tune — otherwise it is a leak the next round will argue about.

Two derivations worth keeping:

- **Secondary text is ink at reduced alpha**, never a second grey. A separate muted colour is how a page ends up with four greys and no hierarchy.
- **Motion is one duration and one curve**, and `--dur: 0ms` is a legitimate design state (as is the reduced-motion media query). A lever that cannot be switched off is not a lever.

## A draft extracted from a running product

The product's built stylesheet already encodes its design, usually through its own custom properties (`--radius-lg`, `--spacing`, `--color-primary`). Rewriting it into the thirteen levers would be a redesign by the wrong agent and would make the draft drift from the product it represents.

- Bind the panel to the properties the product already has: a token's `prop` names the product's property, its `unit` the unit the product uses.
- Leave a lever out when the product has no single property for it. A slider that writes a property nothing reads is a control that lies.
- Record the mapping (`--radius` ↔ `--radius-lg`) in `design-contract.md`.
- **Bind `--fs` to the type sizes, not to `html { font-size }`,** when breakpoints, containers or spacing are in `rem` (Tailwind CSS's are): a root font size scales the whole layout, so `--fs: 21px` widens a 1280px container to 1680px.
- **`--dur` reaches transitions only through the product's duration property.** Keyframe animations (`animate-pulse`, `--animate-*`) carry their own durations; say in the contract that the slider does not stop them.
- **A product with a colour scale rather than a few colour properties** (Tailwind's `--color-gray-50` … `--color-gray-950`) is bridged scale-wide: let the scalar stand for one step (`--surface` for `gray-950`) and give every other step its measured lightness offset from it (`--color-gray-800: oklch(calc(var(--surface) + 15%) 0.03 262)`), so the steps move together and keep their spacing. Write the formula in the contract.
- **Splitting a colour into a lightness scalar is theme-specific.** A block that redefines the product's colour property from the scalar (`--foreground: oklch(var(--ink) 0 0)`) on `:root` overrides the product's `.dark` block too — same specificity, and the later file wins — so dark mode silently turns light. Scope the block to the theme it was measured in (`:root:not(.dark)`), and either measure a second set of scalars for the dark theme or leave those sliders inert there and say so in the contract. A product with a single theme has no second block to override: bridge on `:root` directly.

## Mapping an external component onto the tokens

Library components arrive designed. Dropped in as-is, six of them look like six products. Strip first, then map:

1. **Replace its radius, shadow, border and gradient with the tokens** — not with "something similar".
2. **Replace its spacing with `calc()` of `--gap`** — internal padding included, or the block will sit at a different rhythm than its neighbours.
3. **Reduce its accent to `--hue`**, on the action.
4. **Cut its motion to zero** unless it is the page's single animated element; if it is, give it `--dur` and `--ease`.
5. **Reduce its font sizes to the scale** — keep at most three of its size levels.
6. **Keep its structure and semantics.** The reason for taking an existing component is the layout decision inside it, not its skin.

If a component cannot survive that stripping without falling apart, it belongs to a different design system; ask the design source whether it belongs on this page.

## Light and dark

- Dark mode is a second set of the same levers in a theme block (`.dark { --ink: 94%; --surface: 6%; --line: 24% }`), not a filter: `invert()` and `filter: brightness()` produce muddy accents and broken images.
- `--ink`, `--surface` and `--line` move together: ink goes light, surface goes dark, line sits between them. Move one and the page breaks in a way that looks like a rendering bug.
- In dark mode, elevation is expressed by *lighter* surfaces, not larger shadows.
- Check contrast on the accent against the dark surface separately; an accent that passes on white often fails on near-black.
- A slider the reviewer moved writes an inline value, and an inline value beats the theme block. Reset the panel before judging the other theme.

## Recording the binding

Write the values, their source and the rejected directions into `design-contract.md`, next to the draft. It is the only artefact that survives a new session, it stops the next request from re-deciding the palette, and it tells whoever ports the draft which numbers are deliberate.

Update the contract when a lever changes; do not let it drift into a description of what the page looked like two rounds ago.
