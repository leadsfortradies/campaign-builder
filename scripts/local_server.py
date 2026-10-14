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
import sys
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
        if self.path == "/api/chat":
            self._chat()
            return
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

    def _chat(self):
        """Chat box: needs ANTHROPIC_API_KEY in the environment."""
        def reply(code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            path = os.path.join(WEB_ROOT, "data", os.path.basename(body["project_id"]),
                                os.path.basename(body["step"]) + ".json")
            with open(path, encoding="utf-8") as f:
                rows = json.load(f).get("rows") or []
            sys.path.insert(0, os.path.dirname(WEB_ROOT))
            from server import chat
            model = os.environ.get("CHAT_MODEL", "claude-sonnet-5-5")
            reply(200, chat.suggest(rows, body["message"], body.get("excluded") or [], model))
        except Exception as exc:  # noqa: BLE001 - shown to the user in the chat box
            reply(502, {"detail": str(exc)})

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
