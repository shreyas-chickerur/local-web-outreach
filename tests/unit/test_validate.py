"""Adversarial re-validation: catch stale facts and stale pitches before sending."""

from __future__ import annotations

import pytest

from app.adapters.directory import DirectoryPlace
from app.adapters.site_fetch import FetchResult
from app.core.enums import ClaimStatus, Severity
from app.models.research_claim import ResearchClaim
from app.models.site_weakness import SiteWeakness
from app.stages.validate import (
    check_claims_against_live_sources,
    check_weaknesses_are_real,
)

pytestmark = pytest.mark.unit


class _Biz:
    id = "b1"
    name, location = "Camero's Lawncare", "Frisco, TX"
    existing_site_url = "http://cameroslawncare.com/"
    contact_email = None


class _Dir:
    name = "test"

    def __init__(self, place):
        self._p = place

    def lookup(self, name, location):  # noqa: ARG002
        return self._p


class _Fetcher:
    def __init__(self, ok=True, final_url="http://x/", html=""):
        self._r = FetchResult(ok=ok, status=200 if ok else None, final_url=final_url,
                              html=html, elapsed_ms=5, error=None)

    def fetch(self, url):  # noqa: ARG002
        return self._r


def _claim(field, value):
    return ResearchClaim(business_id="b1", field=field, value=value,
                         status=ClaimStatus.VERIFIED, confidence=0.9,
                         corroborations=2, sources=[])


def _place(**kw):
    base = dict(name="Camero's", address=None, phone=None, website=None,
                source_url="https://yelp.com/x")
    base.update(kw)
    return DirectoryPlace(**base)


# ----------------------------- stored vs live ------------------------------ #
def test_matching_phone_passes():
    out = check_claims_against_live_sources(
        _Biz(), [_claim("phone", "(469) 920-1802")],
        [_Dir(_place(phone="469-920-1802"))])
    assert [f.level for f in out] == ["ok"]


def test_changed_phone_fails():
    out = check_claims_against_live_sources(
        _Biz(), [_claim("phone", "(469) 920-1802")],
        [_Dir(_place(phone="(972) 000-0000"))])
    assert out[0].level == "fail"


def test_rating_drift_inside_tolerance_passes():
    out = check_claims_against_live_sources(
        _Biz(), [_claim("rating", "4.7")], [_Dir(_place(rating=5.0))])
    assert out[0].level == "ok"


def test_rating_drift_outside_tolerance_fails():
    out = check_claims_against_live_sources(
        _Biz(), [_claim("rating", "4.7")], [_Dir(_place(rating=3.2))])
    assert out[0].level == "fail"


def test_unreachable_directory_warns_rather_than_failing():
    """Not being able to re-check is not the same as being wrong."""
    out = check_claims_against_live_sources(
        _Biz(), [_claim("phone", "(469) 920-1802")], [_Dir(None)])
    assert out[0].level == "warn"


def test_no_verified_facts_warns():
    out = check_claims_against_live_sources(_Biz(), [], [_Dir(None)])
    assert out[0].level == "warn" and out[0].check == "verified-facts"


# --------------------------- is the pitch still true? ----------------------- #
def _weak(issue):
    return SiteWeakness(business_id="b1", issue=issue, severity=Severity.HIGH, evidence="x")


def test_no_https_pitch_still_true():
    out = check_weaknesses_are_real(_Biz(), [_weak("no_https")],
                                    _Fetcher(final_url="http://cameroslawncare.com/"))
    assert out[0].level == "ok"


def test_no_https_pitch_goes_stale_when_they_fix_it():
    """They added HTTPS since we drafted — emailing that claim would be wrong."""
    out = check_weaknesses_are_real(_Biz(), [_weak("no_https")],
                                    _Fetcher(final_url="https://cameroslawncare.com/"))
    assert out[0].level == "fail"
    assert "stale" in out[0].detail


def test_down_site_pitch_goes_stale_when_it_comes_back_up():
    out = check_weaknesses_are_real(_Biz(), [_weak("site_unreachable")], _Fetcher(ok=True))
    assert out[0].level == "fail"


def test_down_site_still_down_passes():
    out = check_weaknesses_are_real(_Biz(), [_weak("site_unreachable")], _Fetcher(ok=False))
    assert out[0].level == "ok"


def test_mobile_pitch_goes_stale_when_a_viewport_appears():
    html = '<head><meta name="viewport" content="width=device-width"></head>'
    out = check_weaknesses_are_real(_Biz(), [_weak("not_mobile_responsive")],
                                    _Fetcher(html=html))
    assert out[0].level == "fail"


# ---------------------- entity match before comparing ----------------------- #
def test_a_directory_hit_for_a_different_business_is_ignored():
    """Real case: two Frisco roofers both 'matched' one unrelated Yelp listing,
    whose phone then looked like proof our stored phone was wrong."""
    out = check_claims_against_live_sources(
        _Biz(), [_claim("phone", "(469) 920-1802")],
        [_Dir(_place(name="Totally Different Roofing Co", phone="(972) 994-6386"))])
    levels = {f.level for f in out}
    assert "fail" not in levels                      # never call it wrong on bad evidence
    assert any(f.check == "entity-match" for f in out)


def test_a_close_name_still_counts_as_the_same_business():
    out = check_claims_against_live_sources(
        _Biz(), [_claim("phone", "(469) 920-1802")],
        [_Dir(_place(name="Camero's Lawncare LLC", phone="(469) 920-1802"))])
    assert [f.level for f in out] == ["ok"]
