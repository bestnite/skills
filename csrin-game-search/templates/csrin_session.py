#!/usr/bin/env python3
"""CS.RIN.RU client template: handshake, optional login, fetch, parse posts to JSON.

Copy this file, then edit only the spots marked ``ADAPT``. It is a template, not a
fixed tool: the cookie source, the user agent and the session path are yours to
decide, because they depend on the machine and the account, not on the board.

Standard library only. Nothing is probed, nothing is written unless you pass
``--save-session``, and no request is made that the URL does not name.

Usage:
    python csrin_session.py 'viewtopic.php?f=10&t=145160' --json
    python csrin_session.py 'search.php?keywords=2622380&sr=posts' --text
    CSRIN_USER=name CSRIN_PASSWORD=secret python csrin_session.py 'index.php'

Exit codes: 0 ok, 2 board rejected the request, 3 login failed, 4 no posts found.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

# ADAPT: the board's base URL. Keep it as the canonical domain; csrin.org only
# redirects here, and links inside pages are rendered against the redirector.
BASE = "https://cs.rin.ru/forum/"

# ADAPT: send a plausible desktop user agent. The board does not fingerprint it,
# but a bare urllib UA stands out in logs and is needlessly rude to the operator.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# ADAPT: where a saved session may live. The default is this skill's own .state/
# directory, which the skill gitignores; anything else is the user's call.
STATE_FILE = Path(__file__).resolve().parent.parent / ".state" / "session.json"

TOKEN_RE = re.compile(r"securitytoken=([A-Za-z0-9_-]{10,})")
TOKEN_EXP_RE = re.compile(r"securitytoken_expiration=(\d+)")
BUILD_RE = re.compile(r"(?i)\bbuild(?:\s*id)?[^0-9]{0,8}\[?(\d{5,})")
POST_ANCHOR_RE = re.compile(r'<a name="p(\d+)"[^>]*></a>')
BODY_OPEN_RE = re.compile(r'<div\b[^>]*class="postbody"[^>]*>', re.I)
SIGNATURE_RE = re.compile(r"_{10,}")
AUTHOR_RE = re.compile(r'class="postauthor"[^>]*>(.*?)</', re.S)
DATE_RE = re.compile(r"Posted:</b>\s*([^<]{4,60})")
DETAILS_RE = re.compile(r'<span class="postdetails">(.*?)</span>', re.S)
JOINED_RE = re.compile(r"Joined:</b>\s*([^<]+?)\s*(?:<br|$)")
POSTS_RE = re.compile(r"Posts:</b>\s*([\d,]+)")
ANCHOR_RE = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)


# --------------------------------------------------------------------------- #
# transport
# --------------------------------------------------------------------------- #

def _cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def _absorb(headers, cookies: dict[str, str]) -> None:
    """Keep the board's rotated session cookies.

    The board sets ``csrinru_phpbb3_u/_k/_sid`` on every response and changes
    ``_sid`` each time. A client that pastes one cookie header and ignores the
    response authenticates on its first request and answers as a guest from the
    second on -- which reads exactly like an expired session, but is not. Keep
    the jar, and the session survives.
    """
    for raw in headers.get_all("Set-Cookie") or []:
        name, _, value = raw.partition("=")
        value = value.split(";", 1)[0].strip()
        name = name.strip()
        if name.startswith("csrinru_phpbb3_") or name.startswith("securitytoken"):
            cookies[name] = value


def _request(url: str, cookies: dict[str, str], data: bytes | None = None,
             referer: str | None = None) -> tuple[int, str]:
    """Return (status, body). Never raises for HTTP status; raises for transport."""
    if not url.startswith("http"):
        url = urllib.parse.urljoin(BASE, url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if cookies:
        headers["Cookie"] = _cookie_header(cookies)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _absorb(resp.headers, cookies)
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        _absorb(exc.headers, cookies)
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Slow board or a dropped connection: report as status 0 so fetch retries.
        print(f"transport error: {exc}", file=sys.stderr)
        return 0, ""


def _mint_token(body: str, cookies: dict[str, str]) -> bool:
    """Read a 401 challenge page and install its two cookies. False if absent."""
    token, exp = TOKEN_RE.search(body), TOKEN_EXP_RE.search(body)
    if not token or not exp:
        return False
    cookies["securitytoken"] = token.group(1)
    cookies["securitytoken_expiration"] = exp.group(1)
    return True


def fetch(url: str, cookies: dict[str, str], data: bytes | None = None,
          referer: str | None = None) -> tuple[int, str]:
    """GET/POST with the board's two gates handled: the 401 cookie challenge and
    the rotating session cookie.

    The challenge is not a one-time gate: it reappears on some requests, so every
    response is checked for it and answered with a fresh token before one retry.
    A token is bound to the client that minted it, so always mint your own and
    never replay the user's.
    """
    status, body = 0, ""
    for _ in range(4):
        status, body = _request(url, cookies, data=data, referer=referer)
        if status == 0:
            continue
        if status != 401 and "CS RIN - Security check" not in body[:4000]:
            return status, body
        if not _mint_token(body, cookies):
            if not _mint_token(_request(BASE, cookies)[1], cookies):
                return status, body
    return status, body


def load_saved_session() -> dict[str, str]:
    """Read .state/session.json if the user allowed one to be saved. No probing."""
    try:
        blob = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}
    # Accept both {"cookies": {...}} (the documented shape) and a flat cookie map.
    raw = blob.get("cookies") if isinstance(blob, dict) and "cookies" in blob else blob
    if not isinstance(raw, dict):
        return {}
    return {k: str(v) for k, v in raw.items()}


def login(cookies: dict[str, str], username: str, password: str) -> dict[str, str]:
    """POST the phpBB login form. Returns the refreshed cookie set."""
    url = urllib.parse.urljoin(BASE, "ucp.php?mode=login")
    status, page = fetch(url, cookies)
    if status != 200:
        raise SystemExit(f"login: login page returned {status}")
    sid = re.search(r'name="sid"\s+value="([^"]+)"', page)
    fields = {
        "username": username,
        "password": password,
        "autologin": "on",
        "redirect": "index.php",
        "sid": sid.group(1) if sid else "",
        "login": "Login",
    }
    # ADAPT: hidden inputs change when the board hardens the form. If login starts
    # failing, read the form and copy every hidden field rather than guessing.
    data = urllib.parse.urlencode(fields).encode()
    status, page = fetch(url, cookies, data=data, referer=url)
    if "mode=logout" in page or "mode=logout" in fetch(BASE, cookies)[1]:
        return cookies
    raise SystemExit("login: rejected (wrong password, or a field the form now wants)")


def is_logged_in(html: str) -> bool:
    """The toolbar is the only reliable signal: Logout link versus Login link."""
    return "ucp.php?mode=logout" in html


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #

def strip_element(html: str, tag: str, cls: str) -> tuple[str, list[str]]:
    """Remove every <tag class="cls">…</tag>, returning (rest, removed_blocks)."""
    removed: list[str] = []
    opener = re.compile(rf'<{tag}\b[^>]*class="[^"]*\b{cls}\b[^"]*"[^>]*>', re.I)
    while True:
        match = opener.search(html)
        if not match:
            return html, removed
        depth, pos = 0, match.start()
        token_re = re.compile(rf"</?{tag}\b", re.I)
        while True:
            nxt = token_re.search(html, pos)
            if not nxt:
                break
            depth += -1 if html[nxt.start():nxt.start() + 2] == "</" else 1
            pos = nxt.end()
            if depth == 0:
                break
        removed.append(html[match.start():pos])
        html = html[:match.start()] + html[pos:]


def _text(fragment: str) -> str:
    fragment = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)</(p|div|li|tr)>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    text = unescape(fragment)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def post_regions(html: str) -> list[tuple[str, str]]:
    """Return [(post_id, region_html)] split on the board's per-post anchors.

    Each post begins with ``<a name="p<id>"></a>`` immediately before the author
    cell. Splitting there is robust across the theme's odd nesting, whereas
    counting ``<div class="postbody">`` is not: quotes, spoilers and signatures
    sometimes carry that class too.
    """
    anchors = [(m.start(), m.group(1)) for m in POST_ANCHOR_RE.finditer(html)]
    regions = []
    for index, (start, post_id) in enumerate(anchors):
        end = anchors[index + 1][0] if index + 1 < len(anchors) else len(html)
        regions.append((post_id, html[start:end]))
    return regions


def clean_date(value: str) -> str:
    """Post dates carry trailing nbsp entities; drop them and any cut-off tail."""
    text = _text(value)
    return re.sub(r"&[a-zA-Z#0-9]*\s*$", "", text).strip()


def parse_links(body_html: str) -> list[dict]:
    """Anchors in a post, with the board's own safety flags."""
    safe_part, unsafe_blocks = strip_element(body_html, "span", "link_unsafe")
    links = []
    for block, unsafe in [(safe_part, False)] + [(b, True) for b in unsafe_blocks]:
        for href, label in ANCHOR_RE.findall(block):
            href = unescape(href)
            if href.startswith(("#", "javascript:")):
                continue
            absolute = urllib.parse.urljoin(BASE, href)
            host = urllib.parse.urlsplit(absolute).netloc.lower()
            links.append({
                "href": absolute,
                "label": _text(label),
                "host": host,
                "internal": host.endswith("rin.ru") or host.endswith("csrin.org"),
                "unsafe": unsafe,
            })
    return links


