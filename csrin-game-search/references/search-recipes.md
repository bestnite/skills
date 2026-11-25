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
| `fid[]` | forum id | optional scope, for a follow-up only — see "Search globally" below |
| `author` | username | restrict results to one account's posts — the uploader-measurement query |
| `submit` | `Search` | required by the form, harmless in a GET |

## Search globally — the forum column does the sorting

Do not pre-select a section, and never run one query per forum. A global query already returns every section the account can see, and each row names its forum: `Main Forum`, `Steam Content Sharing`, `Temporarily Restricted Topics`, and so on. That column is how you tell a clean-files thread from a discussion thread — filtering by `fid[]` before you know which is which is exactly how the SCS thread gets missed.

`Steam Content Sharing` is a section (`f=22`) under English Forums, not a tag and not a search mode. Its threads carry an `SCS - …` prefix in the title, which is the upload team's naming, not a phpBB category. Search the game name globally and let the forum column classify the hit.

The one legitimate use of `fid[]` is a follow-up after a global search has already told you where the thread lives.

## Two shapes

They answer different questions:

- **`sr=topics`** — "which thread is this game's?" Returns one row per topic with forum name, author, reply count, view count, last-post time. Cheap and precise when the title matches.
- **`sr=posts`** — "what is the newest build, and who uploaded it?" Returns post rows with author, post date, and a ~300-character excerpt that usually contains the build number and host names.

## AppID first

Uploader posts embed Steam artwork URLs such as
`https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/<appid>/header.jpg`
or a cached variant like `.../api/image-cache/app_<appid>_header.jpg`. That makes the AppID a word in the post text, so it is searchable:

```
search.php?keywords=<appid>&terms=all&sf=all&sr=posts&sk=t&sd=d&submit=Search
```

Measured: a single AppID query returned dozens of matches, newest first, with build numbers, uploader names and host names in the excerpts. This is the single best entry point — it finds the newest build without walking 200 thread pages, and it works even for games whose thread title is not exactly the store name.

Caveat: a post only matches if it actually contains the AppID. Posts that only say "updated, see previous post" do not. When the AppID query returns nothing, fall back to the title query.

## Title first (fallback)

```
search.php?keywords=<game+name>&terms=all&sf=titleonly&sr=topics&submit=Search
```

One title search returns a game's two threads: the `Main Forum` discussion thread and the `SCS - <Game>` clean-files thread in Steam Content Sharing (`f=22`). Read the forum column, not the title, to tell them apart — see `scs-and-clean-files.md`.

The board indexes the English Steam store name. Topic titles carry a square-bracket tag in front of the game name (`[ Info ]`, `[ Release ]`) or a trailing one (`[Pre-Release]`, `[Early Access]`, a cracked marker), and separate reupload topics name their purpose in the title. Search the bare game name and ignore the tag rather than searching for the tag.

`sf=firstpost` is useful for a distinctive phrase, but not for a game lookup: it searches only the opening post, and the newest build lives in a reply.

## Author search: measuring an uploader

```
search.php?author=<username>&terms=all&sr=posts&submit=Search
```

The result header reads `Search found N matches`: the account's posting volume. That figure is reliable, and it is what the ranking in `source-ranking.md` starts from.

**Do not try to filter it by keyword.** phpBB drops words that occur in too many posts, and a phrase every release post contains is exactly the kind of term it drops: measured on 2026-11-25, an author search with a `Clean Steam Files` keyword returned 4,422 matches for an account whose total post count was 5,450 — its whole history, not its releases. Any author-plus-keyword count is noise, however plausible it looks.

Read composition off the same result page instead. It lists posts with forum, date and an excerpt, so the sample is already there: count how many of the visible posts are release posts — depot or manifest blocks, build stamps, host lists — against replies, questions and chatter. One page is a sample, not a census; say "most of the first page" rather than inventing a ratio.

It is one search either way, so the cost per candidate is one query. Flood control applies (see below), so measure only the two or three accounts genuinely in contention.

## One call instead of six

`templates/csrin_session.py` ships two modes that collapse the usual sequence:

```
python csrin_session.py --find "<English name>" [--topics 2] [--posts 15]
python csrin_session.py 'viewtopic.php?t=<id>' --last [--posts 15]
```

`--find` runs the title search and lists every matching row; with `--topics N` it also opens the newest pages of the first N topics, printing one two-line block per post: id, date, author with post count and join date, build stamp, hosts, unsafe count, masked flag, and the first 240 characters. `--last` does the same for one topic over its last three pages (`--pages N`): the newest page costs one request, because phpBB clamps `start=999999` to the final page, and the two before it follow from its pagination links.

Cost is one search request plus `opened × pages` page requests (opened defaults to 0, capped at 6; pages default 3), whatever the query returns — forty-one matches list the same as five. The tool prints the arithmetic before it fetches.

 a page of forty-one matching topics is still one request, and each opened topic is one more — never a page-by-page walk. `--topics N` (default 0, capped at 6) is the only lever, and the opened pages run in parallel. The usual run is therefore two commands: survey with `--find`, then open the chosen thread with `--last`. `--list N` trims the printed rows (0, the default, prints every row on the page, which is what keeps a `Steam Content Sharing` thread from hiding under a dozen same-name games). `--sort time` orders results by newest topic instead of relevance.

They exist to save round trips, not to decide anything: the result is raw material for the judgement in `source-ranking.md`. A page that turns out to be chatter is a normal outcome, and the next step is one page further back or another topic.

## Result rows

A `sr=posts` row carries everything needed to continue:

- forum name and topic title, with `viewtopic.php?f=<forum>&t=<topic>`
- `<a name="p<post_id>" id="p<post_id>">` — the post id, i.e. the permalink `viewtopic.php?p=<post_id>#p<post_id>`
- `<b class="postauthor">` — the uploader
- `Posted: <date>` — post date
- the excerpt, where the build stamp, the version string, the download size, host names and `[[Please login to see this link.]]` appear

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

The shipped client paces itself and treats the two limits differently:

- **Request starts are spaced by 250 ms** (`PACING`), so the four parallel page fetches of a thread tail arrive as a stagger rather than a burst. This is what keeps a normal run under the limit at all.
- **An HTTP 429** means the host is throttling: it waits once (the `Retry-After` header when present, 2 s otherwise, never more than 5 s), retries, and gives up with status 429 if refused again. The run reports that instead of hanging.
- **The board's flood page** (`Sorry but you cannot use search at this time`) is not a 429 — it arrives as a 200 with that sentence in it. The client maps it to exit code 5, and the right response is to stop searching and read threads by URL, which are not search.

A retry that is not throttling-related is not a strategy: on a 403 or a timeout, report it rather than pinging the host until it relents.

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
