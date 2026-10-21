# Drafting from a reference

The fastest reliable way to a first draft is to start from a page someone already designed — a template or a well-made live site — and carry its design into the draft. A good reference brings composition, type, spacing and interaction decisions that already fit together; generating a page from a one-line brief invents all of them at once, and every later round argues with choices nobody made.

There are two routes, and the reference decides which (step 4):

- **Reuse its code** when the template publishes it openly — a code tab, a copy-paste component, a public repository. Working markup and CSS are the most faithful copy of a design there is.
- **Rebuild from study and measurement** when there is only a demo, a live site or a screenshot: take the structure and the measured values, and write the page in the draft's own tokens.

Most drafts mix them: one template's open code for the shell, a gallery site's hero rebuilt from measurement. Where to look, and which sources publish code, is in `references/sources.md`.

## 1. Classify the page

Name what the page is before looking at anything: admin panel or dashboard, settings or auth, product landing page, company homepage, blog, docs, portfolio, shop. The class picks the catalogues (`references/sources.md`, "Which source for which page"). A landing-page reference stretched into a dashboard, or the reverse, fails at the parts nobody looks at first: tables, navigation depth, long content.

Also collect what the reference cannot know: the product's name, its real copy (or the user's notes for it), the sections or screens it needs, and any brand colour or typeface that is already fixed.

## 2. Shortlist, and let the user pick

- Ask the user for preferred sources before searching anywhere else, and search those first; the starter catalogue in `references/sources.md` fills gaps or stands in when they have none.
- Find two or three references that match the class and cover the required sections. Prefer a template over a gallery screenshot for the main reference: a template is a whole system — every state, every breakpoint, consistent values — it can be measured, and its code is often open.
- Show them. If you have a browser tool, screenshot each at desktop and phone width; otherwise give the links and ask the user to look.
- The user picks one main reference. Choosing a reference is choosing a design, so it is the user's decision, not yours. Further references may supply a single section or pattern ("the pricing table from this one"), never the overall look.

## 3. Study and measure the main reference

Looking gives the structure; measuring gives the values. Do both before writing anything — even on the reuse route, because they tell you which parts of the template's code the page actually needs and what its levers are.

**Structure**, from screenshots at each width:

- section order, and what each section is for;
- the layout of each section — columns, alignment, what spans, what stacks on a phone;
- navigation: header, sidebar, depth, what collapses and when;
- the states the page shows: hover and press, menus, dialogs, empty and loading states, as far as the demo exposes them.

**Values**, from the live demo's computed styles. With a browser tool, run a small script in the demo page that collects `getComputedStyle()` over the rendered elements and counts distinct values — the same reduction the panel's audit does (`references/panel.md`, "The audit"):

| Measure | Becomes |
| --- | --- |
| body font size, and the heading sizes above it | `--fs`, and `--ratio` from the steps between them |
| font families and weights | the draft's font stack and weight scale |
| most common gaps and paddings | `--gap`, and the multiples the sections use |
| space between sections | `--room` |
| text column width | `--measure` |
| radii, shadows, border widths | `--radius`, `--shadow`, `--edge` |
| text, background and divider colours; the accent | `--ink`, `--surface`, `--line` as OKLCH lightness, `--hue` from the accent |
| transition durations and easing | `--dur`, `--ease` |

Pitfalls when measuring:

- **Colours come back in whatever space the page used** — `lab()`, `oklab()`, `oklch()`, `rgb()`. To get OKLCH lightness for `--ink`, `--surface` and `--line`, let the browser convert: set an element's `color` to `oklch(from <computed colour> l c h)` and read its computed value back.
- **Type sizes rarely form an exact ratio** (16 / 18 / 20 / 24 / 48 / 64). Fit `--ratio` to the steps that carry the hierarchy — body to the main heading — and express the others as fractional powers of it (`fs × ratio^1.5`) rather than adding a second scale; list the sizes that do not fit as standing decisions if the user keeps them.
- **Scroll-triggered animations** hide content until it scrolls into view, so full-page screenshots and measurements come back with empty blocks. Emulate `prefers-reduced-motion: reduce` before measuring (most such libraries honour it), or scroll through the page first.
- **Measure at rest.** Hover, transitions and theme switches change computed values while they run; wait for them to finish.

Without a browser tool, read the values from the template's source where it is public (its theme or Tailwind configuration, its CSS variables), and ask the user for screenshots of the parts you cannot see.

## 4. Write the draft

### Route A — reuse the open code

Take this route for every part the template publishes code for.