def parse_posts(html: str, limit: int | None = None) -> list[dict]:
    """Turn one topic page into a list of post records.

    Quotes are stripped before link extraction, because a quoted post carries the
    quoted author's links and attributing those to the poster is how the wrong
    uploader ends up in a report. Signatures are cut at the board's underscore
    separator for the same reason: they hold the uploader's own site link, not a
    download for this game.
    """
    posts = []
    for post_id, region in post_regions(html):
        author = AUTHOR_RE.findall(region)
        date = DATE_RE.findall(region)
        details = [d for d in DETAILS_RE.findall(region) if "Joined:" in d]
        joined = JOINED_RE.findall(details[0]) if details else []
        count = POSTS_RE.findall(details[0]) if details else []
        message = region
        body_start = BODY_OPEN_RE.search(region)
        if body_start:
            message = region[body_start.start():]
        signature = SIGNATURE_RE.search(message)
        if signature and signature.start() > 200:
            message = message[:signature.start()]
        quoted_free, _ = strip_element(message, "div", "quote")
        text = _text(quoted_free)
        links = [link for link in parse_links(quoted_free) if not link["internal"]]
        posts.append({
            "post_id": post_id,
            "author": _text(author[0]) if author else None,
            "posted": clean_date(date[0]) if date else None,
            "joined": joined[0].strip() if joined else None,
            "post_count": int(count[0].replace(",", "")) if count else None,
            "build_ids": sorted({int(b) for b in BUILD_RE.findall(text)}, reverse=True),
            "links": links,
            "masked_links": text.count("[[Please login to see this link.]]"),
            "text": text,
        })
        if limit and len(posts) >= limit:
            break
    return posts


