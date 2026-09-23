"""Slice 1b — a company name or URL becomes a brief you can walk in with."""

from __future__ import annotations

import pytest

from app.adapters.directory import DirectoryPlace
from app.adapters.site_fetch import FetchResult
from app.workbench.brief import build_brief, format_brief, site_state
from app.workbench.types import Confidence

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


_PDF_MENU_SITE = """
<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head><body>
<a href="/menu.pdf">Dinner Menu</a>
</body></html>
"""


def _pdf_bytes(text: str) -> bytes:
    stream = text.encode()
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>"
        b"/MediaBox[0 0 400 200]/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length " + str(len(stream)).encode() + b">>\nstream\n"
        + stream + b"\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF")


def test_a_menu_pdf_is_read_not_just_linked(monkeypatch):
    """Cause 1 of "thicken the brief": a PDF used to be found (`menu_media`)
    but never read. Its own text now reaches `menu_items` the same way an
    HTML page's would."""
    import app.workbench.brief as brief_module

    data = _pdf_bytes("BT /F1 18 Tf 20 100 Td (Short Rib $32) Tj ET")
    monkeypatch.setattr(brief_module, "download", lambda url, timeout=15.0: (data, ""))
    brief = build_brief("craftwaykitchen.com", fetcher=_Fetcher(_PDF_MENU_SITE))
    pub = brief.published
    assert pub is not None
    assert any(i["name"] == "Short Rib" for i in pub.menu_items)
    assert pub.menu_media and pub.menu_media[0]["readable"] is True


class _MultiPageFetcher:
    """A different page's HTML per URL — the plain `_Fetcher` always
    returns the same page, which cannot exercise a real multi-level
    crawl."""

    def __init__(self, pages: dict[str, str]):
        self._pages = pages
        self.fetched: list[str] = []

    def fetch(self, url):
        self.fetched.append(url)
        html = self._pages.get(url)
        return FetchResult(ok=html is not None, status=200 if html else 404,
                           final_url=url, html=html or "", elapsed_ms=5)


def test_a_page_linked_only_from_a_depth_one_page_is_still_reached():
    """Cause 3: the crawl used to be one level deep, so anything linked
    only from a SECOND page (never the homepage itself) was invisible —
    exactly the shape of a real restaurant's site, where the homepage
    links "Our Philosophy" and the philosophy page is the one that links
    the actual story."""
    home = ('<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head>'
           '<body><a href="/philosophy/">Our Philosophy</a></body></html>')
    philosophy = ('<html><body>'
                  '<h2>Our Roots</h2>'
                  '<p>Started in 1994, this family has served Blackland '
                  'Prairie cuisine for three generations, sourcing every '
                  'ingredient from farms within an hour of the kitchen.</p>'
                  '<a href="/chefs-tasting-menu/">Chef&#8217;s Tasting Menu</a>'
                  '</body></html>')
    tasting = ('<html><body>'
              '<h2>Chef&#8217;s Tasting Menu</h2>'
              '<p>A seven-course paired dinner built around whatever the '
              'farms send us that week, curated fresh every single week.</p>'
              '</body></html>')
    brief = build_brief("craftwaykitchen.com", fetcher=_MultiPageFetcher({
        "https://craftwaykitchen.com/": home,
        "https://craftwaykitchen.com/philosophy/": philosophy,
        "https://craftwaykitchen.com/chefs-tasting-menu/": tasting,
    }))
    pub = brief.published
    assert pub is not None
    headings = {b["heading"] for b in pub.blocks}
    assert "Our Roots" in headings
    # The tasting-menu page is TWO levels from the homepage (homepage ->
    # philosophy -> tasting menu) — only reachable at all if the crawl
    # itself goes two levels deep, not one.
    assert "Chef’s Tasting Menu" in headings


def test_on_progress_is_told_about_each_page_the_crawl_reads():
    """The crawl is the slow part — real page fetches, one at a time — and
    a caller with no visibility into it sees nothing at all for however
    long that takes. `on_progress` is optional and additive: every
    existing caller that omits it (every test above this one) behaves
    exactly as before."""
    home = ('<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head>'
           '<body><a href="/philosophy/">Our Philosophy</a></body></html>')
    philosophy = ('<html><body><h2>Our Roots</h2><p>' + 'word ' * 20 + '</p>'
                 '</body></html>')
    seen: list[str] = []
    build_brief("craftwaykitchen.com", fetcher=_MultiPageFetcher({
        "https://craftwaykitchen.com/": home,
        "https://craftwaykitchen.com/philosophy/": philosophy,
    }), on_progress=seen.append)
    assert any("reading their website" in m for m in seen)
    assert any("homepage" in m for m in seen)
    assert any("philosophy" in m for m in seen)


