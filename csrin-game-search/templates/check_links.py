#!/usr/bin/env python3
"""Check whether resource links still resolve, one verdict per link.

File hosts rot: a link that worked when the post was written is often gone by
the time someone reads the thread. This checker answers one question per URL --
alive, dead, or unverified -- without downloading anything.

    python check_links.py URL [URL ...]

Output: ``<VERDICT>\t<host>\t<url>\t<evidence>``; exit status is always 0,
because a verdict is the result, not a failure.

This is the cheap first pass. ``UNVERIFIED`` is a handoff, not a verdict: hand
the URL to a browser and let the rendered page answer before you call a link
unknowable.

Three host behaviours make a naive HTTP status useless:

* a public JSON API that states liveness (``pixeldrain``-style) -- ask the API;
* a page that answers 200 for a missing file and says so in the body
  (``1fichier``, ``mediafire``-style) -- read the body for the marker;
* an API that refuses anonymous callers or a page rendered only by JavaScript
  (``gofile``, ``mega``-style) -- there is no honest verdict, so say unverified
  rather than guess.

Standard library only. It fetches nothing but the URLs it is given.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# ADAPT: an ordinary desktop user agent; some hosts serve a challenge page to
# anything that looks like a script, which would read as "dead" if not for the
# unverified rule below.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 20
BODY_LIMIT = 200_000

# Markers that mean the file is gone even though the page answered 200.
DEAD_MARKERS = {
    "1fichier.com": ("file not found", "file has been removed", "file has been deleted"),
    "mediafire.com": ("file removed", "invalid or deleted file", "no longer available"),
    "drive.google.com": ("sorry, you can't view or download this file", "file not found"),
    "filecrypt.cc": ("container is not available", "does not exist", "no files found"),
    "pearcrypt.lol": ("container is not available", "does not exist", "not found"),
}
# 403/429/503 and challenge pages mean "cannot tell", never "dead".
UNVERIFIED_STATUS = {401, 403, 405, 429, 451, 503}
DEAD_STATUS = {404, 410}


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(BODY_LIMIT).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(BODY_LIMIT).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, f"transport: {exc}"


def check_pixeldrain(parts: urllib.parse.SplitResult) -> tuple[str, str] | None:
    """Album and file pages expose a JSON API that states liveness."""
    path = parts.path.strip("/")
    if path.startswith("l/"):
        status, body = fetch(f"https://pixeldrain.com/api/list/{path[2:]}")
    elif path.startswith("u/"):
        status, body = fetch(f"https://pixeldrain.com/api/file/{path[2:]}/info")
    else:
        return None
    if status == 200:
        return "ALIVE", "api 200"
    if status == 404:
        return "DEAD", "api 404 not_found"
    return "UNVERIFIED", f"api {status}"


def check(url: str) -> tuple[str, str]:
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()

    if "pixeldrain.com" in host:
        result = check_pixeldrain(parts)
        if result:
            return result

    if "gofile.io" in host:
        # The content API answers 401 to anonymous callers and needs a guest or
        # premium token; the page renders in JavaScript. HTTP cannot tell alive
        # from dead here, so hand it to a browser rather than guessing.
        return "UNVERIFIED", "JS-only page and token-gated API; open it in a browser"

    if "mega.nz" in host or "mega.co.nz" in host:
        return "UNVERIFIED", "encrypted API; needs the client or a browser"

    status, body = fetch(url)
    lowered = body.lower()
    for marker in DEAD_MARKERS.get(host, ()):
        if marker in lowered:
            return "DEAD", f"page says {marker!r}"
    if status in DEAD_STATUS:
        return "DEAD", f"http {status}"
    if status in UNVERIFIED_STATUS or status == 0:
        return "UNVERIFIED", f"http {status or 'transport error'}"
    if status == 200:
        return "ALIVE", "http 200, no dead marker"
    return "UNVERIFIED", f"http {status}"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    for url in argv:
        verdict, note = check(url)
        host = urllib.parse.urlsplit(url).hostname or "?"
        print(f"{verdict}\t{host}\t{url}\t{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
