"""Slice 1b — a company name or URL becomes a brief you can walk in with."""

from __future__ import annotations

import pytest

from app.adapters.directory import DirectoryPlace
from app.adapters.site_fetch import FetchResult
from app.workbench.brief import build_brief, format_brief

pytestmark = pytest.mark.unit

_SITE = """
<html><head><title>Home | Craftway Kitchen | Frisco TX</title>
<meta name="description" content="A neighborhood scratch kitchen in Frisco.">
</head><body>
<h2>Weekend Brunch</h2>
<ul><li>Short Rib $32 braised eight hours</li><li>Gulf Snapper $28</li></ul>
<p>Monday - Friday: 11am - 9pm</p>
<a href="https://www.instagram.com/craftway">Instagram</a>
<img src="/img/dining.jpg">
</body></html>
"""


class _Dir:
    def __init__(self, name, place):
        self.name = name
        self._place = place

    def lookup(self, name, location):  # noqa: ARG002
        return self._place


class _Fetcher:
    def __init__(self, html=_SITE, ok=True):
        self._html, self._ok = html, ok
        self.fetched: list[str] = []

    def fetch(self, url):
        self.fetched.append(url)
        return FetchResult(ok=self._ok, status=200 if self._ok else None,
                           final_url=url, html=self._html if self._ok else "",
                           elapsed_ms=5, error=None)


def _place(**kw):
    base = dict(name="Craftway Kitchen", address=None, phone=None, website=None,
                source_url="https://src.example/x")
    base.update(kw)
    return DirectoryPlace(**base)


# ------------------------------ the URL path -------------------------------- #
def test_a_url_is_read_directly_and_names_itself_from_the_page_title():
    brief = build_brief("craftwaykitchen.com", fetcher=_Fetcher())
    assert brief.name == "Craftway Kitchen"        # not "Craftwaykitchen"
    assert brief.website_url == "https://craftwaykitchen.com"
    assert brief.site_reachable is True
    assert any("page title" in a for a in brief.assumptions)


def test_the_site_is_read_before_directories_are_searched():
    """A lookup keyed on a name guessed from a domain matches nothing. Reading
    their page title first is what makes the directory search work at all."""
    seen: list[str] = []

    class _Recorder:
        name = "google"

        def lookup(self, name, location):  # noqa: ARG002
            seen.append(name)
            return None

    build_brief("craftwaykitchen.com", directories=[_Recorder()], fetcher=_Fetcher())
    assert seen == ["Craftway Kitchen"]


def test_their_published_content_is_captured():
    brief = build_brief("craftwaykitchen.com", fetcher=_Fetcher())
    pub = brief.published
    assert pub is not None
    assert "scratch kitchen" in (pub.description or "")
    assert any(i["name"] == "Short Rib" for i in pub.menu_items)
    assert pub.hours and "Monday" in pub.hours[0]
    assert {s["name"] for s in pub.socials} == {"Instagram"}


def test_an_unreachable_site_is_reported_not_hidden():
    brief = build_brief("dead-site.example", fetcher=_Fetcher(ok=False))
    assert brief.site_reachable is False
    assert brief.published is None


# ------------------------------ the name path ------------------------------- #
def test_a_name_lookup_finds_the_website():
    google = _Dir("google", _place(address="1 Main St, Frisco, TX",
                                   phone="(469) 294-0067",
                                   website="https://craftwaykitchen.com"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[google],
                        fetcher=_Fetcher())
    assert brief.website_url == "https://craftwaykitchen.com"
    assert any("website found via google" in a for a in brief.assumptions)
    assert brief.published is not None      # the discovered site is then read


def test_two_agreeing_sources_verify_a_fact():
    a = _Dir("google", _place(phone="(469) 294-0067",
                              source_url="https://maps.google/x"))
    b = _Dir("yelp", _place(phone="469-294-0067", source_url="https://yelp.com/x"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    phone = next(f for f in brief.facts if f.field == "phone")
    assert phone.status.value == "verified"
    assert phone.corroborations == 2


def test_disagreeing_sources_conflict_rather_than_picking_one():
    a = _Dir("google", _place(phone="(469) 294-0067", source_url="https://a/"))
    b = _Dir("yelp", _place(phone="(972) 000-0000", source_url="https://b/"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    phone = next(f for f in brief.facts if f.field == "phone")
    assert phone.status.value == "conflict"
    assert "469" in phone.value and "972" in phone.value


def test_a_directory_hit_for_a_different_business_is_refused():
    wrong = _Dir("yelp", _place(name="Totally Different Diner",
                                phone="(972) 111-1111"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[wrong],
                        fetcher=_Fetcher(ok=False))
    assert brief.facts == []
    assert any("different business" in a for a in brief.assumptions)


def test_no_website_anywhere_becomes_an_open_question():
    brief = build_brief("Ghost Business, Frisco, TX",
                        directories=[_Dir("yelp", None)], fetcher=_Fetcher())
    assert brief.website_url is None
    assert any("No website found" in q for q in brief.open_questions)


def test_notes_are_carried_through():
    brief = build_brief("Craftway Kitchen, Frisco, TX", notes="owner is Allison",
                        fetcher=_Fetcher(ok=False))
    assert brief.notes == "owner is Allison"
    assert "owner is Allison" in format_brief(brief)


def test_gaps_become_questions_to_ask_in_person():
    brief = build_brief("Craftway Kitchen, Frisco, TX", fetcher=_Fetcher(ok=False))
    asked = " ".join(brief.open_questions).lower()
    assert "address" in asked and "call" in asked


def test_format_brief_shows_confidence_and_sources():
    a = _Dir("google", _place(phone="(469) 294-0067", source_url="https://maps.google/x"))
    b = _Dir("yelp", _place(phone="(469) 294-0067", source_url="https://yelp.com/x"))
    text = format_brief(build_brief("Craftway Kitchen, Frisco, TX",
                                    directories=[a, b], fetcher=_Fetcher(ok=False)))
    assert "verified" in text and "90%" in text
    assert "maps.google" in text and "yelp.com" in text
