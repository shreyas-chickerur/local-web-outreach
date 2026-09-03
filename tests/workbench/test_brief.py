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
    assert phone.confidence.value == "verified"
    assert phone.corroborations == 2


def test_disagreeing_sources_conflict_rather_than_picking_one():
    a = _Dir("google", _place(phone="(469) 294-0067", source_url="https://a/"))
    b = _Dir("yelp", _place(phone="(972) 000-0000", source_url="https://b/"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    phone = next(f for f in brief.facts if f.field == "phone")
    assert phone.confidence.value == "conflict"
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


# ------------------- reading the brief, not just producing it ---------------- #
def test_a_conflict_shows_which_source_said_what():
    """Two values joined by a pipe are unreadable — you cannot tell whether it
    is Google or Yelp claiming the 2.4 rating, which is the whole question."""
    a = _Dir("google", _place(name="Ryno Lawn Care", rating=4.8,
                              source_url="https://maps.google.com/x"))
    b = _Dir("yelp", _place(name="Ryno Lawn Care", rating=2.4,
                            source_url="https://www.yelp.com/biz/x"))
    brief = build_brief("Ryno Lawn Care, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    rating = next(f for f in brief.facts if f.field == "rating")
    assert rating.confidence.value == "conflict"
    by_source = {c["source_url"]: c["value"] for c in rating.candidates}
    assert by_source["https://maps.google.com/x"] == "4.8"
    assert by_source["https://www.yelp.com/biz/x"] == "2.4"

    text = format_brief(brief)
    assert "google: 4.8" in text
    assert "yelp: 2.4" in text


def test_marketing_headlines_are_not_listed_as_services():
    """'What We Do Best' and 'Enjoy a Weed Free Lawn' are copy, not offerings."""
    html = """<html><head><title>Ryno Lawn Care</title></head><body>
      <h2>What We Do Best</h2><h2>Enjoy a Weed Free Lawn</h2>
      <h2>Ryno Lawn Care?</h2><h2>Sustainable Lawn Care</h2>
      <h2>Premium Sod Installation</h2></body></html>"""
    brief = build_brief("rynolawncare.com", fetcher=_Fetcher(html))
    services = brief.published.services
    assert "Sustainable Lawn Care" in services
    assert "Premium Sod Installation" in services
    assert not any(s in services for s in
                   ("What We Do Best", "Enjoy a Weed Free Lawn", "Ryno Lawn Care?"))


def test_the_same_hours_written_twice_appear_once():
    html = """<html><head><title>Ryno Lawn Care</title></head><body>
      <p>Mon-Fri 8am-5pm</p><p>Sat-Sun Closed</p>
      <p>Mon-Fri 8:00am - 5:00pm</p></body></html>"""
    brief = build_brief("rynolawncare.com", fetcher=_Fetcher(html))
    hours = brief.published.hours
    assert len(hours) == 2
    assert any("8:00am" in h for h in hours)     # the fuller spelling is kept


def test_a_match_in_another_town_is_flagged_not_hidden():
    """Matching on name alone picks up the same-named business one town over.
    It may still be the right company — a Plano lawn service covers Frisco —
    but the reader has to be told rather than left to notice the address."""
    elsewhere = _Dir("yelp", _place(name="Craftway Kitchen",
                                    address="1 Main St, Plano, TX 75025",
                                    phone="(903) 456-9799"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[elsewhere],
                        fetcher=_Fetcher(ok=False))
    assert any("different town" in a for a in brief.assumptions)
    # the data is still used — being in the next town is not disqualifying
    assert any(f.field == "phone" for f in brief.facts)


def test_a_match_in_the_same_town_is_not_flagged():
    local = _Dir("yelp", _place(name="Craftway Kitchen",
                                address="5729 Lebanon Rd, Frisco, TX 75034",
                                phone="(469) 294-0067"))
    brief = build_brief("Craftway Kitchen, Frisco, TX", directories=[local],
                        fetcher=_Fetcher(ok=False))
    assert not any("different town" in a for a in brief.assumptions)


@pytest.mark.parametrize("text,town", [
    ("Frisco, TX", "frisco"),
    ("2770 Main St, Frisco, TX 75033", "frisco"),
    ("1 Main St, The Colony, TX 75056", "the colony"),
    ("Frisco", "frisco"),
])
def test_town_is_read_out_of_a_location_or_an_address(text, town):
    from app.workbench.brief import _town_of
    assert _town_of(text) == town


# ------------------------------ chains -------------------------------------- #
def test_several_branches_are_called_a_chain_not_a_disagreement():
    """Sources naming different street addresses are not disagreeing about one
    business — they each picked a different branch. Reporting that as a data
    conflict hides the thing that actually matters: this is not a lead."""
    a = _Dir("google", _place(name="Starbucks", address="3193 Main St, Frisco, TX 75034"))
    b = _Dir("yelp", _place(name="Starbucks", address="7135 Preston Rd, Frisco, TX 75034",
                            source_url="https://yelp.com/x"))
    brief = build_brief("Starbucks, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    assert brief.looks_like_a_chain
    assert any("different street addresses" in s for s in brief.chain_signals)
    assert "MULTIPLE LOCATIONS" in format_brief(brief)


def test_a_store_locator_url_marks_a_chain():
    google = _Dir("google", _place(
        name="Starbucks", website="https://www.starbucks.com/store-locator/store/12496/"))
    brief = build_brief("Starbucks, Frisco, TX", directories=[google],
                        fetcher=_Fetcher(ok=False))
    assert any("store locator" in s for s in brief.chain_signals)


def test_one_location_is_not_a_chain():
    a = _Dir("google", _place(name="Hutchins BBQ",
                              address="9225 Preston Rd, Frisco, TX 75033"))
    b = _Dir("yelp", _place(name="Hutchins BBQ",
                            address="9225 Preston Rd, Frisco, TX 75033",
                            source_url="https://yelp.com/x"))
    brief = build_brief("Hutchins BBQ, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    assert not brief.looks_like_a_chain
    assert "MULTIPLE LOCATIONS" not in format_brief(brief)


def test_the_same_address_written_two_ways_is_not_a_chain():
    """A formatting difference must never read as two branches."""
    a = _Dir("google", _place(name="Hutchins BBQ",
                              address="9225 Preston Rd, Frisco, TX 75033, USA"))
    b = _Dir("yelp", _place(name="Hutchins BBQ",
                            address="9225 Preston Road, Frisco, Texas, 75033",
                            source_url="https://yelp.com/x"))
    brief = build_brief("Hutchins BBQ, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))
    assert not brief.looks_like_a_chain


def test_a_locations_menu_marks_multiple_branches():
    """A three-city restaurant group went unflagged because its nav is a
    LOCATIONS dropdown with no /locations URL behind it."""
    html = """<html><head><title>CraftWay Kitchen</title></head><body>
      <nav><a href="/">Home</a><a href="#loc">LOCATIONS</a></nav>
      <h2>Weekend Brunch</h2></body></html>"""
    brief = build_brief("craftwaykitchen.com", fetcher=_Fetcher(html))
    assert brief.looks_like_a_chain
    assert any("locations page" in s for s in brief.chain_signals)


def test_branch_names_are_not_listed_as_services():
    """On a site with a locations menu, 'Plano' is a branch, not an offering."""
    html = """<html><head><title>CraftWay Kitchen</title></head><body>
      <nav><a href="/locations">Locations</a></nav>
      <h2>Plano</h2><h2>Southlake</h2><h2>Weekend Brunch</h2></body></html>"""
    brief = build_brief("craftwaykitchen.com", fetcher=_Fetcher(html))
    services = brief.published.services
    assert "Weekend Brunch" in services
    assert "Plano" not in services and "Southlake" not in services


@pytest.mark.parametrize("junk", [
    "Skip to content MENU", "LOCATIONS PLANO", "GIFT CARDS", "We're Social Too",
    "Donations", "Hutchins Barbeque Texas Shape Tee – Rust", "Merchandise",
])
def test_navigation_and_merchandise_are_not_services(junk):
    """Every one of these appeared in a real brief's services line."""
    from app.workbench.extract import _clean_service
    assert _clean_service(junk) is None
