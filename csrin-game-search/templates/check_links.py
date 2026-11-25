#!/usr/bin/env python3
"""Check whether resource links still resolve, one verdict per link.

File hosts rot: a link that worked when the post was written is often gone by
the time someone reads the thread. This checker answers one question per URL —
alive, dead, blocked or unverified — without downloading anything.

    python check_links.py URL [URL ...]
    python check_links.py --json URL [URL ...]
    python check_links.py --per-host 1 URL [URL ...]

Verdicts:

* ``ALIVE``      the host says the file exists;
* ``DEAD``       the host says it is gone;
* ``BLOCKED``    the host answered 401/403/451 — one browser attempt, then the
                 link belongs to the user, who has a real browser;
* ``UNVERIFIED`` cannot tell: a JavaScript-only page, a 429, a transport error.

``UNVERIFIED`` is a handoff, not a verdict: hand the URL to a browser and let the
rendered page answer before calling a link unknowable. Never label a link dead
because a bot check refused you.

Three host behaviours make a naive HTTP status useless:

* a public JSON API that states liveness (``pixeldrain``-style) — ask the API;
* a page that answers 200 for a missing file and says so in the body
  (``1fichier``, ``mediafire``-style) — read the body for the marker;
* an API that refuses anonymous callers or a page rendered only by JavaScript
  (``gofile``, ``mega``-style) — there is no honest verdict, so say unverified.

Links are checked in parallel with a short timeout, because this is the last step
of a task and must not become the slowest. A per-host cap keeps a twelve-part
upload from arriving as twelve simultaneous requests at one host.

Exit status: 0 when at least one link is alive, 1 when none is, 2 on bad usage.
Standard library only. It fetches nothing but the URLs it is given.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# ADAPT: an ordinary desktop user agent. Some hosts serve a challenge page to
# anything that looks like a script, which would read as "dead" if not for the
# BLOCKED/UNVERIFIED split below.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 8.0
DEFAULT_WORKERS = 6
DEFAULT_PER_HOST = 2
BODY_LIMIT = 200_000

# Markers that mean the file is gone even though the page answered 200.
DEAD_MARKERS = {
    "1fichier.com": ("file not found", "file has been removed", "file has been deleted"),
    "mediafire.com": ("file removed", "invalid or deleted file", "no longer available"),
    "drive.google.com": ("sorry, you can't view or download this file", "file not found"),
    "filecrypt.cc": ("container is not available", "does not exist", "no files found"),
    "pearcrypt.lol": ("container is not available", "does not exist", "not found"),
}
# An outright refusal: one browser attempt is allowed, then it is the user's.
BLOCKED_STATUS = {401, 403, 451}
# Rate limits and odd gates: cannot tell, never "dead".
UNVERIFIED_STATUS = {405, 429, 503}
DEAD_STATUS = {404, 410}


def fetch(url: str, timeout: float) -> tuple[int, str]:
    """GET one URL. Status is returned, not raised, so a 403 is data."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(BODY_LIMIT).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(BODY_LIMIT).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, f"transport: {exc}"


def check_pixeldrain(parts: urllib.parse.SplitResult, timeout: float) -> tuple[str, str] | None:
    """Album and file pages expose a JSON API that states liveness."""
    path = parts.path.strip("/")
    if path.startswith("l/"):
        status, _ = fetch(f"https://pixeldrain.com/api/list/{path[2:]}", timeout)
    elif path.startswith("u/"):
        status, _ = fetch(f"https://pixeldrain.com/api/file/{path[2:]}/info", timeout)
    else:
        return None
    if status == 200:
        return "ALIVE", "api 200"
    if status == 404:
        return "DEAD", "api 404 not_found"
    if status in BLOCKED_STATUS:
        return "BLOCKED", f"api {status}"
    return "UNVERIFIED", f"api {status or 'transport error'}"


def check(url: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """One verdict and its evidence for one URL."""
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()

    if "pixeldrain.com" in host:
        result = check_pixeldrain(parts, timeout)
        if result:
            return result

    if "gofile.io" in host:
        # The content API answers 401 to anonymous callers and needs a guest or
        # premium token; the page renders in JavaScript. HTTP cannot tell alive
        # from dead here, so hand it to a browser rather than guessing.
        return "UNVERIFIED", "JS-only page and token-gated API; open it in a browser"

    if "mega.nz" in host or "mega.co.nz" in host:
        return "UNVERIFIED", "encrypted API; needs the client or a browser"

    status, body = fetch(url, timeout)
    lowered = body.lower()
    for marker in DEAD_MARKERS.get(host, ()):
        if marker in lowered:
            return "DEAD", f"page says {marker!r}"
    if status in DEAD_STATUS:
        return "DEAD", f"http {status}"
    if status in BLOCKED_STATUS:
        return "BLOCKED", f"http {status}; one browser attempt, then hand it to the user"
    if status in UNVERIFIED_STATUS or status == 0:
        return "UNVERIFIED", f"http {status or 'transport error'}"
    if status == 200:
        return "ALIVE", "http 200, no dead marker"
    return "UNVERIFIED", f"http {status}"


def check_all(urls: list[str], timeout: float, workers: int,
              per_host: int) -> list[tuple[str, str, str, str]]:
    """Check every URL, at most ``per_host`` at a time against one host.

    The per-host cap is what keeps a split upload from becoming a burst: twelve
    parts of one file land on the same host and a parallel fan-out there is how a
    working link turns into a 429.
    """
    hosts = {(urllib.parse.urlsplit(url).hostname or "?").lower() for url in urls}
    gates = {host: threading.Semaphore(per_host) for host in hosts}

    def run(url: str) -> tuple[str, str, str, str]:
        host = (urllib.parse.urlsplit(url).hostname or "?").lower()
        with gates[host]:
            verdict, note = check(url, timeout)
        return verdict, host, url, note

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(urls)))) as pool:
        return list(pool.map(run, urls))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_links.py",
        description="Check whether download links still resolve. Never downloads.",
    )
    parser.add_argument("urls", nargs="+", metavar="URL")
    parser.add_argument("--json", action="store_true", help="print records as JSON")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="S",
                        help=f"per-request timeout in seconds (default {DEFAULT_TIMEOUT:g})")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, metavar="N",
                        help=f"checks in flight overall (default {DEFAULT_WORKERS})")
    parser.add_argument("--per-host", type=int, default=DEFAULT_PER_HOST, metavar="N",
                        help=f"checks in flight per host (default {DEFAULT_PER_HOST})")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    urls = list(dict.fromkeys(args.urls))  # same link twice is the same question
    results = check_all(urls, args.timeout, args.workers, args.per_host)
    if args.json:
        print(json.dumps([
            {"verdict": verdict, "host": host, "url": url, "evidence": note}
            for verdict, host, url, note in results
        ], indent=2))
    else:
        for verdict, host, url, note in results:
            print(f"{verdict}\t{host}\t{url}\t{note}")
    return 0 if any(verdict == "ALIVE" for verdict, *_ in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
