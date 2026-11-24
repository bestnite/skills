# Ranking sources and hosts

Verified against the live board on 2026-11-24. The board maintains all of this itself; this file is the working summary, the pinned threads are the authority.

Two pinned threads carry the trust decisions:

| Thread | What it holds |
|---|---|
| `t=95461` Recommended download and upload sites | trusted download sites, trusted file hosts, and the untrusted-site list; edited hundreds of times by staff |
| `t=159345` How to protect against malicious filehosters | banned hosts and multi-uploaders, plus the malware pattern behind them |

Both are edited continuously. When a host decision is close, re-read the pinned thread instead of trusting this summary — the summary has a date, the thread does not.

## What the labels mean

| Label in a post | What it actually is | Rank |
|---|---|---|
| **Clean Steam Files** (CSF) | unmodified Steam depot files, often with the manifests and `appmanifest_<appid>.acf` | 1 |
| `Pre-Installed`, `portable`, `loose files` | an extracted install tree, usually a repacked Steam build | 2 |
| repack (FitGirl, KaOsKrew, …) | compressed, pre-patched installer | 2 |
| direct-download site page | a third-party site hosting the build | 2 if staff-listed, else 3 |
| plain upload by an unknown account | file set of unknown provenance | 4 |

Clean files win because they can be patched by the routes in `patch-and-run.md`, their build is verifiable, and nothing was modified between Valve and the user. A repack is already patched: patching it again usually breaks it, and its build number can lag the thread.

Do not call something CSF because the thread title says "Clean Steam Files" — check that the post actually contains depots or manifests, or that the uploader's history is CSF. Uploaders reuse titles.

## Host tiers

**Tier A — on the staff recommended file hosts list.** As of 2026-11-24 that list is: 1Fichier, Catbox, Clicknupload, Daily Uploads, FileDitch, GoFile, Google Drive, HexUpload, Krakenfiles, Mail.ru Cloud, MediaFire, MEGA, Mixdrop, Pixeldrain, Sendcm, SendSpace, Yandex.Disk. Some are annotated "Requires an account" — quote that annotation to the user rather than promising an anonymous download.

Staff select these on explicit criteria, which are also the criteria worth quoting when a user asks why one host beats another: online for at least six months, anonymous browsing and downloading, no VPN block, works with uBlock Origin at default settings, HTTPS with no mixed content, no malware, no filehosters with malicious ads, fast takedown.

**Tier A — on the staff recommended sites list.** Direct-download and repack sites the staff reviewed: AnkerGames, FitGirl Repacks, GameBounty, KaOsKrew, Kapital Sin, SteamRIP, Appnetica, GLOAD, scene.cat, Scnlog, ReleaseBB, My Abandonware, oldgamesdownload, Old-Games.RU, The Collection Chamber, Torrminatorr, Wendy's Forum; trackers Rutracker, Rustorka, Rutor; crack and trainer sites Fearless Revolution, FLiNG, GameCopyWorld, Megagames, Online-Fix. A staff-listed direct-download site outranks any filehost chain, because the file is one page away instead of five.

**Tier B — a direct-download site the uploader runs, not on either list.** Sites like this exist (the forum has several uploaders with personal pages). They are not banned and not reviewed. Treat them as unverified: check the uploader's history in the thread, prefer the same uploader's filehost mirror if one exists, and say in the report that the site is not staff-listed.

**Tier C — any other host.** Report it, marked unlisted, only when nothing better exists in the thread.

**Never — the untrusted list.** The board's "NOT recommended" list is long and includes both plain bad and actively malicious: `dodi-repacks.site`, `game-repack.site`, `elamigosgames.net` and its lookalikes, `gamedrive.org` / `cybar.to`, `nexusgames.to`, `repack-games.com`, `steam-repacks.net`, `steamunderground.net`, `steamunlocked.net`, `worldofpcgames.com`, `oceanofgames.com`, `IGG-Games.com`, `freetp.org`, `nosteamgames.ro`, `pcgamestorrents.com`, `agfy.co`, `crackingpatching.com`, `getgamez.net`, `hishgames.org`, `games4u.org`, `loadgames.org`, `mrpcgamer.co`, `rgmechanics.com`, `sgcrack.com`, `small-games.info`, `steamcracked.co`, `steamhub.co`, `stggege.org`, `TinkerGames`, `unlocked-games.com`, `alltorrents.co`, `extrogames.com`, `gamesreleaser.com`, `game3rb.com`, `nosteamgames.ro` and any site named after a scene group (CODEX, CPY, RELOADED, SKIDROW …), because scene groups do not run public sites.

The banned-hosts thread adds the currently-banned malicious filehosters and multi-uploaders, including 1cloudfile, bowfile, buzzheavier / bzzhr / fuckingfast, datavaults, devuploads, file-me, filemirage, fileq, koramaup, ranoz, swiftuploads, usersdrive, zpaste, plus `akirabox`, `rootz.so`, `multiup.io` and `mirrored.to` flagged for pending bans on 2026-12-01 and 2027-01-01. Multi-uploaders matter because a single "download here" link can route to any of the banned hosts underneath.

Never present a banned host as an option, even as a last resort. Report "the thread exists, every link in it is on the staff ban list" and stop.

## Recency

Build number is the version. Compare numerically, newest wins.

| Signal | Use |
|---|---|
| `Build 22818764` | primary sort key |
| `v1.03.5`, `1.0.4` | human-readable, not comparable across uploaders |
| post date | tiebreaker between equal builds |
| "see my previous post" | follow one hop back, not the whole thread |
| thread last-post time | tells whether anyone still maintains the upload |

An old build is not automatically worse: if the newer build is a repack from an unknown account and the older one is CSF from a long-running uploader, report both and let the user choose, newest first.

## Uploader reputation

Read these off the post and the profile (`memberlist.php?mode=viewprofile&u=<id>`):

- join date and post count — years and thousands of posts is a track record; days and a handful of posts is not;
- whether the same account has maintained the thread across months, reuploading when hosts die;
- whether the account appears on the staff recommended list (several do, e.g. the uploaders behind Appnetica and GameBounty);
- whether the post publishes a build number, a size, a changelog or checksums — detail correlates with care;
- the `link_unsafe` wrapper: the board itself flagged the host, so say so.

## Reporting format

One table, most trusted first, then a short note on what was skipped and why:

| # | Build | Uploader | Host | Link | Notes |
|---|---|---|---|---|---|
| 1 | 22818764 | <name> | GoFile | <url> | CSF, staff-listed host, post 2026-09-04 |
| 2 | 22818764 | <name> | <site> | <url> | pre-installed, site not staff-listed |

Every row answers: what it is, how new it is, who posted it, where it comes from, and what to distrust. A bare list of URLs is not a report — the user cannot tell a CSF build from a repack of unknown origin.

## Keeping this current

- Re-read `t=95461` and `t=159345` when a host is unknown, newly seen, or on the edge of a ban date.
- Treat this file's host lists as a snapshot with a date, not a policy. The board edits its lists; this file does not update itself.
- When the board adds a host to its list, that is new information for the user, not a licence to add it here without reading the criteria above.
