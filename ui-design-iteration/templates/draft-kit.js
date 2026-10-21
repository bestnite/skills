/* Draft kit — the review panel for a design draft.
 *
 * One file, no dependencies, no build step. Copy it next to the draft and attach
 * it after the draft's own markup:
 *
 *   <script>window.DRAFT_KIT = { tokens: [...], states: [...] };</script>
 *   <script src="draft-kit.js" defer></script>
 *
 * Delete those two blocks and what remains is the draft: the port target must
 * never inherit the review tooling.
 *
 * What it does
 *   - sliders bound to the page's own custom properties, seeded from the page
 *   - picking mode, off by default (toggle button, `P`, `Esc` leaves), with
 *     point-accurate hit-testing, a layer list and a parent step
 *   - marks: several elements, each with the reviewer's note, numbered on the page
 *   - contrast of the selected element's text against its effective background
 *   - an audit of the current state: distinct radii, shadows, type sizes and
 *     families, gradients, animations, contrast failures
 *   - posts a review snapshot (selection, marks, moved sliders, state flags,
 *     viewport, last audit) to the server, which writes selection.json
 *   - reloads the page when the HTML or a same-origin CSS/JS file changes, but
 *     asks first while sliders hold values that a reload would discard
 *
 * The panel and its overlays live in a shadow root, so page CSS cannot restyle
 * them and they never add classes or nodes the picker or the audit could see.
 *
 * Config (window.DRAFT_KIT, all optional):
 *   tokens  [{key, min, max, step, def, unit?, prop?, label?, suffix?, apply?}]
 *             prop   custom property to read and write, default `--${key}`
 *             unit   CSS unit the value carries ('px', '%', 'ch', 'ms', '' …)
 *             def    shown only when the page value cannot be read in `unit`
 *             apply  (value|null, setVar) => void, for a token that writes
 *                    several properties; null means "back to the page value"
 *   states  [{id, label, run(), on()}]   buttons for states the page cannot reach
 *   post    snapshot endpoint, default '/__select'; null disables posting
 *   gutter  px reserved beside the panel while it is open (≥1180px wide), default 336
 *   side    'right' (default) or 'left'; the reviewer can swap it from the panel
 *   watch   false disables live reload
 *   ignoreClass  RegExp of utility classes skipped when building a path
 *
 * Keys: `P` picking, `Esc` leaves picking, `H` hides the kit completely (for
 * screenshots) and shows it again.
 *
 * API for an agent driving a browser: window.draftKit.snapshot(), .audit(),
 * .hide(true|false). Picking and marking have no API on purpose: they are the
 * reviewer's acts. To simulate them, drive the pointer and the keyboard.
 */

