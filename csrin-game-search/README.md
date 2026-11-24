# CS.RIN.RU Game Search

[English](./README.md) | [简体中文](./README.zh-CN.md)

An agent skill for finding a game on [CS.RIN.RU](https://cs.rin.ru/forum) (Steam Underground) and getting it running: search the board, read the right thread, rank what it finds, then patch the downloaded build.

Link hunting alone is a half-answer. A clean Steam build that will not start is not a resource, so the skill carries both halves.

## What it covers

- **The board's access model** — the 401 cookie handshake that replaces the usual bot wall, what an anonymous client can and cannot see, and why a downloaded link needs a session at all
- **Search that works** — the phpBB query parameters, the AppID-as-keyword trick that finds the newest build in one query, post-time sorting, pagination, and the flood control that punishes looping
- **Thread reading** — the two post templates (game card and upload post), build-stamp extraction, permalinks, quote and signature traps, and the two link states the board renders
- **Ranking** — Clean Steam Files over staff-recommended direct-download sites over known uploaders over one-off uploads, with host quality and build recency as tie-breakers, built on the board's own two pinned trust lists
- **Patching** — Steamless for the Steam Stub, Unsteam and uc-online2 for online play, GBE Fork for offline and LAN, Nemirtingas Epic Emulator for games on Epic Online Services, and the Unreal Engine two-exe trap
- **Session hygiene** — where a cookie may be stored, why a pasted session can die between two requests, and how to tell "not logged in" from "nothing found"

## What it does not cover

- **Downloading.** The skill returns links and says which downloader suits them; it does not fetch, extract, or install anything.
- **Accounts.** No registration, no password recovery, no ban evasion. A login is either the user's cookie or the user's credentials, used as given.
- **Bypassing the login wall.** Links behind the wall stay behind it. The skill reports what it can see and says what it cannot, rather than guessing URLs.
- **Banned hosts.** The board's untrusted-site and banned-host lists are binding; a banned host is never presented, not even as a fallback.

## Installation

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s csrin-game-search
```

Manual installation: copy this directory into the skills directory your agent reads.

## Requirements

- Network access to `cs.rin.ru` (or its onion service when the plain domain is unreachable)
- For anything that ends in a download link: a logged-in session, supplied by the user as cookies or credentials
- Python 3.9+ only if you use the shipped template; it is standard library only and makes no decisions on its own

## Structure

```text
SKILL.md                            # entry point: the three-phase workflow and the ranking summary
references/access-and-session.md    # handshake, login form, cookie formats, guest matrix, failure table
references/search-recipes.md        # query parameters, AppID search, sorting, throttling, fallbacks
references/thread-and-post-format.md# post templates, build stamps, pagination, link markup
references/source-ranking.md        # source tiers, host tiers, staff trust lists, reporting format
references/patch-and-run.md         # Steamless, Unsteam, GBE Fork, uc-online2, Nemirtingas EOS
references/session-persistence.md   # where a cookie may live, and how to revoke it
templates/csrin_session.py          # copy-and-adapt client: handshake, optional login, fetch, parse
```

## Warning

The board is a file-sharing community: links point at third-party hosts, and the uploads are not the board's. The staff maintain a malicious-host list precisely because downloads from it get people infected — use an ad blocker, prefer the hosts the staff recommend, scan what you download, and treat every archive password and "downloader" prompt as hostile until proven otherwise.

Nothing here grants a licence to any game. How a user obtained the files, and what their local law says about it, is their responsibility.
