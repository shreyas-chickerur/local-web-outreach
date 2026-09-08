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
from app.site.render import (
    build_from_spec,
    material_from_brief,
    plan_for,
    unsupported,
)
from app.site.spec import SiteSpec
from app.site.theme import theme_for
from app.site.understand import understand
from app.store import fingerprints, leads, messages, photos, sites


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
        first_screen=str(config.get("first_screen") or "photo"),
        type_treatment=str(config.get("type_treatment") or "quiet"),
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
    sites.forget_stages(conn, lead_id)
    brief = leads.brief_with_overrides(conn, lead_id)
    # Through the gate, not around it. This called `opening_spec` directly and
    # handed the answer straight to `_build_opening`, which records it in the
    # shared fingerprint history — so a rebuild shipped an ungated decision and
    # then counted as precedent for everyone after it. It is also the path most
    # likely to need the gate: it fires right after vision unblocks a build,
    # which is when the first direction was decided on the thinnest material.
    config = _stage_direction(conn, lead_id, brief)["config"]
    return _build_opening(conn, lead_id, brief, config, actor=actor,
                          parent_version=parent,
                          instruction="rebuilt from the photo descriptions")


# The build in the order it happens, each one persisted so a retry re-runs only
# what failed. A timeout in the last stage used to throw away the vision pass
# and the design decision that preceded it, and the operator paid for both
# again — while standing in someone's shop.
STAGES = ("photographs", "direction", "page")

STAGE_SAYS = {
    "photographs": "Looking at the photographs",
    "direction": "Choosing a direction",
    "page": "Building the page",
}


class BuildFailed(RuntimeError):
    """A stage did not finish, and which one it was.

    Raised rather than swallowed. `workspace()` used to run the whole build
    inside a bare `except Exception: pass`, so a failure anywhere produced a
    blank screen after twenty-five seconds with nothing said about why.
    """

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(f"{stage}: {reason}")
        self.stage = stage
        self.reason = reason


def build_progress(conn: sqlite3.Connection, lead_id: int) -> dict:
    """Which stages are already answered, without running anything."""
    done = [stage for stage in STAGES
            if sites.recall_stage(conn, lead_id, stage) is not None]
    return {"stages": list(STAGES), "done": done,
            "says": dict(STAGE_SAYS),
            "next": next((s for s in STAGES if s not in done), None)}


def run_stage(conn: sqlite3.Connection, lead_id: int, stage: str,
              *, actor: str | None = None) -> dict:
    """One stage of the opening build.

    Each is idempotent: a stage whose answer is already stored returns it
    without asking again. That is what makes a retry cheap, and it is also what
    makes the census meaningful — a second pass over the same fixtures must pay
    nothing, or tuning the diversity budget over a few dozen leads is
    unaffordable.
    """
    if stage not in STAGES:
        raise BuildFailed(stage, "no such stage")
    stored = sites.recall_stage(conn, lead_id, stage)
    if stored is not None:
        return {**stored, "stage": stage, "reused": True}

    brief = leads.brief_with_overrides(conn, lead_id)
    try:
        if stage == "photographs":
            answer = _stage_photographs(conn, lead_id, brief)
        elif stage == "direction":
            answer = _stage_direction(conn, lead_id, brief)
        else:
            answer = _stage_page(conn, lead_id, brief, actor=actor)
    except BuildFailed:
        raise
    except Exception as exc:                                   # noqa: BLE001
        raise BuildFailed(stage, str(exc)) from exc

    if not answer.pop("_transient", False):
        sites.remember_stage(conn, lead_id, stage, answer)
    return {**answer, "stage": stage, "reused": False}


def _stage_photographs(conn: sqlite3.Connection, lead_id: int,
                       brief: dict) -> dict:
    """Look at them before designing around them.

    Which picture leads, whether the only usable images are of food, whether
    the "hero" is a photograph of a menu — all of it turns on what they show.
    """
    material = material_from_brief(brief)
    unseen = photos.unreviewed(conn, lead_id, list(material.images))
    looked = unreachable = 0
    if unseen:
        answers = vision.look(unseen, material.place_photos)
        # Only when something actually looked. Without a key `answers` is empty
        # for every photograph, and filling them all in as "could not fetch"
        # would silently unblock a build nobody has looked at — which is the
        # whole thing the keyless path is gating.
        fill = bool(answers)
        for url in unseen:
            seen = answers.get(url)
            if seen is None and not fill:
                continue
            if seen is None:
                # We could not fetch it to look at — a scraped image that
                # 404s, hotlink protection, something too large to send. That
                # is a decision about the photograph too, and recording it is
                # what stops one dead URL blocking the build forever. It never
                # leads, and the operator can still describe it.
                seen = {"subject": "unclear", "quality": 1,
                        "is_hero_candidate": False,
                        "why_not": "could not be fetched to look at",
                        "alt_text": ""}
                unreachable += 1
            if photos.record_vision(conn, lead_id, url, seen):
                looked += 1
    pending = photos.unreviewed(conn, lead_id, list(material.images))
    if pending:
        # Nothing looked, so designing blind around photographs is worse than
        # asking. The keyless path keeps the labelling step.
        raise BuildFailed("photographs",
                          f"{len(pending)} still to be described")
    return {"looked_at": looked, "unreachable": unreachable,
            "photographs": len(material.images)}


