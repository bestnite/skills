# Drafting from a reference

The fastest reliable way to a first draft is to take a page someone already designed — a template or a well-made live site — and carry its design over to your content. A good reference brings composition, type, spacing, colour, imagery and interaction decisions that already fit together; generating a page from a one-line brief invents all of them at once, and every later round argues with choices nobody made.

**Keep the design language; let the content decide the structure.** A reference's sections rarely match the page you need — it has a logo row and a closing band, you need a comparison table and a sign-up form. That is expected: the page's sections come from its content. What must survive is the design language, everything that makes the reference look like itself: where the navigation sits and whether the header has a border, the background, an accent used once on a badge, the style of its illustrations and icons, a dark band inset from the edges instead of full-bleed, its type and its spacing rhythm. Each looks optional on its own, and together they are why the page works. A draft that keeps the reference's sections but re-decides these details looks stiff and generic; a draft with different sections that keeps them still looks like it belongs to the reference. Content decides the structure; the reference decides the look; the user decides any change to the look.

There are two routes, and what the reference offers decides which (step 4):

- **Route A — copy its code.** The template's published code (a repository, a code tab, a copy-paste block), or, without published code, the live demo's rendered page: its DOM, stylesheets, fonts, icons and images, saved as they are. Both are code, and both are the most faithful copy there is. This is the default.
- **Route B — rebuild from screenshots**, only when there is nothing to copy: a screenshot the user sent, a gallery entry whose site cannot be loaded, an app behind a login.

Where to look, and which sources publish code, is in `references/sources.md`.

## 1. Classify the page and write the argument

Name what the page is before looking at anything: admin panel or dashboard, settings or auth, product landing page, company homepage, blog, docs, portfolio, shop. The class picks the catalogues (`references/sources.md`, "Which source for which page"). A landing-page reference stretched into a dashboard, or the reverse, fails at the parts nobody looks at first: tables, navigation depth, long content.

Then collect what no reference can know:

- **What is fixed**: the product's name, any brand colour, typeface or logo, and the stack the page will be ported to. Only these override the reference's look, and only where the user says so.
- **The argument and the required parts.** Write the page as claims with their proof, one line per claim: "works with no signal — the offline queue, the sync log", "free for one person — what the free plan includes". Add every part the user asked for by name — a comparison table, a sign-up form, a four-step timeline. Together they decide the page's sections and their order (step 4); the reference decides how those sections look.
- **The proof that exists.** Customers, testimonials, press, logos, usage figures: only what the user can name. Proof is never sampled (step 4).
- **The imagery that exists**: the product's own interface, its photographs or product shots, illustrations, or nothing. Until real imagery exists, the reference's own pictures stay in their slots as placeholders (step 4).

## 2. Shortlist, and let the user pick

- Ask the user for preferred sources before searching anywhere else, and search those first; the starter catalogue in `references/sources.md` fills gaps or stands in when they have none.
- Find two or three references that match the class. Prefer a template with a live demo for the main reference: a template is a whole system — every state, every breakpoint, consistent values — and its code is either published or can be saved from the demo. Screen each one against step 1:
  - **Parts**: does it have the parts the content needs, or close relatives to compose them from — a table style for a comparison, a form for a sign-up, a list treatment for steps? The section order does not have to match. A reference whose design language says nothing about the hardest part of the content (a dense table, a long form) leaves that part to invention; say so when showing it.
  - **Imagery**: a photograph-led template keeps its photographs as placeholders until the user has their own; say so when showing it.
  - **Stack**: a template in the stack the page will be ported to makes the port nearly free.
- Show them. If you have a browser tool, screenshot each at desktop and phone width; otherwise give the links and ask the user to look.
- The user picks one main reference. Choosing a reference is choosing a design, so it is the user's decision, not yours. Further references may supply a single section or pattern ("the pricing table from this one"), never the overall look.
- **When the user hands the choice to you** ("you pick"), choose only after the screening above, and pick the candidate that leaves the least of the content to composition: the one whose parts cover the hardest part of the content, then the one whose imagery the user can replace, then the one in the port's stack. Tell the user which one and why, and one line for each candidate you passed over, before drafting; record it in the contract as chosen by you on the user's request. Show the main reference again next to the first draft and ask the user to confirm it before the first review round: a reference nobody looked at is a design nobody chose, and it is cheapest to change before any section has been reviewed.

## 3. Study and measure the main reference

Looking gives the structure; measuring gives the values. Do both before writing anything — on route A they tell you which parts of the code the page needs and which values the levers bind to; on route B they are the design.

**Structure**, from screenshots at each width:

- section order, and what each section is for;
- the layout of each section — columns, alignment, what spans, what stacks on a phone, which bands are full-bleed and which are inset;
- navigation: header layout (what sits left, centre, right), sidebar, depth, what collapses and when;
- the devices that give the page its character: illustrations, icon set and icon treatment, badges, accent colours, borders and their absence;
- the picture layer down the whole page: where illustrations, abstract interface sketches, glows, background shapes and photographs sit, and how often one appears — every section, every other one, only at the top;
- the states the page shows: hover and press, menus, dialogs, empty and loading states, as far as the demo exposes them.

**The design language**, written down before drafting: eight to fifteen concrete lines, each saying what the reference does and where, precise enough to check a section the reference never had against it. For example: "black and white only; one blue accent, used on small badges", "line-art illustration with one pastel fill, beside the hero headline", "icons white on a black circle, left of each item's title", "header in three parts — wordmark, centred links, actions — no border", "closing call to action in a black band inset from the page edges, radius 8px", "no shadows; 2px borders on cards and outline buttons", "display face with tight tracking; body in slate grey". Mark the lines that are the page's signature — the few devices someone would recognise it by. Include the picture layer and its rhythm ("a glow behind every section heading; an abstract interface sketch on top of each card; a picture or glow at least once per screen"): it is the part of a reference most easily mistaken for content and dropped with a section. The list goes into the contract ("Design language"); step 4 places it and step 5 checks against it.

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
- **Type sizes rarely form an exact ratio** (16 / 18 / 20 / 24 / 48 / 64). On route B, fit `--ratio` to the steps that carry the hierarchy — body to the main heading — and express the others as fractional powers of it (`fs × ratio^1.5`); keep the reference's sizes, not the ratio's rounding.
- **Scroll-triggered animations** hide content until it scrolls into view, so full-page screenshots, measurements and saved pages come back with empty blocks. Emulate `prefers-reduced-motion: reduce` first (most such libraries honour it), or scroll through the page.
- **Client-rendered parts can be blank in the first screenshot** — charts, maps, canvases drawn after hydration or after measuring their container. Wait for them, resize the window once, or scroll them into view, until they show. Do not fill their look in from the source's variables: the dashboard whose chart variables are blue may draw its chart in its black primary. The design language is what the rendered page shows; a value defined in the stylesheet and never seen on screen is not part of it.
- **Measure at rest.** Hover, transitions and theme switches change computed values while they run; wait for them to finish.

Without a browser tool, read the values from the template's source where it is public (its theme or Tailwind configuration, its CSS variables), and ask the user for screenshots of the parts you cannot see.

## 4. Write the draft

### Plan the page

List the page's sections in order, from step 1, and give each one a source, in this order of preference:

1. **A reference section that already fits** — copy it, with the user's content.
2. **A section from the reference's other pages** or its component library (a pricing page, a features page, a blocks gallery).
3. **Composed from the reference's parts** — its components, type steps, colours, borders, radii, spacing and icon treatment, arranged for this content. Everything in it is the reference's; only the arrangement is new.
4. **A pattern from a supporting reference**, restyled in the main reference's language (`references/tokens.md`, "Mapping an external component").

A section that needs a colour, radius, typeface, shadow or device the design language does not have is new design: ask the user. Write the plan into the contract next to the argument.

- **Leave out reference sections the content does not need** — but first check which signature devices and which pictures they carry.
- **Every signature device keeps a place.** Give each one a role in the new page like the one it had: the illustration beside the hero headline, the icon treatment on whatever list of features or steps the page has, the inset dark band on the page's closing call to action, the accent badge on whatever is new. When the content leaves no place for one, ask the user before letting it go: a page that loses its signature devices loses its reference, whatever else it keeps.
- **Decoration moves with the language, not with the sections.** A section left out takes its illustrations, sketches and glows with it unless you move them: put them on the composed sections in the roles the reference gives them — the sketch that topped each card now tops each step of a timeline or each pricing tier, the glow that sat behind every heading sits behind the new headings too.
- **Give each composed section a form, and take it from the reference first.** The form is the shape the content takes: a card grid, centred columns, a ruled list, a table, a band, a single large statement, alternating text and picture. Before reaching for a table or a list of rows divided by lines — the default an agent falls into for anything with several items — try the forms the reference already uses: four steps of a day can be four of its cards, each with a sketch on top, as easily as four ruled rows. Use a table only where the reader compares values across rows and columns; steps, features and questions are not tables.
- **Vary the form between neighbours.** Write each section's form into the plan, and do not let two adjacent sections share one, or both be drawn mostly in lines (rules, cell borders, outlined boxes): two ruled sections in a row read as one long form, and the page goes stiff. When the content forces a table, put a form with mass — cards, a band, a picture — on either side of it.
- **Keep the reference's rhythm of rich and plain.** Find the longest stretch of the reference without a picture, glow or band, and do not let the draft go longer. Composed sections tend to be text — a timeline, a table, a feature list, pricing, questions — and five of them in a row read as a plainer, different page even when each one is on-language.
- **Order the sections by the content**, keeping the reference's habits at the ends: its kind of opening first, its closing call to action and footer last.

