# The draft is a live page, not a picture of one

A design draft is reviewed by using it. If a control does not move, a menu does not open, or a click reloads the page, the reviewer is judging a screenshot — and every judgement about motion, feedback and state is made blind.

This file holds the rules for keeping a draft usable, the recipe for producing one from an existing interface, and how to verify it. The panel that sits on top is in `references/panel.md`.

## Six rules

### 1. Nothing navigates

A draft is one page. A link that follows its `href` throws away the current selection, the slider values and the open state — the reviewer lands on a 404 or on the live app.

Intercept link clicks once, on the document, in the capture phase — not on each link, because a stretched link or a link added later slips past per-element handlers. Leave in-page anchors alone: `#pricing` scrolling to its section is part of the page.

```js
document.addEventListener('click', e => {
  const a = e.target.closest('a[href]');
  if (!a) return;
  const href = a.getAttribute('href');
  if (href.length > 1 && href.startsWith('#') && document.getElementById(href.slice(1))) return;
  e.preventDefault();
}, true);
```

This is draft behaviour, not review tooling: it lives in the draft runtime and stays at hand-off.

### 2. Picking is an explicit mode, off by default

Outside picking mode the page must behave exactly as the product does — hover, menus, dialogs, focus. Otherwise the reviewer can never test an interaction, only pick elements. Inside picking mode the page must not react at all, or picking a menu item also fires it. The shipped panel does both.

### 3. Picking must survive overlay hit-testing

The element under the cursor is not always the element you see. A row made clickable with a stretched link (`a::after { content: ''; position: absolute; inset: 0 }`) puts the link on top of every cell, so `e.target` and `closest('[data-node]')` both resolve to the link whichever cell was clicked. The panel resolves this with `elementsFromPoint()` and a box-containment check; when you build a picker of your own, do the same.

### 4. Every element is addressable, not just the components

Components carry `data-node`; that is a coarse address. Anything inside one is addressed by a selector from the component down to the leaf, plus the computed values that describe it now. Anchor names come from the component's role, plus `#n` for its position among siblings of the same role (`pricing/row#2`) — never from its order in the file, which changes with every edit above it.

### 5. Reproduce the states that need script, and say which are approximations

Menus, dialogs, drawers, toasts and empty states exist only after interaction; a DOM dump does not contain them. Rebuild them with the product's own classes — copied from the component that owns them — so they land on the real design, not on an invented one.

Then tell the reviewer, in one line, which of them are approximations — focus traps, scroll locking, form submission and data writes are usually absent — and record the same list in the contract.

### 6. What cannot be triggered from the page gets an external control

If the page does not contain the entry point, or the state needs data the draft does not have, add a panel state button that forces it: theme, sidebar collapse, menu open, dialog open, empty state, loading state.

A state the reviewer cannot reach is a state they will not review, and the most expensive defects live exactly there.

## The draft runtime

Behaviour the product implements in JavaScript belongs next to the draft, in `<name>-runtime.js` and `<name>-runtime.css`: link neutralisation, menus, dialogs, drawers, empty states, theme switching. It is part of what the port must reproduce, which is exactly why it must not hide inside the review tooling. Panel state buttons call into it; they do not replace it.

## Every conditional surface belongs to the draft

A draft contains everything the view can show, not only what the first paint shows. Confirm dialogs, selection toolbars, batch actions, drawers, popovers, empty and error states are all part of that page; leaving them out means the reviewer signs off on a screen that does not exist as a whole.

Enumerate them from the source, then confirm each one by driving the app — a surface nobody opened is a surface nobody checked:

1. Read the view for every conditional render (`{#if}`, `v-if`, `&&` or a ternary in JSX, `*ngIf`, a template `{% if %}`), every dialog, menu or drawer component it mounts, and every state variable that guards markup.
2. In the running app, trigger each one and capture its `outerHTML` while it is open.
3. Store the captures as data (`<name>-fragments.js`), not as markup pasted into the draft: they are regenerated, never hand-edited. When a captured surface needs changing, change the source it was captured from and capture again (`references/drafting.md`, route A).
4. Wire the triggers — the row's own buttons, the checkboxes, the keyboard — so the reviewer reaches each surface the way a user would.
5. Add a state button for anything that cannot be reached without data the draft does not have.

