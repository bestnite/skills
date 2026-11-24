# Threads and posts

Verified against the live board on 2026-11-24.

## URL shapes

| URL | Meaning |
|---|---|
| `viewtopic.php?f=<forum>&t=<topic>` | topic, page 1; the forum id is accepted but the topic id is what matters |
| `viewtopic.php?t=<topic>&start=<n>` | later page — `start` is a post offset in steps of 15 |
| `viewtopic.php?p=<post>#p<post>` | permalink to one post |
| `viewtopic.php?t=<topic>&view=print` | print view: all posts, still link-masked for guests |
| `viewforum.php?f=10` | topic list, last-post time per row |
| `feed.php?t=<topic>` | Atom, last 15 posts with full post HTML |
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
<GAME> (v<version> | Build <build> ALL DLC + ONLINE) (<size>)
  ~Pre-Installed, Download, extract, Play

Game v<version> / patch v<version> [Build <build>] loose files update and
  <file> is now in my previous download post <link>

✦ Game Name: ... ✦ Build ID: <build> ✦ Base Game <size>, <parts>
  ╰┈➤ Download Links: ✦ <host> (DDL Available, ...)
```

So the build stamp has to be extracted with tolerant matching, not a fixed field position:

- a `Build` word followed by the number, in any punctuation: `Build <n>`, `BuildID: <n>`, `[Build <n>]`, `build <n>`
- version strings `v1.03.5`, `1.0.4`, `Update 12` — useful for humans, not comparable across uploaders
- `Pre-Installed` / `portable` / `loose files` / `repack` — tells you what the archive is before you download a multi-gigabyte build

A third shape exists for Denuvo titles — a hypervisor release, recognisable by `EXPERIMENTAL hypervisor-based release`, a build number, and a group name such as `-ARTIFACT` or `DenuvOwO`. It is not a portable build; treat it as its own category and read `denuvo-and-hypervisor.md` before reporting it as playable.

Treat a build number as the primary sort key, the post date as the tiebreaker, and the version string as decoration. Compare build numbers numerically, never as strings.

## Link markup

**Anonymous.** Every link in a post body is replaced server-side:

```html
<span class="link_removed">
  <span style="font-style: italic; color: #96964C">[[Please login to see this link.]]</span>
</span>
```

The href is gone — not hidden, not base64, not recoverable. `[[Please login to see this link.]]` is the literal string the board renders, and it is also what appears inside search excerpts and Atom feed content.

**Logged in.** Links are ordinary anchors with `class="postlink"` and `rel="nofollow"`. Links on hosts the board does not approve are wrapped in a reveal widget:

```html
<span class="link_unsafe_overlay2">
  <a class="postlink link_unsafe_reveal" onclick="return reveal_unsafe(this);">&lt;aggregator&gt;.cc link</a>
  <span class="link_unsafe"><a href="https://&lt;aggregator&gt;/Container/..." class="postlink">...</a></span>
</span>
```

The href is **in the HTML**, hidden only by `display: none`, so a parser reads it without clicking and without a browser. The stylesheet defines two warning wrappers, `link_unsafe_overlay2` (orange) and `link_unsafe_overlay` (red); the orange one is what the clean-files team's aggregator links use. Neither is a ban — the board's own SCS posts carry them — so report such a link with the flag attached instead of dropping it.

Verified logged in on 2026-11-25 against a live topic in the clean-files section.

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
