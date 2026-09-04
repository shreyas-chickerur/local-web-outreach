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

from app.adapters.gplaces import PlacesError, search
from app.adapters.photos import fetch as fetch_photo
from app.cli import available_directories
from app.core.config import google_places_api_key
from app.site.pipeline import iterate as run_iteration
from app.site.render import build as build_site
from app.store import db, leads, photos, sites
from app.web.serialize import brief_to_dict
from app.workbench.brief import build_brief
from app.workbench.categories import BY_KEY, CATEGORIES
from app.workbench.discover import find_all

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


def locate(query: str) -> dict:
    """Turn a typed place name into a point, so the list works without
    granting location access."""
    key = google_places_api_key()
    if not key:
        return {"error": "GOOGLE_PLACES_API_KEY is not set."}
    try:
        results = search(key, query, limit=1)
    except PlacesError as exc:
        return {"error": str(exc)}
    if not results:
        return {"error": f"Could not find {query!r}."}
    point = (results[0].get("location") or {})
    if not point:
        return {"error": f"Could not place {query!r} on a map."}
    return {"latitude": point["latitude"], "longitude": point["longitude"],
            "label": (results[0].get("formattedAddress")
                      or (results[0].get("displayName") or {}).get("text", query))}


def prospects(latitude: float, longitude: float, refresh: bool = False,
              category: str | None = None) -> dict:
    """Prospects near a point, best first. Never raises.

    One category at a time by default: eight categories cold is ninety-odd site
    fetches and half a minute, and a page that arrives in pieces beats a page
    that arrives at once, late. The lookup lock is deliberately not held here —
    the whole point is that these run at the same time.
    """
    key = google_places_api_key()
    if not key:
        return {"error": "GOOGLE_PLACES_API_KEY is not set, so there is nothing "
                         "to search with."}
    wanted = ([BY_KEY[category]] if category in BY_KEY else None)
    if category and wanted is None:
        return {"error": f"unknown category {category!r}"}
    try:
        with db.session() as conn:
            groups = find_all(conn, key, latitude, longitude, refresh=refresh,
                              categories=wanted or CATEGORIES)
    except Exception as exc:
        return {"error": f"Search failed: {type(exc).__name__}: {exc}"}
    return {"groups": groups}


def generate(lead_id: int, spec_text: str) -> dict:
    """Build a site for a saved lead and keep it as a new version."""
    with db.session() as conn:
        brief = leads.brief_with_overrides(conn, lead_id)
        html, spec = build_site(brief, spec_text)
        notes = {"mood": spec.mood, "understood": spec.understood,
                 "unmet": spec.unmet, "ignored": spec.ignored,
                 "lead_with": spec.lead_with}
        version = sites.save(conn, lead_id, html, spec_text, notes)
        payload = leads.brief_with_overrides(conn, lead_id)
        payload["site"] = {"version": version, "notes": notes,
                           "url": f"/site/{lead_id}/{version}"}
        payload["site_versions"] = sites.versions(conn, lead_id)
        return payload


def workspace(lead_id: int) -> dict:
    """Everything the iteration screen needs, in one round trip."""
    with db.session() as conn:
        return {
            "lead_id": lead_id,
            "versions": sites.versions(conn, lead_id),
            "events": leads.events(conn, lead_id),
        }