SEARCH_TOPIC_RE = re.compile(r'Topic:\s*<a\s[^>]*href="[^"]*viewtopic\.php\?[^"]*?t=(\d+)[^"]*"[^>]*>(.*?)</a>', re.S)
SEARCH_FORUM_RE = re.compile(r'Forum:\s*<a[^>]*>([^<]+)</a>', re.S)
SEARCH_TOTAL_RE = re.compile(r"Search found (\d+) matches?")


TOPIC_ROW_RE = re.compile(
    r'<a href="\./viewtopic\.php\?f=(\d+)&amp;t=(\d+)[^"]*"[^>]*class="topictitle">(.*?)</a>', re.S)
TOPIC_FORUM_RE = re.compile(r'viewforum\.php\?f=\d+[^"]*">([^<]+)</a>')
TOPIC_AUTHOR_RE = re.compile(r'class="topicauthor"[^>]*>.*?>([^<]+)</a>', re.S)


def parse_topics(html: str, limit: int | None = None) -> list[dict]:
    """Turn a topic-list search page (`sr=topics`) into rows.

    One title search returns both threads a game needs: the `Main Forum`
    discussion thread and the `Steam Content Sharing` clean-files thread. Read the
    forum column to tell them apart.
    """
    rows, matches = [], list(TOPIC_ROW_RE.finditer(html))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(html)
        rest = html[match.end():end]
        forum = TOPIC_FORUM_RE.search(rest)
        author = TOPIC_AUTHOR_RE.search(rest)
        rows.append({
            "forum_id": match.group(1),
            "topic_id": match.group(2),
            "title": _text(match.group(3)),
            "forum": _text(forum.group(1)) if forum else None,
            "author": _text(author.group(1)) if author else None,
        })
        if limit and len(rows) >= limit:
            break
    return rows


def _strip_search_chrome(text: str) -> str:
    """Drop the reply/view counters that precede a search result's excerpt."""
    lines = text.splitlines()
    while lines and re.match(r"^(Replies:|Views:|\s*$)", lines[0]):
        lines.pop(0)
    return "\n".join(lines).strip()


def search_total(html: str) -> int | None:
    """The result count on a search page: a cheap volume metric for one author."""
    match = SEARCH_TOTAL_RE.search(html)
    return int(match.group(1)) if match else None


