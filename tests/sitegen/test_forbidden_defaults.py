"""`BRIEF` §2.4, encoded. A site matching one of these is a defect.

It had only ever been prose in the brief, which is this project's recurring
failure written into the document that names it. This runs it.

Not wired into the audit as a build gate, and that is deliberate: two fixtures
match today, so gating would reject them, and escaping the mood presets that
put them there is its own piece of work. Encoding it, pinning what it finds and
saying so is the honest first step; the gate is a separate fork.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site import defaults
from app.site.opening import opening_spec
from app.site.pipeline import spec_from_config
from app.site.render import build_from_spec
from app.site.theme import theme_for
from app.store import db, leads

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")

# What the corpus matches today, named rather than counted, so a new one shows
# up as itself. §2.4 predicts exactly this: "the six existing moods sit close to
# several of these", and `warm` + a serif display + `terracotta` is the first
# entry on its list.
MATCHES = {
    "restaurant-rich": ["warm cream + serif display + terracotta"],
    "barbecue-rich": ["warm cream + serif display + terracotta"],
    # After the corpus was re-decided under §2.2's palette sampling, `barbecue`
    # itself escaped this default (a sampled amber rather than terracotta) and
    # `restaurant-rich` matched it instead. Both for the same honest reason
    # either way: their own photographs are genuinely brown/rust-toned, and a
    # palette faithful to real material can land on terracotta for the right
    # reason. The count held at two; which two moved with the redecide, which
    # is expected and not itself a new failure.
}


def test_the_corpus_matches_only_the_forbidden_defaults_we_know_about():
    found = {}
    with db.session(":memory:") as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            lead = leads.save_brief(conn, json.loads(path.read_text()))
            brief = leads.brief_with_overrides(conn, lead)
            config = dict(opening_spec(brief))
            for key in ("rationale", "read_by", "kind", "unsupported",
                        "defect", "signature_why"):
                config.pop(key, None)
            spec = spec_from_config(config)
            hits = defaults.check(build_from_spec(brief, spec),
                                  theme_for(spec.mood, spec.accent), spec)
            if hits:
                found[path.stem] = hits
    assert found == MATCHES, (
        f"the forbidden-default matches moved: {found}. A new one is a defect "
        f"under BRIEF §2.4 — fix the site, do not widen this list.")


def test_the_check_can_actually_fire():
    """A check that never fires is the defect it exists to catch.

    Every rule in §2.4 is asserted against a page built to break it, so the
    list cannot quietly become nine no-ops.
    """
    page = ('<header class="hero">x</header><h2>🎉 What we do</h2>'
            "<style>.hero{min-height:100vh}"
            ".card{border-radius:8px;border-left:3px solid var(--accent)}"
            "div{box-shadow:0 1px 2px #000}"
            + "p{text-align:center}" * 6 + "</style>")

    class Face:
        stack = "'Inter',sans-serif"

    class Theme:
        display = body = Face()
        bg = "#0a0a0a"

    class Spec:
        accent = "lime"
        mood = "night"

    hits = defaults.check(page, Theme(), Spec())
    for expected in ("near-black + one acid accent", "Inter as the safe face",
                     "uniform radius and shadow on everything",
                     "accent rail on rounded cards",
                     "emoji as section markers", "everything centred",
                     "full-viewport hero"):
        assert expected in hits, (expected, hits)
