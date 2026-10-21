#!/usr/bin/env python3
"""Serve a design draft and record what the reviewer selects.

Why a server and not a bare static directory: the draft kit posts a review
snapshot (selection, moved sliders, state flags) to `POST /__select`, and the
agent reads `selection.json` from the draft directory. A selection that only
exists inside one browser tab cannot be acted on.

Usage:
    python3 draft_server.py <draft-dir> <port> [--host HOST]

Port 0 picks a free port and prints it. HOST defaults to 127.0.0.1; pass
--host 0.0.0.0 only when the browser runs on another host or container, because
that exposes the directory listing and the write endpoint to the network.
Stdlib only.

Endpoints
    GET  /__selection   the last snapshot, or 404 when nothing was recorded
    POST /__select      JSON object body -> selection.json, plus a server "ts"
    everything else     static files from <draft-dir>, never cached
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 1 << 20  # a snapshot is a few KB; anything larger is not one


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("draft_dir", help="directory holding the draft HTML")
    ap.add_argument("port", type=int, help="port to listen on; 0 picks a free one")
    ap.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    args = ap.parse_args()

    root = os.path.abspath(args.draft_dir)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    selection = os.path.join(root, "selection.json")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=root, **kw)

        def log_message(self, format, *a):  # requests are noise; errors still reach stderr via send_error
            return

        def end_headers(self):
            # The kit reloads when a file changes; a cached stylesheet would
            # make that reload show the old design.
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.split("?")[0] != "/__selection":
                return super().do_GET()
            try:
                with open(selection, encoding="utf-8") as fh:
                    return self._json(json.load(fh))
            except FileNotFoundError:
                return self._json({"error": "no selection recorded yet"}, 404)
            except json.JSONDecodeError as err:
                return self._json({"error": f"selection.json unreadable: {err}"}, 500)

        def do_POST(self):
            # Unknown paths fail loudly: a 200 here would tell the kit a
            # selection was recorded when it was not.
            if self.path.split("?")[0] != "/__select":
                return self._json({"error": f"unknown endpoint {self.path}"}, 404)
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json({"error": "body too large"}, 413)
            try:
                data = json.loads(self.rfile.read(length) or b"null")
            except json.JSONDecodeError as err:
                return self._json({"error": f"invalid JSON: {err}"}, 400)
            if not isinstance(data, dict):
                return self._json({"error": "body must be a JSON object"}, 400)
            data["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            # Atomic replace with a per-request temp file: the agent must never
            # read a half-written file, and two posts must not share one temp.
            fd, tmp = tempfile.mkstemp(prefix=".selection.", suffix=".tmp", dir=root)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, selection)
            self._json({"ok": True, "ts": data["ts"]})

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    host, port = server.server_address[:2]
    print(f"draft server: {root}")
    print(f"listening:    http://{host}:{port}/")
    print(f"selections:   {selection}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