def parse_search(html: str, limit: int | None = None) -> list[dict]:
    """Turn a search results page into rows: forum, topic, post id, author, date, excerpt.

    The excerpt is the payload: it carries the build stamp and the host names even
    for an anonymous reader, whose links are masked everywhere on the board.
    """
    rows = []
    for post_id, region in post_regions(html):
        topic = SEARCH_TOPIC_RE.search(region)
        forum = SEARCH_FORUM_RE.search(region)
        author = AUTHOR_RE.findall(region)
        date = DATE_RE.findall(region)
        text = _text(region)
        if date:
            stamp = clean_date(date[0])
            cut = text.find(stamp)
            if cut >= 0:
                text = text[cut + len(stamp):].lstrip()
        rows.append({
            "post_id": post_id,
            "forum": _text(forum.group(1)) if forum else None,
            "topic_id": topic.group(1) if topic else None,
            "topic": _text(topic.group(2)) if topic else None,
            "author": _text(author[0]) if author else None,
            "posted": clean_date(date[0]) if date else None,
            "excerpt": _strip_search_chrome(text)[:400],
            "build_ids": sorted({int(b) for b in BUILD_RE.findall(text)}, reverse=True),
        })
        if limit and len(rows) >= limit:
            break
    return rows


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="board path or absolute URL")
    parser.add_argument("--cookies", help="cookie header string, k=v; k=v")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--text", action="store_true", help="print post text only")
    parser.add_argument("--max-posts", type=int, default=None)
    parser.add_argument("--save-session", action="store_true",
                        help="write the cookie set to .state/session.json (0600)")
    args = parser.parse_args(argv)

    cookies: dict[str, str] = {}
    if args.cookies:
        for part in args.cookies.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                cookies[key.strip()] = value.strip()
    else:
        cookies = load_saved_session()

    had_session = bool(cookies.get("csrinru_phpbb3_sid"))
    _, index = fetch(BASE, cookies)
    if had_session and not is_logged_in(index):
        # A stale phpBB session answers as a guest, not with an error.
        print("warning: session not logged in (toolbar shows Login)", file=sys.stderr)

    user, password = os.environ.get("CSRIN_USER"), os.environ.get("CSRIN_PASSWORD")
    if user and password:
        login(cookies, user, password)

    status, page = fetch(args.url, cookies, referer=BASE)
    if status != 200:
        print(f"request failed: {status}", file=sys.stderr)
        return 2
    if "cannot use search at this time" in page:
        print("search is flood-limited right now; wait a few minutes "
              "or use a known topic URL instead", file=sys.stderr)
        return 5
    if args.save_session and args.cookies:
        STATE_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"cookies": cookies}, indent=2))
        tmp.chmod(0o600)
        tmp.replace(STATE_FILE)

    is_search = "Search found" in page or "Search these results" in page
    if is_search and 'class="topictitle"' in page and 'name="p' not in page:
        topics = parse_topics(page, args.max_posts)
        if not topics:
            print("topic search returned no rows", file=sys.stderr)
            return 4
        if args.json:
            print(json.dumps({"url": args.url, "logged_in": is_logged_in(page),
                              "matches": search_total(page), "topics": topics},
                             indent=2, ensure_ascii=False))
        else:
            total = search_total(page)
            if total is not None:
                print(f"matches={total}")
            for row in topics:
                print(f"t{row['topic_id']}\tf{row['forum_id']}\t{row['author']}\t"
                      f"[{row['forum']}] {row['title']}")
        return 0
    if is_search:
        rows = parse_search(page, args.max_posts)
        if not rows:
            print("search page returned no rows", file=sys.stderr)
            return 4
        if args.json:
            print(json.dumps({"url": args.url, "logged_in": is_logged_in(page),
                              "matches": search_total(page), "results": rows},
                             indent=2, ensure_ascii=False))
        else:
            total = search_total(page)
            if total is not None:
                print(f"matches={total}")
            for row in rows:
                print(f"p{row['post_id']}\t{row['posted']}\t{row['author']}\t"
                      f"build={row['build_ids'] or '-'}\ttopic={row['topic_id']}\t"
                      f"[{row['forum']}] {row['topic']}")
                print(f"    {row['excerpt'][:200]}")
        return 0

    posts = parse_posts(page, args.max_posts)
    if not posts:
        print(json.dumps({"url": args.url, "logged_in": is_logged_in(page), "posts": []},
                         indent=2, ensure_ascii=False) if args.json
              else "no posts found on this page", file=sys.stdout)
        return 4
    if args.json:
        print(json.dumps({"url": args.url, "logged_in": is_logged_in(page),
                          "posts": posts}, indent=2, ensure_ascii=False))
    elif args.text:
        for post in posts:
            print(f"--- p{post['post_id']} {post['author']} {post['posted']}")
            print(post["text"])
    else:
        for post in posts:
            hosts = ", ".join(sorted({urllib.parse.urlsplit(l['href']).netloc
                                      for l in post["links"] if l["href"].startswith("http")}))
            print(f"p{post['post_id']}\t{post['posted']}\t{post['author']}\t"
                  f"build={post['build_ids'] or '-'}\tlinks={len(post['links'])}\t{hosts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