Two traps:

- **A captured fragment carries the entity it was captured from.** A confirmation captured as `Delete "Project Alpha"?` must show the name of whatever row the reviewer actually clicked.
- **Selection state may be plain attributes.** A row styled through `:has([data-state=checked])` needs only `data-state` flipped on its checkbox; adding a class of your own produces a state the product can never have.

## A rule that matches nothing fails silently

A state rule written from memory rather than from the captured markup often matches nothing. `#sidebar-projects` guessed from a component name is a no-op when the dump carries `data-testid="sidebar-projects"` — and a no-op selector looks exactly like a correct one. Ids are no safer: component libraries (Radix, Base UI, Headless UI, React's `useId`) generate them per render, so `#radix-:r1:` matches today's dump and nothing after the next render.

- **Select from the dump; prefer `data-node`, then `data-testid` or `data-slot`, never a generated id.** Read the attribute off the captured element; do not infer it.
- **Assert the rule hit something.** After writing a state rule, check that `document.querySelectorAll(selector).length` is non-zero and that the target's computed style actually changed. A `0` is a failed state, not a cosmetic detail.
- **Capture the state, do not imitate it.** A product's collapsed, narrow or compact layout usually changes more than visibility — labels become separators, badges and wordmarks disappear, padding is re-decided. Hiding text in the expanded capture is not the same layout; capture the state from the product.

## Producing a draft from an existing interface

1. **Render the real thing.** Serve the built frontend and answer its API calls with a small mock that returns realistic sample data, so every component renders with real content instead of skeletons.
2. **Dump the live DOM.** `document.documentElement.outerHTML` after the view has settled. This keeps the real classes and the real markup, which is what makes the draft faithful.
3. **Strip the app runtime.** Remove every `<script>`, the module preloads and the framework's mount-point behaviour. Left in place, the app re-fetches and re-renders, wiping every edit.
4. **Keep the real stylesheet.** Copy the built CSS next to the draft and link it relatively. Do not re-derive styles by hand — that is how a draft drifts from the product it claims to represent.
5. **Add anchors** (`data-node`) on the section and component roots, then the draft runtime (rule 1, rule 5), the conditional surfaces, and the panel bound to the product's own custom properties (`references/tokens.md`).

## Verify by looking

A measurement is not a verification. A collapsed sidebar can measure `64px` while the picture shows a full-width column with squeezed text, because the width lives on the outer element and the measurement was taken on the one inside it.

- **Measure the node that owns the property.** When a computed value disagrees with the picture, the selector is wrong, not the picture.
- **Check overflow, not just width.** Shrinking a container re-lays-out only what was shrunk; a row of avatar, gap, label and chevron can still spill past the new edge. Walk every descendant and compare `getBoundingClientRect().right` against the container's — the list of offenders must come back empty.
- **Look at every reviewed width**, not just the one the draft was built at — the widths are listed in `references/audit.md`. A desktop-only review signs off a phone layout nobody saw.
- **Screenshot after every state change and look at it.** Widths, colours and computed styles can all pass while the state is visually broken. Without a browser of your own, ask the user for the screenshot and say which states you could not see.

## Checklist before calling a draft ready

- [ ] No link in the draft navigates or reloads.
- [ ] Picking is off by default; in picking mode the page does not react; leaving it clears the marks and keeps the readout.
- [ ] Clicking a cell inside a stretched-link row selects the cell, and the row link is still pickable from the layer list.
- [ ] Every state the product reaches by interaction has either a working entry point or a panel button.
- [ ] Every conditional surface of the view is present and reachable from the page itself.
- [ ] Captured fragments substitute the entity the reviewer clicked.
- [ ] State buttons agree with the page after a change made outside the panel.
- [ ] Transitions and press feedback come from the product's own CSS, not from a reimplementation.
- [ ] Every state rule is verified to match: `querySelectorAll(selector).length > 0` and the computed value changed.
- [ ] Collapsed, narrow and long-content states are captured from the product, and no descendant's right edge crosses its container's.
- [ ] Every state is checked at every reviewed width.
- [ ] Approximations are named to the reviewer and in the contract.
- [ ] After each state change: screenshot, then look.