(() => {
  'use strict';
  if (window.draftKit) return;

  const CONFIG = window.DRAFT_KIT || {};
  const SELF = document.currentScript ? document.currentScript.src : '';
  const POST_URL = CONFIG.post === undefined ? '/__select' : CONFIG.post;
  const GUTTER = CONFIG.gutter === undefined ? 336 : CONFIG.gutter;
  const WATCH = CONFIG.watch !== false;
  // Utility classes say how something is laid out, not what it is. The default
  // covers Tailwind-style names; a draft with other conventions passes its own.
  const UTILITY = CONFIG.ignoreClass || new RegExp(
    '^(flex|grid|block|inline|inline-block|inline-flex|inline-grid|hidden|contents|table|flow-root|relative|absolute|' +
    'fixed|sticky|static|visible|invisible|isolate|truncate|grow|shrink|border|rounded|shadow|ring|outline|' +
    'transition|uppercase|lowercase|capitalize|normal-case|italic|not-italic|underline|no-underline|line-through|' +
    'antialiased|subpixel-antialiased|tabular-nums|lining-nums|oldstyle-nums|proportional-nums|slashed-zero|' +
    'container|sr-only|not-sr-only|group|peer)$' +
    '|^-?(items|justify|self|place|content|order|col|row|auto|gap|space|divide|[mp][trblxyse]?|[wh]|min|max|size|' +
    'inset|top|right|bottom|left|start|end|z|overflow|overscroll|whitespace|break|text|font|leading|tracking|' +
    'align|caption|table|list|decoration|underline|bg|from|via|to|border|rounded|shadow|ring|outline|opacity|' +
    'transition|duration|ease|delay|animate|cursor|select|pointer|touch|resize|scroll|snap|appearance|will|' +
    'basis|flex|grid|line-clamp|aspect|object|fill|stroke|accent|caret|columns|box|float|clear|backdrop|blur|' +
    'drop|translate|scale|rotate|skew|origin|transform|mix|isolation)-' +
    '|^@|[:[\\]/]');
  const MARKS_KEY = `draft-kit:marks:${location.pathname}`;

  const root = document.documentElement;
  const TOKENS = (CONFIG.tokens || []).map(t => {
    const prop = t.prop || `--${t.key}`;
    const decimals = (String(t.step).split('.')[1] || '').length;
    return { ...t, prop, label: t.label || prop, unit: t.unit || '', decimals, digits: decimals,
             min0: t.min, value: t.def, orig: t.def, moved: false, read: false };
  });
  const STATES = CONFIG.states || [];

  // ---------------------------------------------------------------- tokens ---
  const setVar = (name, value) => value === null
    ? root.style.removeProperty(name)
    : root.style.setProperty(name, value);
  // null removes the inline override instead of writing the default: an inline
  // default would shadow the page's own theme block, so `.dark` stops working.
  const writeToken = (t, v) => t.apply
    ? t.apply(v, setVar)
    : setVar(t.prop, v === null ? null : v + t.unit);

  // Read the page, do not assume it. A value is trusted only in the unit the
  // slider speaks: `0.5rem` read into a px slider would be a number the reviewer
  // acts on and the page ignores.
  function seed(t, cs){
    if (t.moved) return;
    const raw = cs.getPropertyValue(t.prop).trim();
    const m = raw.match(/^(-?\d*\.?\d+)\s*([a-z%]*)$/i);
    t.read = !!(m && m[2].toLowerCase() === t.unit.toLowerCase());
    t.orig = t.read ? parseFloat(m[1]) : t.def;
    if (t.orig > t.max) t.max = t.orig;
    // A range input snaps to min + k·step. Shift min so the page's own value
    // sits on that grid; otherwise a measured 3.333 is drawn at 3.5.
    const below = Math.ceil((t.orig - Math.min(t.min0, t.orig)) / t.step - 1e-9);
    t.min = +(t.orig - below * t.step).toFixed(6);
    const shown = (String(t.orig).split('.')[1] || '').length;
    t.digits = Math.max(t.decimals, Math.min(3, shown));
    t.value = t.orig;
  }
  function slide(t, v){
    t.value = v;
    t.moved = v !== t.orig;
    writeToken(t, t.moved ? v : null);
    render();
    schedulePost(400);
  }
  function resetTokens(){
    for (const t of TOKENS) if (t.moved) { t.moved = false; writeToken(t, null); }
    refresh();
    schedulePost(0);
  }

  const isOn = s => { try { return !!(s.on && s.on()); } catch { return false; } };
  const stateFlags = () => Object.fromEntries(STATES.map(s => [s.id, isOn(s)]));

  // ------------------------------------------------------------- geometry ---
  let host = null;
  const stackAt = (x, y) => document.elementsFromPoint(x, y)
    .filter(el => el !== root && el !== document.body && el !== host);
  const covers = (el, x, y) => {
    const r = el.getBoundingClientRect();
    return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
  };
  // The element under the cursor is not always the one you see: a stretched
  // link (`::after { inset: 0 }`) sits over every cell of its row. Prefer the
  // first element whose own box covers the point.
  function hit(x, y){
    const stack = stackAt(x, y);
    return { stack, el: stack.find(el => covers(el, x, y)) || stack[0] || null };
  }

  const meaningfulClass = el => [...el.classList].find(c => !UTILITY.test(c)) || null;
  function segment(el){
    const tag = el.tagName.toLowerCase();
    const cls = meaningfulClass(el);
    const parent = el.parentElement;
    const twins = parent ? [...parent.children].filter(x => x.tagName === el.tagName) : [];
    const nth = twins.length > 1 ? `:nth-child(${[...parent.children].indexOf(el) + 1})` : '';
    return tag + (cls ? '.' + CSS.escape(cls) : '') + nth;
  }
  // Ids minted by component libraries (Radix, Base UI, Headless UI, React's
  // useId …) change on every render, so they are never used as a root.
  const GENERATED_ID = /^(radix-|base-ui-|headlessui-|react-aria|mui-|_?[rR]_|«|:)|[:«»]|\d{3,}|[0-9a-f]{8,}/;
  // A real CSS selector, rooted at the nearest anchor: the agent can hand it to
  // querySelector, and it survives edits outside the owning component. A stable
  // id is a root only when no data-node sits above the element.
  function pathOf(el){
    const anchored = !!el.closest('[data-node]');
    const parts = [];
    for (let cur = el; cur && cur !== document.body && cur !== root; cur = cur.parentElement) {
      if (cur.dataset.node) { parts.unshift(`[data-node="${cur.dataset.node.replace(/["\\]/g, '\\$&')}"]`); break; }
      if (!anchored && cur.id && !GENERATED_ID.test(cur.id)) { parts.unshift('#' + CSS.escape(cur.id)); break; }
      parts.unshift(segment(cur));
    }
    return parts.join(' > ');
  }
  const compact = path => {
    const parts = path.split(' > ');
    return parts.length > 4 ? `${parts[0]} > … > ${parts.slice(-2).join(' > ')}` : path;
  };
  const ownText = el => [...el.childNodes].filter(n => n.nodeType === 3)
    .map(n => n.textContent).join('').trim().replace(/\s+/g, ' ');
  const labelOf = el => {
    const cls = meaningfulClass(el);
    const own = ownText(el).slice(0, 22);
    return el.tagName.toLowerCase() + (cls ? '.' + cls : '') + (own ? ` "${own}"` : '');
  };

  // -------------------------------------------------------------- contrast ---
  // Any CSS colour the browser understands (oklch, color-mix, named …) is
  // resolved by painting it on a 1×1 canvas and reading back sRGB.
  let paint = null;
  function rgba(color){
    paint = paint || document.createElement('canvas').getContext('2d', {willReadFrequently: true});
    paint.clearRect(0, 0, 1, 1);
    paint.fillStyle = '#000';
    paint.fillStyle = color;
    paint.fillRect(0, 0, 1, 1);
    const d = paint.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255];
  }
  const over = (top, under) => {
    const a = top[3] + under[3] * (1 - top[3]);
    if (!a) return [0, 0, 0, 0];
    return [0, 1, 2].map(i => (top[i] * top[3] + under[i] * under[3] * (1 - top[3])) / a).concat(a);
  };
  const luminance = c => {
    const [r, g, b] = c.slice(0, 3).map(v => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const ratioOf = (fore, back) => {
    const [hi, lo] = [luminance(over(fore, back)), luminance(back)].sort((x, y) => y - x);
    return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
  };
  const COLOR = /(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^()]*\)|#[0-9a-f]{3,8}\b|\btransparent\b/gi;
  // Split on commas outside any parentheses: `linear-gradient(a, b), url(c)`.
  const splitTop = v => {
    const out = [];
    let depth = 0, cur = '';
    for (const ch of v) {
      if (ch === '(') depth++;
      else if (ch === ')') depth--;
      if (ch === ',' && !depth) { out.push(cur.trim()); cur = ''; } else cur += ch;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  };
  const SIDES = {top: 0, right: 90, bottom: 180, left: 270};
  // The colour a linear gradient paints at a point, interpolated between its
  // stops along the gradient line (sRGB; browsers may interpolate in another
  // space, so expect a small error). Null for anything it cannot place.
  function linearAt(image, box, x, y){
    const m = image.match(/^linear-gradient\((.*)\)$/);
    if (!m || !box) return null;
    const args = splitTop(m[1]);
    let deg = 180;
    const head = args[0];
    const to = head.match(/^to ((?:top|bottom|left|right)(?: (?:top|bottom|left|right))?)/);
    const angle = head.match(/^(-?[\d.]+)(deg|turn|rad|grad)/);
    if (to) {
      const w = to[1].split(' ').map(k => SIDES[k]);
      // a corner points along the box diagonal
      deg = w.length === 1 ? w[0]
        : (Math.atan2((w.includes(90) ? 1 : -1) * box.width, (w.includes(0) ? 1 : -1) * box.height) * 180 / Math.PI + 360) % 360;
      args.shift();
    } else if (angle) {
      const k = {deg: 1, turn: 360, rad: 180 / Math.PI, grad: 0.9}[angle[2]];
      deg = parseFloat(angle[1]) * k;
      args.shift();
    } else if (/^in /.test(head)) args.shift();
    const th = deg * Math.PI / 180, dx = Math.sin(th), dy = -Math.cos(th);
    const len = Math.abs(box.width * dx) + Math.abs(box.height * dy);
    if (!len) return null;
    const cx = box.left + box.width / 2, cy = box.top + box.height / 2;
    const at = ((x - cx) * dx + (y - cy) * dy) / len + 0.5;
    const stops = [];
    for (const arg of args) {
      const col = (arg.match(COLOR) || [])[0];
      if (!col) continue;   // a colour hint, not a stop
      const pos = (arg.replace(col, '').match(/-?[\d.]+(%|px)/g) || [])
        .map(p => p.endsWith('%') ? parseFloat(p) / 100 : parseFloat(p) / len);
      const c = rgba(col);
      if (!pos.length) stops.push({c, p: null});
      for (const p of pos) stops.push({c, p});
    }
    if (stops.length < 2) return null;
    if (stops[0].p === null) stops[0].p = 0;
    if (stops[stops.length - 1].p === null) stops[stops.length - 1].p = 1;
    for (let i = 1; i < stops.length; i++) {
      if (stops[i].p !== null) { stops[i].p = Math.max(stops[i].p, stops[i - 1].p); continue; }
      let j = i; while (stops[j].p === null) j++;
      for (let k = i; k < j; k++) stops[k].p = stops[i - 1].p + (stops[j].p - stops[i - 1].p) * (k - i + 1) / (j - i + 1);
    }
    if (at <= stops[0].p) return stops[0].c;
    for (let i = 1; i < stops.length; i++) {
      if (at > stops[i].p) continue;
      const a = stops[i - 1], b = stops[i], f = b.p > a.p ? (at - a.p) / (b.p - a.p) : 1;
      // premultiplied, as browsers interpolate: a 5%-alpha stop barely tints
      const alpha = a.c[3] + (b.c[3] - a.c[3]) * f;
      if (!alpha) return [0, 0, 0, 0];
      return [0, 1, 2].map(n => (a.c[n] * a.c[3] + (b.c[n] * b.c[3] - a.c[n] * a.c[3]) * f) / alpha).concat(alpha);
    }
    return stops[stops.length - 1].c;
  }
  // One element's paint layers, top first, as the colours each can contribute:
  // a solid colour is one candidate; a linear gradient is its colour at the
  // point when the point is known; any other gradient gives one candidate per
  // colour stop (the worst is reported); an image is unknowable.
  function layersOf(cs, out, box, x, y){
    const image = cs.backgroundImage;
    if (image && image !== 'none') {
      for (const one of splitTop(image)) {
        if (/^url\(/.test(one)) { out.push({unknown: 'image behind the text'}); continue; }
        const here = x === undefined ? null : linearAt(one, box, x, y);
        const stops = here ? [here] : (one.match(COLOR) || []).map(rgba);
        if (stops.length) out.push({stops, gradient: here ? 'interpolated' : 'stops', opaque: stops.every(c => c[3] >= 1)});
      }
    }
    const bg = rgba(cs.backgroundColor);
    if (bg[3] > 0) out.push({stops: [bg], opaque: bg[3] >= 1});
  }
  const shown = ps => ps.content !== 'none' && ps.content !== 'normal';
  // Paint layers under the point, top to bottom, from the hit-test stack: a
  // dark band drawn by a sibling or by a ::before is behind the text even
  // though no ancestor has a background. Null when the text is not the
  // topmost hit there (covered by a header, pointer-events: none …).
  function layersAt(el, x, y){
    const stack = document.elementsFromPoint(x, y).filter(e => e !== host);
    const i = stack.indexOf(el);
    if (i < 0) return null;
    const out = [];
    for (const e of stack.slice(i)) {
      const own = covers(e, x, y), box = e.getBoundingClientRect();
      for (const pseudo of ['::after', '::before']) {
        const ps = getComputedStyle(e, pseudo);
        // a positioned pseudo-element usually paints a whole band; when the
        // element's own box misses the point, the hit came through one of them
        // (its own box is not measurable; the owner's stands in)
        if (shown(ps) && (!own || /absolute|fixed/.test(ps.position))) layersOf(ps, out, box, x, y);
      }
      if (own) layersOf(getComputedStyle(e), out, box, x, y);
      if (out.some(l => l.opaque || l.unknown)) break;
    }
    return out;
  }
  // Fallback for text that cannot be hit-tested: the ancestor chain only.
  function layersUp(el){
    const out = [];
    for (let cur = el; cur; cur = cur.parentElement) {
      for (const pseudo of ['::after', '::before']) {
        const ps = getComputedStyle(cur, pseudo);
        if (cur !== el && shown(ps) && /absolute|fixed/.test(ps.position)) layersOf(ps, out);
      }
      layersOf(getComputedStyle(cur), out);
      if (out.some(l => l.opaque || l.unknown)) break;
    }
    return out;
  }
  // Points along the element's own text, not its box: a wide block with a short
  // line of text should be judged where the glyphs are.
  function textRects(el){
    const rects = [];
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(n);
      for (const r of range.getClientRects()) if (r.width > 0 && r.height > 0) rects.push(r);
    }
    return rects;
  }
  // Screen-reader-only text (`sr-only`: a clipped 1×1 box) is not seen, so it
  // has no contrast and no type size to count. Its text still lays out at full
  // size, so the clipping box, not the text, gives it away.
  const visuallyHidden = el => {
    const rects = textRects(el);
    if (!rects.length || rects.every(r => r.width <= 1 || r.height <= 1)) return true;
    for (let cur = el, i = 0; cur && i < 4; cur = cur.parentElement, i++) {
      const cs = getComputedStyle(cur), b = cur.getBoundingClientRect();
      if ((b.width <= 1 || b.height <= 1) && cs.overflow !== 'visible') return true;
      if (/rect\(0(px)?,? 0(px)?,? 0(px)?,? 0(px)?\)/.test(cs.clip) || cs.clipPath === 'inset(50%)') return true;
    }
    return false;
  };
  const onScreen = r => r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth;

  // WCAG 2 ratio of the element's text against what paints behind it. Layers
  // are composited bottom-up onto white; a gradient yields one candidate per
  // colour stop and the worst one is reported, so a failure over a gradient is
  // conservative and worth a look at the screenshot.
  function contrastOf(el){
    const cs = getComputedStyle(el);
    if (cs.webkitBackgroundClip === 'text' || cs.backgroundClip === 'text')
      return {ratio: null, reason: 'gradient text'};
    let layerSets = [], method = 'stack';
    for (const r of textRects(el).slice(0, 3)) {
      for (const f of [0.25, 0.5, 0.75]) {
        const x = r.left + r.width * f, y = r.top + r.height / 2;
        if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) continue;
        const l = layersAt(el, x, y);
        if (l) layerSets.push(l);
      }
    }
    if (!layerSets.length) { layerSets = [layersUp(el)]; method = 'ancestors'; }
    const fore = rgba(cs.color);
    let worst = null, best = null, gradient = false;
    for (const set of layerSets) {
      const unknown = set.find(l => l.unknown);
      if (unknown) return {ratio: null, reason: unknown.unknown};
      let backs = [[255, 255, 255, 1]];
      for (const layer of set.slice().reverse()) {
        if (layer.gradient === 'stops') gradient = true;
        backs = layer.stops.flatMap(stop => backs.map(b => over(stop, b))).slice(0, 64);
      }
      for (const back of backs) {
        const ratio = ratioOf(fore, back);
        if (!worst || ratio < worst.ratio) worst = {ratio, back};
        if (!best || ratio > best.ratio) best = {ratio, back};
      }
    }
    const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight, 10) || 400;
    const required = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
    const result = {ratio: worst.ratio, required, passes: worst.ratio >= required,
      against: `rgb(${worst.back.slice(0, 3).map(Math.round).join(' ')})`, method};
    if (gradient) { result.gradient = true; result.range = [worst.ratio, best.ratio]; }
    return result;
  }

  function computedOf(el){
    const cs = getComputedStyle(el);
    const px = v => (Math.round(parseFloat(v) * 10) / 10) + 'px';
    const r = el.getBoundingClientRect();
    return {
      'font-size': px(cs.fontSize),
      'line-height': cs.lineHeight === 'normal' ? 'normal' : px(cs.lineHeight),
      'font-weight': cs.fontWeight,
      'font-family': cs.fontFamily,
      'color': cs.color,
      'background-color': cs.backgroundColor,
      'padding': [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft].map(px).join(' '),
      'border-radius': cs.borderRadius,
      'size': `${Math.round(r.width)}×${Math.round(r.height)}`,
    };
  }
  // Levers declared on every anchor above the element, nearest first: a FAQ
  // answer inside `faq/item#2` inside `faq` is tuned by both.
  function leversOf(el){
    const keys = [];
    for (let a = el.closest('[data-node]'); a; a = a.parentElement && a.parentElement.closest('[data-node]'))
      for (const k of (a.dataset.levers || '').split(',').map(s => s.trim()).filter(Boolean))
        if (!keys.includes(k)) keys.push(k);
    return keys;
  }
  function describe(el){
    if (!el || !el.isConnected) return null;
    const comp = el.closest('[data-node]');
    return {
      target: pathOf(el),
      component: comp ? comp.dataset.node : null,
      levers: leversOf(el),
      tag: el.tagName.toLowerCase(),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
      computed: computedOf(el),
      contrast: ownText(el) && !visuallyHidden(el) ? contrastOf(el) : null,
    };
  }

  // ----------------------------------------------------------------- audit ---
  // Split a computed box-shadow list into drawn shadows and rings: a layer with
  // no offset and no blur but a spread is an outline in disguise (Tailwind's
  // `ring-1`), and a layer that is all zeros draws nothing (`--shadow: 0`).
  function shadowsOf(value){
    const shadows = [], rings = [];
    if (!value || value === 'none') return {shadows, rings};
    for (const part of splitTop(value)) {
      const lengths = (part.replace(COLOR, '').match(/-?[\d.]+px/g) || []).map(parseFloat);
      const [x = 0, y = 0, blur = 0, spread = 0] = lengths;
      if (!x && !y && !blur && !spread) continue;
      (!x && !y && !blur ? rings : shadows).push(part.trim());
    }
    return {shadows, rings};
  }
  // One radius is one key, however many corners use it: `12px 12px 0px 0px`
  // (a box flush with an edge) is still the 12px radius. `rounded-full`
  // computes to an enormous length; call it what it is. '' means square.
  const radiusOf = v => {
    if (v.includes('/')) return v;   // elliptical corners: keep as computed
    const corners = v.split(' ').filter(c => parseFloat(c));
    if (corners.some(c => parseFloat(c) >= 1000)) return 'pill';
    return [...new Set(corners)].join(' ');
  };

  // Content the browser keeps laid out but does not paint — a closed <details>,
  // `content-visibility: hidden` — belongs to a state that is not active.
  const unpainted = el => el.checkVisibility ? !el.checkVisibility()
    : !!el.closest('details:not([open]) > :not(summary)');

  // Facts about the current state only: elements hidden by a state that is not
  // active are not counted, so run it once per state the reviewer signs off.
  // Limits and waivers are the agent's business (references/audit.md).
  function audit(){
    // Each key keeps its first element, so the agent can tell which part of
    // the page brought a value in (references/audit.md: tag keys by origin).
    const tally = () => new Map();
    const add = (map, key, el) => {
      const e = map.get(key);
      if (e) e.n++; else map.set(key, {n: 1, el});
    };
    const radii = tally(), shadows = tally(), rings = tally(), sizes = tally(), families = tally();
    const gradients = [], animated = [], texts = [];
    let elements = 0, hiddenText = 0;
    for (const el of document.body.querySelectorAll('*')) {
      if (el === host || /^(SCRIPT|STYLE|TEMPLATE|NOSCRIPT|LINK|META)$/.test(el.tagName)) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || !el.getClientRects().length || unpainted(el)) continue;
      elements++;
      const radius = radiusOf(cs.borderRadius);
      if (radius) add(radii, radius, el);
      const sh = shadowsOf(cs.boxShadow);
      if (sh.shadows.length) add(shadows, sh.shadows.join(', '), el);
      if (sh.rings.length) add(rings, sh.rings.join(', '), el);
      if (cs.backgroundImage.includes('gradient(')) gradients.push(pathOf(el));
      if (cs.animationName !== 'none') animated.push(pathOf(el));
      if (!ownText(el)) continue;
      if (visuallyHidden(el)) { hiddenText++; continue; }
      add(sizes, Math.round(parseFloat(cs.fontSize) * 10) / 10 + 'px', el);
      add(families, cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, ''), el);
      texts.push(el);
    }
    // Contrast needs the text on screen to hit-test what paints behind it, so
    // the page is walked one viewport at a time and the scroll put back after.
    const results = new Map();
    const start = {x: scrollX, y: scrollY};
    const scroller = document.scrollingElement || root;
    const step = Math.max(200, Math.floor(innerHeight * 0.8));
    for (let y = 0; y < scroller.scrollHeight; y += step) {
      window.scrollTo({left: 0, top: y, behavior: 'instant'});
      for (const el of texts) {
        if (results.has(el)) continue;
        const rects = textRects(el);
        if (rects.slice(0, 3).some(onScreen)) {
          const c = contrastOf(el);
          if (c.method === 'stack' || c.ratio === null) results.set(el, c);
        }
      }
      if (scroller.scrollHeight <= innerHeight) break;
    }
    window.scrollTo({left: start.x, top: start.y, behavior: 'instant'});
    const contrastFailures = [], contrastUnknown = [], contrastApproximate = [];
    for (const el of texts) {
      let c = results.get(el);
      const entry = () => ({target: pathOf(el), ratio: c.ratio, required: c.required});
      if (!c) {   // never reachable on screen: ancestors only
        c = contrastOf(el);
        contrastApproximate.push(entry());
      }
      if (c.ratio === null) contrastUnknown.push({target: pathOf(el), reason: c.reason});
      else if (!c.passes) contrastFailures.push(c.gradient ? {...entry(), gradient: true, range: c.range} : entry());
    }
    placeOverlays();
    // Colours read while a transition runs are in-between values: a theme
    // switched a moment ago reports dark surfaces over white. Report the count
    // so a result taken mid-transition is recognisable and gets re-run.
    const transitions = typeof CSSTransition === 'undefined' ? null : document.getAnimations()
      .filter(a => a instanceof CSSTransition && a.playState === 'running' &&
        !(a.effect && a.effect.target && host && host.shadowRoot &&
          a.effect.target.getRootNode() === host.shadowRoot)).length;
    const sorted = map => [...map].sort((a, b) => b[1].n - a[1].n);
    const rank = map => Object.fromEntries(sorted(map).map(([k, e]) => [k, e.n]));
    const firstOf = map => Object.fromEntries(sorted(map).map(([k, e]) => [k, pathOf(e.el)]));
    return {
      elements, viewport: viewport(), states: stateFlags(),
      radii: rank(radii), shadows: rank(shadows), rings: rank(rings),
      fontSizes: rank(sizes), fontFamilies: rank(families),
      examples: {radii: firstOf(radii), shadows: firstOf(shadows), rings: firstOf(rings),
        fontSizes: firstOf(sizes), fontFamilies: firstOf(families)},
      gradients, animated, contrastFailures, contrastUnknown,
      contrastApproximate, hiddenText, transitions,
    };
  }

  // ------------------------------------------------------------- snapshot ---
  let current = null, layers = [], layerPoint = null, warn = '', notice = '', lastAudit = null;
  let marks = [];      // [{note, target, el}] — el re-resolved from target after a reload

  // The width the reviewer saw. A vertical scrollbar and the open panel's
  // gutter both narrow the page; `content` is what the layout actually got.
  // To see it again without the panel: hide the kit and size the window to
  // content + scrollbar.
  function viewport(){
    const gutter = gutterOn() ? GUTTER : 0;
    const scrollbar = innerWidth - root.clientWidth;
    return {width: innerWidth, height: innerHeight, content: root.clientWidth - gutter,
            scrollbar, gutter, panel: hidden ? 'hidden' : open ? side : 'collapsed', dpr: devicePixelRatio};
  }
  function snapshot(){
    return {
      page: location.pathname,
      viewport: viewport(),
      selection: describe(current),
      marks: marks.map((m, i) => {
        const d = describe(resolve(m));
        return d ? {n: i + 1, note: m.note, ...d} : {n: i + 1, note: m.note, target: m.target, stale: true};
      }),
      overrides: Object.fromEntries(TOKENS.filter(t => t.moved).map(t => [t.prop, t.value + t.unit])),
      states: stateFlags(),
      audit: lastAudit,
    };
  }
  let postTimer = 0;
  function schedulePost(delay){
    clearTimeout(postTimer);
    postTimer = setTimeout(post, delay);
  }
  async function post(){
    if (!POST_URL) return;
    if (location.protocol === 'file:') { setWarn('opened from file:// — selections are not recorded'); return; }
    try {
      const res = await fetch(POST_URL, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(snapshot()),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setWarn('');
    } catch (err) {
      // never a silent success: the reviewer must know the agent cannot see this
      setWarn(`not recorded (${POST_URL}: ${err.message}) — is scripts/draft_server.py serving this page?`);
    }
  }

  // ----------------------------------------------------------------- marks ---
  // Marks survive the live reload that follows the agent's patch, so the
  // reviewer can check each one against the result. sessionStorage may be
  // unavailable (private mode, blocked storage); marks then last one page load.
  const store = {
    load(){ try { return JSON.parse(sessionStorage.getItem(MARKS_KEY)) || []; } catch { return []; } },
    save(){ try { sessionStorage.setItem(MARKS_KEY, JSON.stringify(marks.map(({note, target}) => ({note, target})))); } catch {} },
  };
  function resolve(m){
    if (m.el && m.el.isConnected) return m.el;
    try { m.el = document.querySelector(m.target); } catch { m.el = null; }
    return m.el;
  }
  function addMark(note){
    if (!current || !current.isConnected) return;
    marks.push({note: note.trim(), target: pathOf(current), el: current});
    store.save();
    renderMarks();
    schedulePost(0);
  }
  function removeMark(i){
    marks.splice(i, 1);
    store.save();
    renderMarks();
    schedulePost(0);
  }

  // ---------------------------------------------------------------- panel ---
  const css = `
  :host{all:initial;position:fixed;top:0;left:0;width:0;height:0;z-index:2147483600}
  *{box-sizing:border-box}
  .dk{position:fixed;right:12px;bottom:12px;width:300px;max-height:calc(100vh - 24px);overflow:auto;
    background:rgb(255 255 255/.97);border:1px solid #e4e4e7;border-radius:12px;padding:12px 14px;
    font:11.5px/1.5 ui-sans-serif,system-ui,sans-serif;color:#18181b;box-shadow:0 10px 30px rgb(0 0 0/.12)}
  .dk.left{right:auto;left:12px}
  .dk.min{width:auto}
  .dk.min .body{display:none}
  header{display:flex;justify-content:space-between;align-items:center;gap:6px;
    font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:#a1a1aa;font-weight:600}
  h4{margin:14px 0 6px;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:#a1a1aa;font-weight:600}
  button{font:inherit;font-size:10.5px;cursor:pointer;border:1px solid #e4e4e7;border-radius:6px;
    background:#fff;color:#18181b;padding:3px 7px}
  button:hover{background:#eff4ff;border-color:#bcd2ff}
  button:disabled{opacity:.45;cursor:default}
  button.on{background:#18181b;color:#fff;border-color:#18181b}
  .mode{width:100%;margin:10px 0 8px;padding:5px 8px;font-size:11px;border-color:#18181b;
    display:flex;justify-content:space-between}
  .row{margin:0 0 7px -4px;padding:2px 4px;border-radius:6px}
  .row.lever{background:#eff4ff;box-shadow:inset 0 0 0 1px #bcd2ff}
  .row label{display:flex;justify-content:space-between;color:#71717a;font-size:10.5px}
  .row b{color:#18181b;font-weight:600;font-variant-numeric:tabular-nums}
  .row.moved b::after{content:' •';color:#2563eb}
  .row.unread label span::after{content:' (not read)';color:#b45309}
  input[type=range]{width:100%;margin:0;accent-color:#2563eb}
  .states{display:grid;grid-template-columns:1fr 1fr;gap:4px}
  .states button{text-align:left}
  pre{margin:0;font:11px/1.6 ui-monospace,Menlo,monospace;white-space:pre-wrap;word-break:break-all;
    background:#fafafa;border:1px solid #ececef;border-radius:6px;padding:8px 9px;color:#3f3f46;
    max-height:170px;overflow:auto}
  .layers{display:flex;flex-wrap:wrap;gap:3px;align-items:center;margin:6px 0}
  .layers span{color:#a1a1aa;font-size:10px}
  .layers button{font:10.5px/1.4 ui-monospace,Menlo,monospace;padding:1px 5px;max-width:100%;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#3f3f46}
  .layers button.via{border-style:dashed;color:#71717a}
  .acts{display:flex;gap:6px;margin-top:8px}
  .acts button{flex:1}
  .note{display:flex;gap:6px}
  .note input{flex:1;min-width:0;font:inherit;font-size:11px;padding:3px 7px;border:1px solid #e4e4e7;
    border-radius:6px;color:#18181b;background:#fff}
  ol{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:3px}
  li{display:flex;align-items:baseline;gap:6px;font-size:11px}
  li .n{flex:none;padding:0 6px;font-variant-numeric:tabular-nums}
  li .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  li.stale .t{color:#b45309;text-decoration:line-through}
  li .x{flex:none;border:0;background:none;color:#a1a1aa;padding:0 4px}
  .audit{margin-top:6px;font-size:10.5px;color:#3f3f46}
  .hd{display:flex;gap:4px;text-transform:none;letter-spacing:0}
  .warn{font-size:10.5px;color:#b45309;margin:8px 0 0}
  .notice{font-size:10.5px;color:#1d4ed8;margin:8px 0 0}
  .notice button{margin-left:6px}
  .box{position:fixed;pointer-events:none;border-radius:2px}
  .hover{border:1px solid #2563eb;background:rgb(37 99 235/.07)}
  .sel{outline:2px solid #2563eb;outline-offset:2px}
  .tip{position:fixed;pointer-events:none;font:10px/1.4 ui-monospace,Menlo,monospace;background:#18181b;
    color:#fff;padding:2px 5px;border-radius:4px;white-space:nowrap;max-width:60vw;overflow:hidden;
    text-overflow:ellipsis}
  .badge{position:fixed;pointer-events:none;min-width:18px;height:18px;padding:0 5px;border-radius:9px;
    background:#2563eb;color:#fff;font:600 10.5px/18px ui-sans-serif,system-ui,sans-serif;text-align:center;
    box-shadow:0 0 0 2px #fff}
  [hidden]{display:none!important}`;

  const html = `
    <div class="box hover" hidden></div><div class="box sel" hidden></div><div class="tip" hidden></div>
    <div class="badges"></div>
    <aside class="dk" aria-label="Draft kit">
      <header><span>Draft kit</span><span class="hd">
        <button type="button" class="side" title="move the panel to the other side">⇄</button>
        <button type="button" class="toggle" title="collapse; H hides the kit completely">hide</button></span></header>
      <div class="body">
        <button type="button" class="mode" title="P toggles, Esc leaves"><span>pick element</span><b>off</b></button>
        <div class="tokens"></div>
        <div class="state-wrap"><h4>States</h4><div class="states"></div></div>
        <h4>Selected element</h4>
        <pre class="readout"></pre>
        <div class="layers"></div>
        <div class="acts">
          <button type="button" class="parent">parent</button>
          <button type="button" class="reset">reset tokens</button>
        </div>
        <h4>Marks</h4>
        <form class="note">
          <input type="text" placeholder="note for the selected element" aria-label="note">
          <button type="submit">mark</button>
        </form>
        <ol class="marks"></ol>
        <div class="acts"><button type="button" class="clear">clear marks</button>
          <button type="button" class="run-audit">audit this state</button></div>
        <div class="audit" hidden></div>
      </div>
      <p class="warn" hidden></p>
      <p class="notice" hidden><span></span><button type="button">reload</button></p>
    </aside>`;

  let ui = null, open = true, picking = false, hidden = false;
  const SIDE_KEY = 'draft-kit:side';
  let side = (() => { try { return sessionStorage.getItem(SIDE_KEY); } catch { return null; } })() ||
    (CONFIG.side === 'left' ? 'left' : 'right');
  const gutterOn = () => !hidden && open && GUTTER && innerWidth >= 1180;
  // `H` or draftKit.hide(true): nothing of the kit is drawn — no panel, no
  // badges, no outline, no gutter — so a screenshot shows the page alone.
  function setHidden(on){
    hidden = !!on;
    if (hidden && picking) setPicking(false);
    if (host) host.style.display = hidden ? 'none' : '';
    render();
  }
  const pageStyle = document.createElement('style');   // the only rules the kit puts in the page

  function build(){
    host = document.createElement('draft-kit');
    const shadow = host.attachShadow({mode: 'open'});
    shadow.innerHTML = `<style>${css}</style>${html}`;
    const $ = s => shadow.querySelector(s);
    ui = {
      panel: $('.dk'), toggle: $('.toggle'), mode: $('.mode'), tokens: $('.tokens'),
      stateWrap: $('.state-wrap'), states: $('.states'), readout: $('.readout'), layers: $('.layers'),
      warn: $('.warn'), notice: $('.notice'), hover: $('.hover'), sel: $('.sel'), tip: $('.tip'),
      badges: $('.badges'), note: $('.note input'), markBtn: $('.note button'), marks: $('.marks'),
      clear: $('.clear'), audit: $('.audit'),
      rows: [], stateButtons: [],
    };

    for (const t of TOKENS) {
      const row = document.createElement('div');
      row.className = 'row';
      row.innerHTML = '<label><span></span><b></b></label><input type="range">';
      row.querySelector('span').textContent = t.label;
      const input = row.querySelector('input');
      input.step = t.step;
      input.setAttribute('aria-label', t.label);
      input.addEventListener('input', () => slide(t, Number(input.value)));
      ui.tokens.appendChild(row);
      ui.rows.push({t, row, input, out: row.querySelector('b')});
    }
    ui.stateWrap.hidden = !STATES.length;
    for (const s of STATES) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = s.label || s.id;
      b.addEventListener('click', () => {
        try { s.run(); } catch (err) { setWarn(`state "${s.id}" failed: ${err.message}`); }
        refresh();
        schedulePost(0);
      });
      ui.states.appendChild(b);
      ui.stateButtons.push({s, b});
    }

    ui.toggle.addEventListener('click', () => { open = !open; render(); });
    // A fixed drawer or an absolutely placed header button can sit exactly
    // where the panel is; the gutter only moves the page's flow, not those.
    $('.side').addEventListener('click', () => {
      side = side === 'right' ? 'left' : 'right';
      try { sessionStorage.setItem(SIDE_KEY, side); } catch {}
      render();
      schedulePost(400);
    });
    ui.mode.addEventListener('click', () => setPicking(!picking));
    $('.parent').addEventListener('click', () => {
      const up = current && current.parentElement;
      if (up && up !== document.body && up !== root) select(up, layers.includes(up) ? layers : [up, ...layers], layerPoint);
    });
    $('.reset').addEventListener('click', resetTokens);
    $('.note').addEventListener('submit', e => {
      e.preventDefault();
      addMark(ui.note.value);
      ui.note.value = '';
    });
    ui.clear.addEventListener('click', () => { marks = []; store.save(); renderMarks(); schedulePost(0); });
    $('.run-audit').addEventListener('click', () => {
      lastAudit = audit();
      const a = lastAudit, n = o => Object.keys(o).length;
      ui.audit.textContent =
        `radii ${n(a.radii)} · shadows ${n(a.shadows)} · sizes ${n(a.fontSizes)} · families ${n(a.fontFamilies)} · ` +
        `rings ${n(a.rings)} · gradients ${a.gradients.length} · animated ${a.animated.length} · ` +
        `contrast fails ${a.contrastFailures.length}` +
        (a.contrastUnknown.length ? ` · unknown ${a.contrastUnknown.length}` : '') +
        (a.contrastApproximate.length ? ` · approximate ${a.contrastApproximate.length}` : '');
      ui.audit.hidden = false;
      schedulePost(0);
    });
    ui.notice.querySelector('button').addEventListener('click', () => location.reload());

    // While open, the panel reserves a gutter on its side so it does not cover
    // the page's flow. Collapsing removes the gutter; `H` removes everything.
    pageStyle.id = 'draft-kit-page';
    document.head.appendChild(pageStyle);
    document.body.appendChild(host);

    marks = store.load().map(m => ({note: m.note, target: m.target, el: null}));
    renderMarks();
  }

  function setWarn(text){ warn = text; render(); }

  function place(box, el){
    if (!el || !el.isConnected) { box.hidden = true; return null; }
    const r = el.getBoundingClientRect();
    Object.assign(box.style, {left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px'});
    box.hidden = false;
    return r;
  }

  const readoutOf = d => {
    if (!d) return 'Turn picking on and click anything.';
    const c = d.contrast;
    const contrast = !c ? '(no text of its own)'
      : c.ratio === null ? `unknown — ${c.reason}`
      : `${c.ratio}:1 on ${c.against} — ${c.passes ? 'meets' : 'FAILS'} ${c.required}:1` +
        (c.gradient ? ` (gradient, ${c.range[0]}–${c.range[1]}:1 across its stops)` : '') +
        (c.method === 'ancestors' ? ' (approximate: text not on screen)' : '');
    return `target:    ${compact(d.target)}\n` +
      `component: ${d.component || '(no data-node above)'}\n` +
      `text:      ${d.text ? '"' + d.text.slice(0, 60) + '"' : '(empty)'}\n` +
      `computed:  ${d.computed['font-size']} · ${d.computed.color} · pad ${d.computed.padding} · r ${d.computed['border-radius']}\n` +
      `contrast:  ${contrast}`;
  };

  function render(){
    if (!ui) return;
    ui.panel.classList.toggle('min', !open);
    ui.panel.classList.toggle('left', side === 'left');
    ui.toggle.textContent = open ? 'hide' : 'show';
    pageStyle.textContent =
      (!hidden && open && GUTTER ? `@media (min-width:1180px){html body{padding-${side}:${GUTTER}px}}\n` : '') +
      (picking && !hidden ? 'html,html *{cursor:crosshair!important}' : '');
    ui.mode.classList.toggle('on', picking);
    ui.mode.querySelector('b').textContent = picking ? 'on' : 'off';

    const d = describe(current);
    if (current && !d) { current = null; layers = []; renderLayers(); }
    const levers = d ? d.levers : [];
    for (const {t, row, input, out} of ui.rows) {
      input.min = t.min; input.max = t.max;
      if (Number(input.value) !== t.value) input.value = t.value;
      out.textContent = +t.value.toFixed(t.moved ? t.decimals : t.digits) + (t.suffix !== undefined ? t.suffix : t.unit);
      row.classList.toggle('moved', t.moved);
      row.classList.toggle('unread', !t.read);
      row.classList.toggle('lever', levers.includes(t.key));
    }
    for (const {s, b} of ui.stateButtons) b.classList.toggle('on', isOn(s));

    ui.readout.textContent = readoutOf(d);
    ui.note.disabled = ui.markBtn.disabled = !d;
    ui.clear.disabled = !marks.length;
    ui.warn.hidden = !warn;
    ui.warn.textContent = warn;
    ui.notice.hidden = !notice;
    ui.notice.querySelector('span').textContent = notice;
    placeOverlays();
  }

  // Rebuilt only when the selection changes: replacing a chip between mousedown
  // and mouseup would swallow the reviewer's click.
  function renderLayers(){
    ui.layers.replaceChildren();
    if (layers.length) {
      const n = document.createElement('span');
      n.textContent = layers.length + ' layers';
      ui.layers.appendChild(n);
    }
    // Ancestors above the section are noise, and a long strip of chips pushes
    // the actions off the panel.
    layers.slice(0, 6).forEach(node => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = labelOf(node);
      b.title = 'select this layer';
      b.classList.toggle('on', node === current);
      b.classList.toggle('via', !!(layerPoint && !covers(node, layerPoint.x, layerPoint.y)));
      b.addEventListener('click', () => select(node, layers, layerPoint));
      ui.layers.appendChild(b);
    });
  }

  // Rebuilt only when the list changes, for the same reason as the layer chips.
  function renderMarks(){
    if (!ui) return;
    ui.marks.replaceChildren();
    ui.badges.replaceChildren();
    marks.forEach((m, i) => {
      const li = document.createElement('li');
      li.innerHTML = '<button type="button" class="n"></button><span class="t"></span><button type="button" class="x" aria-label="remove mark">×</button>';
      li.querySelector('.n').textContent = i + 1;
      li.querySelector('.t').textContent = m.note || '(no note)';
      li.title = m.target;
      li.classList.toggle('stale', !resolve(m));
      li.querySelector('.n').addEventListener('click', () => { const el = resolve(m); if (el) select(el, [el], null); });
      li.querySelector('.x').addEventListener('click', () => removeMark(i));
      ui.marks.appendChild(li);
      const badge = document.createElement('div');
      badge.className = 'badge';
      badge.textContent = i + 1;
      ui.badges.appendChild(badge);
    });
    render();
  }

  // The outline is a picking-mode mark; outside the mode only the readout
  // stays. Mark badges show whenever the panel is open.
  function placeOverlays(){
    if (!ui) return;
    place(ui.sel, picking ? current : null);
    [...ui.badges.children].forEach((badge, i) => {
      const el = open && marks[i] ? resolve(marks[i]) : null;
      const r = el && el.getBoundingClientRect();
      // a badge for an element scrolled out of view would pin itself to an edge
      if (!r || r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) { badge.hidden = true; return; }
      badge.style.left = Math.max(2, r.left - 9) + 'px';
      badge.style.top = Math.max(2, r.top - 9) + 'px';
      badge.hidden = false;
    });
  }

  // Re-read the page instead of trusting what the panel last did: a theme can
  // be toggled from the page's own menu, a media query can zero --dur.
  function refresh(){
    const cs = getComputedStyle(root);
    for (const t of TOKENS) seed(t, cs);
    render();
  }

  // --------------------------------------------------------------- picking ---
  function setPicking(on){
    picking = on;
    if (!on) { ui.hover.hidden = true; ui.tip.hidden = true; }
    // leaving the mode keeps the selection and its readout: the reviewer keeps
    // talking about what they just pointed at
    render();
  }
  function select(el, stack, point){
    current = el;
    layers = stack && stack.length ? stack : [el];
    layerPoint = point;
    renderLayers();
    render();
    schedulePost(0);
  }

  const fromKit = e => host && e.composedPath().includes(host);
  // In picking mode the page must not react: no menu opens, no link follows,
  // no focus moves. Capture on window runs before the page's own listeners.
  for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click', 'dblclick', 'auxclick']) {
    window.addEventListener(type, e => {
      if (!picking || fromKit(e)) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (type !== 'click') return;
      const {stack, el} = hit(e.clientX, e.clientY);
      if (el) select(el, stack, {x: e.clientX, y: e.clientY});
    }, true);
  }

  let hoverFrame = 0;
  window.addEventListener('mousemove', e => {
    if (!picking || !ui) return;
    if (fromKit(e)) { ui.hover.hidden = true; ui.tip.hidden = true; return; }
    cancelAnimationFrame(hoverFrame);
    hoverFrame = requestAnimationFrame(() => {
      const {stack, el} = hit(e.clientX, e.clientY);
      const r = place(ui.hover, el);
      if (!r) { ui.tip.hidden = true; return; }
      ui.tip.textContent = labelOf(el) + (stack.length > 1 ? `  +${stack.length - 1}` : '');
      ui.tip.hidden = false;
      ui.tip.style.left = Math.max(4, Math.min(r.left, innerWidth - ui.tip.offsetWidth - 16)) + 'px';
      ui.tip.style.top = Math.max(0, r.top - 18) + 'px';
    });
  }, {passive: true});

  window.addEventListener('keydown', e => {
    if (!ui) return;
    if (e.key === 'Escape' && picking) { e.stopImmediatePropagation(); setPicking(false); return; }
    const t = e.composedPath()[0];
    const typing = t && t.nodeType === 1 && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
    if (typing || e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
    if (e.key === 'h' || e.key === 'H') { setHidden(!hidden); return; }
    if (hidden) return;
    if (e.key === 'p' || e.key === 'P') setPicking(!picking);
  }, true);

  // State buttons and seeded sliders must agree with the page after a change
  // made outside the panel; re-read after the page's own handlers have run.
  const later = () => setTimeout(refresh, 0);
  window.addEventListener('click', later, true);
  window.addEventListener('keydown', later, true);
  window.addEventListener('scroll', placeOverlays, {capture: true, passive: true});
  window.addEventListener('resize', () => { render(); schedulePost(400); }, {passive: true});
  setInterval(refresh, 500);

  // ----------------------------------------------------------- live reload ---
  function watch(){
    if (!WATCH || location.protocol === 'file:') return;
    const hash = s => { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h; };
    const files = () => [location.href.split('#')[0],
      ...[...document.querySelectorAll('link[rel~="stylesheet"][href], script[src]')].map(n => n.href || n.src)]
      .filter(u => u && u !== SELF && new URL(u).origin === location.origin);
    const seen = new Map();
    let busy = false;
    setInterval(async () => {
      if (busy || notice) return;
      busy = true;
      try {
        for (const url of files()) {
          let text;
          try {
            const res = await fetch(url, {cache: 'no-store'});
            if (!res.ok) continue;
            text = await res.text();
          } catch { continue; }            // server restarting: try again next tick
          const h = hash(text);
          if (!seen.has(url)) { seen.set(url, h); continue; }
          if (seen.get(url) === h) continue;
          const moved = TOKENS.filter(t => t.moved).map(t => t.prop);
          if (!moved.length) { location.reload(); return; }
          // A reload would silently discard the reviewer's slider work.
          notice = `File changed on disk. Reloading discards ${moved.join(', ')}.`;
          render();
          return;
        }
      } finally { busy = false; }
    }, 1200);
  }

  // ------------------------------------------------------------------ boot ---
  function start(){
    build();
    refresh();
    watch();
    if (location.protocol === 'file:' && POST_URL) setWarn('opened from file:// — selections are not recorded');
    // A data-levers key that names no token highlights nothing, silently.
    const known = new Set(TOKENS.map(t => t.key));
    const unknown = new Set();
    if (known.size) for (const a of document.querySelectorAll('[data-levers]'))
      for (const k of a.dataset.levers.split(',').map(s => s.trim()).filter(Boolean)) if (!known.has(k)) unknown.add(k);
    if (unknown.size) setWarn(`data-levers names no token: ${[...unknown].join(', ')} (keys are: ${[...known].join(', ')})`);
  }
  window.draftKit = Object.freeze({ snapshot, audit, hide: on => setHidden(on !== false), version: 6 });
  if (document.body) start();
  else document.addEventListener('DOMContentLoaded', start, {once: true});
})();
