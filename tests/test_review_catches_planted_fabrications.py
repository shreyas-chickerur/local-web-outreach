"""The claim checks against pages with fabrications planted in them on purpose.

`tests/fixtures/seam/` holds foreign pages (markup nothing in this repository
wrote) with one invented claim per class planted among the business's real
material: a founding year, a credential, a review count, an award, a ranking,
a paraphrase that inflates. Each page's manifest names the sentence and why it
is false. Built to test the old generator's gates, it is the harder test of the
current checks: a page from Claude Design is exactly such foreign markup.

The old gates missed twelve of these. The current checks flag every one: a
planted sentence may be unsourced, assembled or contradicted, never
corroborated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.review import checks
from app.review.run import findings, page_text

pytestmark = pytest.mark.unit

SEAM = Path("tests/fixtures/seam")


def _plantings() -> list[tuple[str, str, str]]:
    out = []
    for manifest in sorted(SEAM.glob("*.manifest.json")):
        planted = json.loads(manifest.read_text())
        for entry in planted["plantings"]:
            out.append((manifest.name, str(entry["class"]), entry["sentence"]))
    return out


def _judged(manifest_name: str) -> list[dict]:
    manifest = json.loads((SEAM / manifest_name).read_text())
    brief = json.loads(Path(manifest["brief"]).read_text())
    page = Path(manifest["source_page"]).read_text()
    return [r for r in findings(page, brief, page_text(brief)) if r["stage"] == "claim"]


@pytest.mark.parametrize("manifest_name,class_num,sentence", _plantings(),
                         ids=lambda v: v if len(str(v)) < 12 else None)
def test_every_planted_fabrication_is_flagged_never_corroborated(
        manifest_name, class_num, sentence):
    """A claim invented for the page that comes back corroborated is the one
    failure the final gate exists to prevent: it would reach an owner as a fact."""
    wanted = checks._fold(sentence)[:40]
    verdicts = [r["verdict"] for r in _judged(manifest_name)
                if wanted in checks._fold(r["quote"]) or checks._fold(r["quote"])[:40] in wanted]
    assert verdicts, f"class {class_num} was not found on the page at all: {sentence!r}"
    assert "corroborated" not in verdicts, (class_num, sentence, verdicts)


@pytest.mark.parametrize("business", ["hvac", "restaurant-casual"])
def test_a_page_made_only_of_their_own_words_raises_no_false_alarm(business):
    """A checker that calls the business's own words unsourced teaches the
    reviewer to stop reading it. The control pages are real material only.
    (Leaving out a verified fact, like the hvac page's phone number, is a true
    finding, not a false alarm, and is not what this counts.)"""
    brief = json.loads(Path(f"tests/fixtures/briefs/{business}.json").read_text())
    page = (SEAM / f"{business}-control.html").read_text()
    unsourced = [r["quote"] for r in findings(page, brief, page_text(brief))
                 if r["verdict"] == "unsourced"]
    assert unsourced == []
