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

from app.adapters import logos
from app.adapters import photos as photos_api
from app.adapters.gplaces import PlacesError, search
from app.adapters.photos import fetch as fetch_photo
from app.cli import available_directories
from app.core.config import DEFAULT_PORT, google_places_api_key
from app.design import bridge
from app.review import run as review_run
from app.site.census import measure as measure_census
from app.site.pipeline import (
    STAGE_SAYS as STAGES_SAY,
)
from app.site.pipeline import (
    STAGES,
    BuildFailed,
    build_progress,
    rebuild_opening,
    run_stage,
    spec_from_config,
)
from app.site.pipeline import iterate as run_iteration
from app.site.render import build as build_site
from app.site.render import material_from_brief, plan_for
from app.store import brief_archive, db, leads, messages, photos, reviews, sites
from app.web.serialize import brief_to_dict
from app.workbench import hours
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
    # A permanent, never-overwritten copy of THIS crawl, before the DB's own
    # cached row (which the next re-crawl will overwrite) ever sees it — so
    # "what did the model actually see" always has a real file and hash to
    # point at, not a row that has since changed twice.
    payload["_archive"] = brief_archive.save(payload)
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


def _worst_first(urls: list[str], known: dict) -> list[str]:
    """Least confident first, so attention goes where it is worth spending.

    A machine guess at quality 2 with a reason it could not be the hero is
    worth ten seconds of the operator's time. A confident one is worth none,
    and putting them in upload order spends the same attention on both.
    """
    def rank(url: str) -> tuple[int, int, int]:
        said = known.get(url) or {}
        if not said:
            return (0, 0, urls.index(url))          # nothing looked at all
        quality = said.get("quality")
        quality = quality if isinstance(quality, int) else 3
        # A person's own description is settled; leave it at the end.
        settled = 0 if said.get("by_machine") else 1
        return (1 + settled, quality, urls.index(url))
    return sorted(urls, key=rank)


