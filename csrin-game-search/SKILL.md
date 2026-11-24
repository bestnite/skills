---
name: csrin-game-search
description: "Use when searching cs.rin.ru for a game's Steam files or download links, and for patching a downloaded Steam build so it runs."
---

# CS.RIN.RU (Steam Underground) game resources

Two jobs in one skill, in this order:

1. **Find** the newest trustworthy download for a game on CS.RIN.RU — then report it ranked, with the build and the uploader named.
2. **Run** what was downloaded: remove Steam DRM, drop in a Steam emulator or online patch, handle Epic Online Services when the game uses it.

A link is not the deliverable. A game that starts is.

## What the board actually gives you

The board is phpBB3 at `https://cs.rin.ru/forum/`. It is not Cloudflare-gated and no browser is needed: one cookie handshake, then ordinary HTML.

| Surface | Anonymous | Logged in |
|---|---|---|
| Board index, `Main Forum`, topic pages | readable | readable |
| Search (`search.php`) | works, flood-limited | works, larger quota |
| Links inside posts | **replaced** by `[[Please login to see this link.]]` | present in the HTML |
| `Steam Content Sharing` (`f=22`) | hidden — "Please register or log in" | readable |
| Atom feeds (`feed.php`) | readable, links still masked | readable |

So: **anonymous browsing answers "does it exist, which build, who posted it" but never yields a URL.** Any task that ends in a downloadable link needs a session. Say that to the user early instead of returning a page of placeholders.

## Workflow

**0. Establish the session.** Cookie string, username/password, or nothing (degraded). Details, the handshake, and where session material may be written: `references/access-and-session.md`. Do not write a session anywhere except the skill's own `.state/`, which is gitignored.

**1. Resolve the game identity before searching.** The English store name is what the board uses, and the AppID is a better search key than the name. Use the Steam store search API (`https://store.steampowered.com/api/storesearch/?term=<name>&l=english&cc=us`) to turn a title into `{appid, canonical name}`; if the user gave an AppID, use `appdetails` to get the name. Never search a translated or abbreviated title first — the board indexes the English Steam name. That name is the usual key, not a guaranteed one: when the title query comes back empty, try the AppID, then the series or developer name.

**2. Search, cheapest query first.** The AppID is usually the fastest path, because uploader posts embed Steam image URLs containing `app_<id>_header.jpg` and therefore match an AppID keyword. Search recipes, parameters, sorting, and fallbacks: `references/search-recipes.md`.

**3. Read the newest, not the whole thread.** Uploader posts carry a build stamp (`Build 22818764`, `v1.03.5 | Build ...`). Search sorted by post time, or the last pages of a long thread, gives the newest builds directly. Post shapes, pagination, and link markup: `references/thread-and-post-format.md`.

**4. Rank before reporting.** Source type first, then host quality, then build recency. The rules and the board's own trust lists are in `references/source-ranking.md`. Never present a banned host, even if it is the only link — say the thread exists and that every link in it is on the staff ban list.

**5. Report, then patch.** Report a short ranked table: build, uploader, host, link, post permalink, and what kind of release it is (clean files, repack, direct-download site). Then, if the user wants to play rather than read: `references/patch-and-run.md`.

## Ranking, in one table

| Rank | Source | Why |
|---|---|---|
| 1 | Thread or post labelled **Clean Steam Files** | untouched Steam files plus manifests: patchable, version-verifiable, no repacker interference |
| 2 | Staff-recommended direct-download site (list in `t=95461`) | reviewed for malware, anonymous download, no VPN block |
| 3 | Known long-running uploader's release in a game thread | track record, but verify the build |
| 4 | One-off upload by an unknown account | may be fine, treat as unverified |

Tie-breakers, in order: higher build number wins; then later post date; then a host that downloads without a quota; then fewer hops (direct file beats a link aggregator beats a redirect chain).

## What not to do

- Do not invent a link from a masked placeholder. `[[Please login to see this link.]]` means the board refused to render it, not that the URL can be guessed.
- Do not treat a repack as a clean build. A repack is pre-patched and its build number may be older than the thread's newest post.
- Do not answer from one post. The newest build is usually a later post in the same thread, and uploaders re-upload when hosts die.
- Do not run searches in a loop. The board answers `Sorry but you cannot use search at this time` and the wait is minutes; plan two or three queries, not twenty.
- Do not hand the user a link and stop. The patch step is what makes the download usable, and it is short.

## What ships here

- `references/access-and-session.md` — the 401 cookie handshake, login form, cookie formats, flood control, feeds.
- `references/search-recipes.md` — search parameters, AppID search, sorting, pagination, fallbacks when search is throttled.
- `references/thread-and-post-format.md` — post templates, build stamps, pagination, link markup, permalinks.
- `references/source-ranking.md` — source tiers, host tiers, the staff ban list with its date, and how to keep it current.
- `references/patch-and-run.md` — Steamless, Unsteam, GBE Fork, uc-online2, Nemirtingas EOS, and the traps between them.
- `references/session-persistence.md` — the rules for storing a login in `.state/`.
- `templates/csrin_session.py` — copy-and-adapt client: handshake, optional login, fetch, and parse either a topic page (posts, build stamps, links) or a search page (topic id, author, build, excerpt) to JSON. Standard library only; it makes no decisions for you.

Prose carries the judgement; the template carries only the parts that must be byte-exact (cookie names, handshake order, parse targets).
