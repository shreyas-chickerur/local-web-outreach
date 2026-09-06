"""Running one iteration: sentence in, new version out — or a refusal.

The coordination layer. It is the only place that knows about all four of the
parser, the renderer, the content gatekeeper and the store, which keeps each of
those unaware of the others.

Two decisions are worth stating plainly:

* **A refusal is a result, not an exception.** The gatekeeper raises internally,
  but that is caught here and returned as `IterationResult(rejected=True)` with
  the offending phrases attached. An exception escaping to the UI would tell
  the operator that something went wrong and nothing about which words did it.
* **A refusal writes no version.** The previous site stays live and untouched.
  The attempt is still recorded on the lead's trail, because an instruction
  that produced unsafe output is the most interesting thing that happened.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from app.adapters import claude, vision
from app.adapters.claude import ClaudeError
from app.site.audit import audit
from app.site.iterate import DEFAULT_SPEC, parse_iteration_instruction
from app.site.opening import opening_spec
from app.site.render import (
    build_from_spec,
    material_from_brief,
    plan_for,
    unsupported,
)
from app.site.spec import SiteSpec
from app.site.theme import theme_for
from app.site.understand import understand
from app.store import leads, photos, sites


class ContentSafetyError(RuntimeError):
    """The rendered page asserted something the brief does not support."""

    def __init__(self, findings: list[str]) -> None:
        super().__init__("; ".join(findings))
        self.findings = findings


@dataclass(frozen=True)
class IterationResult:
    """What one instruction did, in the shape the UI binds to.

    `notes` on the stored row is the persisted copy so an old version can still
    explain itself; this is the live contract, so callers never have to dig
    through a JSON blob to find out what was understood.
    """

    lead_id: int
    spec: dict
    understood: list[str] = field(default_factory=list)
    unmet: list[str] = field(default_factory=list)
    ignored_tokens: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    # What the design audit found, and what the build corrected on its own.
    defects: list[str] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    # What the site was decided to be, before it was emitted. Reviewing this is
    # a different and much cheaper activity than reviewing a rendered page.
    plan: dict = field(default_factory=dict)
    outline: str = ""
    version: int | None = None
    parent_version: int | None = None
    rejected: bool = False
    findings: list[str] = field(default_factory=list)
    # The instruction parsed to exactly the configuration it started from, so
    # no version was written. Distinct from `rejected`: nothing was wrong with
    # it, there was simply nothing in it this could act on.
    unchanged: bool = False
    # What kind of thing the instruction was: an edit, a bug report, a request
    # to change what the site says, or something the renderer cannot do. Only
    # "style" writes a version — the misread this replaced was treating all
    # four as edits.
    kind: str = "style"
    # Genuinely asked for, and outside what the generator can express. The
    # queue of what to build next, in the operator's own words.
    unsupported: list[str] = field(default_factory=list)
    defect: str = ""
    read_by: str = "phrases"
    # Why the fuller reading was not used, when a key is configured but the
    # call failed. An operator whose instructions suddenly stop being
    # understood should be told the model is unreachable, not left guessing.
    reader_error: str = ""
    # Why the opening version looks the way it does, in words the operator can
    # repeat to the owner.
    rationale: str = ""

    @property
    def url(self) -> str | None:
        if self.version is None:
            return None
        return f"/site/{self.lead_id}/{self.version}"

    def as_dict(self) -> dict:
        return {
            "version": self.version, "parent_version": self.parent_version,
            "url": self.url, "spec": self.spec, "understood": self.understood,
            "unmet": self.unmet, "ignored_tokens": self.ignored_tokens,
            "contradictions": self.contradictions,
            "defects": self.defects, "repairs": self.repairs,
            "plan": self.plan, "outline": self.outline,
            "rejected": self.rejected, "findings": self.findings,
            "unchanged": self.unchanged, "kind": self.kind,
            "unsupported": self.unsupported, "defect": self.defect,
            "read_by": self.read_by, "reader_error": self.reader_error,
            "rationale": self.rationale,
        }


def spec_from_config(config: dict) -> SiteSpec:
    """The resolved configuration as the renderer's own spec object."""
    cta = config.get("cta")
    return SiteSpec(
        text=config.get("instruction", ""),
        mood=config.get("mood") or "fresh",
        lead_with=config.get("lead_with"),
        emphasis=list(config.get("emphasis") or []),
        suppress=list(config.get("suppress") or []),
        cta=(cta or {}).get("kind") if isinstance(cta, dict) else cta,
        cta_label=(cta or {}).get("label") if isinstance(cta, dict) else None,
        accent=config.get("accent"),
        hero_offset=int(config.get("hero_offset") or 0),
        understood=list(config.get("understood") or []),
        ignored=list(config.get("ignored_tokens") or []),
    )


