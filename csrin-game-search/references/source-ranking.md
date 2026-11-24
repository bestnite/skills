# Ranking sources and hosts

Verified against the live board on 2026-11-24.

Ranking answers one question: *which of these links would a careful member of this board download first?* The board answers it in two stages: the clean-files section first, then the people who post in the game's own thread. The board has its own answer — an uploader's posting history — and it is a better signal than the name of the site the file sits on.

## The order

| Priority | Signal | Why |
|---|---|---|
| 1 | **How much this account posts, and how long it has been doing it** | volume plus tenure cannot be bought by launching a site with a promising name |
| 2 | **Build recency, compared across both threads** | an old build is a wasted download, and SCS is not automatically the newer one |
| 3 | Release type: SCS depots and manifests, then pre-installed, then repack, then unlabelled | purity decides whether the patch routes apply, not how fresh the build is |
| 4 | Host quality | affects the download, not the trust |
| gate | Banned hosts | malware; a hard refusal, never a ranking |

Do **not** maintain a whitelist or blacklist of uploader-run sites. A site is just where the bytes sit: judge the account, then judge the host's download experience. A brandable domain tells you nothing that the author's post history does not tell you better.

## 0. SCS is the purity floor, not the freshness ceiling

An SCS topic in `f=22` gives depots and manifests, uploaded by people who own the game, with a build id that can be checked. That makes it the most trustworthy *copy*. It does not make it the newest one: SCS is refreshed by volunteers, and the volunteers are not always ahead of the Main Forum, where uploaders race to post each new build.

Reported by this skill's maintainer, and the reason this section is worded carefully: in practice SCS often lags the Main Forum's user-posted clean files. Spot checks on 2026-11-25 over three games were mixed and too small to generalise: two had the identical build in both threads, posted within a minute of each other. Treat freshness as unknown until you compare the numbers, and never assume either thread is ahead.

So: read both threads, take the build from each (the SCS `Depots & Manifests` post, the newest build posts in the Main Forum), and rank by the numbers. SCS wins on purity and verifiability; it does not win on recency by default. Thread anatomy, passwords and extraction: `scs-and-clean-files.md`.

Denuvo titles break this rule. Their clean files are real and still worth having as a base, but nothing starts until a hypervisor release for that exact build is applied — so for those games the only playable candidate is the hypervisor release, and the ranking below applies to it only for the host and the uploader, never to the build (`denuvo-and-hypervisor.md`).

## 1. Measuring an uploader

Every post carries two numbers for free, in the author cell: the account's join date and its total post count. Read them from the page — no search, no login.

For volume, search the author's posts:

```
search.php?author=<username>&terms=all&sr=posts&submit=Search
```

The result header states `Search found N matches` — the account's posting volume. Reliable, and one query.

Composition comes from that same page: it lists posts with forum, date and excerpt. Count how many of the visible ones are releases (depot or manifest block, build stamp, host list) against replies and questions. That is a sample of fifteen, so phrase the conclusion as "most of the first page is releases", not as a percentage.

**Do not add `keywords=` to an author search.** phpBB's index drops high-frequency words, so the filter does almost nothing while looking precise: measured on 2026-11-25, `keywords=Clean Steam Files` with an author returned 4,422 matches for an account with 5,450 total posts.

Cost: one query per candidate, flood-limited to a few per few minutes (`search-recipes.md`). Measure the two or three accounts in contention, not every author on the page.

| Evidence | Reading |
|---|---|
| Four-digit post count, account years old, the game's thread runs for years | long-running uploader — rank first |
| Hundreds of posts, first page mostly release posts | regular uploader — rank above newcomers |
| Double-digit post count on a days-old account | newcomer: not disqualifying, but it has no record yet |
| Posting only inside this one thread, nothing else anywhere | drive-by reupload — treat as unverified |

Two cautions when quoting numbers:

- The `Posts:` figure in a post's author cell is **total** posts, not resource posts. Say which one you are quoting.
- A high count proves activity, not competence: an account with 4,000 one-line replies has a record of talking, not of uploading. Only the sampled page separates the two.

## 2. Build recency

Compare build numbers numerically, newest first.

| Signal | Use |
|---|---|
| `<build>` from the post | primary comparison |
| `v1.03.5`, `1.0.4` | human-readable, not comparable across uploaders |
| post date | tiebreaker between equal builds |
| "see my previous post" | follow one hop back, not the whole thread |
| thread's last-post time | whether anyone still maintains the upload |

A newer build from an unknown account does not automatically beat an older build from a four-digit uploader: report both, newest first, and let the reader see who posted what.

## 3. Release type

