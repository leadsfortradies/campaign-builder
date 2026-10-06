"""
Local review server for the web app (replaces the Netlify Forms + Netlify
MCP round-trip - see PROCESS.md "Review happens in the web app").

Serves web/ as static files and handles POST /approve by writing the
approval straight to web/approvals/<project_id>__<step>__<timestamp>.json.
Claude reads that directory directly - no deploy, no MCP form lookup.

Usage:
    venv/bin/python scripts/local_server.py [--port 8787]
"""

import argparse
import json
import os
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

WEB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
APPROVALS_DIR = os.path.join(WEB_ROOT, "approvals")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_ROOT, **kwargs)

    def end_headers(self):
        # This server is for active local development - stale browser-cached
        # JS/JSON after an edit is confusing, so disable caching entirely.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_POST(self):
        if self.path != "/approve":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return

        os.makedirs(APPROVALS_DIR, exist_ok=True)
        fname = f"{payload.get('project_id', 'unknown')}__{payload.get('step', 'unknown')}__{int(time.time())}.json"
        with open(os.path.join(APPROVALS_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        print(f"Approval written: web/approvals/{fname} "
              f"({payload.get('total_kept')} kept, {payload.get('total_excluded')} excluded)")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, fmt, *args):
        if "/approve" not in (self.path or ""):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description="Local review server")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("localhost", args.port), Handler)
    print(f"Serving {WEB_ROOT} at http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