def current_config(conn: sqlite3.Connection, lead_id: int,
                   parent_version: int | None = None) -> dict:
    """The configuration an iteration builds on.

    An iteration is a delta, so without this "make it more rustic" would drop
    every earlier instruction on the floor.

    When a parent is named, the delta applies to THAT version's configuration
    rather than the newest one. This is what makes branching real: going back
    to v3 and changing the mood has to inherit v3's ordering and call to
    action, not whatever v8 happened to be doing.
    """
    history = sites.versions(conn, lead_id)
    if parent_version is not None:
        for row in history:
            if row["version"] == parent_version:
                return dict(row.get("spec_json") or {}) or dict(DEFAULT_SPEC)
        raise ValueError(
            f"cannot branch from v{parent_version}: no such version for this lead")
    for row in history:                      # newest first
        stored = row.get("spec_json") or {}
        if stored:
            return dict(stored)
    return dict(DEFAULT_SPEC)


def read_instruction(sentence: str, base: dict) -> dict:
    """One instruction, read as well as we can read it.

    Claude first, because a table of phrases understands about a fifth of what
    an operator actually types. The phrase parser is the fallback rather than
    the fallback being nothing: no key, a timeout, or a refusal must not lose
    the instruction, and offline the tool still works with a smaller vocabulary.

    Both readings resolve to the same validated configuration, so nothing
    downstream — the renderer, the audit, the content gate — can tell which one
    it got.
    """
    if claude.available():
        try:
            answer = understand(sentence, base)
            answer["read_by"] = "claude"
            return answer
        except ClaudeError as exc:
            # Worth carrying rather than swallowing: an operator whose
            # instructions suddenly stop being understood should be told the
            # model is unreachable, not left guessing.
            fallback = parse_iteration_instruction(sentence, base)
            fallback["read_by"] = "phrases"
            fallback["kind"] = "style"
            fallback["unsupported"] = []
            fallback["defect"] = ""
            fallback["reader_error"] = str(exc)
            return fallback
    config = parse_iteration_instruction(sentence, base)
    config["read_by"] = "phrases"
    config["kind"] = "style"
    config["unsupported"] = []
    config["defect"] = ""
    return config


def rebuild_opening(conn: sqlite3.Connection, lead_id: int,
                    *, actor: str | None = None) -> IterationResult:
    """The opening design again, now that the photographs are better described.

    `open_site` is idempotent on purpose — opening the workspace twice is not a
    request to rebuild — and that left a hole the moment vision started
    unblocking the first build. The order used to be label, then build; it is
    now build, then correct, and a correction with no way to reach the page is
    a correction that does nothing.

    A new version rather than an edit of the old one, so the trail still says
    what happened and the previous page stays reachable.
    """
    history = sites.versions(conn, lead_id)
    parent = history[0]["version"] if history else None
    brief = leads.brief_with_overrides(conn, lead_id)
    config = opening_spec(brief)
    return _build_opening(conn, lead_id, brief, config, actor=actor,
                          parent_version=parent,
                          instruction="rebuilt from the photo descriptions")