| Label in a post | What it is | Rank |
|---|---|---|
| **Clean Steam Files** (CSF) | unmodified Steam depot files, often with manifests and `appmanifest_<appid>.acf` | 1 |
| `Pre-Installed`, `portable`, `loose files` | an extracted install tree, usually a repacked Steam build | 2 |
| repack (FitGirl, KaOsKrew, …) | compressed, pre-patched installer | 2 |
| plain upload, no label | unknown provenance | 3 |

Clean files win because the routes in `patch-and-run.md` apply to them unchanged, the build is verifiable, and nothing was modified between Valve and the reader. A repack is already patched: patching it again usually breaks it, and its build can lag the thread.

Do not take the thread title as proof. "Clean Steam Files" in a title, with a repack inside, happens — check the post for depots, manifests, or a `Pre-Installed` note.

## 4. Host quality

Hosts are about download experience, not trust. The board publishes its own recommended file-host list, on stated criteria: anonymous browsing and downloading, no VPN block, works with uBlock Origin at default settings, HTTPS with no mixed content, no malware ads, fast takedown of reports. Read the current list from the pinned topic instead of keeping a copy — it changes, and a stale copy is worse than none. Some entries carry the board's own annotation that an account is required; quote it rather than promising an anonymous download.

Between two equally trusted uploads, prefer the one on a listed host, then the one with fewer hops (a direct file beats a link aggregator beats a redirect chain).

## The gate: banned hosts

The board maintains two lists, both in pinned topics, and both override every ranking above:

| List | Where it lives | What it means |
|---|---|---|
| Banned hosts and sites | the pinned warning about malicious filehosters | "Do not link to these sites" — linking them is a rule violation, and some entries carry an announced start date |
| Not-recommended sites | the bottom of the pinned recommended-sites topic | the staff will not vouch for them: malicious ads, modified game files, reuploads without credit |

Read both lists when the task needs them. Do not memorise them and do not keep a cached copy in this skill: the thread is edited continuously, entries are added with effective dates, and a domain that was acceptable last month can be banned now.

Two rules that hold regardless of what the lists currently say:

- Never present a banned host as an option, even when it is the only link in the thread. Report that the thread exists and that every link in it sits on the staff list.
- Treat any site named after a scene group as fake, whatever it serves: scene groups do not run public sites.

## Reporting format

Two layers: an overview table to choose from, then a self-contained block per candidate. The post permalink is provenance — where the facts came from — never a step the reader has to take.

Overview, best first:

| # | Uploader | Record | Version / build | Type | Size | Host | State |
|---|---|---|---|---|---|---|---|
| 1 | `<name>` | `<posts>`, joined `<year>`, first page mostly releases | `v<version>` / `<build>` | CSF | `<size>` | `<host>` | alive `<date>` |
| 2 | `<name>` | `<posts>`, joined `<year>` | `v<version>` / `<build>` | pre-installed | `<size>` | `<host>` | dead |
| 3 | `<name>` | `<posts>`, joined `<year>` | `v<version>` / `<build>` | repack | `<size>` | `<host>` | unverified |

Then one block per candidate, in the same order:

```
### <n>. <uploader> — <what it is>, v<version> / build <build>
- Download: <size> archive, <size> unpacked, <n> parts
- Contents: depots <ids> with manifests / repack base / installer; crack <emulator or group>, version
- Password: <password>, or none
- Install: 1) which archive to open 2) where to extract 3) which exe to run 4) which ini or steam_settings folder matters
- Launch and notes: exe name, language switching, save path, overlay or achievement caveats
- Links: <host> <url> — <verdict, date checked>
- From: <post permalink>, posted <date>
```

Required fields, and why none of them can be dropped:

| Field | Why it cannot be omitted |
|---|---|
| version + build | freshness is the whole ranking |
| size, download and unpacked | decides whether the user can even start the download |
| type and contents | a repack cannot be patched the way clean files can |
| crack or emulator, with version | decides whether the game starts at all |
| archive password | the archives are usually encrypted |
| install steps | this is exactly the work the reader would otherwise do inside a 600-post thread |
| a verdict per link | a dead link is not an offer |

If the post does not state a field, write "not stated" rather than dropping it silently; a missing size is information too. If the install steps only exist in a `ReadMe.txt` inside the archive, say that and what it is expected to cover — do not send the reader back to the thread to find the version or the procedure.

## Keeping this current

- Volume and join dates drift; re-measure when two candidates are close.
- The ban lists change; a host decision on the edge deserves a re-read of the pinned threads.
- When a new uploader starts dominating a game's thread, their measured record is the evidence — not a hunch about their site.
