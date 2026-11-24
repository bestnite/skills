# Steam Content Sharing (f=22)

Verified against the live board on 2026-11-25, with a logged-in session.

`Steam Content Sharing` — SCS — is the board's clean-files section: unmodified game files uploaded by people who own the game, taken straight from Steam. There are no cracks in this section, and that is the point: it is the only place where "Clean Steam Files" is a claim you can check rather than a phrase in a title.

The whole section is login-only. An anonymous client sees "Please register or log in to view this forum", and a topic inside it answers `The requested topic does not exist` — the same answer a deleted topic gives.

Size, measured on 2026-11-25: 13,824 topics across 139 pages.

## Thread anatomy

A game has two threads on this board, and they do different jobs:

| Thread | Forum | Holds |
|---|---|---|
| `[ Info ] <Game>` | Main Forum (`f=10`) | discussion, the game card, user uploads, repacks, pre-installed builds, cracks and emulators |
| `SCS - <variant> <Game> [DD.MM.YYYY]` | SCS (`f=22`) | the clean depot files and their manifests |

One title search returns both — see `search-recipes.md`.

An SCS topic is two posts, both by the maintenance account **`SCS God`** (joined 2007, 20k+ posts). Do not credit that account with the upload; the human uploader is named in the post body.

**Post 1 — the download card:**

```
About This Game:
<store description>
Official Site:
<store URL — carries the AppID>
Download Links:
Mirror 1
filecrypt.cc link  <Game> | <date>  ⚠ Unsafe filehosts - [READ ME]
  (Multi Hosts) < uploaded by <name> / pw: cs.rin.ru >
```

**Post 2 — the proof:**

```
Depots & Manifests
<depot id> - Depot <depot id> [Manifest <manifest id>]
Uploaded version: <full UTC timestamp> [Build <build id>]
```

The depot and manifest ids are what make this the trustworthy source: they identify exactly which Steam content is inside the archive, and the build id dates it. Quote the build id, not the thread title's date, when comparing versions.

## Freshness

An SCS thread is refreshed by the volunteer who maintains that game, on their own schedule, so its build can be older than what a user has already posted in the Main Forum thread — the maintainer of this skill reports that as the common case. Spot checks on 2026-11-25 over three games found two where both threads carried the same build — a reminder that the lag is per-game, not a rule.

Read both threads' numbers before reporting: the SCS build from the `Depots & Manifests` post, and the newest build in the Main Forum thread. Report the newer one as the playable build, and the SCS copy as the verifiable one — they are different claims.

## Titles

Sampled 324 titles on 2026-11-25: 276 `SCS - online <Game> [...]`, 20 `SCS - partially online <Game> [...]`, 28 pinned or administrative, and plain `SCS - <Game> [...]` entries in the archive pages. The bracketed date is the last upload date in `DD.MM.YYYY`.

Search the game name alone; do not include `SCS`, `online`, or the date. The variant word is part of the thread's identity, not a query term — do not interpret it as a guarantee about multiplayer support without reading the thread.

## Password and extraction

From the section FAQ (`t=46384`):

- Standard archive password: `cs.rin.ru`. Some uploads differ, and the real password is printed next to the download link as `< uploaded by <name> / pw: <password> >`. Read it there rather than assuming.
- The password field on the aggregator page is easy to miss, especially when it sits next to a CAPTCHA.
- Multi-part archives (`.part1.rar`, `.7z.001`, `.001`): download every part into one folder and open **only the first part** with a current 7-Zip or WinRAR.
- Extract `steamapps\common\<Game>` into its own directory, not into the Steam library — the game is not owned, so Steam cannot add it, and extracting into the library invites a mess.
- `.manifest` and `.acf` files are not needed to run a patched game.

## Downloads are aggregator containers

The `Mirror 1` link is a Filecrypt (or similar) container, and the board wraps those in the orange "unsafe filehosts" warning: the container fans out to many hosts, and some of them serve fake download pages and malware ads. That warning is not a ban — the board's own SCS team publishes these links. Treat it as an instruction to read the host list inside the container and to keep an ad blocker on.

Hosts inside the container still have to pass the ban list in `source-ranking.md`. A container that resolves to a banned host is not usable, however clean the files behind it are.

## Cracks are somewhere else

SCS never ships a crack. To run the download:

1. Read the opening post of the game's **Main Forum** thread — maintained uploaders keep the emulator and instructions there.
2. If the OP is stale, read the last pages of that thread and search it for `emu` or `crack*`.
3. If nothing fits, build the patch yourself: `patch-and-run.md`.

## When a link is dead

- Report a dead link in the SCS questions thread (`t=97145`).
- Request a re-upload in the Steam app request thread (`t=59381`), not in the questions thread, and not in the game thread.

Both are the board's own process; there is no faster channel, and asking in the wrong thread gets ignored.
