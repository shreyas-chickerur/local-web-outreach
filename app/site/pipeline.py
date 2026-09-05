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
from app.store import leads, sites


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
            "unchanged": self.unchanged,
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


def iterate(conn: sqlite3.Connection, lead_id: int, sentence: str,
            *, parent_version: int | None = None,
            actor: str | None = None) -> IterationResult:
    """Apply one instruction and store the result, unless it fails the gate."""
    brief = leads.brief_with_overrides(conn, lead_id)
    base = current_config(conn, lead_id, parent_version)
    config = parse_iteration_instruction(sentence, base)
    config["instruction"] = sentence

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
                parent_version=parent_version, unchanged=True)

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
        version=version, parent_version=parent_version)
