"""A fact should carry the words it was read from, not only a score.

A confidence rating says how much to trust a value. It never says what to go
and look at. These tests hold the line that every claim carries its source's
own words and where in the source they were, all the way from reading a page
to the fact an operator is shown.
"""

from __future__ import annotations

import json

from app.workbench.corroborate import corroborate
from app.workbench.extract import read_structured_data
from app.workbench.types import RawClaim, SourceType

SCHEMA = """
<html><head><script type="application/ld+json">
{"@type":"Restaurant","name":"The Heritage Table","telephone":"(469) 664-0100",
 "address":{"@type":"PostalAddress","streetAddress":"7110 Main St",
   "addressLocality":"Frisco","addressRegion":"TX","postalCode":"75033"},
 "openingHours":["Mo-We 17:00-21:00","Th-Sa 17:00-22:00"]}
</script></head><body><p>Dinner nightly.</p></body></html>
"""

PLAIN = """
<html><body><header>Home Menu Visit</header>
<p>Open Thursday to Saturday. Call us any evening on
<a href="tel:4696640100">(469) 664-0100</a> to book a table.</p>
</body></html>
"""


def test_a_schema_fact_says_which_property_it_came_from():
    _, _, _, evidence = read_structured_data(SCHEMA)
    assert evidence["phone"]["found_in"] == "schema.org Restaurant · telephone"
    assert evidence["phone"]["quote"] == "(469) 664-0100"
    assert "7110 Main St" in evidence["address"]["quote"]
    assert "Th-Sa 17:00-22:00" in evidence["hours"]["quote"]


def test_a_number_read_off_the_page_quotes_the_sentence_around_it():
    phone, _, _, evidence = read_structured_data(PLAIN)
    # The value is taken from the link's target, so it arrives as bare digits
    # even though the page prints "(469) 664-0100". The quote is what makes
    # that visible instead of puzzling.
    assert phone == "4696640100"
    quote = evidence["phone"]["quote"]
    assert "Call us any evening" in quote, "the sentence, so a person recognises it"
    assert "<a href" not in quote, "readable words, not the markup they sat in"
    assert evidence["phone"]["found_in"] == "a telephone link on the page"


def test_a_rejected_number_takes_its_evidence_with_it():
    """A short code is not a phone number, and quoting one would be worse than
    quoting nothing: it points somebody at a line that supports no fact."""
    phone, _, _, evidence = read_structured_data(
        '<html><body><a href="tel:611">Dial 611</a></body></html>')
    assert phone is None
    assert "phone" not in evidence


def test_evidence_survives_corroboration_and_names_each_source():
    facts = {f.field: f for f in corroborate([
        RawClaim("phone", "(469) 664-0100", "https://maps.google.test/1",
                 SourceType.GBP, quote="(469) 664-0100",
                 found_in="google listing · phone"),
        RawClaim("phone", "(469) 664-0100", "https://yelp.test/biz",
                 SourceType.YELP, quote="(469) 664-0100",
                 found_in="yelp listing · phone"),
    ])}
    said = facts["phone"].sources
    assert [s["found_in"] for s in said] == ["google listing · phone",
                                             "yelp listing · phone"]


def test_a_disagreeing_source_is_quoted_so_the_operator_can_judge_it():
    """This is the case the whole change is for. The brief carried a dissent of
    '1568175315' against a real phone number with nothing to explain it. With
    the sentence attached, it is obvious at a glance what was misread."""
    facts = {f.field: f for f in corroborate([
        RawClaim("phone", "(469) 664-0100", "https://maps.google.test/1",
                 SourceType.GBP, quote="(469) 664-0100", found_in="google listing · phone"),
        RawClaim("phone", "(469) 664-0100", "https://yelp.test/biz",
                 SourceType.YELP, quote="(469) 664-0100", found_in="yelp listing · phone"),
        RawClaim("phone", "1568175315", "https://theheritagetable.test/",
                 SourceType.EXISTING_SITE,
                 quote="Reservations powered by OpenTable restref=1568175315",
                 found_in="the page's own words"),
    ])}
    dissent = facts["phone"].dissent
    assert len(dissent) == 1
    assert "OpenTable" in dissent[0]["quote"]
    assert dissent[0]["value"] == "1568175315"