- **Replace content and cut scope in the template's source, before rendering.** Product name, copy, demo data, navigation entries, sections to delete: change them in the source (its data files and components). One render then produces the draft and every captured state with the right content; changing it in the dump afterwards means hand-editing each captured fragment, which `references/live-draft.md` forbids.
- **Get it into static form.** Code that is already HTML and CSS (TailAdmin's HTML edition, a static Astro build output) goes in as it is, with its built stylesheet. Framework code (shadcn/ui blocks, Tremor, Next.js templates) needs rendering once: run it and follow "Producing a draft from an existing interface" in `references/live-draft.md` — dump the rendered DOM, strip the app runtime, keep the built CSS, capture menus and dialogs while open. Rendering needs a shell with Node and network access; without one, ask the user to run it and send the output, or take a part whose code is plain HTML, or switch that part to route B.
- **Make the extraction repeatable.** Keep the steps after the render — dump, strip, add `data-node` anchors, capture fragments — as a small script, not as hand edits, so a second render costs one command.
- **Bind the levers to the template's own custom properties** instead of rewriting its CSS — treat it as an extracted product (`references/tokens.md`). shadcn/ui, for example, exposes a numeric `--radius` in `rem`; its colour properties are full colours (the build emits `lab()` or `oklch()`), so they get no slider unless you split them into lightness scalars — and if you do, scope the split to the theme it was measured in (`references/tokens.md`, "A draft extracted from a running product").

After the first extraction, decide where each later change goes, because the built stylesheet only contains the utility classes the template already used — a class that was not in the source (`text-4xl` when the build never needed it) does nothing in the draft:

- **Values and styling** (sizes, colours, spacing, one element's weight): write plain CSS in a local `<name>-patches.css` linked after the built stylesheet, in terms of the bound properties. The draft stays the source; no re-render.
- **Structure, content or behaviour that lives in components** (a new column, a different menu, copy repeated across states): change the template's source, re-render, and rerun the extraction script, then re-apply `<name>-patches.css` (it is a separate file, so nothing is lost). Never fix the same thing twice, once in the source and once by hand in the dump.
- Record which of the two each patch took in the contract, so the porter knows which changes exist in component source and which only in the draft's CSS.
- **Note in the contract which parts are reused code** and where they came from (block name, repository), so whoever ports the draft can go back to the original components instead of reverse-engineering the dump.

### Route B — rebuild from study and measurement

Take this route for every part you only have a demo, a live site or a screenshot of.

- **Start from the lever block.** Write `:root` from the measured values first, then every section in terms of it (`references/tokens.md`). The reference's design lives in those numbers; a draft that reproduces the look with literals has nothing left to tune.
- **Rebuild section by section in the reference's composition**, with the user's content. Reading the reference's markup is useful when it explains how something is built — a sticky header, a responsive grid, a stretched-link row — but a live site's markup is generated for its own build; write the part in the draft's own classes and tokens.

### Adapting, on either route

- **One reference owns the page.** Its system sets the levers. A section borrowed from a second reference — reused or rebuilt — is restyled in the first one's tokens (`references/tokens.md`, "Mapping an external component"); blending two references' values produces exactly the assembled look this skill exists to prevent.
- **Use the user's content, not the reference's.** The product's name, its copy, its data, at real lengths. The reference's logo, wording, illustrations and photos belong to its own product and say nothing true about this one; where real copy or images do not exist yet, write plausible ones and list them under "Samples that must be confirmed" in the contract.
- **Delete what the page does not need.** A section kept because the reference had it is filler; the reference's author did not know this product.
- **Add missing sections from the same reference first** — its other pages, its section library — then from another reference, reused or rebuilt, in the owner's tokens. When none fits, ask the user rather than drawing one.
- **Carry the interaction details over.** Hover and press states, transition timings, focus styles: on route A they come with the code — keep them through extraction; on route B measure and reproduce them. They are what makes a reference feel finished, and the first thing a rebuild drops.
- **Keep it a draft**: one entry page with local CSS and JS, system fonts or font files copied into the draft directory, images stored locally (`SKILL.md`, Step 1).

## 5. Hand over to intake

From here the draft is like any other (`SKILL.md`, Step 1), and most of intake is already done: the levers are bound (to the template's properties on route A, to measured values on route B), the content is real. What remains:

- anchor sections and components with `data-node`;
- enumerate the conditional surfaces the reference showed and make each reachable (`references/live-draft.md`);
- fill in `design-contract.md`: the references, what was taken from each and whether as code or as measurement, the levers marked `design` (measured) or `product` (the template's own properties), and the reference's signature devices (an eyebrow label, a gradient hero) under "Standing decisions" if the user wants to keep them — otherwise the audit will flag them later as if they were drift.
