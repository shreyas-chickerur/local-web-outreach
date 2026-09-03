"""The workbench UI — a local, single-user server on the standard library.

Deliberately not a framework. This serves one page and one endpoint, and the
endpoint calls exactly the same build_brief() the CLI does, so what you see in
the browser cannot drift from what the terminal prints.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.cli import available_directories
from app.web.serialize import brief_to_dict
from app.workbench.brief import build_brief

_UI = Path(__file__).parent / "index.html"

# Looking a company up hits three directories and their website. Doing that
# twice for the same query while the first is still running wastes the quota.
_lock = threading.Lock()


def lookup(query: str, location: str | None, notes: str | None) -> dict:
    """Run a brief, or explain why it could not run. Never raises."""
    if not query.strip():
        return {"error": "Give a company name or a website URL."}
    try:
        with _lock:
            brief = build_brief(query, location=location or None,
                                notes=notes or None,
                                directories=available_directories())
    except ValueError as exc:          # a bad input is the operator's typo
        return {"error": str(exc)}
    except Exception as exc:           # a source being down must not blank the UI
        return {"error": f"Lookup failed: {type(exc).__name__}: {exc}"}
    return brief_to_dict(brief)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802  (stdlib naming)
        route = urlparse(self.path)
        if route.path in ("/", "/index.html"):
            self._send(200, _UI.read_bytes(), "text/html; charset=utf-8")
            return
        if route.path == "/api/brief":
            params = parse_qs(route.query)
            payload = lookup(
                (params.get("q") or [""])[0],
                (params.get("location") or [""])[0],
                (params.get("notes") or [""])[0],
            )
            body = json.dumps(payload).encode()
            self._send(200 if "error" not in payload else 400, body,
                       "application/json; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:   # quieter console
        return


def serve(port: int = 8099) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"workbench UI on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