### Route A — copy the code

Take this route for every part there is code for. Get the code from the first of these that exists:

1. **The template's own source** (a public repository, a code tab, a copy-paste block). Code that is already HTML and CSS (TailAdmin's HTML edition, a static Astro build output) goes in as it is, with its built stylesheet. Framework code (Astro, Next.js, shadcn/ui blocks, Tremor) needs rendering once: build or run it and follow "Producing a draft from an existing interface" in `references/live-draft.md` — dump the rendered DOM, strip the app runtime, keep the built CSS, capture menus and dialogs while open. Rendering needs a shell with Node and network access; without one, ask the user to run it and send the output, or take the live demo instead. Install with the repository's lockfile and its package manager (`pnpm-lock.yaml` → `pnpm install --frozen-lockfile`, `package-lock.json` → `npm ci`): a plain install resolves version ranges to newer releases, a newer build tool can emit different CSS, and the copy then breaks in ways the template does not.
2. **The live demo's rendered page.** In a browser you drive, let the page settle (fonts loaded, reduced motion emulated, lazy content scrolled into view), save `document.documentElement.outerHTML`, and download every stylesheet, font, image and icon it references next to it, rewriting the URLs to the local copies. Inline SVG icons come with the DOM. Then strip the scripts the draft does not need and add the draft runtime (`references/live-draft.md`).

Then:

- **Change content and structure where they live.** With the template's source, replace product name, copy, demo data and navigation entries in its data files and components, and rearrange, remove and add sections in the page file that composes them, before rendering: one render then produces the planned page and every captured state. Build a composed section as a new component from the template's own components and classes. With a saved demo page, the saved HTML is the source: edit and rearrange it directly, building composed sections from markup copied out of it.
- **Keep the copy's markup and CSS.** Do not rewrite the reference's classes into your own, and do not rewrite its CSS to fit the levers: every rewrite is a chance to lose a detail nobody noticed was there.
- **Bind the levers to what the CSS already exposes** — treat it as an extracted product (`references/tokens.md`). shadcn/ui, for example, exposes a numeric `--radius` in `rem`; Tailwind CSS v4 builds emit the theme variables the page uses (`--spacing`, `--color-*`, `--text-*`) — except those declared with `@theme inline`, which are inlined into the utilities and never exist at run time (shadcn/ui declares its radius and colour aliases that way, so bind its own `--radius`, `--background`, `--primary` instead); search the built CSS for a property before binding a lever to it; Tailwind v3 builds compile the theme into literal values and expose almost nothing. This is the extracted-product case of `references/tokens.md`, not the thirteen-lever `:root` of a design delivered as a page: the draft's own `:root` holds only the bridges from levers to the template's properties and a comment for each lever left unbound. Bind what exists, record every unbound lever in the contract, and tell the user which sliders the draft has. Fewer sliders on a faithful copy beat thirteen on a page that no longer looks like its reference.
- **Make the extraction repeatable** when it is more than one save: keep the steps after the render — dump, strip, add `data-node` anchors, capture fragments — as a small script, so a second render costs one command.

After the first extraction, decide where each later change goes, because the built stylesheet only contains the utility classes the template already used — a class that was not in the source (`text-4xl` when the build never needed it) does nothing in the draft:

- **Values and styling** (sizes, colours, spacing, one element's weight): write plain CSS in a local `<name>-patches.css` linked after the built stylesheet, in terms of the bound properties. The draft stays the source; no re-render.
- **Structure, content or behaviour that lives in components** (a new column, a different menu, copy repeated across states): change the template's source, re-render, and rerun the extraction script, then re-apply `<name>-patches.css`. Never fix the same thing twice, once in the source and once by hand in the dump.
- Record which of the two each patch took in the contract, and **note which parts are copied code** and where they came from (repository, block name, demo URL), so whoever ports the draft can go back to the original components instead of reverse-engineering the dump.

### Route B — rebuild from screenshots

Take this route only for a part there is no code for.

- **Start from the lever block.** Write `:root` from the measured values first, then every section in terms of it (`references/tokens.md`).
- **Reproduce each copied section exactly** — the same header layout, the same bands and insets, the same alignment, the same devices — with the user's content, and compose new sections only from what the screenshots show. The screenshot is the specification; anything you would "simplify" is a detail you are dropping.

### Adapting, on either route

- **One reference owns the page, and its look is not yours to change.** Keep its design language in every section, copied or composed: header layout, borders and their absence, background and surface colours, accent colours (including one used only on a badge), type, illustration and icon style, band widths and insets, spacing rhythm. Pick no colour, typeface, border or background of your own. A change to any of these is a design decision: propose it to the user, do not make it. A section borrowed from a second reference is restyled in the owner's tokens (`references/tokens.md`, "Mapping an external component").
- **Use the user's content, not the reference's.** The product's name, its copy, its data, at real lengths, in place of the reference's text. Where details do not exist yet — feature names, prices, example records — write plausible ones and list them under "Samples that must be confirmed" in the contract, so the page is seen at full density.
- **Keep the reference's pictures and icons until the user has their own.** Sort each picture first. *Decoration* — illustrations, abstract interface sketches, glows, background shapes, patterns — is design language: keep it and place it as the plan says. *Content* — photographs, product screenshots, avatars, customer logos — is the reference's material: it stays in its slot as a placeholder, listed in the contract as "to replace", unless its subject would mislead (a conference photo on a field-research product); then use a placeholder of the same size, radius and treatment, labelled with what goes there, and tell the user. Replacing either with something of a different kind — a rectangular card where an irregular illustration was, a text wordmark where an icon mark was — changes the page's look. Icons are replaced by icons from the same set and in the same treatment, chosen for what each item says. Offer the product's own interface as a picture only where the reference's slot has the same shape and role, and let the user decide.
- **Proof is never sampled.** Customer logos, testimonials, quotes, press, ratings, user counts and business figures are claims about the world: a sampled one is a fabrication that survives into production because it looks finished. Use what the user named in step 1. Without it, ask the user whether to drop the section or keep it as a placeholder that cannot pass for proof — the reference's layout with a short note saying what will go there ("Field stations using Fieldnote will be listed here once they agree to it"), no invented names or logos — and list it in the contract as waiting for real material.
- **Check the typefaces cover the content's script.** A reference set in a Latin-only display face gives Chinese, Japanese or Arabic copy whatever fallback the browser finds, and the page's type changes character. Choose a fallback for that script close to the reference face in weight and width, put it in the font stack right after the reference face, and tell the user: it is a design decision, so it goes into the contract.
- **Fit the copy to the composition.** The reference's headlines are set for its own words. Count the main reference's hero headline — characters and lines at desktop and phone width — and write the new one within it. A longer headline changes the composition; show the user, do not shrink the type to hide it.
- **Carry the interaction details over.** Hover and press states, transition timings, focus styles: on route A they come with the code — keep them through extraction; on route B measure and reproduce them.
- **Keep it a draft**: one entry page with local CSS and JS, fonts copied into the draft directory with their licence file next to them, images stored locally (`SKILL.md`, Step 1).

## 5. Compare with the reference

Before showing the draft, screenshot it and the main reference at the same widths — the desktop width and 375px at least — and check three things:

- **Copied sections against their originals.** Only the text and the line breaks its length causes may differ. A border added or lost, a navigation moved, an icon missing, an illustration replaced by a box, a band full-bleed where the original is inset, a spacing or size a step off: drift.
- **Composed and rearranged sections against the design language**, line by line: colours, type steps, borders and their absence, radii, shadows, spacing rhythm, icon and illustration treatment, band widths. A value or device that is not in the list is drift, however good it looks.
- **The whole page.** Every signature device has its place (step 4), and the two full-page screenshots, side by side at a small scale, read as the same family. A draft that passes the first two checks and fails this one has kept the parts and lost the character. Read the forms down the draft: neighbours that share a form, or a run of sections drawn mostly in lines, is drift even when each section is on-language. Look at where the pictures, glows and bands fall down each page: a stretch of the draft that is only text and lines, longer than any the reference has, is the most common way this happens. Otherwise find which device or proportion went missing.

The only other intended differences are decisions the user made in this conversation, recorded in the contract. Fix the drift and compare again; stop after three rounds and list what still differs, so the user sees it before the first review. Without a browser tool, send the user both links and ask what looks different.

## 6. Hand over to intake

From here the draft is like any other (`SKILL.md`, Step 1), and most of intake is already done: the levers are bound (to the copied CSS's properties on route A, to measured values on route B), the content is real. What remains:

- anchor sections and components with `data-node`;
- enumerate the conditional surfaces the reference showed and make each reachable (`references/live-draft.md`);
- fill in `design-contract.md`: the argument and the section plan, the design language, the references, what was taken from each and whether as code or as measurement, the placeholders still to replace, the levers marked `design` (measured) or `product` (the copied CSS's own properties) and those left unbound, and the main reference's devices — badges, icon rows, gradients, illustrations, shadows, extra radii — under "Standing decisions". They are the design, not drift, and the audit limits do not apply to them (`references/audit.md`).