def open_site(conn: sqlite3.Connection, lead_id: int,
              *, actor: str | None = None) -> IterationResult:
    """The first version of a new lead's site, designed before anyone types.

    The operator walks in with a site. It must already look made for this
    business — a version that opens on "no site yet", or on the same default
    theme every trade gets, is worse than nothing because it says the tool did
    not look. So the direction is chosen from the evidence, and everything the
    generator enforces about craft applies to it exactly as to any later
    version, the content gate included.

    Idempotent: a lead that already has a version keeps it. This runs when the
    workspace opens, and opening the workspace twice is not a request to
    rebuild.
    """
    history = sites.versions(conn, lead_id)
    if history:
        return IterationResult(lead_id=lead_id, spec={},
                               version=history[0]["version"], unchanged=True)

    brief = leads.brief_with_overrides(conn, lead_id)

    # Look at the photographs before designing around them. Which picture
    # leads, whether the only usable images are of food, whether the "hero" is
    # a photograph of a menu — all of it turns on what they show.
    #
    # This used to wait for a person to type a description of every one, which
    # is thirty of them per lead and directly contradicts opening on something
    # worth showing. The vision pass answers it in one call, the screen still
    # shows every guess for correction, and a correction replaces the guess and
    # stays attributed.
    material = material_from_brief(brief)
    unseen = photos.unreviewed(conn, lead_id, list(material.images))
    if unseen:
        for url, seen in vision.look(unseen, material.place_photos).items():
            photos.record_vision(conn, lead_id, url, seen)
        brief = leads.brief_with_overrides(conn, lead_id)
        material = material_from_brief(brief)

    # Without a key nothing looked, and designing blind around photographs is
    # worse than asking. The keyless path keeps the labelling step.
    pending = photos.unreviewed(conn, lead_id, list(material.images))
    if pending:
        return IterationResult(
            lead_id=lead_id, spec={}, kind="needs_labels",
            unsupported=pending, unchanged=True)

    config = opening_spec(brief)
    return _build_opening(conn, lead_id, brief, config, actor=actor)


def _build_opening(conn: sqlite3.Connection, lead_id: int, brief: dict,
                   config: dict, *, actor: str | None = None,
                   parent_version: int | None = None,
                   instruction: str = "opening design") -> IterationResult:
    """Render, audit, gate and store one opening design.

    Shared by the first build and by a rebuild after the photographs have been
    described better, because two copies of the gate would drift and only one
    of them would be the one that matters.
    """
    rationale = str(config.pop("rationale", ""))
    read_by = str(config.pop("read_by", "trade table"))
    for key in ("kind", "unsupported", "defect"):
        config.pop(key, None)
    config["instruction"] = instruction

    spec = spec_from_config(config)
    resolved = plan_for(brief, spec)
    html = build_from_spec(brief, spec)
    report = audit(html, theme_for(spec.mood, spec.accent))
    defects = [str(f) for f in report.failures]
    repairs = report.as_dict()["repairs"]

    findings = unsupported(html, material_from_brief(brief))
    if findings:
        # The gate applies to the opening version too. A first draft that
        # invents something is not a better first impression than none.
        sites.reject(conn, lead_id, instruction, findings, actor=actor)
        return IterationResult(
            lead_id=lead_id, spec=config, defects=defects, repairs=repairs,
            plan=resolved.as_dict(), outline=resolved.outline(),
            rejected=True, findings=findings, read_by=read_by)

    notes = {"mood": spec.mood, "understood": list(config.get("understood") or []),
             "unmet": spec.unmet, "ignored": [], "contradictions": [],
             "defects": defects, "repairs": repairs,
             "plan": resolved.as_dict(), "lead_with": spec.lead_with,
             "rationale": rationale}
    version = sites.save(conn, lead_id, html, instruction, notes=notes,
                         actor=actor, spec_json=config,
                         parent_version=parent_version)
    return IterationResult(
        lead_id=lead_id, spec=config,
        understood=list(config.get("understood") or []),
        defects=defects, repairs=repairs,
        plan=resolved.as_dict(), outline=resolved.outline(),
        version=version, parent_version=parent_version,
        read_by=read_by, rationale=rationale)