def test_the_crawl_never_leaves_the_page_budget(monkeypatch):
    """A large site's real link graph must not turn "read their content"
    into "crawl the whole site" — the page budget caps total fetches
    regardless of how many same-host links exist."""
    import app.workbench.brief as brief_module
    monkeypatch.setattr(brief_module, "CRAWL_PAGE_BUDGET", 3)

    home = "<html><body>" + "".join(
        f'<a href="/page-{i}/">p{i}</a>' for i in range(50)) + "</body></html>"
    fetcher = _MultiPageFetcher({f"https://craftwaykitchen.com/page-{i}/":
                                 "<html><body>x</body></html>" for i in range(50)})
    fetcher._pages["https://craftwaykitchen.com/"] = home
    build_brief("craftwaykitchen.com", fetcher=fetcher)
    crawled = [u for u in fetcher.fetched if "/page-" in u]
    assert len(crawled) <= 3


def test_an_unreadable_menu_pdf_is_disclosed_not_silent(monkeypatch):
    """A stale link (the PDF now 404s, or is a scan with no text layer)
    must not read as "this business has no menu" — `readable: False`
    says plainly that a PDF was found and could not be read."""
    import app.workbench.brief as brief_module

    monkeypatch.setattr(brief_module, "download",
                        lambda url, timeout=15.0: (None, "could not download"))
    brief = build_brief("craftwaykitchen.com", fetcher=_Fetcher(_PDF_MENU_SITE))
    pub = brief.published
    assert pub is not None
    assert pub.menu_items == []
    assert pub.menu_media and pub.menu_media[0]["readable"] is False


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
def test_ratings_are_listed_per_platform_not_corroborated():
    """Google's 4.8 and Yelp's 2.4 are not a disagreement to resolve — they
    measure different review populations, so both are reported, with the review
    counts that say how much each one is worth."""
    a = _Dir("google", _place(name="Ryno Lawn Care", rating=4.8,
                              review_count=106,
                              source_url="https://maps.google.com/x"))
    b = _Dir("yelp", _place(name="Ryno Lawn Care", rating=2.4, review_count=9,
                            source_url="https://www.yelp.com/biz/x"))
    brief = build_brief("Ryno Lawn Care, Frisco, TX", directories=[a, b],
                        fetcher=_Fetcher(ok=False))

    assert not [f for f in brief.facts if f.field == "rating"]
    assert [(r["source"], r["value"], r["reviews"]) for r in brief.ratings] == [
        ("google", 4.8, 106), ("yelp", 2.4, 9)]

    text = format_brief(brief)
    assert "4.8" in text and "106 reviews" in text
    assert "2.4" in text and "9 reviews" in text


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
    from app.workbench.resolve import town_of as _town_of
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


def test_town_only_address_does_not_conflict_with_a_street_address():
    """Yelp knew only "Frisco, TX 75035" for Ryno Lawn Care while Google had the
    street. Scoring that as a conflict hid a good address and then asked for the
    address we already had."""
    google = _Dir("google", DirectoryPlace(
        name="Ryno Lawn Care", address="2770 Main St #155, Frisco, TX 75033",
        phone="(469) 496-2778", website=None,
        source_url="https://maps.google.com/x"))
    yelp = _Dir("yelp", DirectoryPlace(
        name="Ryno Lawn Care", address="Frisco, TX 75035", phone=None,
        website=None, source_url="https://yelp.com/biz/ryno"))
    brief = build_brief("Ryno Lawn Care", location="Frisco, TX",
                        directories=[google, yelp], fetcher=_Fetcher(ok=False))

    address = next(f for f in brief.facts if f.field == "address")
    assert address.confidence is not Confidence.CONFLICT
    assert address.value.startswith("2770 Main St")
    assert any("only a town" in a for a in brief.assumptions)


def test_header_shows_the_address_found_not_the_town_typed_in():
    """Looking the same business up by name and by URL printed different
    headers, because the typed location won over the address we established."""
    google = _Dir("google", DirectoryPlace(
        name="Craftway Kitchen", address="5729 Lebanon Rd #100, Frisco, TX 75034",
        phone="(469) 294-0067", website=None,
        source_url="https://maps.google.com/x"))
    brief = build_brief("Craftway Kitchen", location="Frisco, TX",
                        directories=[google], fetcher=_Fetcher(ok=False))
    assert "5729 Lebanon Rd #100" in format_brief(brief).splitlines()[1]


def test_a_single_source_value_is_offered_for_confirmation():
    """Printing an address and then asking "what is their street address?"
    wastes the visit; ask them to confirm the one we have."""
    yelp = _Dir("yelp", DirectoryPlace(
        name="JS Lawn Care", address="Plano, TX 75025", phone=None,
        website=None, source_url="https://yelp.com/biz/js"))
    brief = build_brief("JS Lawn Care", location="Plano, TX",
                        directories=[yelp], fetcher=_Fetcher(ok=False))
    assert any("confirm Plano, TX 75025" in q for q in brief.open_questions)


