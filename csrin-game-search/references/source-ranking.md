# Ranking sources and hosts

Verified against the live board on 2026-11-24.

Ranking answers one question: *which of these links would a careful member of this board download first?* The board answers it in two stages: the clean-files section first, then the people who post in the game's own thread. The board has its own answer — an uploader's posting history — and it is a better signal than the name of the site the file sits on.

## The order

| Priority | Signal | Why |
|---|---|---|
| 1 | **An SCS thread** in `f=22`, with depots and manifests | unmodified Steam content, and a build you can verify rather than believe |
| 2 | **How much this account posts, and how long it has been doing it** | volume plus tenure cannot be bought by launching a site with a promising name |
| 3 | Build recency | an old build of a patched game is a wasted download |
| 4 | What the release is (clean files vs repack vs plain upload) | decides whether the patch routes even apply |
| 5 | Host quality | affects the download, not the trust |
| gate | Banned hosts | malware; a hard refusal, never a ranking |

Do **not** maintain a whitelist or blacklist of uploader-run sites. A site is just where the bytes sit: judge the account, then judge the host's download experience. A brandable domain tells you nothing that the author's post history does not tell you better.

## 0. The clean-files section comes first

When the game has an SCS topic in `f=22`, that is the answer: depots and manifests, uploaded by people who own the game, with a build id that can be checked. Ranking individual uploaders is what you do for the games it does not cover, or when the user wants a pre-installed build that needs no extraction work. Thread anatomy, passwords and extraction: `scs-and-clean-files.md`.

Denuvo titles break this rule. Their clean files are real and still worth having as a base, but nothing starts until a hypervisor release for that exact build is applied — so for those games the only playable candidate is the hypervisor release, and the ranking below applies to it only for the host and the uploader, never to the build (`denuvo-and-hypervisor.md`).

## 1. Measuring an uploader

Every post carries two numbers for free, in the author cell: the account's join date and its total post count. Read them from the page — no search, no login.

To measure volume properly, search the author's posts:

```
search.php?author=<username>&terms=all&sr=posts&submit=Search
```

The header of the result page states `Search found N matches` — that is the account's posting volume. Add a word the resource posts always contain to approximate *resource* posts:

```
search.php?author=<username>&keywords=Build&terms=all&sr=posts&submit=Search
search.php?author=<username>&keywords=Clean+Steam+Files&terms=all&sr=posts&submit=Search
```

That pair — total posts and posts containing a build stamp — is the closest thing the board offers to an uploader's track record, and it is what the ranking should quote.

Cost: each query is a search, and searches are flood-limited to a few per few minutes (`search-recipes.md`). So measure the two or three accounts that are actually in contention, not every author on the page.

| Evidence | Reading |
|---|---|
| Four-digit post count, account years old, the game's thread runs for years | long-running uploader — rank first |
| Hundreds of posts concentrated in release threads | regular uploader — rank above newcomers |
| Double-digit post count on a days-old account | newcomer: not disqualifying, but it has no record yet |
| Posting only inside this one thread, nothing else anywhere | drive-by reupload — treat as unverified |

Two cautions when quoting numbers:

- The `Posts:` figure in a post's author cell is **total** posts, not resource posts. Say which one you are quoting.
- A high count proves activity, not competence: an account that posts 4,000 one-line replies has a record of talking, not of uploading. The keyword-filtered count is what separates the two, which is why both queries exist.

## 2. Build recency

Compare build numbers numerically, newest first.

| Signal | Use |
|---|---|
| `Build 22818764` | primary comparison |
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

Hosts are about download experience, not trust. The board maintains a recommended file-host list in `t=95461` (1Fichier, Catbox, GoFile, MediaFire, MEGA, Pixeldrain, Sendcm, SendSpace, Yandex.Disk and others), selected on stated criteria: anonymous browsing and downloading, no VPN block, works with uBlock Origin, HTTPS, no malware ads, fast takedown. Some entries carry the board's own annotation "Requires an account" — quote it instead of promising an anonymous download.

Between two equally trusted uploads, prefer the one on a listed host, then the one with fewer hops (direct file beats a link aggregator beats a redirect chain).

## The gate: banned hosts

Two pinned threads carry malware findings, and they override everything above:

| Thread | What it holds |
|---|---|
| `t=159345` How to protect against malicious filehosters | banned hosts and multi-uploaders, plus the malware pattern behind them |
| `t=95461` Recommended download and upload sites | the untrusted-site list at the bottom of the same post |

Banned and untrusted examples as of 2026-11-24: `dodi-repacks.site` and its mirrors, `elamigosgames.net` and its lookalikes, `gamedrive.org` / `cybar.to`, `nexusgames.to`, `repack-games.com`, `steam-repacks.net`, `steamunderground.net`, `steamunlocked.net`, `worldofpcgames.com`, `oceanofgames.com`, `IGG-Games.com`, `freetp.org`, `agfy.co`, `crackingpatching.com`, `getgamez.net`, `hishgames.org`, `games4u.org`, `loadgames.org`, `mrpcgamer.co`, `rgmechanics.com`, `sgcrack.com`, `small-games.info`, `steamcracked.co`, `steamhub.co`, `stggege.org`, `TinkerGames`, `unlocked-games.com`, `alltorrents.co`, `extrogames.com`, `gamesreleaser.com`, `game3rb.com`; filehosters 1cloudfile, bowfile, buzzheavier / bzzhr / fuckingfast, datavaults, devuploads, file-me, filemirage, fileq, koramaup, ranoz, swiftuploads, usersdrive, zpaste; and the multi-uploaders akirabox, rootz.so, multiup.io, mirrored.to (with announced ban dates). Any site named after a scene group (CODEX, CPY, RELOADED, SKIDROW) is fake by definition: scene groups do not run public sites.

Never present a banned host as an option, even when it is the only one in the thread. Report that the thread exists and that every link in it is on the staff ban list.

Both threads are edited continuously; this file is a snapshot with a date. Re-read them when a host is unknown or newly seen.

## Reporting format

One table, best record first, then a short note on what was skipped and why:

| # | Uploader | Record | Build | Type | Host | Link |
|---|---|---|---|---|---|---|
| 1 | `<name>` | 3,900 posts, joined 2019, 240 with build stamps | 22818764 | CSF | GoFile | `<url>` |
| 2 | `<name>` | 137 posts, joined 2022 | 22818764 | pre-installed | `<site>` | `<url>` |

Every row answers: who posted it, what their record is, how new the build is, what kind of release it is, and where it comes from. A bare list of URLs is not a report.

## Keeping this current

- Volume and join dates drift; re-measure when two candidates are close.
- The ban lists change; a host decision on the edge deserves a re-read of the pinned threads.
- When a new uploader starts dominating a game's thread, their measured record is the evidence — not a hunch about their site.
