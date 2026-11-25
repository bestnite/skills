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

The table exists to explain *why* a session is mandatory, not to offer a degraded mode. **This skill does not search anonymously.** Guest reading shows that a thread exists and which build it names, but never yields a URL, so a guest run cannot finish the job — ask for credentials first (step 0) instead of returning placeholders.

## Workflow

### The shape of a fast run

Once the session exists (step 0), a routine lookup is three commands:

```bash
python csrin_session.py --find "<English name>"        # one search request: every matching row
python csrin_session.py 'viewtopic.php?t=<id>' --last  # 3 pages of that thread's tail
python check_links.py <primary link> <fallback link>   # one parallel pass
```

`--find` lists and stops: it does not open a thread the agent has not chosen, because the first two rows of a search are often not the two that matter. Choosing is the part no flag can do — read the rows, pick the threads by their forum column, then spend the fetches on those. `--topics N` (max 6) is there for when the choice is already obvious and a round trip is worth saving.


**0. Get a session before anything else — this skill does not run anonymously.** A guest reads topic pages, but every download link is replaced by `[[Please login to see this link.]]` and the whole clean-files section is hidden, so an anonymous run produces a report nobody can act on and the work is spent twice.

1. **Look first.** Check the skill's own `.state/` directory for a stored session before touching the board.
2. **No session: stop and ask.** Ask before running a single search, in the user's own language, and say what is needed and why. Three shapes, best first: account name and password (always works), a cookie set from the user's browser (only from the same network), or a browser session the agent can drive.
3. **No account: send them to register.** Tell them plainly that the board requires an account for links and for the clean-files section, and point at the forum's registration page (`ucp.php?mode=register`). It is free. Then wait — do not search while waiting, and do not "just try a few pages anonymously to see what is there".
4. **Log in with the shipped client.** `templates/csrin_session.py` already performs the handshake, the login and the retry logic; running those requests by hand with `curl` re-derives them and usually gets the token or the cookie rotation wrong.
5. **Then ask about persistence.** Once the login is verified, ask whether to keep the session in `.state/session.json` (`0600`, gitignored) or to use it once and drop it. Details: `references/session-persistence.md`.

A pasted cookie only authenticates when the agent's requests leave from the same network as the user's browser — the board's security token and session are bound to the client that created them. When that cannot be arranged, ask for credentials and log in from the client that will make the requests; that is the path that always works. Details and the failure table: `references/access-and-session.md`. Do not write a session anywhere except the skill's own `.state/`, which is gitignored.

**1. Resolve the game identity before searching.** The English store name is what the board uses, and the AppID is a better search key than the name. Use the Steam store search API (`https://store.steampowered.com/api/storesearch/?term=<name>&l=english&cc=us`) to turn a title into `{appid, canonical name}`; if the user gave an AppID, use `appdetails` to get the name. Never search a translated or abbreviated title first — the board indexes the English Steam name. That name is the usual key, not a guaranteed one: when the title query comes back empty, try the AppID, then the series or developer name.

**2. Search and open the newest page in one call.** `python csrin_session.py --find "<English name>"` runs the title search and prints every matching row — topic id, forum, title. Add `--topics N` to also digest the newest pages of the first N threads (per post: author with post count and join date, build stamp, hosts, and a text peek); the default opens none, because the rows that matter are the agent's to pick.

A broad query is normal: a common word can return dozens of topics on one page. Listing them is one search request, whatever the count. Opening is opt-in: `--topics N` (default 0, hard cap 6) fetches that many of the listed threads, `--pages` pages each (default 3), and the tool prints the arithmetic before it starts — `opening 2 of 41 topics, 3 page(s) each = 1 search + 6 page requests`. It is never `1 + N × 3`, and by default it is the search alone.

It gathers, it does not decide. Which topic matters, whether the last page actually holds a release, whether to walk one page further back, whether a name needs the AppID instead — that is the agent's judgement, and `--find` prints the evidence for it rather than a verdict. When the title query comes back empty or short, retry with the AppID or the series name; the board indexes the English Steam name. All three threads a game can have (Main Forum discussion, `SCS - <Game>` clean files, a reupload thread) show up in the same result list, with their forum named. Search parameters and fallbacks: `references/search-recipes.md`.