def test_being_refused_is_not_being_broken():
    """Home Depot answers our reader with a 403 from its bot protection while
    the page loads fine in a browser. Reporting that as "not loading" tells the
    reader something false about the business."""
    assert site_state(403, ok=False) == "blocked"
    assert site_state(429, ok=False) == "blocked"
    assert site_state(500, ok=False) == "error"
    assert site_state(None, ok=False) == "unreachable"
    assert site_state(200, ok=True) == "ok"


def test_a_chain_is_flagged_even_when_its_site_blocks_us():
    """Chain detection used to depend on reading their website — exactly what a
    national chain's bot protection prevents. The directory already knows."""
    google = _Dir("google", _place(name="The Home Depot",
                                   address="4600 State Hwy 121, Plano, TX",
                                   source_url="https://maps.google.com/x",
                                   same_name_nearby=4))
    brief = build_brief("Home Depot", location="Plano, TX",
                        directories=[google], fetcher=_Fetcher(ok=False))
    assert brief.looks_like_a_chain
    assert any("4 locations" in s for s in brief.chain_signals)


def test_the_working_spelling_is_read_and_the_fault_is_kept():
    class _CertFetcher:
        """Fails TLS on www, serves the site on the apex — like the real one."""

        def __init__(self):
            self.tried: list[str] = []

        def fetch(self, url):
            self.tried.append(url)
            if "www." in url and url.startswith("https"):
                return FetchResult(ok=False, status=None, final_url=None, html="",
                                   elapsed_ms=1, error="CERTIFICATE_VERIFY_FAILED",
                                   tls_error=True)
            return FetchResult(ok=True, status=200, final_url=url,
                               html="<html><h2>Dinner Service</h2></html>",
                               elapsed_ms=1)

    fetcher = _CertFetcher()
    google = _Dir("google", _place(name="Yama Izakaya", address="1 Main St, Plano, TX",
                                   website="https://www.yama.example/",
                                   source_url="https://maps.google.com/x"))
    brief = build_brief("Yama Izakaya", location="Plano, TX", directories=[google],
                        fetcher=fetcher)

    assert brief.site_status == "insecure"
    # It did not give up: the site was read at the address that works.
    assert any("www." not in u for u in fetcher.tried)
    assert brief.published is not None
    assert "certificate" in format_brief(brief).lower()


# ------------------------- the text the crawl read -------------------------- #
class _FailingFetcher(_MultiPageFetcher):
    """Pages it has serve normally; a URL listed in `errors` fails the way a
    real fetch does when it never gets a response — no status, an error."""

    def __init__(self, pages: dict[str, str], errors: dict[str, str]):
        super().__init__(pages)
        self._errors = errors

    def fetch(self, url):
        if url in self._errors:
            self.fetched.append(url)
            return FetchResult(ok=False, status=None, final_url=url, html="",
                               elapsed_ms=5, error=self._errors[url])
        return super().fetch(url)


def _pages(brief) -> list[dict]:
    # Through the serializer, not off the dataclass: `brief_to_dict` copies
    # only the keys it names, so a field that never reaches it never reaches
    # the archive or the database either.
    from app.web.serialize import brief_to_dict
    return brief_to_dict(brief)["pages"]


def test_every_page_the_crawl_reads_keeps_its_text():
    """The crawl read the business's own pages and kept only the fields it
    extracted. The claim checks then had nothing of the business's own words
    to search, and fell back on a hand-made copy two weeks out of date."""
    home = ('<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head>'
            '<body><p>Scratch kitchen on Main Street.</p>'
            '<a href="/wine/">Wine</a></body></html>')
    wine = ('<html><body><h2>Wine</h2><p>Cabernet Sauvignon, Napa Valley</p>'
            '<a href="/story/">Our story</a></body></html>')
    story = '<html><body><p>Opened in 2013 by two sisters.</p></body></html>'
    pages = _pages(build_brief("craftwaykitchen.com", fetcher=_MultiPageFetcher({
        "https://craftwaykitchen.com/": home,
        "https://craftwaykitchen.com/wine/": wine,
        "https://craftwaykitchen.com/story/": story,
    })))
    assert [p["url"] for p in pages] == [
        "https://craftwaykitchen.com/",
        "https://craftwaykitchen.com/wine/",
        "https://craftwaykitchen.com/story/",
    ]
    assert all(p["read"] and p["kind"] == "page" and p["reason"] == "" for p in pages)
    assert "Scratch kitchen on Main Street." in pages[0]["text"]
    assert "Cabernet Sauvignon, Napa Valley" in pages[1]["text"]
    assert "Opened in 2013" in pages[2]["text"]
    assert "<p>" not in pages[1]["text"]


