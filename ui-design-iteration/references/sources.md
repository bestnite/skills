# Sources — where drafts start

## The user's sources come first

The catalogue below is a starter set for a user who has no preference — not a whitelist. Before shortlisting, ask the user whether they have sources they like: a component library their team already uses, a template marketplace, a gallery, specific sites they admire, their own earlier products. Search those first, and use this catalogue only to fill gaps or when they have none.

A preference that will hold across projects is worth keeping where your runtime keeps user preferences (agent memory, the user's own notes) — not in this skill, which ships the same to every user.

## Judging any source

Any source is usable; these questions tell you how (`references/drafting.md`):

| Question | Why it matters |
| --- | --- |
| Does it fit the page class? | A landing-page source stretched into a dashboard fails at tables, navigation depth and long content |
| Is there a live demo, or only screenshots? | A demo can be clicked through and measured — every state, every breakpoint; a screenshot gives structure only |
| Does it publish its code? | Open code can be reused directly (route A); otherwise rebuild from measurement (route B) |
| Is it one consistent system? | A template or a design system carries consistent values; a collage of unrelated sites does not, so take one section from it, not the whole look |
| Can you reach it? | Sources behind a login or paywall need the user to share screenshots or exports; do not try to sign in as them |

## Starter catalogue

Facts verified on 2026-10-21 against each site. Catalogues reorganise; update this section when a fact here turns out wrong.

Two kinds of source, useful in different ways:

- **Template catalogues** publish complete, consistent designs with live demos, and many publish their code too. A demo can be clicked through and measured — every state, every breakpoint — and open code can be reused directly (route A in `references/drafting.md`), so a template makes the best main reference.
- **Galleries** collect shipped sites and products. They show range and real-world patterns but publish no code: rebuild from them (route B), for direction, a single section or flow, or to show the user what a choice looks like.

### Template catalogues

| Source | Best for | What you can study | Open code |
| --- | --- | --- | --- |
| shadcn/ui blocks (`ui.shadcn.com/blocks`) | app shells, dashboards, sidebars, login and signup, settings, data tables | each block's live preview; a coherent system of CSS variables (`--radius`, `--background`, `--primary` …) | yes — each block's code tab, or `npx shadcn add <block>`; React + Tailwind CSS |
| Tremor (`tremor.so`, blocks at `blocks.tremor.so`) | charts, KPI cards, filters, dashboard pages, reports, a SaaS marketing one-pager | component and block previews; chart styling in a dashboard context | components: copy-paste and npm (`tremorlabs/tremor`); blocks: public repository `tremorlabs/tremor-blocks`, while the site still lists some as premium — check the specific block |
| TailAdmin (`tailadmin.com`) | admin dashboards, tables, forms, auth pages | a full multi-page admin demo | free edition: public repository, HTML + Alpine.js + Tailwind CSS (also React, Next.js, Vue, Angular, Laravel); pro edition: paid |
| Cruip (`cruip.com`) | product landing pages, SaaS homepages, company sites; one dashboard (Mosaic) | live demos of each template; the demo pages on `cruip.com/demos/…` frame the template and can show only an error in a scripted browser — open the template's own demo address instead (its repository README links it, e.g. `simple.cruip.com`) | free templates: public repositories (the one checked is Next.js + Tailwind CSS); the rest: paid |
| Astro themes (`astro.build/themes`) | blogs, docs, portfolios, e-commerce, landing pages | demos filtered by category | per theme: check the theme page for a linked repository; paid themes are sold, not published |
| Vercel templates (`vercel.com/templates`) | full sites of most kinds: commerce, CMS, docs, AI apps, blogs | organised by framework (mostly Next.js); each template has its own page with a demo | per template: check the template page for a linked repository |

### Galleries

| Source | What it shows | Access |
| --- | --- | --- |
| One Page Love (`onepagelove.com`) | one-page websites, plus a separate collection of section examples, tagged by genre (landing page, SaaS, app, portfolio …) | public |
| Recent (`recent.design`) | web interfaces, branding, motion, landing pages, app screenshots and icons, credited to their creators | public |
| Mobbin (`mobbin.com`) | screens, end-to-end flows (onboarding, checkout, paywalls), UI patterns and website sections from shipped apps and sites | free account with limited access; the full library needs a paid plan |

You will usually not have the user's Mobbin session. Ask the user for screenshots or a shared collection rather than trying to sign in.

When a gallery entry links to the live site, that site can be measured like a template demo.

### Which source for which page

| Page | Main reference | Supporting references |
| --- | --- | --- |
| Admin panel, dashboard, internal tool | shadcn/ui blocks for the shell; TailAdmin for a full multi-page admin | Tremor for charts and KPIs; Mobbin for tables, filters, empty states |
| Settings, account, auth | shadcn/ui blocks (login, signup, sidebar) | Mobbin flows |
| Product or SaaS landing page, company homepage | Cruip; Astro themes (landing pages); Tremor's marketing template | One Page Love (whole pages and single sections), Recent |
| Blog, docs, portfolio, shop | Astro themes, filtered by category; Vercel templates | One Page Love |
| Anything else | Vercel templates, filtered by framework | Recent |
