"""
Minimal stateless single-user state server for 文盲英语 MVP.

Endpoints:
  GET  /api/state            -> 200 JSON (returns {} if no state yet)
  PUT  /api/state            -> body is JSON, replaces state atomically, 200 OK
  GET  /api/health           -> 200 'ok'

Listens on 127.0.0.1:8000 by default.
State file: ./data/state.json (path overridable via env STATE_FILE).
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile

STATE_FILE = Path(os.environ.get("STATE_FILE", "./data/state.json"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
MAX_BODY = 1024 * 1024  # 1 MB


def ensure_state_dir():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def read_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception as e:
        print(f"[warn] failed to read state: {e}", file=sys.stderr)
        return {}


def atomic_write_state(data: dict):
    ensure_state_dir()
    fd, tmp_path = tempfile.mkstemp(dir=str(STATE_FILE.parent), prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/state":
            self._send_json(200, read_state())
        elif self.path == "/api/health":
            self._send_text(200, "ok")
        else:
            self._send_text(404, "not found")

    def do_PUT(self):
        if self.path != "/api/state":
            self._send_text(404, "not found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            self._send_text(400, "bad length")
            return
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("state must be a JSON object")
        except Exception as e:
            self._send_text(400, f"bad json: {e}")
            return
        try:
            atomic_write_state(data)
        except Exception as e:
            self._send_text(500, f"write failed: {e}")
            return
        self._send_json(200, {"ok": True})

    def log_message(self, format, *args):
        # Concise log line
        sys.stderr.write(f"{self.address_string()} {format % args}\n")


def main():
    ensure_state_dir()
    print(f"state file: {STATE_FILE}")
    print(f"listening on {HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