def iterate(conn: sqlite3.Connection, lead_id: int, sentence: str,
            *, parent_version: int | None = None,
            actor: str | None = None) -> IterationResult:
    """Apply one instruction and store the result, unless it fails the gate."""
    brief = leads.brief_with_overrides(conn, lead_id)
    base = current_config(conn, lead_id, parent_version)
    config = read_instruction(sentence, base)
    read_by = str(config.pop("read_by", "phrases"))
    kind = str(config.pop("kind", "style"))
    unsupported_asks = list(config.pop("unsupported", []))
    complaint = str(config.pop("defect", ""))
    reader_error = str(config.pop("reader_error", ""))
    config["instruction"] = sentence

    if kind != "style":
        # A bug report, a request for different facts, or something the
        # renderer cannot express. None of them is an edit. Answering a
        # complaint by restyling the page is exactly the misread this replaced.
        live = parent_version
        if live is None:
            history = sites.versions(conn, lead_id)
            live = history[0]["version"] if history else None
        found: list[str] = []
        if kind == "defect" and live is not None:
            # Say what the audit already knows about the page they are looking
            # at, rather than asking them to describe it again.
            page = sites.html_for(conn, lead_id, live)
            if page:
                spec_now = spec_from_config(base)
                report = audit(page, theme_for(spec_now.mood, spec_now.accent))
                found = [str(f) for f in report.failures]
        return IterationResult(
            lead_id=lead_id, spec={**config},
            understood=list(config.get("understood") or []),
            defects=found, parent_version=live, unchanged=True,
            kind=kind, unsupported=unsupported_asks, defect=complaint,
            read_by=read_by, reader_error=reader_error)

    spec = spec_from_config(config)
    resolved = plan_for(brief, spec)
    html = build_from_spec(brief, spec)

    # The design audit: defects the operator should never have to catch. It
    # runs before the honesty gate because a page that fails on contrast is
    # worth knowing about even when it also fails on content.
    report = audit(html, theme_for(spec.mood, spec.accent))
    defects = [str(f) for f in report.failures]
    repairs = report.as_dict()["repairs"]

    # The gatekeeper, immediately before the write and after every other
    # decision — so nothing added downstream of the parser can slip past it.
    findings = unsupported(html, material_from_brief(brief))
    if findings:
        sites.reject(conn, lead_id, sentence, findings, actor=actor)
        return IterationResult(
            lead_id=lead_id, spec=config, understood=config["understood"],
            unmet=spec.unmet, ignored_tokens=config["ignored_tokens"],
            contradictions=config["contradictions"],
            defects=defects, repairs=repairs,
            plan=resolved.as_dict(), outline=resolved.outline(),
            rejected=True, findings=findings)

    if parent_version is None:
        history = sites.versions(conn, lead_id)
        parent_version = history[0]["version"] if history else None

    # A version should mean something changed. "the page should have more blue"
    # was a word the parser had no rule for, so it minted a version byte-for-byte
    # identical to its parent and left the operator staring at an unchanged page
    # wearing a fresh number.
    #
    # The comparison is on the rendered page rather than on the configuration,
    # because the brief can move underneath an unchanged instruction — confirm
    # the hours and the same words legitimately produce a different site.
    if parent_version is not None:
        previous = sites.html_for(conn, lead_id, parent_version)
        if previous is not None and previous == html:
            return IterationResult(
                lead_id=lead_id, spec=config, understood=config["understood"],
                unmet=spec.unmet, ignored_tokens=config["ignored_tokens"],
                contradictions=config["contradictions"],
                defects=defects, repairs=repairs,
                plan=resolved.as_dict(), outline=resolved.outline(),
                parent_version=parent_version, unchanged=True,
                unsupported=unsupported_asks, read_by=read_by,
                reader_error=reader_error)

    notes = {"mood": spec.mood, "understood": config["understood"],
             "unmet": spec.unmet, "ignored": config["ignored_tokens"],
             "contradictions": config["contradictions"],
             "defects": defects, "repairs": repairs,
             "plan": resolved.as_dict(),
             "lead_with": spec.lead_with}
    version = sites.save(conn, lead_id, html, sentence, notes=notes,
                         actor=actor, spec_json=config,
                         parent_version=parent_version)
    return IterationResult(
        lead_id=lead_id, spec=config, understood=config["understood"],
        unmet=spec.unmet, ignored_tokens=config["ignored_tokens"],
        contradictions=config["contradictions"],
        defects=defects, repairs=repairs,
        plan=resolved.as_dict(), outline=resolved.outline(),
        version=version, parent_version=parent_version,
        unsupported=unsupported_asks, read_by=read_by,
        reader_error=reader_error)
