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

**0. Establish the session.** Cookie string, username/password, or nothing (degraded). A pasted cookie only authenticates when the agent's requests leave from the same network as the user's browser — the board's security token and session are bound to the client that created them. When that cannot be arranged, ask for credentials and log in from the client that will make the requests; that is the path that always works. Details and the failure table: `references/access-and-session.md`. Do not write a session anywhere except the skill's own `.state/`, which is gitignored.

**1. Resolve the game identity before searching.** The English store name is what the board uses, and the AppID is a better search key than the name. Use the Steam store search API (`https://store.steampowered.com/api/storesearch/?term=<name>&l=english&cc=us`) to turn a title into `{appid, canonical name}`; if the user gave an AppID, use `appdetails` to get the name. Never search a translated or abbreviated title first — the board indexes the English Steam name. That name is the usual key, not a guaranteed one: when the title query comes back empty, try the AppID, then the series or developer name.

**2. Search, cheapest query first.** Search globally — no section pre-selected; each result names its forum, and that column is what distinguishes a clean-files thread from a discussion thread. A title search returns a game's two threads at once: the `Main Forum` discussion thread and the `SCS - <Game>` thread in Steam Content Sharing, which holds the clean depot files (`references/scs-and-clean-files.md`). The AppID is the other fast path, because uploader posts embed Steam image URLs containing `app_<id>_header.jpg`. Search recipes, parameters, sorting, and fallbacks: `references/search-recipes.md`.

**3. Read the newest, not the whole thread.** The SCS thread states its build in a `Depots & Manifests` post; Main Forum uploader posts carry a build stamp (`Build <number>`, `v<version> | Build ...`). Search sorted by post time, or the last pages of a long thread, gives the newest builds directly. Post shapes, pagination, and link markup: `references/thread-and-post-format.md`.

**Denuvo titles break this flow.** Some games cannot be run by patching Steam at all: their clean files are real, but they will not start without a hypervisor crack release bound to the exact build. Detect it (no usable SCS thread, a release marked `EXPERIMENTAL hypervisor-based`, a group name like `-ARTIFACT` or `DenuvOwO`), then report the build, the group and the hardware requirements, and route to `references/denuvo-and-hypervisor.md`. Never present such a download as a portable build.

**4. Rank by uploader, before anything else.** Measure the account's posting volume and tenure, then compare build numbers, then look at what the release is, then at the host. Rules, the measurement recipes, and the staff ban lists are in `references/source-ranking.md`. Never present a banned host, even if it is the only link — say the thread exists and that every link in it is on the staff ban list.

**5. Report, then patch.** Report a short ranked table: uploader with their record, build, release type, host, link, post permalink. Then, if the user wants to play rather than read: `references/patch-and-run.md`.

## Ranking, in one table

| Priority | Signal | Why |
|---|---|---|
| 1 | **The uploader's record**: posting volume, tenure, how many of those posts carry build stamps | the board's own history, and the one thing a promising domain name cannot fake |
| 2 | **Build recency, compared across both threads** | an older build is a wasted download — and SCS is not automatically the newer one |
| 3 | Release type: SCS depots and manifests, then pre-installed or repack, then unlabelled upload | purity decides whether the patch routes apply, not how fresh the build is |
| 4 | Host quality | affects the download, not the trust |
| gate | Hosts on the staff ban list | malware; a hard refusal, never a fallback |

Measure the record, do not guess it: `search.php?author=<name>&sr=posts` states `Search found N matches` for the account, and the same page samples what those posts are — releases or chatter. Do not add a `keywords=` filter to that query: the board's index drops high-frequency words, so the count looks precise and means nothing. Every post also shows the account's join date and total post count for free. Searches are flood-limited, so measure only the two or three accounts genuinely in contention.

SCS is the purity floor, not the freshness ceiling: it is refreshed by volunteers, and in practice it often lags the Main Forum, where uploaders post each new build. Compare the build numbers from both threads before ranking anything.

Do not keep a whitelist or blacklist of uploader-run sites. A site is where the bytes sit; judge the account, then the host's download experience. SCS is not an exception to this — it is a section of this board, with its own rules and its own password convention, not a third-party site.

## What not to do

- Do not invent a link from a masked placeholder. `[[Please login to see this link.]]` means the board refused to render it, not that the URL can be guessed.
- Do not treat a repack as a clean build. A repack is pre-patched and its build number may be older than the thread's newest post.
- Do not answer from one post. The newest build is usually a later post in the same thread, and uploaders re-upload when hosts die.
- Do not run searches in a loop. The board answers `Sorry but you cannot use search at this time` and the wait is minutes; plan two or three queries, not twenty.
- Do not hand the user a link and stop. The patch step is what makes the download usable, and it is short.
- Do not present a Denuvo title's download as something that will start. It needs a hypervisor release for that exact build, and running it means turning Windows' virtualization-based security off for the session.
- Do not mix hypervisor crack files across games or builds. The Denuvo token is bound to one build, and the hypervisor drivers carry game-specific code.

## What ships here

- `references/access-and-session.md` — the 401 cookie handshake, login form, cookie formats, flood control, feeds.
- `references/search-recipes.md` — search parameters, AppID search, sorting, pagination, fallbacks when search is throttled.
- `references/thread-and-post-format.md` — post templates, build stamps, pagination, link markup, permalinks.
- `references/scs-and-clean-files.md` — the clean-files section: thread anatomy, depots and manifests, title patterns, passwords, extraction, dead links.
- `references/source-ranking.md` — measuring an uploader's record, build comparison, release types, host quality, and the staff ban lists.
- `references/denuvo-and-hypervisor.md` — why clean files do not run, what a hypervisor release is, hardware requirements, the security tradeoff, and the Linux path.
- `references/patch-and-run.md` — Steamless, Unsteam, GBE Fork, uc-online2, Nemirtingas EOS, and the traps between them.
- `references/session-persistence.md` — the rules for storing a login in `.state/`.
- `templates/csrin_session.py` — copy-and-adapt client: handshake, optional login, fetch, and parse either a topic page (posts, build stamps, links) or a search page (topic id, author, build, excerpt) to JSON. Standard library only; it makes no decisions for you.

Prose carries the judgement; the template carries only the parts that must be byte-exact (cookie names, handshake order, parse targets).
