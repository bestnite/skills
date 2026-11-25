#!/usr/bin/env python3
"""CS.RIN.RU client: handshake, optional login, search topics, digest a thread tail.

It runs as shipped. The spots marked ``ADAPT`` are the ones that change when the
board changes — a hidden login field, a user agent that starts getting refused —
not settings for a particular machine: the session path is resolved from this
file's location and the cookie source is a flag or an environment variable.

Standard library only. Nothing is probed, nothing is written unless you pass
``--save`` on ``login``, and no request is made that the URL does not name.

Usage:
    csrin_session.py search "<English game name>"     # one request: every matching topic row
    csrin_session.py topic 102530                     # 3 pages of that thread's tail
    csrin_session.py post 3607669 3607680 --links     # two posts by id, in parallel
    csrin_session.py fetch 'search.php?keywords=<appid>&sr=posts'
    csrin_session.py login --save                     # credentials from env or prompt
    csrin_session.py whoami                           # is the session still logged in?

    csrin_session.py search --help                    # every subcommand explains itself

Exit codes: 0 ok, 1 not logged in, 2 request failed or bad argument, 3 login
rejected, 4 nothing found, 5 search flood-limited.
"""

from __future__ import annotations

import argparse
import atexit
import getpass
import json
import os
import re
import sys
import threading
import time
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

# Request pacing. The board is a hobby server and answers 429 when hammered, so
# request starts are spaced instead of fired in a burst; a 429 waits, it does not
# fail. Measured on 2026-11-25: four parallel page fetches stayed under the limit
# with this spacing.
PACING = 0.25          # seconds between two request starts
RETRY_AFTER = 2.0      # default wait for a 429 that carries no Retry-After
RETRY_AFTER_CAP = 5.0  # a host that asks for longer than this is not worth the wait
_rate_lock = threading.Lock()
_last_start = 0.0
_last_retry_after = 0.0

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


def _throttle() -> None:
    """Space request starts so parallel workers do not burst at the board."""
    global _last_start
    with _rate_lock:
        wait = PACING - (time.monotonic() - _last_start)
        if wait > 0:
            time.sleep(wait)
        _last_start = time.monotonic()


