# Threads and posts

Verified against the live board on 2026-11-24.

## URL shapes

| URL | Meaning |
|---|---|
| `viewtopic.php?f=10&t=145160` | topic, page 1; `f` is accepted but the topic id is what matters |
| `viewtopic.php?t=145160&start=3030` | page 21 — `start` is a post offset in steps of 15 |
| `viewtopic.php?p=3591862#p3591862` | permalink to one post |
| `viewtopic.php?t=145160&view=print` | print view: all posts, still link-masked for guests |
| `viewforum.php?f=10` | topic list, last-post time per row |
| `feed.php?t=145160` | Atom, last 15 posts with full post HTML |
| `memberlist.php?mode=viewprofile&u=<id>` | uploader profile — join date and post count are the reputation signal |

15 posts per page. A big game thread can pass 200 pages; the pagination block lists the last pages directly, so read the last page first instead of walking forward.

## Two kinds of post

**Opening post — the game card.** A fixed template, and it is where the AppID and the game's identity live:

```
<header image: .../steam/apps/<appid>/header.jpg>
GAME NAME
Details
Store Page: <link>
Genre(s): ... Developer: ... Publisher: ... Release Date: ...
Language(s): ... Operating system(s): ...
Features: Single-player / Multi-player / ...
About The Game ...
```

The header image URL carries the AppID even for an anonymous reader, whose Store link is masked. Use it to confirm that a thread is the right game and to recover the AppID the post was stamped with.

**Upload post — the payload.** Uploaders do not follow one template. Observed shapes:

```
ELDEN RING NIGHTREIGN (v1.03.5 | Build 22818764 ALL DLC + ONLINE) (26.41 GB)
  ~Pre-Installed, Download, extract, Play

Game v1.03.3 / Calibration v1.03.5 [Build 22818764] loose files update and
  regulation.bin are now in my previous download post <link>

✦ Game Name: ... ✦ Build ID: 22818764 ✦ Base Game 26 GB, 1 Part
  ╰┈➤ Download Links: ✦ <host> (DDL Available, ...)
```

So the build stamp has to be extracted with tolerant matching, not a fixed field position:

- `Build 22818764`, `BuildID: 22818764`, `[Build 22818764]`, `build 22818764`
- version strings `v1.03.5`, `1.0.4`, `Update 12` — useful for humans, not comparable across uploaders
- `Pre-Installed` / `portable` / `loose files` / `repack` — tells you what the archive is before you download 26 GB

Treat a build number as the primary sort key, the post date as the tiebreaker, and the version string as decoration. Compare build numbers numerically, never as strings.

## Link markup

**Anonymous.** Every link in a post body is replaced server-side:

```html
<span class="link_removed">
  <span style="font-style: italic; color: #96964C">[[Please login to see this link.]]</span>
</span>
```

The href is gone — not hidden, not base64, not recoverable. `[[Please login to see this link.]]` is the literal string the board renders, and it is also what appears inside search excerpts and Atom feed content.

**Logged in.** Links render as anchors. Links on hosts outside the board's approved list are wrapped in a reveal widget:

```html
<span class="link_unsafe" style="display: none"> <a href="...">...</a> </span>
```

with a `reveal_unsafe()` click handler that flips `display`. Because the hiding is CSS on the client, a parser that reads the HTML gets the href without clicking. Do not report such a link without saying the board flagged the host as unapproved.

> This section is the one place where the wording of the markup for a logged-in reader is still unverified end to end; the CSS and JS that produce it are confirmed in the page source, the href-inside-HTML behaviour follows from that, and any parser must degrade gracefully if an anchor is absent.

## Parsing posts

- Each post body is `<div class="postbody"> … </div>`; a page holds 15 of them.
- Author: `<b class="postauthor">`; join date and total post count sit next to it in `<span class="postdetails">` — the two numbers that separate a long-running uploader from a drive-by account, and both are visible to an anonymous reader. The profile page behind `memberlist.php?mode=viewprofile&u=<id>` repeats them but needs a session; a post's author cell is the reliable source.
- Volume beyond those two numbers comes from an author search (`search.php?author=<name>&sr=posts`), not from the profile page — see `search-recipes.md`.
- Post date: `Posted: <date>` in the post header, in board-local time.
- **Quotes are not posts.** Quote blocks contain a nested `postbody` from an earlier post, with that post's links. Attribute a quoted link to the quoted author, or better, ignore quoted links entirely and use the author's own post.
- **Signatures are not content.** Signatures sit outside `postbody` and often carry the uploader's site link, Discord invite, or donation link. Never present a signature link as the game download.
- Deleted or moved topics answer `The requested topic does not exist` (an Information page). That includes topics in forums the current session cannot view — it is a permission answer, not proof of deletion.

## Reading order that saves work

1. Search by AppID, newest first — the first few rows already name the newest build and uploader.
2. Open the permalink of the newest plausible post (`&p=<post id>#p<post id>` puts it at the top of its page).
3. If that post points back ("see my previous post"), follow one hop, not the whole thread.
4. Only when search is unavailable, open the last page of the thread and scan backwards for the newest upload post.