**3. Read the newest, not the whole thread.** The SCS thread states its build in a `Depots & Manifests` post; Main Forum uploader posts carry a build stamp (`Build <number>`, `v<version> | Build ...`). Start from the tail — `python csrin_session.py 'viewtopic.php?t=<id>' --last` digests the last three pages by default (`--pages N`). Three, not one, because the final page of a live thread is usually people discussing the release: on a real example the newest page held only complaints and a trainer, while the release itself sat one page back. The newest page is one request — phpBB clamps an oversized `start` offset to the final page — and its pagination gives the offsets for the two before it. Walk further back only when all three hold nothing usable, and say so if you had to. Post shapes, pagination, and link markup: `references/thread-and-post-format.md`.

**Whether the game is Denuvo is read off the thread, not investigated separately.** Its regulars talk about it in plain sight: `hypervisor`, `VBS`, `Crack.Only`, `EXPERIMENTAL hypervisor-based release`, a group name such as `-ARTIFACT`. If those words are absent and the posts show a plain Steam emulator or an online fix, it is not Denuvo — do not spend a query or an API call proving a negative. When the signals are there, report the build, the group and the hardware requirements and route to `references/denuvo-and-hypervisor.md`; never present such a download as a portable build.

**4. Rank by uploader, before anything else.** Measure the account's posting volume and tenure, then compare build numbers, then look at what the release is, then at the host. Rules, the measurement recipes, and the staff ban lists are in `references/source-ranking.md`. Never present a banned host, even if it is the only link — say the thread exists and that every link in it is on the staff ban list.

**5. Verify the links before promising them.** If the agent can fetch a URL, check each candidate the user is about to click: `ALIVE`, `DEAD`, or `UNVERIFIED`. Check only the links the user will actually click — the primary link of the top two or three, plus a fallback host — in one parallel pass. When the cheap check cannot tell (a JavaScript-only page, a 429), make exactly one more attempt: a browser. If the browser is refused too, the verdict is `BLOCKED` and the link goes back to the user, who has a real browser and the right network; do not chain more tools or retry a host that already said no. Details and the per-host behaviour: `references/link-verification.md`; the shipped checker is `templates/check_links.py`.

**6. Report every viable candidate, fully, then patch.** Never hand over a single link, and never hand over a link that makes the reader open a 600-post thread for the details. Each candidate is a self-contained block: version and build, download and unpacked size, what is inside, the crack or emulator with its version, the archive password, numbered install steps, every link with its verdict, and the post permalink as provenance. Three or four candidates, spread across hosts and uploaders. Format and required fields: `references/source-ranking.md`. Then, if the user wants to play rather than read: `references/patch-and-run.md`.

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
- Do not return one candidate. File hosts die; give every viable option found, best first, each with its verdict.
- Do not call a link dead because a bot check refused you. 401/403/429/503 and JavaScript-only pages are `UNVERIFIED`.
- Do not present a Denuvo title's download as something that will start. It needs a hypervisor release for that exact build, and running it means turning Windows' virtualization-based security off for the session.
- Do not mix hypervisor crack files across games or builds. The Denuvo token is bound to one build, and the hypervisor drivers carry game-specific code.

## What ships here

- `references/access-and-session.md` — the 401 cookie handshake, login form, cookie formats, flood control, feeds.
- `references/search-recipes.md` — search parameters, AppID search, sorting, pagination, fallbacks when search is throttled.
- `references/thread-and-post-format.md` — post templates, build stamps, pagination, link markup, permalinks.
- `references/scs-and-clean-files.md` — the clean-files section: thread anatomy, depots and manifests, title patterns, passwords, extraction, dead links.
- `references/source-ranking.md` — measuring an uploader's record, build comparison, release types, host quality, and the staff ban lists.
- `references/denuvo-and-hypervisor.md` — why clean files do not run, what a hypervisor release is, hardware requirements, the security tradeoff, and the Linux path.
- `references/link-verification.md` — the three verdicts, how hosts answer, and the rule against returning a single link.
- `references/patch-and-run.md` — Steamless, Unsteam, GBE Fork, uc-online2, Nemirtingas EOS, and the traps between them.
- `references/session-persistence.md` — the rules for storing a login in `.state/`.
- `templates/check_links.py` — liveness checker: one request per URL, host-aware verdicts, standard library only.
- `templates/csrin_session.py` — copy-and-adapt client: handshake, optional login, `--find` and `--last` one-shot digests, and parse either a topic page (posts, build stamps, links) or a search page (topic id, author, build, excerpt) to JSON. Standard library only; it makes no decisions for you.

Prose carries the judgement; the template carries only the parts that must be byte-exact (cookie names, handshake order, parse targets).