VERBOSE = False


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
    _throttle()
    started = time.monotonic()
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            _absorb(resp.headers, cookies)
            body = resp.read().decode("utf-8", "replace")
            if VERBOSE:
                print(f"# {resp.status} {time.monotonic() - started:5.2f}s "
                      f"{len(body):7d}B {url}", file=sys.stderr)
            return resp.status, body
    except urllib.error.HTTPError as exc:
        global _last_retry_after
        if VERBOSE:
            print(f"# {exc.code} {time.monotonic() - started:5.2f}s {url}", file=sys.stderr)
        _absorb(exc.headers, cookies)
        try:
            _last_retry_after = float(exc.headers.get("Retry-After") or 0)
        except (TypeError, ValueError):
            _last_retry_after = 0.0
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
    """GET/POST with the board's gates handled: the 401 cookie challenge, the
    rotating session cookie, and a 429 that is waited out rather than failed.

    The challenge is not a one-time gate: it reappears on some requests, so every
    response is checked for it and answered with a fresh token before one retry.
    A token is bound to the client that minted it, so always mint your own and
    never replay the user's.
    """
    status, body = 0, ""
    rate_hits = 0
    for _ in range(4):
        status, body = _request(url, cookies, data=data, referer=referer)
        if status == 0:
            continue
        if status == 429:
            # One wait, then give up: a host still refusing after a pause is a
            # host to retry later, not to stall the run for.
            if rate_hits:
                return status, body
            rate_hits += 1
            wait = min(_last_retry_after or RETRY_AFTER, RETRY_AFTER_CAP)
            print(f"rate limited (429); waiting {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
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
    """Write the session for the next run.

    The phpBB cookies survive between runs. ``securitytoken`` is bound to the
    client that minted it — this machine — and expires daily; keeping it too
    removes the 401 challenge (measured at 10s) from every following run, and a
    token that has expired simply earns one more challenge.
    """
    keep = {k: v for k, v in cookies.items()
            if k.startswith(COOKIE_PREFIX) or k.startswith("securitytoken")}
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
# session handling
# --------------------------------------------------------------------------- #

def parse_cookie_header(value: str) -> dict[str, str]:
    """``k=v; k=v`` to a dict — the shape a browser's copy-cookies gives."""
    cookies: dict[str, str] = {}
    for part in value.split(";"):
        if "=" in part:
            key, val = part.split("=", 1)
            cookies[key.strip()] = val.strip()
    return cookies


def open_session(cookies_arg: str | None) -> dict[str, str]:
    """Cookies for this run: explicit header first, then ``.state/``.

    Credentials in ``CSRIN_USER`` / ``CSRIN_PASSWORD`` log in for this run only
    and are never written anywhere. No request is spent checking the session up
    front — that check used to cost a page load on every command; the first real
    page reports a stale session instead (see ``request_page``).
    """
    saved = not cookies_arg
    cookies = parse_cookie_header(cookies_arg) if cookies_arg else load_saved_session()
    user, password = os.environ.get("CSRIN_USER"), os.environ.get("CSRIN_PASSWORD")
    if user and password:
        login(cookies, user, password)
    if saved and STATE_FILE.exists():
        # The token this run mints is written back, so the next run starts clean.
        atexit.register(lambda: _rewrite_session(cookies))
    return cookies


_warned_guest = False


def _rewrite_session(cookies: dict[str, str]) -> None:
    """Persist the refreshed token after a command; silence failures at exit."""
    try:
        save_session(cookies)
    except OSError:
        pass


def request_page(url: str, cookies: dict[str, str]) -> tuple[int, str]:
    """Fetch one board page, mapping the two failures worth their own exit code.

    A stale saved session answers as a guest rather than with an error, so the
    first such page produces one warning. Costs nothing extra: it is the page the
    command needed anyway.
    """
    global _warned_guest
    status, page = fetch(url, cookies, referer=BASE)
    if status == 200 and cookies and not _warned_guest and not is_logged_in(page):
        _warned_guest = True
        print("warning: the session is not logged in; links will be masked. "
              "Run 'login --save' or pass --cookies.", file=sys.stderr)
    if status == 200 and "cannot use search at this time" in page:
        print("search is flood-limited right now; wait a few minutes or open "
              "a known topic URL", file=sys.stderr)
        return 5, page
    if status != 200:
        print(f"request failed: {status}", file=sys.stderr)
        return 2, page
    return 0, page


# --------------------------------------------------------------------------- #
# board queries
# --------------------------------------------------------------------------- #

def search_url(query: str, sort: str | None = None) -> str:
    """Topic-title search — the cheapest useful first query.

    ``sort="time"`` asks for the newest topics first, which is the only ordering
    that separates one game from a dozen similarly named ones.
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
    """One request for a topic's newest page.

    phpBB clamps an offset past the end, so a huge ``start`` returns the final
    page without paging through the thread first. Verified on 2026-11-25 against
    a 44-page topic: ``start=99999`` and the true last offset returned the same
    posts.
    """
    url = f"{BASE}viewtopic.php?t={topic_id}&start=999999"
    return fetch(url, cookies, referer=BASE)


def topic_tail(topic_id: str, cookies: dict[str, str],
               pages: int = 3) -> tuple[int, list[tuple[int, str]]]:
    """The last ``pages`` pages of a topic, oldest first, in 1 + (pages-1) requests.

    A tail of three exists because the newest page of a live thread is often
    people discussing the release rather than the release itself. The final page
    is one request; its pagination supplies the offsets of the two before it.
    """
    status, first = fetch_last_page(topic_id, cookies)
    if status != 200:
        return status, []
    # Pagination links arrive entity-escaped: viewtopic.php?t=68085&amp;start=645.
    starts = [int(value) for value in
              re.findall(r"(?:&amp;|&|\?)start=(\d+)", first)]
    last = max(starts) if starts else 0
    offsets = sorted({max(0, last - 15 * step) for step in range(max(1, pages))})
    found = {last: first}
    todo = [offset for offset in offsets if offset != last]
    if todo:
        with ThreadPoolExecutor(max_workers=min(4, len(todo))) as pool:
            fetched = pool.map(
                lambda offset: (offset, fetch(
                    f"{BASE}viewtopic.php?t={topic_id}&start={offset}",
                    cookies, referer=BASE)),
                todo,
            )
            for offset, (status, html) in fetched:
                if status == 200:
                    found[offset] = html
    return 200, [(offset, found[offset]) for offset in offsets if offset in found]


def format_post(post: dict) -> str:
    """Two lines per post: the metadata ranking needs, then a peek at the text."""
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
    return "  ".join(bits) + "\n      " + " ".join(post["text"].split())[:240]


def search_rows(page: str) -> tuple[int | None, list[dict]]:
    """Every topic row on one search page, with the board's stated total."""
    return search_total(page), parse_topics(page, None)


def format_links(post: dict) -> list[str]:
    """The hrefs behind a post, one per line — what a report has to quote."""
    lines = []
    for link in post.get("links", []):
        mark = "  unsafe" if link.get("unsafe") else ""
        lines.append(f"      LINK {link.get('host') or '?'} {link.get('href')}{mark}")
    return lines


def post_id_from(token: str) -> str | None:
    """Accept ``123``, ``p=123``, or a permalink ending in ``#p123``."""
    match = re.search(r"[?&#]p=?(\d+)", token) or re.fullmatch(r"(?:p=)?(\d+)", token.strip())
    return match.group(1) if match else None


def topic_id_from(target: str) -> str | None:
    """Accept ``t=123``, ``viewtopic.php?t=123``, or a bare id."""
    match = re.search(r"[?&]t=(\d+)", target) or re.fullmatch(r"(?:t=)?(\d+)", target.strip())
    return match.group(1) if match else None


def fetch_post(post_id: str, cookies: dict[str, str]) -> dict | None:
    """One post by id: ``viewtopic.php?p=<id>`` loads the page that holds it."""
    status, html = fetch(f"{BASE}viewtopic.php?p={post_id}", cookies, referer=BASE)
    if status != 200:
        return None
    for post in parse_posts(html):
        if post["post_id"] == post_id:
            return post
    return None


def topic_digest(topic_id: str, cookies: dict[str, str], pages: int,
                 posts_n: int) -> dict:
    """Structured tail: the pages and their posts, ready for text or JSON."""
    status, tail = topic_tail(topic_id, cookies, pages)
    pages_out = [{"start": start, "posts": parse_posts(html, posts_n)}
                 for start, html in tail]
    # `posts` is the flat reading order; `pages` keeps the offsets. Both are
    # shipped because a caller that only wants the posts should not have to know
    # about pagination, and that guess is what sends it off to write its own client.
    flat = [dict(post, page_start=page["start"])
            for page in pages_out for post in page["posts"]]
    return {"status": status, "topic_id": topic_id, "pages": pages_out, "posts": flat}


def print_digest(digest: dict, label: str = "", links: bool = False) -> None:
    head = f"--- t={digest['topic_id']}"
    if label:
        head += f"  {label}"
    print(f"{head}  (status {digest['status']}, {len(digest['pages'])} page(s))")
    for page in digest["pages"]:
        print(f"  [start={page['start']}]")
        for post in page["posts"]:
            print(format_post(post))
            if links:
                for line in format_links(post):
                    print(line)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_search(args) -> int:
    cookies = open_session(args.cookies)
    code, page = request_page(search_url(args.query, args.sort), cookies)
    if code:
        return code
    total, rows = search_rows(page)
    shown = rows[:args.list] if args.list > 0 else rows
    opened = shown[:max(0, min(args.open, 6))]
    if not args.json:
        print(f"search: {args.query!r} -> {total if total is not None else '?'} matches; "
              f"{len(rows)} rows on this page, showing {len(shown)}")
        if total is not None and total > len(rows):
            print(f"  note: {total - len(rows)} more matches are on later result pages; "
                  f"narrow with the AppID or the exact English name")
        if len(rows) > len(shown):
            print(f"  note: {len(rows) - len(shown)} rows hidden by --list")
        for index, row in enumerate(shown, 1):
            print(f"  {index}. t={row['topic_id']}  [{row['forum']}]  {row['title']}")
        print(f"  opening {len(opened)} of {len(shown)} topics, {args.pages} page(s) each "
              f"= 1 search + {len(opened) * max(1, args.pages)} page requests")
    digests = []
    if opened:
        with ThreadPoolExecutor(max_workers=max(1, min(4, len(opened)))) as pool:
            digests = list(pool.map(
                lambda row: topic_digest(row["topic_id"], cookies, args.pages, args.posts),
                opened))
        if not args.json:
            for row, digest in zip(opened, digests):
                print()
                print_digest(digest, row["title"])
    elif not args.json:
        print("  next: pick a t=<id>, then: csrin_session.py topic <id>")
    if args.json:
        print(json.dumps({"query": args.query, "total": total,
                          "rows": shown, "opened": digests}, indent=2))
    return 4 if not rows else 0


def cmd_post(args) -> int:
    cookies = open_session(args.cookies)
    ids = [post_id_from(token) for token in args.ids]
    if not ids or any(pid is None for pid in ids):
        print("expected post ids: 123, p=123, or a ...#p123 permalink", file=sys.stderr)
        return 2
    with ThreadPoolExecutor(max_workers=max(1, min(4, len(ids)))) as pool:
        posts = list(pool.map(lambda pid: fetch_post(pid, cookies), ids))
    missing = [pid for pid, post in zip(ids, posts) if post is None]
    if args.json:
        print(json.dumps([post for post in posts if post], indent=2))
    else:
        for post in posts:
            if post is None:
                continue
            print(format_post(post))
            if args.links:
                for line in format_links(post):
                    print(line)
        for pid in missing:
            print(f"p{pid}: not found on the page it points to", file=sys.stderr)
    return 0 if any(posts) else 4


def cmd_topic(args) -> int:
    topic_id = topic_id_from(args.target)
    if not topic_id:
        print("expected a topic id: 123, t=123, or viewtopic.php?t=123", file=sys.stderr)
        return 2
    digests = [topic_digest(topic_id, open_session(args.cookies), args.pages, args.posts)]
    if args.json:
        print(json.dumps(digests[0], indent=2))
    else:
        print_digest(digests[0], links=args.links)
    return 0 if digests[0]["status"] == 200 else 2


def cmd_fetch(args) -> int:
    cookies = open_session(args.cookies)
    code, page = request_page(args.url, cookies)
    if code:
        return code
    if "Search found" in page or "Search these results" in page:
        if 'class="topictitle"' in page and 'name="p' not in page:
            rows = parse_topics(page, args.max_posts)
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                for row in rows:
                    print(f"t={row['topic_id']}  [{row['forum']}]  {row['title']}")
            return 0 if rows else 4
        rows = parse_search(page, args.max_posts)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f"p{row['post_id']}  {row['posted']}  {row['author']}  "
                      f"[{row['forum']}]  {row['topic']}")
                print(f"      {row['excerpt'][:200]}")
        return 0 if rows else 4
    posts = parse_posts(page, args.max_posts)
    if args.json:
        print(json.dumps(posts, indent=2))
    elif args.text:
        for post in posts:
            print(post["text"])
    else:
        for post in posts:
            print(format_post(post))
            if args.links:
                for line in format_links(post):
                    print(line)
    return 0 if posts else 4