def iteration(lead_id: int, sentence: str, parent: object) -> dict:
    """Run one chat instruction and return the result plus the refreshed panes.

    A rejection is a result, not an error: the operator has to see which words
    tripped the content gate, and an exception would tell them only that
    something went wrong.
    """
    if not sentence.strip():
        return {"error": "Type an instruction first."}
    parent_version: int | None = None
    if isinstance(parent, (int, str)) and str(parent).strip():
        try:
            parent_version = int(parent)
        except ValueError:
            parent_version = None
    with db.session() as conn:
        try:
            result = run_iteration(conn, lead_id, sentence,
                                   parent_version=parent_version)
        except ValueError as exc:
            return {"error": str(exc)}
        payload = result.as_dict()
        payload["lead_id"] = lead_id
        payload["versions"] = sites.versions(conn, lead_id)
        payload["events"] = leads.events(conn, lead_id)
        return payload


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
                elif route == "/api/generate":
                    self._json(generate(lead_id, str(body.get("spec", ""))))
                    return
                elif route == "/api/iterate":
                    self._json(iteration(
                        lead_id, str(body.get("sentence", "")),
                        body.get("parent_version")))
                    return
                elif route == "/api/label":
                    with db.session() as conn:
                        photos.label(conn, lead_id, str(body.get("url", "")),
                                     str(body.get("label", "")))
                        self._json({"labels": photos.labels_for(conn, lead_id)})
                    return
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
        # A generated site is served as a real page so it can be opened, shown
        # on a phone, or sent to the owner — not just previewed in a frame.
        # Generated pages reference photos through here, so the API key that
        # fetches them is never written into a page we hand to anyone.
        if route.path.startswith("/photo/"):
            bits = route.path.strip("/").split("/")
            try:
                lead_id, index = int(bits[1]), int(bits[2])
            except (IndexError, ValueError):
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            with db.session() as conn:
                try:
                    brief = leads.load_brief(conn, lead_id)
                except ValueError:
                    self._send(404, b"no such lead", "text/plain; charset=utf-8")
                    return
            names = brief.get("place_photos") or []
            if not (0 <= index < len(names)):
                self._send(404, b"no such photo", "text/plain; charset=utf-8")
                return
            image = fetch_photo(google_places_api_key() or "", names[index])
            if image is None:
                self._send(404, b"photo unavailable", "text/plain; charset=utf-8")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(image)))
            self.send_header("Cache-Control", "public, max-age=604800")
            self.end_headers()
            self.wfile.write(image)
            return
        if route.path.startswith("/site/"):
            bits = route.path.strip("/").split("/")
            try:
                lead_id = int(bits[1])
                version = int(bits[2]) if len(bits) > 2 else None
            except (IndexError, ValueError):
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            with db.session() as conn:
                page = sites.html_for(conn, lead_id, version)
            if page is None:
                self._send(404, b"no site generated for this lead yet",
                           "text/plain; charset=utf-8")
                return
            self._send(200, page.encode(), "text/html; charset=utf-8")
            return
        # The photographs worth labelling: everything we might place, with
        # whatever a person has already said about each.
        if route.path == "/api/photos":
            try:
                lead_id = int((parse_qs(route.query).get("id") or ["0"])[0])
            except ValueError:
                lead_id = 0
            with db.session() as conn:
                try:
                    brief = leads.brief_with_overrides(conn, lead_id)
                except ValueError:
                    self._json({"error": "no such lead"}, 400)
                    return
                known = photos.labels_for(conn, lead_id)
            urls = [f"/photo/{lead_id}/{i}"
                    for i in range(len(brief.get("place_photos") or []))]
            urls += list((brief.get("published") or {}).get("photos") or [])
            self._json({"lead_id": lead_id, "labels": known,
                        "options": list(photos.LABELS),
                        "photos": [{"url": u, "label": known.get(u)}
                                   for u in urls[:24]]})
            return
        if route.path == "/api/workspace":
            try:
                lead_id = int((parse_qs(route.query).get("id") or ["0"])[0])
            except ValueError:
                lead_id = 0
            self._json(workspace(lead_id))
            return
        if route.path == "/api/sites":
            try:
                lead_id = int((parse_qs(route.query).get("id") or ["0"])[0])
            except ValueError:
                lead_id = 0
            with db.session() as conn:
                self._json({"versions": sites.versions(conn, lead_id)})
            return
        if route.path == "/api/where":
            self._json(locate((parse_qs(route.query).get("q") or [""])[0]))
            return
        if route.path == "/api/prospects":
            params = parse_qs(route.query)
            try:
                lat = float((params.get("lat") or [""])[0])
                lng = float((params.get("lng") or [""])[0])
            except ValueError:
                self._json({"error": "a latitude and longitude are required"}, 400)
                return
            payload = prospects(
                lat, lng,
                refresh=(params.get("refresh") or [""])[0] == "1",
                category=(params.get("category") or [""])[0] or None)
            self._json(payload, 200 if "error" not in payload else 400)
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
