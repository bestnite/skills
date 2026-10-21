#!/usr/bin/env python3
"""TEMPLATE — copy this file next to your work, adapt the EDIT lines, then run it.

It signs one mtop call for Goofish/Xianyu and prints the exact material for an
in-page `fetch()`: the URL to call and the form body to pass. This is a starting
point, not an interface: read it, change what your environment needs, run it.
Nothing here needs third-party packages.

**The send happens in the browser, not here.** A host HTTP client reaches the
endpoint and looks fine for roughly a dozen calls, then the server answers
`FAIL_SYS_USER_VALIDATE` / `RGV587_ERROR` — risk control, which reads like a dead
session. Issued as a `fetch()` from a page already open on www.goofish.com, the
same signed call does not trip it. Signing is host-side arithmetic; sending is
the browser's job. There is deliberately no `SEND` switch.

Three things are environment-specific, marked with `# EDIT`:

  1. COOKIES — where the user's session is. A raw "k=v; k=v" string, or a path to
     a file holding one (raw, a JSON list from DevTools/Cookie-Editor, a flat
     dict, or a browser storage export such as <skill dir>/.state/storage-state.json
     — see references/session-persistence.md). Prefer asking your browser tool for
     the jar scoped to the API host (there can be two `_m_h5_tk` values; only one
     signs correctly — see below).
  2. API / DATA — which endpoint and payload. See references/mtop-apis.md.
  3. FETCH — how your browser tool takes a snippet. It prints a ready-to-run
     `fetch()` call; which tool call wraps it differs per environment.

Two functions at the bottom are the whole algorithm; keep them if you rewrite
the rest:
    h5_token(jar)                 -> the part of _m_h5_tk before the first "_"
    sign(token, t_ms, data)       -> md5(token & t & appKey & data)

Usage after adapting:  python3 mtop_request.py
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

# ---------------------------------------------------------------- EDIT 1: cookies
COOKIES = ""            # raw string, or a path to a file holding one (for a saved
                        # session: <skill dir>/.state/storage-state.json)
# A jar can carry TWO `_m_h5_tk` values that both go to h5api.m.goofish.com (set
# on .goofish.com and on .taobao.com). Only one is the live signing token; the
# other answers FAIL_SYS_ILLEGAL_ACCESS. If that comes back, re-run with the other
# token before suspecting the session.

# ------------------------------------------------------------- EDIT 2: the call
API = "mtop.taobao.idle.pc.detail"
DATA: dict | str = {"itemId": "1059363804910"}
VERSION = "1.0"
SPM = "a21ybx.item.0.0"        # page token; see references/mtop-apis.md
APP_KEY = "34839810"           # Xianyu web appKey — a protocol constant
MTOP_HOST = "https://h5api.m.goofish.com"

# ------------------------------------------------------------- EDIT 3: the fetch
# The snippet below is printed for you to run inside the page. Nothing to fill in
# unless your browser tool needs a different shape (some take a function to
# evaluate, some take `url` + `body` separately):
FETCH_SNIPPET = """async (url, body) => {
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  return await res.json();
}"""


# ------------------------------------------------------------------- the maths
def h5_token(jar: dict[str, str]) -> str:
    """Everything before the first '_' in _m_h5_tk (the cookie is <token>_<ts>).

    The server rotates it on most responses: re-read it from the live jar every
    call rather than caching it anywhere.
    """
    return (jar.get("_m_h5_tk") or "").split("_")[0]


def sign(token: str, t_ms: str, data: str, app_key: str = APP_KEY) -> str:
    """md5(token & t & appKey & data) — the entire signing algorithm."""
    return hashlib.md5(f"{token}&{t_ms}&{app_key}&{data}".encode()).hexdigest()


# ------------------------------------------------------------------ plumbing
def load_cookies(source: str) -> dict[str, str]:
    """Raw string, or a file holding a raw string / JSON list / flat JSON dict /
    storage export ({"cookies": [...], "origins": [...]})."""
    text = source.strip()
    p = Path(text).expanduser()
    if text and "\n" not in text and "=" not in text and p.is_file():
        text = p.read_text(encoding="utf-8").strip()
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("cookies"), list):
            data = data["cookies"]
        if isinstance(data, list):
            return {c["name"]: c["value"] for c in data
                    if isinstance(c, dict) and "name" in c and "value" in c}
        return {str(k): str(v) for k, v in data.items()}
    jar: dict[str, str] = {}
    for part in re.split(r"[;\n]", text):
        if "=" in part:
            k, v = part.split("=", 1)
            jar[k.strip()] = v.strip()
    return jar


def build(jar: dict[str, str], api: str, data, version: str, spm: str) -> dict:
    """The signed request: URL, query params, and the form body for the page."""
    from urllib.parse import urlencode
    payload = (data if isinstance(data, str)
               else json.dumps(data, separators=(",", ":"), ensure_ascii=False))
    token = h5_token(jar)
    t_ms = str(int(time.time() * 1000))
    query = {
        "jsv": "2.7.2", "appKey": APP_KEY, "t": t_ms,
        "sign": sign(token, t_ms, payload),
        "v": version, "type": "originaljson", "accountSite": "xianyu",
        "dataType": "json", "timeout": "20000", "api": api,
        "sessionOption": "AutoLoginOnly", "spm_cnt": spm,
    }
    return {
        "url": f"{MTOP_HOST}/h5/{api}/{version}/?{urlencode(query)}",
        "body": "data=" + urlencode({"data": payload})[5:],
        "t": t_ms, "token": token,
    }


if __name__ == "__main__":
    jar = load_cookies(COOKIES)
    if not h5_token(jar):
        print("! _m_h5_tk missing — this request will be treated as signed-out.")
    req = build(jar, API, DATA, VERSION, SPM)
    print(json.dumps({"url": req["url"], "body": req["body"]}, ensure_ascii=False, indent=2))
    print("\n--- run this in a page you already have open on www.goofish.com ---")
    print(FETCH_SNIPPET)
    print(f"// ...called with (url, body) above")
    print("\n# If ret says the token expired, the response carried a fresh _m_h5_tk:")
    print("# update the jar and retry ONCE. If it says ILLEGAL_ACCESS, re-sign with")
    print("# the other _m_h5_tk from the jar. Do not loop.")
