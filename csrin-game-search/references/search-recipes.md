# Search recipes

Verified against the live board on 2026-11-24. Endpoint: `https://cs.rin.ru/forum/search.php`.

## Query parameters that matter

| Parameter | Values | Effect |
|---|---|---|
| `keywords` | free text, or an AppID | the query; `+` between words |
| `terms` | `all` / `any` | AND / OR |
| `sf` | `all`, `titleonly`, `firstpost` | search whole post, topic title only, opening post only |
| `sr` | `topics` / `posts` | return topic rows, or post rows with an excerpt |
| `sk` | `t` | sort key: post time |
| `sd` | `d` / `a` | descending / ascending |
| `start` | `0`, `15`, `30`, … | result pagination, 15 per page |
| `fid[]` | forum id | restrict to a forum (not separately verified; expect the same flood control) |
| `author` | username | restrict results to one account's posts — the uploader-measurement query |
| `submit` | `Search` | required by the form, harmless in a GET |

Two shapes, and they answer different questions:

- **`sr=topics`** — "which thread is this game's?" Returns one row per topic with forum name, author, reply count, view count, last-post time. Cheap and precise when the title matches.
- **`sr=posts`** — "what is the newest build, and who uploaded it?" Returns post rows with author, post date, and a ~300-character excerpt that usually contains the build number and host names.

## AppID first

Uploader posts embed Steam artwork URLs such as
`https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2622380/header.jpg`
or a cached variant like `.../api/image-cache/app_2622380_header.jpg`. That makes the AppID a word in the post text, so it is searchable:

```
search.php?keywords=<appid>&terms=all&sf=all&sr=posts&sk=t&sd=d&submit=Search
```

Measured: AppID `2622380` returned 62 matches, newest first, with build numbers, uploader names, and host names in the excerpts. This is the single best entry point — it finds the newest build without walking 200 thread pages, and it works even for games whose thread title is not exactly the store name.

Caveat: a post only matches if it actually contains the AppID. Posts that only say "updated, see previous post" do not. When the AppID query returns nothing, fall back to the title query.

## Title first (fallback)

```
search.php?keywords=<game+name>&terms=all&sf=titleonly&sr=topics&submit=Search
```

One title search returns a game's two threads: the `Main Forum` discussion thread and the `SCS - <Game>` clean-files thread in Steam Content Sharing (`f=22`). Read the forum column, not the title, to tell them apart — see `scs-and-clean-files.md`.

The board indexes the English Steam store name. Topic titles look like `[ Info ] ELDEN RING NIGHTREIGN`, `[ Release ] ...`, `... [Pre-Release]`, `... [Early Access]`, and separate `... Clean Steam Files` reupload topics. Search the bare game name and ignore the tag prefix rather than searching for `[Info]`.

`sf=firstpost` is useful for a distinctive phrase — `Build ID` returned 379 opening posts — but not for a game lookup: it searches only the first post, and the newest build lives in a reply.

## Author search: measuring an uploader

```
search.php?author=<username>&terms=all&sr=posts&submit=Search
```

The result header reads `Search found 3977 matches`: that is the account's posting volume, and it is the number the ranking in `source-ranking.md` is built on. Repeat with a keyword the resource posts always carry to separate uploads from chatter:

```
search.php?author=<username>&keywords=Build&terms=all&sr=posts&submit=Search
search.php?author=<username>&keywords=Clean+Steam+Files&terms=all&sr=posts&submit=Search
```

Two queries per candidate, and only for candidates genuinely in contention — each one spends the search budget described below. A guest can run these; no session is needed to read the counts.

## Result rows

A `sr=posts` row carries everything needed to continue:

- forum name and topic title, with `viewtopic.php?f=<forum>&t=<topic>`
- `<a name="p<post_id>" id="p<post_id>">` — the post id, i.e. the permalink `viewtopic.php?p=<post_id>#p<post_id>`
- `<b class="postauthor">` — the uploader
- `Posted: <date>` — post date
- the excerpt, where `Build 22818764`, `v1.03.5`, `26.41 GB`, host names and `[[Please login to see this link.]]` appear

Sorting is newest-first with `sk=t&sd=d`; the same order came back without those parameters, so treat newest-first as the default and re-sort yourself if the board changes.

## Rate limiting is the real constraint

Ask too much and the board answers with an Information page:

> Sorry but you cannot use search at this time. Please try again in a few minutes.

Observed: the block persists for minutes and is **not** reset by minting a fresh `securitytoken` — it is tied to the client address, not the session. A separate network path got its own quota, which is confirmation of the per-address model, not a workaround to build on.

So budget searches per task:

1. one AppID query (`sr=posts`) — normally enough to find the thread and the newest build;
2. one title query only if the AppID found nothing;
3. stop. Read threads by URL from there; `viewtopic.php` and `viewforum.php` are not search and are not throttled this way.

Do not loop, and never fan out one search per forum to "be thorough".

## When search is unavailable

In order of cost:

1. **Direct URL** — if the user, a previous run, or a feed item gave a topic id, open `viewtopic.php?t=<id>` and skip search entirely.
2. **Forum listing** — `viewforum.php?f=10` lists topics with last-post time; the board default order already puts recently updated threads near the top. It is not search and costs nothing.
3. **Atom feed** — `feed.php?t=<topic id>` returns the last 15 posts of one topic with full post HTML, and `feed.php` returns the sitewide latest 15 with the forum label. No handshake needed, no flood control, but links inside entries are masked exactly like the HTML pages.
4. **External index** — a general web search for `site:cs.rin.ru "<game name>"` finds the thread when the board's own search refuses. Treat the result as a hint and verify on the board.

## What the search cannot do

- No regular expressions, no operators, no "build greater than".
- Short or common tokens (`build`, `update`, `dlc`) return thousands of hits and are useless alone.
- It does not search the contents of `Steam Content Sharing` for an anonymous client, and no login-only content is visible before authenticating.
