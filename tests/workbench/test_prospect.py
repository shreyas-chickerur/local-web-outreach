"""The prospect score.

The score exists to answer "who should I walk into today?", which is a
different question from "how sure are we about this data". These tests pin the
cases where the two get confused, and the ones where a signal would be a lie.
"""

from __future__ import annotations

import pytest

from app.workbench.prospect import Prospect, rank, score

pytestmark = pytest.mark.unit


def _p(name: str = "Test Co", **kw) -> Prospect:
    return Prospect(name=name, **kw)


def test_no_website_is_the_strongest_signal():
    with_site = score(_p(website="https://x.com", reviews=200, rating=4.8))
    without = score(_p(website=None, reviews=200, rating=4.8))
    assert without.score > with_site.score
    assert any("no website" in r for r in without.reasons)


def test_a_good_site_counts_against_them():
    """The business least likely to hire you is the one whose site already
    works. Without this the score rewarded every large, healthy business."""
    fine = score(_p(website="https://x.com", mobile_ready=True, https=True,
                    site_reachable=True, reviews=500, rating=4.7))
    dated = score(_p(website="https://x.com", mobile_ready=False, https=False,
                     site_reachable=True, reviews=500, rating=4.7))
    assert dated.score > fine.score
    assert any("already responsive" in r for r in fine.reasons)


def test_a_javascript_site_is_not_called_empty():
    """We received a shell, not a page. Scoring that as "publishes almost
    nothing" reports our blind spot as their problem."""
    js = score(_p(website="https://x.com", js_rendered=True, thin_site=True))
    assert not any("publishes almost nothing" in r for r in js.reasons)
    assert any("could not read it" in r for r in js.reasons)
    # And it must not be credited as a good site either.
    assert not any("already responsive" in r for r in js.reasons)


def test_a_chain_is_not_a_prospect():
    chain = score(_p(website=None, is_chain=True, reviews=900))
    solo = score(_p(website=None, is_chain=False, reviews=900))
    assert chain.score < solo.score


def test_a_closed_business_scores_nothing():
    closed = score(_p(website=None, reviews=900, business_status="CLOSED_PERMANENTLY"))
    assert closed.score == 0
    assert any("closed" in r for r in closed.reasons)


def test_every_point_carries_its_reason():
    """The score is a heuristic. If you cannot see why, you cannot disagree."""
    p = score(_p(website=None, reviews=4, phone="(469) 000-0000"))
    assert p.reasons
    for reason in p.reasons:
        assert reason.strip()[0] in "+-0"


def test_ranking_puts_the_best_first_and_breaks_ties_on_size():
    small = _p("small", website=None, reviews=30)
    big = _p("big", website=None, reviews=300)
    ranked = rank([small, big])
    assert [p.name for p in ranked][0] == "big"


def test_the_score_stays_inside_its_range():
    worst = score(_p(website="https://x.com", is_chain=True, reviews=2))
    best = score(_p(website=None, reviews=800, rating=4.9, phone="x"))
    assert 0 <= worst.score <= 100 and 0 <= best.score <= 100
