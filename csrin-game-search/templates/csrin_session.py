#!/usr/bin/env python3
"""CS.RIN.RU client template: handshake, optional login, fetch, parse posts to JSON.

Copy this file, then edit only the spots marked ``ADAPT``. It is a template, not a
fixed tool: the cookie source, the user agent and the session path are yours to
decide, because they depend on the machine and the account, not on the board.

Standard library only. Nothing is probed, nothing is written unless you pass
``--save-session``, and no request is made that the URL does not name.

Usage:
    python csrin_session.py --find "<English game name>"      # search + newest pages, one call
    python csrin_session.py 'viewtopic.php?t=<topic>' --last  # digest one thread's newest page
    python csrin_session.py 'viewtopic.php?f=10&t=<topic>' --json
    python csrin_session.py 'search.php?keywords=<appid>&sr=posts' --text
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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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

# One request may not hang the whole run: a slow host costs seconds, not minutes.
TIMEOUT = 15

# The phpBB identity cookies; ``securitytoken`` is deliberately not in this set.
COOKIE_PREFIX = "csrinru_phpbb3_"

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
        if name.startswith(COOKIE_PREFIX) or name.startswith("securitytoken"):
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
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
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


def save_session(cookies: dict[str, str], user: str | None = None) -> Path:
    """Write the session for the next run, keeping only what stays valid.

    The phpBB identity cookies survive between runs; ``securitytoken`` does not
    — it is bound to the client that minted it and expires daily — so writing it
    to disk would store a credential that is useless tomorrow and stale today.
    """
    keep = {k: v for k, v in cookies.items() if k.startswith(COOKIE_PREFIX)}
    payload: dict[str, object] = {
        "cookies": keep,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if user:
        payload["user"] = user
    STATE_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.chmod(0o600)
    tmp.replace(STATE_FILE)
    return STATE_FILE


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
# one-shot lookups: one call, raw material, no decisions
# --------------------------------------------------------------------------- #

def search_url(query: str, sort: str | None = None) -> str:
    """Topic-title search — the cheapest useful first query.

    ``sort="time"`` asks for newest-started topics first, which is the only
    ordering that separates a game from a dozen similarly named ones.
    """
    params = {
        "keywords": query,
        "terms": "all",
        "sf": "titleonly",
        "sr": "topics",
        "submit": "Search",
    }
    if sort == "time":
        params.update({"sk": "t", "sd": "d"})
    return BASE + "search.php?" + urllib.parse.urlencode(params)


def fetch_last_page(topic_id: str, cookies: dict[str, str]) -> tuple[int, str]:
    """One request for the newest page.

    phpBB clamps an offset past the end of the topic, so asking for a huge
    ``start`` returns the last page without paging through the thread first.
    Verified on 2026-11-25 against a 44-page topic: ``start=99999`` and the true
    last offset returned the same posts.
    """
    url = f"{BASE}viewtopic.php?t={topic_id}&start=999999"
    return fetch(url, cookies, referer=BASE)


def format_post(post: dict) -> str:
    """One post as two lines: the metadata the ranking needs, then a text peek."""
    posted = re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*",
                    "", post["posted"] or "")
    bits = [f"p{post['post_id']}", posted[:24], post["author"] or "?"]
    if post.get("post_count") is not None:
        bits.append(f"posts={post['post_count']}")
    if post.get("joined"):
        bits.append(f"joined={post['joined']}")
    if post.get("build_ids"):
        bits.append("build=" + ",".join(str(b) for b in post["build_ids"][:3]))
    hosts = sorted({link["host"] for link in post["links"] if link.get("host")})
    if hosts:
        bits.append("hosts=" + ",".join(hosts[:4]))
    unsafe = sum(1 for link in post["links"] if link.get("unsafe"))
    if unsafe:
        bits.append(f"unsafe={unsafe}")
    if post.get("masked_links"):
        bits.append("masked")
    text = " ".join(post["text"].split())[:240]
    return "  ".join(bits) + "\n      " + text


def find(query: str, cookies: dict[str, str], topics_n: int = 2,
         posts_n: int = 15, list_n: int = 0, sort: str | None = None) -> int:
    """Search by title, then print the newest page of the top topics.

    It gathers; it does not decide. No topic is called the best, nothing is
    filtered for "looks like a release", and a short page is reported as short —
    reading further back, or opening another topic, stays the agent's call.
    """
    status, page = fetch(search_url(query, sort), cookies, referer=BASE)
    if status != 200:
        print(f"search failed: {status}", file=sys.stderr)
        return 2
    if "cannot use search at this time" in page:
        print("search is flood-limited right now; wait a few minutes or open "
              "a known topic URL", file=sys.stderr)
        return 5
    total = search_total(page)
    rows = parse_topics(page, None)
    # Every row on the page is printed by default: a clean-files thread can sit
    # below a dozen same-name games, and the forum column is how it is spotted.
    topics = rows[:list_n] if list_n > 0 else rows
    print(f"search: {query!r} -> {total if total is not None else '?'} matches; "
          f"{len(rows)} rows on this page, showing {len(topics)}")
    if total is not None and total > len(rows):
        print(f"  note: {total - len(rows)} more matches are on later result pages; "
              f"narrow it with the AppID or the exact English name")
    if len(rows) > len(topics):
        print(f"  note: {len(rows) - len(topics)} rows hidden by --list")
    if not topics:
        print("no topic rows: try the AppID, the untranslated English name, or "
              "the series name", file=sys.stderr)
        return 4
    for index, topic in enumerate(topics, 1):
        print(f"  {index}. t={topic['topic_id']}  [{topic['forum']}]  {topic['title']}")
    # One request per opened topic, never a page walk: the cost of --find is
    # 1 + topics_n requests no matter how many matches the query produced.
    chosen = topics[:max(0, min(topics_n, 6))]
    with ThreadPoolExecutor(max_workers=max(1, min(4, len(chosen)))) as pool:
        pages = list(pool.map(lambda t: fetch_last_page(t["topic_id"], cookies), chosen))
    for topic, (status, html) in zip(chosen, pages):
        print(f"\n--- t={topic['topic_id']} last page (status {status}): {topic['title']}")
        for post in parse_posts(html, posts_n):
            print(format_post(post))
    return 0


def last_page(url: str, cookies: dict[str, str], posts_n: int = 15) -> int:
    """Digest the newest page of one topic URL."""
    match = re.search(r"[?&]t=(\d+)", url)
    if not match:
        print("--last needs a viewtopic.php?t=<id> URL", file=sys.stderr)
        return 2
    status, html = fetch_last_page(match.group(1), cookies)
    if status != 200:
        print(f"request failed: {status}", file=sys.stderr)
        return 2
    for post in parse_posts(html, posts_n):
        print(format_post(post))
    return 0


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", nargs="?", help="board path or absolute URL")
    parser.add_argument("--find", metavar="QUERY",
                        help="one shot: title search, then the newest page of the top topics")
    parser.add_argument("--topics", type=int, default=2,
                        help="topics to open in --find, capped at 6 (default 2)")
    parser.add_argument("--list", type=int, default=0, metavar="N",
                        help="result rows to print in --find; 0 means all (default 0)")
    parser.add_argument("--sort", choices=("relevance", "time"),
                        help="--find ordering; 'time' puts the newest topics first")
    parser.add_argument("--posts", type=int, default=15, help="posts per page digest (default 15)")
    parser.add_argument("--last", action="store_true",
                        help="digest the newest page of the given topic URL")
    parser.add_argument("--cookies", help="cookie header string, k=v; k=v")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--text", action="store_true", help="print post text only")
    parser.add_argument("--max-posts", type=int, default=None)
    parser.add_argument("--save-session", action="store_true",
                        help="write the phpBB cookies to .state/session.json (0600); securitytoken is never stored")
    args = parser.parse_args(argv)

    cookies: dict[str, str] = {}
    if args.cookies:
        for part in args.cookies.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                cookies[key.strip()] = value.strip()
    else:
        cookies = load_saved_session()

    had_session = bool(cookies.get(COOKIE_PREFIX + "sid"))
    _, index = fetch(BASE, cookies)
    if had_session and not is_logged_in(index):
        # A stale phpBB session answers as a guest, not with an error.
        print("warning: session not logged in (toolbar shows Login)", file=sys.stderr)

    user, password = os.environ.get("CSRIN_USER"), os.environ.get("CSRIN_PASSWORD")
    if user and password:
        login(cookies, user, password)

    if args.find:
        return find(args.find, cookies, args.topics, args.posts,
                    args.list, None if args.sort in (None, "relevance") else args.sort)
    if not args.url:
        parser.error("give a board URL, or --find QUERY")
    if args.last:
        return last_page(args.url, cookies, args.posts)

    status, page = fetch(args.url, cookies, referer=BASE)
    if status != 200:
        print(f"request failed: {status}", file=sys.stderr)
        return 2
    if "cannot use search at this time" in page:
        print("search is flood-limited right now; wait a few minutes "
              "or use a known topic URL instead", file=sys.stderr)
        return 5
    if args.save_session and args.cookies:
        saved = save_session(cookies, user)
        print(f"session written to {saved}", file=sys.stderr)

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