def test_a_source_with_nothing_to_quote_says_nothing_rather_than_empty():
    """'No quote' and 'an empty quote' read the same on a screen and mean
    different things. A key that is absent can be rendered as 'this source
    answered with a bare value'; a key that is present and empty cannot."""
    fact = corroborate([RawClaim("address", "7110 Main St", "https://osm.test/1",
                                 SourceType.OSM)])[0]
    assert "quote" not in fact.sources[0]
    assert "found_in" not in fact.sources[0]


def test_evidence_is_json_serialisable_for_the_brief_archive():
    fact = corroborate([RawClaim("hours", "Mon 9-5", "https://yelp.test/biz",
                                 SourceType.YELP, quote="Mon 9:00 am - 5:00 pm",
                                 found_in="yelp listing · opening hours")])[0]
    assert json.loads(json.dumps(fact.sources))[0]["quote"] == "Mon 9:00 am - 5:00 pm"


# ---------------------------------------------------------- through the brief


def test_a_facts_evidence_survives_being_stored_and_read_back():
    """The brief is written to the database and archived as JSON. Evidence that
    does not survive that round trip is evidence the operator screen — which
    reads the stored copy, not the crawl — will never see."""
    from app.web.serialize import fact_to_dict

    fact = corroborate([
        RawClaim("phone", "(469) 664-0100", "https://maps.google.test/1",
                 SourceType.GBP, quote="(469) 664-0100",
                 found_in="google listing · phone"),
        RawClaim("phone", "(469) 664-0100", "https://theheritagetable.test/",
                 SourceType.EXISTING_SITE,
                 quote="Call us any evening on (469) 664-0100 to book a table.",
                 found_in="a telephone link on the page"),
    ])[0]

    stored = json.loads(json.dumps(fact_to_dict(fact)))
    quotes = {s["source_type"]: s.get("quote") for s in stored["sources"]}
    assert quotes["their_site"].startswith("Call us any evening")
    assert stored["sources"][0]["found_in"] == "google listing · phone"


def test_the_sites_own_evidence_is_serialised_with_the_rest_of_it():
    from app.web.serialize import published_to_dict
    from app.workbench.extract import extract_from_html

    site = extract_from_html(SCHEMA, "https://theheritagetable.test/")
    published = json.loads(json.dumps(published_to_dict(site)))
    assert published["evidence"]["phone"]["found_in"] == \
        "schema.org Restaurant · telephone"


# -------------------------------------------------------- reading the request


def test_a_postal_code_after_the_state_still_splits_off_the_location():
    """A person copying an address out of a listing brings the ZIP with it.

    Without this the whole string stays in the name, `location` stays None,
    and the different-town check that depends on it never runs — the brief
    then reports whatever town the directory happened to return.
    """
    from app.workbench.resolve import resolve_input, split_location

    assert split_location("The Heritage Table, Frisco, TX 75033") == (
        "The Heritage Table", "Frisco, TX 75033")
    assert split_location("Acme Roofing in Plano, TX 75024-1234") == (
        "Acme Roofing", "Plano, TX 75024-1234")
    resolved = resolve_input("The Heritage Table, Frisco, TX 75033")
    assert resolved.name == "The Heritage Table"
    assert resolved.location == "Frisco, TX 75033"


def test_a_comma_in_a_company_name_is_not_a_location():
    from app.workbench.resolve import split_location

    assert split_location("Smith, Jones & Co") == ("Smith, Jones & Co", None)
    assert split_location("Hutchins BBQ, Frisco") == ("Hutchins BBQ, Frisco", None)


# ------------------------------------------- what the page says in its own words


_FOOTER = """
<html><head><title>The Heritage Table</title></head><body>
<h1>The Heritage Table</h1>
<p>Dinner nightly in downtown Frisco.</p>
<footer>
  <p>Address: 7110 Main Street, Frisco, TX 75033</p>
  <p>Mon - Wed 5pm - 9pm</p>
  <p>Thu - Sat 5pm - 10pm</p>
  <p>Sun 5pm - 9pm</p>
</footer>
</body></html>
"""