def cmd_login(args) -> int:
    cookies = parse_cookie_header(args.cookies) if args.cookies else load_saved_session()
    user = args.user or os.environ.get("CSRIN_USER")
    password = args.password or os.environ.get("CSRIN_PASSWORD")
    if not user:
        user = input("cs.rin.ru username: ").strip()
    if not password:
        password = getpass.getpass("cs.rin.ru password: ")
    login(cookies, user, password)
    status, index = fetch(BASE, cookies)
    print(f"logged in as {user}: {is_logged_in(index)}")
    if is_logged_in(index) and args.save:
        print(f"session written to {save_session(cookies, user)}")
    return 0 if is_logged_in(index) else 3


def cmd_whoami(args) -> int:
    cookies = open_session(args.cookies)
    status, index = fetch(BASE, cookies)
    logged = is_logged_in(index)
    print(f"logged in: {logged}"
          + ("" if logged else " (guest: links are masked, f=22 is hidden)"))
    return 0 if logged else 1


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csrin_session.py",
        description="Talk to cs.rin.ru/forum: search topics, read a thread's tail, "
                    "log in, check the session.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_session_flags(target: argparse.ArgumentParser) -> None:
        target.add_argument("--cookies", metavar="HEADER",
                            help="cookie header, k=v; k=v (default: .state/session.json)")
        target.add_argument("--json", action="store_true", help="print JSON")
        target.add_argument("--verbose", action="store_true",
                            help="log every request to stderr: status, seconds, bytes")

    search = sub.add_parser("search", help="title search; lists every matching topic row")
    search.add_argument("query")
    search.add_argument("--list", type=int, default=0, metavar="N",
                        help="rows to print; 0 means all (default 0)")
    search.add_argument("--open", type=int, default=0, metavar="N",
                        help="also digest the first N rows, capped at 6 (default 0)")
    search.add_argument("--pages", type=int, default=3, metavar="N",
                        help="pages per opened topic (default 3)")
    search.add_argument("--posts", type=int, default=15, metavar="N",
                        help="posts per page in a digest (default 15)")
    search.add_argument("--sort", choices=("relevance", "time"), default=None,
                        help="'time' puts the newest topics first")
    add_session_flags(search)
    search.set_defaults(func=cmd_search)

    post = sub.add_parser("post", help="read one or more posts by id, in parallel")
    post.add_argument("ids", nargs="+", metavar="ID", help="123, p=123, or a ...#p123 link")
    post.add_argument("--links", action="store_true", help="print every link URL")
    add_session_flags(post)
    post.set_defaults(func=cmd_post)

    topic = sub.add_parser("topic", help="digest a thread's tail")
    topic.add_argument("target", help="123, t=123, or viewtopic.php?t=123")
    topic.add_argument("--pages", type=int, default=3, metavar="N",
                       help="pages of the tail to read (default 3)")
    topic.add_argument("--posts", type=int, default=15, metavar="N",
                       help="posts per page (default 15)")
    topic.add_argument("--links", action="store_true", help="print every link URL")
    add_session_flags(topic)
    topic.set_defaults(func=cmd_topic)

    fetch_cmd = sub.add_parser("fetch", help="parse one board URL you already know")
    fetch_cmd.add_argument("url")
    fetch_cmd.add_argument("--text", action="store_true", help="post text only")
    fetch_cmd.add_argument("--max-posts", type=int, default=None, metavar="N")
    fetch_cmd.add_argument("--links", action="store_true", help="print every link URL")
    add_session_flags(fetch_cmd)
    fetch_cmd.set_defaults(func=cmd_fetch)

    login_cmd = sub.add_parser("login", help="log in; --save keeps the session in .state/")
    login_cmd.add_argument("--user", help="account name (default: CSRIN_USER or a prompt)")
    login_cmd.add_argument("--password", help="password (default: CSRIN_PASSWORD or a prompt)")
    login_cmd.add_argument("--save", action="store_true",
                           help="write the phpBB cookies to .state/session.json (0600)")
    login_cmd.add_argument("--cookies", metavar="HEADER",
                           help="start from this cookie header instead of .state/")
    login_cmd.add_argument("--verbose", action="store_true",
                           help="log every request to stderr")
    login_cmd.set_defaults(func=cmd_login)

    whoami = sub.add_parser("whoami", help="is the current session logged in?")
    whoami.add_argument("--cookies", metavar="HEADER")
    whoami.add_argument("--verbose", action="store_true", help="log every request to stderr")
    whoami.set_defaults(func=cmd_whoami)
    return parser


def main(argv: list[str] | None = None) -> int:
    global VERBOSE
    args = build_parser().parse_args(argv)
    VERBOSE = getattr(args, "verbose", False)
    if getattr(args, "json", False) is None:
        args.json = False
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