def workspace(lead_id: int) -> dict:
    """Everything the iteration screen needs, in one round trip.

    Includes the plan for the version currently on screen: the plan is the
    cheap thing to review, so it should be there when the screen opens rather
    than only after the next instruction.
    """
    with db.session() as conn:
        history = sites.versions(conn, lead_id)
        # What the first build is waiting for. Placing a photograph well needs
        # to know what it shows, so the design waits for a person rather than
        # guessing — see `pipeline.open_site`.
        # Anything that goes wrong here is said out loud. Swallowing it gave a
        # screen that looked finished and was not: no photographs to describe,
        # a Build button that would fail, and nothing to explain either.
        trouble: list[str] = []
        pending: list[str] = []
        unlocks: list[str] = []
        try:
            brief = leads.brief_with_overrides(conn, lead_id)
        except Exception as exc:                               # noqa: BLE001
            brief = {}
            trouble.append(f"Could not read the brief: "
                           f"{type(exc).__name__}: {exc}")
        if brief:
            unlocks = list(brief.get("open_questions") or [])
            if not history:
                try:
                    material = material_from_brief(brief)
                    pending = photos.unreviewed(conn, lead_id,
                                                list(material.images))
                except Exception as exc:                       # noqa: BLE001
                    trouble.append(f"Could not list the photographs: "
                                   f"{type(exc).__name__}: {exc}")
        outline = ""
        plan: dict = {}
        if history and brief:
            try:
                spec = spec_from_config(history[0].get("spec_json") or {})
                resolved = plan_for(brief, spec)
                outline, plan = resolved.outline(), resolved.as_dict()
            except Exception as exc:                           # noqa: BLE001
                # A plan we cannot draw must not blank the screen — but it must
                # not pretend the section is simply empty either.
                trouble.append(f"Could not draw the plan: "
                               f"{type(exc).__name__}: {exc}")
        # What of the business's own material never reached the page, and
        # why — BRIEF §5, Slice D item 3. The identical function a corpus-
        # wide report calls (`tools/content_census.py`), reused rather than
        # reimplemented, against the opening version's own frozen
        # direction — the same version `plan`/`outline` above describe.
        census: list[dict] = []
        if history and brief:
            try:
                dropped = measure_census(conn, brief.get("name") or str(lead_id),
                                         lead_id).dropped()
                census = [{"field": name, "reached": reached, "of": raw,
                          "why": rule} for name, raw, reached, rule in dropped]
            except Exception as exc:                           # noqa: BLE001
                trouble.append(f"Could not measure what reached the page: "
                               f"{type(exc).__name__}: {exc}")
        rationale = ""
        signature_why = ""
        signature_device = ""
        if history:
            first = history[-1]
            opening_notes = first.get("notes") or {}
            rationale = str(opening_notes.get("rationale") or "")
            # §2.3: one sentence justifying the signature device against
            # this specific business. Recorded at opening time, read back
            # here rather than re-asked — the same replay guarantee as
            # `rationale`. Model prose, and it stops here: never reaches
            # `render`, which cannot see `notes` at all.
            signature_why = str(opening_notes.get("signature_why") or "")
            signature_device = str(opening_notes.get("signature") or "")
        return {
            "lead_id": lead_id,
            "versions": history,
            "events": leads.events(conn, lead_id),
            "outline": outline,
            "plan": plan,
            "census": census,
            "rationale": rationale,
            "signature_device": signature_device,
            "signature_why": signature_why,
            # What one visit would unlock. A business with no website arrives
            # here with little corroborated material, so its opening version is
            # thin — and the honest response is to say which questions would
            # thicken it, not to publish a single source as though it were a
            # fact.
            "unlocks": unlocks,
            "pending_labels": pending,
            "can_build": not history and not pending,
            "build": build_progress(conn, lead_id),
            "trouble": trouble,
            # The conversation, oldest first. It opens on what was decided and
            # why rather than on an empty box.
            "thread": messages.thread(conn, lead_id),
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
        versions = sites.versions(conn, lead_id)
        base = next((v for v in versions if v["version"] == parent_version),
                    versions[0] if versions else None)
        # A page the old renderer did not build has no spec to restyle: the
        # chat box could not touch a single designed version of Fish Shack.
        if base is not None and not (base.get("spec") or "").strip():
            return _edit(conn, lead_id, sentence, int(base["version"]))
        try:
            result = run_iteration(conn, lead_id, sentence,
                                   parent_version=parent_version)
        except ValueError as exc:
            return {"error": str(exc)}
        payload = result.as_dict()
        payload["lead_id"] = lead_id
        payload["versions"] = sites.versions(conn, lead_id)
        payload["events"] = leads.events(conn, lead_id)
        payload["thread"] = messages.thread(conn, lead_id)
        return payload


def _claim_counts(conn, lead_id: int, version: int) -> dict[str, int]:
    brief, text, _where = _review_brief(conn, lead_id, str(
        conn.execute("SELECT name FROM leads WHERE id = ?", (lead_id,)).fetchone()["name"]))
    counts: dict[str, int] = {}
    for row in review_run.findings(sites.html_for(conn, lead_id, version) or "", brief, text):
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return counts


def _edit(conn, lead_id: int, sentence: str, parent: int) -> dict:
    """A sentence about a designed page, made into a new version by an edit run.

    The reply goes into the thread with what the edit cost and whether the
    claim checks moved, so a wording change that invents a fact is visible in
    the same place the change was asked for.
    """
    outcome = bridge.edit(conn, lead_id, sentence, parent_version=parent)
    said = outcome["reply"]
    if outcome["version"]:
        before, after = _claim_counts(conn, lead_id, parent), _claim_counts(
            conn, lead_id, outcome["version"])
        moved = [f"{verdict} {before.get(verdict, 0)} → {after.get(verdict, 0)}"
                 for verdict in ("contradicted", "unsourced", "defect")
                 if before.get(verdict, 0) != after.get(verdict, 0)]
        said += (f" Saved as v{outcome['version']}. Checks: "
                 + ("; ".join(moved) if moved else "unchanged") + ".")
    said += f" (${outcome['cost_usd']:.2f})"
    messages.add(conn, lead_id, "assistant", said, version=outcome["version"])
    return {"lead_id": lead_id, "version": outcome["version"], "rejected": False,
            "unchanged": outcome["version"] is None, "cost_usd": outcome["cost_usd"],
            "versions": sites.versions(conn, lead_id), "events": leads.events(conn, lead_id),
            "thread": messages.thread(conn, lead_id)}


_ANNOTATE = Path(__file__).with_name("annotate.js")


def _annotated(page: str, lead_id: int, review: dict) -> str:
    """The generated page plus the review layer, for this request only."""
    payload = json.dumps({
        "lead_id": lead_id, "review_id": review["id"], "version": review["version"],
        "findings": review["findings"]}).replace("</", "<\\/")
    layer = (f"<script>window.__REVIEW__ = {payload};</script>\n"
             f"<script>{_ANNOTATE.read_text()}</script>")
    if "</body>" in page:
        return page.replace("</body>", layer + "\n</body>", 1)
    return page + layer


def how_it_was_read(field: str, value: str) -> dict | None:
    """What the tool made of what you typed, in the words you would use.

    Opening times are written a dozen ways and every one of them is correct —
    "Mon-Fri 9-5", "Tuesday through Saturday, 11am to 9pm", "Closed Sundays".
    Any of them can be stored, so the box asks for no particular format. What
    it owes you instead is proof that it understood: a week the tool misread is
    a week the finished page prints wrong, and nothing on the screen would have
    said so.

    A schedule it cannot read is not refused either. It is kept verbatim and
    the screen says it will appear exactly as typed, which is honest and is
    sometimes what you want ("by appointment, call ahead").
    """
    if field != "hours":
        return None
    read = hours.readable([value])
    return {"read": read} if read else {"read": ""}


def rebuild_after(conn, lead_id: int, field: str, outcome: dict) -> dict:
    """A correction changes the page, so the page is rebuilt.

    Confirming what the sources already said is not a correction and costs
    nothing: no instruction is sent and no version is written. A correction
    sends one instruction naming the field, the new value and the old one, so
    the trail shows plainly why the version exists.

    A rebuild that fails never loses the correction: it is already recorded in
    the audit trail by the time this runs, and the failure is reported instead
    of raised.
    """
    if outcome.get("kind") != "corrected":
        return {"built": False, "why": "nothing changed, so nothing to rebuild"}
    if not sites.versions(conn, lead_id):
        return {"built": False, "why": "no version yet — the correction "
                                       "will be in the first build"}
    label = leads.FIELD_LABELS.get(field, field)
    was = outcome.get("was")
    sentence = (
        f"{label} is {outcome.get('value')!r}."
        + (f" The page was built from {was!r}, which was wrong." if was else
           " The page was built without it.")
        + " Correct every place the page shows it, and change nothing else.")
    try:
        result = run_iteration(conn, lead_id, sentence, actor="correction")
    except Exception as exc:                                   # noqa: BLE001
        # Deliberately broad: a generation failure is a bad afternoon, and a
        # correction that raises out of the endpoint looks to the operator
        # like the correction itself did not save. It did.
        return {"built": False, "why": f"{type(exc).__name__}: {exc}",
                "correction_saved": True}
    return {"built": True, "version": result.version, "field": field}


def logo_for(conn, lead_id: int) -> tuple[bytes, str] | None:
    """The logo a lead's pages show, as the brief names it after corrections."""
    try:
        url = (leads.brief_with_overrides(conn, lead_id).get("published") or {}).get("logo")
    except ValueError:
        return None
    return logos.fetch(str(url)) if url else None


def _review_brief(conn, lead_id: int, name: str) -> tuple[dict, str, dict]:
    """What the checks should judge the page against.

    `material` reads the archived crawl, which is the right provenance record
    and the wrong thing to check against: it predates every correction the
    operator has made. What you were told at the door outranks what a directory
    published, and a check that does not know that reports a fact you fixed
    yourself as a contradiction.

    The page text searched comes from that same brief. Taking it from the
    archive meant that when the two held different crawls, a claim was judged
    against one crawl's facts and another crawl's words.
    """
    archived, capture, where = review_run.material(name)
    try:
        brief = leads.brief_with_overrides(conn, lead_id)
    except ValueError:
        return archived, capture, where
    if not brief.get("facts") and archived.get("facts"):
        return archived, capture, where
    text = review_run.page_text(brief)
    pages = brief.get("pages") or []
    where = {**where, "checked_against": "the lead's brief, with your corrections",
             "capture_hash": review_run._hash(text) if text else "",
             "capture_file": (f"page text of {sum(1 for p in pages if p.get('read'))} of "
                              f"{len(pages)} pages, in the lead's brief") if pages else "",
             "capture_missing": not text}
    return brief, text, where


def refresh_review(conn, lead_id: int, version: int) -> dict:
    """Run the checks again over a version whose review is already open."""
    current = reviews.for_version(conn, lead_id, version)
    if current is None:
        return open_review(conn, lead_id, version)
    lead = conn.execute("SELECT name FROM leads WHERE id = ?",
                        (lead_id,)).fetchone()
    html = sites.html_for(conn, lead_id, version)
    if lead is None or html is None:
        raise ValueError("nothing to re-check")
    brief, capture, where = _review_brief(conn, lead_id, str(lead["name"]))
    return reviews.refresh(conn, current["id"],
                           review_run.findings(html, brief, capture))


def open_review(conn, lead_id: int, version: int) -> dict:
    """The approval stage for one version: run the checks once, then keep them.

    Findings are generated the first time somebody opens the review and never
    again, because from that moment they carry notes. Re-running would look
    like a refresh and would be a deletion.
    """
    existing = reviews.for_version(conn, lead_id, version)
    if existing:
        return existing
    lead = conn.execute("SELECT name FROM leads WHERE id = ?",
                        (lead_id,)).fetchone()
    if lead is None:
        raise ValueError("no such lead")
    html = sites.html_for(conn, lead_id, version)
    if html is None:
        raise ValueError(f"there is no version {version} to review")
    brief, capture, where = _review_brief(conn, lead_id, str(lead["name"]))
    found = review_run.findings(html, brief, capture)
    opened = reviews.open_review(conn, lead_id, version, found,
                                 brief_hash=where["brief_hash"],
                                 capture_hash=where["capture_hash"])
    opened["material"] = where
    return opened


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
        rebuilt: dict | None = None
        reading: dict | None = None
        try:
            with db.session() as conn:
                if route == "/api/verify":
                    field = str(body.get("field", ""))
                    outcome = leads.verify(conn, lead_id, field,
                                           str(body.get("value", "")),
                                           note=(body.get("note") or None))
                    rebuilt = rebuild_after(conn, lead_id, field, outcome)
                    reading = how_it_was_read(field, outcome["value"])
                elif route == "/api/status":
                    leads.set_status(conn, lead_id, str(body.get("status", "")),
                                     note=(body.get("note") or None))
                elif route == "/api/generate":
                    self._json(generate(lead_id, str(body.get("spec", ""))))
                    return
                elif route == "/api/build":
                    # One stage at a time, so the screen can say which one is
                    # running and a failure can say which one failed. A stage
                    # already answered returns its answer without asking again,
                    # so a retry costs only the stage that went wrong.
                    stage = str(body.get("stage") or "")
                    progress = build_progress(conn, lead_id)
                    stage = stage or progress["next"] or STAGES[-1]
                    try:
                        answer = run_stage(conn, lead_id, stage)
                    except BuildFailed as failure:
                        self._json({"error": f"{STAGES_SAY[failure.stage]} "
                                             f"did not finish: {failure.reason}",
                                    "stage": failure.stage,
                                    "progress": build_progress(conn, lead_id)},
                                   400)
                        return
                    payload = {"stage": stage, "answer": answer,
                               "progress": build_progress(conn, lead_id),
                               "versions": sites.versions(conn, lead_id),
                               "events": leads.events(conn, lead_id)}
                    self._json(payload)
                    return
                elif route == "/api/rebuild":
                    # A correction to a photo description has to be able to
                    # reach the page. `open_site` is idempotent, so once v1
                    # exists it would otherwise do nothing at all.
                    result = rebuild_opening(conn, lead_id)
                    payload = result.as_dict()
                    payload["versions"] = sites.versions(conn, lead_id)
                    payload["events"] = leads.events(conn, lead_id)
                    self._json(payload)
                    return
                elif route == "/api/iterate":
                    said = str(body.get("sentence", "")).strip()
                    if said:
                        messages.add(conn, lead_id, "user", said)
                    self._json(iteration(
                        lead_id, str(body.get("sentence", "")),
                        body.get("parent_version")))
                    return
                elif route == "/api/label":
                    with db.session() as conn:
                        photos.label(conn, lead_id, str(body.get("url", "")),
                                     str(body.get("description", "")),
                                     what=(body.get("label") or None))
                        self._json({"photos": photos.described(conn, lead_id)})
                    return
                elif route == "/api/labels":
                    # All of them at once: labelling twenty photographs should
                    # not be twenty round trips and twenty redraws.
                    entries = body.get("photos") or []
                    saved, failed = 0, []
                    with db.session() as conn:
                        for entry in entries:
                            try:
                                photos.label(conn, lead_id,
                                             str(entry.get("url", "")),
                                             str(entry.get("description", "")),
                                             what=(entry.get("label") or None))
                                saved += 1
                            except ValueError as exc:
                                failed.append(str(exc))
                        self._json({"saved": saved, "failed": failed,
                                    "photos": photos.described(conn, lead_id)})
                    return
                elif route == "/api/review":
                    self._json(open_review(conn, lead_id,
                                           int(body.get("version") or 0)))
                    return
                elif route == "/api/review/refresh":
                    self._json(refresh_review(
                        conn, lead_id, int(body.get("version") or 0)))
                    return
                elif route == "/api/review/finding":
                    self._json(reviews.mark(
                        conn, int(body.get("finding_id") or 0),
                        str(body.get("status", "")),
                        str(body.get("note", "")).strip()))
                    return
                elif route == "/api/review/decide":
                    self._json(reviews.decide(
                        conn, int(body.get("review_id") or 0),
                        str(body.get("decision", "")),
                        str(body.get("note", "")).strip()))
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
                payload = leads.brief_with_overrides(conn, lead_id)
                if reading is not None:
                    payload["reading"] = reading
                if rebuilt is not None:
                    # What the correction did to the page, said on the screen
                    # that made it rather than found later in the version list.
                    payload["rebuilt"] = rebuilt
                    payload["versions"] = sites.versions(conn, lead_id)
                self._json(payload)
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)

    def do_GET(self) -> None:  # noqa: N802  (stdlib naming)
        route = urlparse(self.path)
        if route.path in ("/", "/index.html"):
            # Never cached: the operator reloading after a change has to get the
            # change, or we spend the next exchange comparing different builds.
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, must-revalidate")
            body = _UI.read_bytes()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # A generated site is served as a real page so it can be opened, shown
        # on a phone, or sent to the owner — not just previewed in a frame.
        # Generated pages reference photos through here, so the API key that
        # fetches them is never written into a page we hand to anyone.
        if route.path.startswith("/photo/"):
            bits = route.path.strip("/").split("/")
            try:
                lead_id, index = int(bits[1]), int(bits[2])
                asked = int((parse_qs(route.query).get("w") or ["0"])[0] or 0)
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
            width = photos_api.nearest_width(asked) if asked else photos_api.MAX_WIDTH
            image = fetch_photo(google_places_api_key() or "", names[index],
                                width=width)
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
        if route.path.startswith("/logo/"):
            try:
                logo_lead = int(route.path.strip("/").split("/")[1])
            except (IndexError, ValueError):
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            with db.session() as conn:
                logo = logo_for(conn, logo_lead)
            if logo is None:
                self._send(404, b"no logo", "text/plain; charset=utf-8")
                return
            self.send_response(200)
            self.send_header("Content-Type", logo[1])
            self.send_header("Content-Length", str(len(logo[0])))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(logo[0])
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
                # ?review=<id> draws the findings on the page itself. The layer
                # is added here, at serve time, and never stored: the version in
                # the database stays the page that would be sent to a client.
                wanted = (parse_qs(route.query).get("review") or [""])[0]
                marks = None
                if page is not None and wanted:
                    try:
                        marks = reviews.review(conn, int(wanted))
                    except (TypeError, ValueError):
                        marks = None
            if page is None:
                self._send(404, b"no site generated for this lead yet",
                           "text/plain; charset=utf-8")
                return
            if marks:
                page = _annotated(page, lead_id, marks)
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
                known = photos.described(conn, lead_id)
            # Exactly what the first build waits on, from the same function
            # that decides it. Two lists built two ways can disagree, and the
            # failure is the worst kind: every photo on screen is labelled and
            # the build still refuses.
            urls = list(material_from_brief(brief).images)
            hints = photos.suggest_all(urls)
            self._json({"lead_id": lead_id, "labels": known,
                        "options": list(photos.LABELS),
                        "suggestions": hints,
                        "photos": [{"url": u,
                                    "label": (known.get(u) or {}).get("label"),
                                    "description":
                                        (known.get(u) or {}).get("description", ""),
                                    "by_machine":
                                        (known.get(u) or {}).get("by_machine", False),
                                    "quality": (known.get(u) or {}).get("quality"),
                                    "why_not": (known.get(u) or {}).get("why_not", ""),
                                    "suggestion": hints.get(u, "")}
                                   for u in _worst_first(urls, known)]})
            return
        if route.path == "/api/workspace":
            try:
                lead_id = int((parse_qs(route.query).get("id") or ["0"])[0])
            except ValueError:
                lead_id = 0
            self._json(workspace(lead_id))
            return
        if route.path == "/api/review":
            params = parse_qs(route.query)
            try:
                lead_id = int((params.get("id") or ["0"])[0])
                version = int((params.get("version") or ["0"])[0])
                with db.session() as conn:
                    found = reviews.for_version(conn, lead_id, version)
                    history = reviews.history(conn, lead_id)
                self._json({"review": found, "history": history})
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
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


def serve(port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"workbench UI on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