def _stage_direction(conn: sqlite3.Connection, lead_id: int,
                     brief: dict) -> dict:
    """What kind of site this business should get, and not one it already made.

    The diversity budget runs here rather than after rendering: a collision is
    a request for a different DECISION, and re-deciding is cheap where
    re-rendering and re-auditing is not.
    """
    from app.site.identity import decide

    made = decide(conn, lead_id, brief)
    return {"config": made.config, "attempts": made.attempts,
            "perturbed": made.perturbed, "unresolved": made.unresolved,
            "collided_with": made.collided_with}


def _stage_page(conn: sqlite3.Connection, lead_id: int, brief: dict,
                *, actor: str | None = None) -> dict:
    """Render, audit, gate and store — from the stored direction."""
    direction = sites.recall_stage(conn, lead_id, "direction")
    if direction is None:
        raise BuildFailed("page", "no direction to build from")
    result = _build_opening(conn, lead_id, brief, dict(direction["config"]),
                            actor=actor)
    return {"version": result.version, "rejected": result.rejected,
            "findings": result.findings, "defects": result.defects,
            # A rejection is a result, not an error — but it is not an answer
            # to remember either. Storing it would let a retry believe the page
            # stage was finished when no version was ever written.
            "_transient": result.rejected}


def open_site(conn: sqlite3.Connection, lead_id: int,
              *, actor: str | None = None) -> IterationResult:
    """The first version of a new lead's site, designed before anyone types.

    The operator walks in with a site. It must already look made for this
    business — a version that opens on "no site yet", or on the same default
    theme every trade gets, is worse than nothing because it says the tool did
    not look.

    Every stage in one call, for scripts and tests. The workspace drives the
    stages one at a time so it can say which one is running; this is the same
    work in the same order.

    Idempotent: a lead that already has a version keeps it. Opening the
    workspace twice is not a request to rebuild.
    """
    history = sites.versions(conn, lead_id)
    if history:
        return IterationResult(lead_id=lead_id, spec={},
                               version=history[0]["version"], unchanged=True)
    page: dict = {}
    try:
        for stage in STAGES:
            page = run_stage(conn, lead_id, stage, actor=actor)
    except BuildFailed as failure:
        if failure.stage == "photographs":
            material = material_from_brief(
                leads.brief_with_overrides(conn, lead_id))
            return IterationResult(
                lead_id=lead_id, spec={}, kind="needs_labels", unchanged=True,
                unsupported=photos.unreviewed(conn, lead_id,
                                              list(material.images)))
        raise
    stored = sites.recall_stage(conn, lead_id, "direction") or {}
    config = dict(stored.get("config") or {})
    return IterationResult(
        lead_id=lead_id, spec=config, version=page.get("version"),
        rejected=bool(page.get("rejected")),
        findings=list(page.get("findings") or []),
        defects=list(page.get("defects") or []),
        understood=list(config.get("understood") or []),
        rationale=str(config.get("rationale") or ""),
        read_by=str(config.get("read_by") or "trade table"))


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

    # What this site actually decided, for the next one to differ from. Written
    # after the gate rather than before it, so the history is what shipped.
    from app.site import fingerprint as fp

    fingerprints.remember(conn, lead_id, version, fp.metric_version(),
                          dict(fp.of(resolved, spec,
                                     material_from_brief(brief)).values))

    # The workspace opens on what was decided and why, not on an empty box —
    # a designer handing over work rather than a tool waiting for input. This
    # is model prose, and it is allowed here because it reaches the operator
    # and never the page: `messages` is a different table on a different code
    # path, and `render` cannot see it.
    if rationale and not messages.opened(conn, lead_id):
        messages.add(conn, lead_id, "assistant", rationale, version=version)
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
