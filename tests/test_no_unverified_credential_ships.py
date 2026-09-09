"""BRIEF §4's first invariant, held across the whole corpus: no rendered page
asserts a credential — licensed, insured, bonded, certified, accredited,
registered, admitted to the bar — that the business's own published material
does not corroborate.

`render.unsupported()` already enforces this per-build and rejects a version
that fails it (`app/site/pipeline.py`). What was missing was the pattern it
checks against: `app.core.claims.CLAIM_RE` had no entry for credential
language at all, so `signature.py`'s `stamp` device could print "Licensed &
insured" on any `trade`-kind business, whether or not it was true, and
nothing caught it. Found shipping uncorroborated on six of nineteen
fixtures — `hvac-rich`, `hvac-second`, `law-rich`, `law`, `roofer-rich`,
`threadbare` — the worst being `threadbare`, which has no about text, no
content blocks and one photograph, asserting a licence four times anyway.
See `.reviews/slice-c-credential-claims.md`.

This is the standing version: not a test that those six strings are gone,
but a test that holds the invariant itself, so a future device, section or
heading that prints an uncorroborated credential fails here regardless of
what it's called or how it's built.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")


def test_no_fixture_asserts_a_credential_its_own_material_does_not_back():
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec, material_from_brief, unsupported
    from app.store import db, leads, sites

    offenders: dict[str, list[str]] = {}
    with db.session(":memory:") as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            lead = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead, stage)
            brief = leads.brief_with_overrides(conn, lead)
            stored = sites.recall_stage(conn, lead, "direction") or {}
            config = dict(stored.get("config") or {})
            assert config.get("read_by") == "frozen", (
                f"{path.stem} did not replay a frozen direction")
            spec = spec_from_config(config)
            page = build_from_spec(brief, spec)
            material = material_from_brief(brief)
            findings = unsupported(page, material)
            if findings:
                offenders[path.stem] = findings

    assert not offenders, (
        f"these fixtures assert a claim their own material does not back: "
        f"{offenders}")
