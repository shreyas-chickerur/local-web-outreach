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
from app.store import db, leads
from app.web.serialize import brief_to_dict
from app.workbench.brief import build_brief

_UI = Path(__file__).parent / "index.html"

# Looking a company up hits three directories and their website. Doing that
# twice for the same query while the first is still running wastes the quota.
_lock = threading.Lock()


def lookup(query: str, location: str | None, notes: str | None) -> dict:
    """Run a brief, store it, and return it with anything you have confirmed
    already applied on top. Never raises."""
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

    payload = brief_to_dict(brief)
    # Researching the same business twice must not discard what you were told
    # the first time, so the stored lead is refreshed and read back with your
    # confirmations applied over the fresh directory data.
    with db.session() as conn:
        lead_id = leads.save_brief(conn, payload)
        return leads.brief_with_overrides(conn, lead_id)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(status, json.dumps(payload).encode(),
                   "application/json; charset=utf-8")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            parsed = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def do_POST(self) -> None:  # noqa: N802  (stdlib naming)
        route = urlparse(self.path).path
        body = self._body()
        try:
            lead_id = int(body.get("lead_id") or 0)
        except (TypeError, ValueError):
            lead_id = 0
        if not lead_id:
            self._json({"error": "lead_id is required"}, 400)
            return
        try:
            with db.session() as conn:
                if route == "/api/verify":
                    leads.verify(conn, lead_id,
                                 str(body.get("field", "")),
                                 str(body.get("value", "")),
                                 note=(body.get("note") or None))
                elif route == "/api/status":
                    leads.set_status(conn, lead_id, str(body.get("status", "")),
                                     note=(body.get("note") or None))
                elif route == "/api/note":
                    text = str(body.get("note", "")).strip()
                    if not text:
                        self._json({"error": "an empty note records nothing"}, 400)
                        return
                    leads.record(conn, lead_id, "note", note=text)
                else:
                    self._json({"error": "not found"}, 404)
                    return
                self._json(leads.brief_with_overrides(conn, lead_id))
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)

    def do_GET(self) -> None:  # noqa: N802  (stdlib naming)
        route = urlparse(self.path)
        if route.path in ("/", "/index.html"):
            self._send(200, _UI.read_bytes(), "text/html; charset=utf-8")
            return
        if route.path == "/api/leads":
            with db.session() as conn:
                self._json({"leads": leads.all_leads(conn),
                            "operator": db.operator()})
            return
        if route.path == "/api/lead":
            try:
                lead_id = int((parse_qs(route.query).get("id") or ["0"])[0])
                with db.session() as conn:
                    self._json(leads.brief_with_overrides(conn, lead_id))
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
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