def test_an_address_in_the_footer_is_read_when_there_is_no_schema_block():
    """Without this the address has one source forever and never corroborates."""
    from app.workbench.extract import extract_from_html

    site = extract_from_html(_FOOTER, "https://theheritagetable.test/")
    assert site.address == "7110 Main Street, Frisco, TX 75033"
    assert site.evidence["address"]["found_in"] == "the page's own words"
    assert "7110 Main Street" in site.evidence["address"]["quote"]


def test_hours_read_off_the_page_carry_their_evidence():
    from app.workbench.extract import extract_from_html

    site = extract_from_html(_FOOTER, "https://theheritagetable.test/")
    assert site.hours
    assert site.evidence["hours"]["found_in"] == "the page's own words"
    assert "5pm" in site.evidence["hours"]["quote"].lower()


def test_schema_org_hours_keep_their_own_evidence_over_the_footers():
    from app.workbench.extract import extract_from_html

    site = extract_from_html(SCHEMA, "https://theheritagetable.test/")
    if "hours" in site.evidence:
        assert site.evidence["hours"]["found_in"].startswith("schema.org")


def test_somebody_elses_address_in_prose_is_not_read_as_this_business():
    """Two unintroduced addresses could be a listing of other people's."""
    from app.workbench.extract import extract_from_html

    page = """
    <html><body><h1>Frisco Guide</h1>
    <p>We loved 100 First Street, Plano, TX and also 200 Second Avenue, Allen, TX
    on our tour of the suburbs this spring with friends and family.</p>
    </body></html>
    """
    site = extract_from_html(page, "https://guide.test/")
    assert site.address is None
    assert "address" not in site.evidence


def test_a_lone_address_on_the_page_is_read_even_unintroduced():
    from app.workbench.extract import extract_from_html

    page = """
    <html><body><h1>Acme Roofing</h1>
    <p>Roofing across North Texas since 1994.</p>
    <footer>2770 Legacy Drive, Frisco, TX 75034</footer>
    </body></html>
    """
    site = extract_from_html(page, "https://acme.test/")
    assert site.address == "2770 Legacy Drive, Frisco, TX 75034"


def test_a_date_or_an_order_number_is_not_mistaken_for_an_address():
    from app.workbench.extract import extract_from_html

    page = """
    <html><body><h1>Acme</h1>
    <p>Serving 500 customers a week since 1994 across North Texas, TX.</p>
    </body></html>
    """
    site = extract_from_html(page, "https://acme.test/")
    assert site.address is None


def test_the_footers_address_is_read_without_a_comma_before_the_town():
    """How a real footer writes it: "7110 Main St. Frisco, TX 75033"."""
    from app.workbench.extract import extract_from_html

    page = """
    <html><body><h1>The Heritage Table</h1>
    <p>7110 Main Street in Frisco, TX was originally purchased in 1911.</p>
    <footer><p>(469) 664-0100</p><p>7110 Main St. Frisco, TX 75033</p></footer>
    </body></html>
    """
    site = extract_from_html(page, "https://theheritagetable.test/")
    assert site.address == "7110 Main St. Frisco, TX 75033"


def test_the_same_place_written_two_ways_still_counts_as_one():
    from app.workbench.corroborate import normalize

    assert normalize("7110 Main St. Frisco, TX 75033", "address") == \
        normalize("7110 Main St, Frisco, TX 75033, USA", "address")


def test_a_quote_never_starts_or_ends_halfway_through_a_word():
    """Fish Shack's address was quoted as "asual Oyster Bar Setting ...": the
    window around the match started at a fixed character count, which
    landed inside "casual". A quote an owner reads has to be words they
    wrote, whole."""
    from app.workbench.extract import _line_around

    text = ("Fantastic Grilled, Boiled, and Fried Seafood in a Casual Oyster Bar "
            "Setting. Plano: 700 East 15th Street Plano, TX 75074 Ph: "
            "469-229-0838 Fax: 469-229-0848 HOURS: Sun - Thu - 10:30am")
    at = text.index("700 East")
    for width in range(20, 80):
        quote = _line_around(text, at, width, already_text=True)
        words = text.split()
        assert quote.split()[0] in words and quote.split()[-1] in words, (width, quote)
        assert "700 East" in quote