def test_a_page_that_fails_is_kept_with_its_reason():
    """A page skipped on failure vanished, and "we never saw it" read exactly
    like "the site does not say so" to everything downstream."""
    home = ('<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head>'
            '<body><a href="/gone/">Old menu</a><a href="/slow/">Events</a>'
            '</body></html>')
    pages = _pages(build_brief("craftwaykitchen.com", fetcher=_FailingFetcher(
        {"https://craftwaykitchen.com/": home},
        {"https://craftwaykitchen.com/slow/": "timed out"})))
    by_url = {p["url"]: p for p in pages}
    gone = by_url["https://craftwaykitchen.com/gone/"]
    slow = by_url["https://craftwaykitchen.com/slow/"]
    assert (gone["read"], gone["reason"], gone["text"]) == (False, "status 404", "")
    assert (slow["read"], slow["reason"]) == (False, "timed out")


def test_a_site_that_cannot_be_reached_still_says_why():
    """The case where the reason matters most is the one where nothing at all
    was read."""
    pages = _pages(build_brief("dead-site.example", fetcher=_Fetcher(ok=False)))
    assert len(pages) == 1
    assert pages[0]["read"] is False
    assert pages[0]["reason"]


def test_a_menu_pdf_keeps_its_text_not_only_its_items(monkeypatch):
    """A PDF's lines were used for menu items and then dropped, so a wine list
    kept as a PDF could never back a claim that named a wine."""
    import app.workbench.brief as brief_module

    data = _pdf_bytes("BT /F1 18 Tf 20 100 Td (Short Rib $32) Tj ET")
    monkeypatch.setattr(brief_module, "download", lambda url, timeout=15.0: (data, ""))
    pdfs = [p for p in _pages(build_brief("craftwaykitchen.com",
                                          fetcher=_Fetcher(_PDF_MENU_SITE)))
            if p["kind"] == "pdf"]
    assert len(pdfs) == 1
    assert pdfs[0]["url"].endswith("/menu.pdf")
    assert pdfs[0]["read"] is True
    assert "Short Rib $32" in pdfs[0]["text"]


def test_a_menu_pdf_that_cannot_be_read_says_which_way_it_failed(monkeypatch):
    import app.workbench.brief as brief_module

    monkeypatch.setattr(brief_module, "download",
                        lambda url, timeout=15.0: (None, "could not download"))
    pdfs = [p for p in _pages(build_brief("craftwaykitchen.com",
                                          fetcher=_Fetcher(_PDF_MENU_SITE)))
            if p["kind"] == "pdf"]
    assert (pdfs[0]["read"], pdfs[0]["reason"]) == (False, "could not download")


def test_a_pdf_the_server_says_is_gone_is_recorded_as_exactly_that(monkeypatch):
    """The Heritage Table's dinner menu PDF returns 404. It was recorded as
    "could not download", which could equally mean a timeout or a refusal."""
    import app.workbench.brief as brief_module

    monkeypatch.setattr(brief_module, "download", lambda url, timeout=15.0: (None, "status 404"))
    pdfs = [p for p in _pages(build_brief("craftwaykitchen.com",
                                          fetcher=_Fetcher(_PDF_MENU_SITE)))
            if p["kind"] == "pdf"]
    assert pdfs[0]["reason"] == "status 404"


_IMAGE_MENU_SITE = """
<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head><body>
<img decoding="async" data-src="/uploads/Wine-List-Web-5-pdf.jpg" title="Wine List Web (5)">
</body></html>
"""


def test_a_menu_published_only_as_an_image_is_read_once_and_kept(monkeypatch):
    """The Heritage Table's wine list is an image. It was never recognised as a
    menu, so every wine on the page came back unsourced. Reading it costs a
    model call, so the same image is read once, however often it is crawled."""
    import app.workbench.brief as brief_module

    monkeypatch.setattr(brief_module, "download",
                        lambda url, timeout=15.0: (b"\xff\xd8same-bytes", ""))
    calls = []
    monkeypatch.setattr(brief_module.image_text, "read",
                        lambda data, media_type=None: calls.append(data)
                        or ("Cabernet Sauvignon, Napa Valley", ""))
    for _ in range(2):
        images = [p for p in _pages(build_brief("craftwaykitchen.com",
                                                fetcher=_Fetcher(_IMAGE_MENU_SITE)))
                  if p["kind"] == "image"]
    assert images and images[0]["read"] and "Cabernet" in images[0]["text"]
    assert images[0]["url"].endswith("/uploads/Wine-List-Web-5-pdf.jpg")
    assert len(calls) == 2  # the reader is asked; its own cache decides the cost
