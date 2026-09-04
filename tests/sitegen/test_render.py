"""Generating a site from a brief.

The governing rule is the one from the requirements: **no unverified fact
ships**. The site is shown to the owner, so one sentence they know to be false
ends the meeting — a fabricated "serving the neighbourhood since 1994" is worse
than a plain page. Most of what is pinned here is that rule.
"""

from __future__ import annotations

import json
import re

import pytest

from app.site.render import build, material_from_brief, unsupported

pytestmark = pytest.mark.unit


def _brief(**kw) -> dict:
    base = {
        "name": "The Heritage Table",
        "facts": [
            {"field": "address", "value": "7110 Main St, Frisco, TX",
             "confidence": "verified"},
            {"field": "phone", "value": "(469) 664-0100", "confidence": "verified"},
        ],
        "published": {
            "tagline": "A neighbourhood restaurant on Main Street.",
            "about": "Scratch kitchen serving dinner nightly.",
            "services": ["Dinner Service", "Online Ordering"],
            "products": [],
            "hours": ["Mon-Sat 5pm-9pm"],
            "menu_items": [{"name": "Short Rib", "price": "$32",
                            "description": "braised eight hours"}],
            "menu_media": [],
            # Enough for a hero plus a mosaic: three tiles is the floor for a
            # gallery that looks built rather than padded.
            "photos": [f"https://x/{n}.jpg" for n in range(1, 7)],
            "socials": [{"name": "Instagram", "url": "https://instagram.com/x"}],
            "emails": [], "has_locations_page": False,
        },
        "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
    }
    return {**base, **kw}


def test_nothing_reaches_the_page_that_was_not_established():
    page, _ = build(_brief())
    assert unsupported(page, material_from_brief(_brief())) == []


def test_an_uncorroborated_fact_is_left_off():
    """A phone number one directory guessed is exactly the kind that is wrong,
    and a wrong number on a demo site ends the meeting."""
    brief = _brief(facts=[{"field": "phone", "value": "(000) 000-0000",
                           "confidence": "unverified"}])
    page, _ = build(brief)
    assert "000-0000" not in page


def test_what_you_confirmed_yourself_does_ship():
    brief = _brief(facts=[{"field": "phone", "value": "(469) 111-2222",
                           "confidence": "operator_verified"}])
    page, _ = build(brief)
    assert "(469) 111-2222" in page


def test_a_section_with_no_data_is_absent_not_empty():
    """A placeholder heading reads as a claim that there is nothing there."""
    thin = _brief(published={**_brief()["published"], "menu_items": [],
                             "photos": [], "about": None})
    page, _ = build(thin)
    for missing in ('id="menu"', 'id="gallery"', 'id="about"'):
        assert missing not in page
    assert 'id="contact"' in page          # address and phone are still known


def test_the_spec_changes_the_result():
    warm, _ = build(_brief(), "warm and rustic")
    night, _ = build(_brief(), "dark moody bar")
    assert warm != night


def test_asking_to_lead_with_a_section_moves_it_up():
    page, spec = build(_brief(), "put the gallery first")
    assert spec.lead_with == "gallery"
    assert page.index('id="gallery"') < page.index('id="services"')


def test_an_instruction_that_cannot_be_honoured_is_reported():
    """Silently dropping it leaves you thinking it was applied."""
    no_menu = _brief(published={**_brief()["published"], "menu_items": []})
    _, spec = build(no_menu, "lead with the menu")
    assert any("no menu section" in note for note in spec.unmet)


def test_generation_is_deterministic():
    """The same brief and the same words give the same page, so a difference
    between two versions is always something you asked for."""
    first, _ = build(_brief(), "warm, book a table")
    second, _ = build(_brief(), "warm, book a table")
    assert first == second


def test_content_is_escaped():
    nasty = _brief(name='Bob\'s "Diner" <script>alert(1)</script>')
    page, _ = build(nasty)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_the_call_to_action_is_wired_to_something_real():
    page, _ = build(_brief(), "call us")
    assert 'href="tel:4696640100"' in page

    # With no phone, it must not render a dead button.
    no_phone = _brief(facts=[{"field": "address", "value": "7110 Main St, Frisco, TX",
                              "confidence": "verified"}])
    page2, _ = build(no_phone)
    assert "tel:" not in page2
    assert "google.com/maps" in page2


def test_the_guard_catches_a_fabricated_claim():
    """If a future section starts inventing, this is what fails."""
    material = material_from_brief(_brief())
    invented = "<html><body><p>Family-run since 1994, award-winning</p></body></html>"
    found = unsupported(invented, material)
    assert "since 1994" in found and "award-winning" in found


def test_a_claim_the_business_makes_itself_is_allowed():
    """Their own words are theirs to make. We just must not add any."""
    brief = _brief(published={**_brief()["published"],
                              "about": "Family-run since 1994."})
    page, _ = build(brief)
    assert unsupported(page, material_from_brief(brief)) == []


def test_the_page_is_responsive_and_titled():
    page, _ = build(_brief())
    assert 'name="viewport"' in page
    assert "<title>The Heritage Table</title>" in page
    assert "@media" in page


def test_every_theme_renders():
    for mood in ("warm", "fresh", "bold", "refined", "industrial", "night"):
        page, spec = build(_brief(), mood)
        assert spec.mood == mood
        assert re.search(r"--accent:#[0-9a-f]{6}", page)


def _rich() -> dict:
    """A brief with everything a real lookup returns."""
    brief = _brief()
    brief["lead_id"] = 7
    brief["latitude"], brief["longitude"] = 33.1506, -96.8225
    brief["place_photos"] = [f"places/x/photos/{n}" for n in range(10)]
    brief["testimonials"] = [
        {"rating": 5, "author": "Gabby Sanchez", "text": "Everything was amazing."},
        {"rating": 4, "author": "Rowland Short", "text": "Lovely rustic room."},
        {"rating": 5, "author": "Kim H", "text": "Chef's twists were superb."},
    ]
    return brief


def test_customer_reviews_are_quoted_with_their_names():
    """The most credible copy on the page is the part the business did not
    write — but it only counts if the reader can see who said it."""
    page, _ = build(_rich())
    assert 'id="reviews"' in page
    assert "Gabby Sanchez" in page and "Everything was amazing." in page
    assert "Google" in page


def test_a_single_review_is_not_a_reviews_section():
    thin = _rich()
    thin["testimonials"] = thin["testimonials"][:1]
    page, _ = build(thin)
    assert 'id="reviews"' not in page


def test_google_photography_is_served_through_us_not_with_the_key():
    """A Places photo URL carries the API key. Putting one in a page we hand to
    a business owner would publish the key to anyone who views source."""
    page, _ = build(_rich())
    assert "/photo/7/0" in page
    assert "places.googleapis.com" not in page
    assert "key=" not in page


def test_the_page_carries_navigation_for_the_sections_it_has():
    page, _ = build(_rich())
    for section in ("services", "gallery", "reviews", "hours", "contact"):
        assert f'href="#{section}"' in page
    # and nothing it does not have
    assert 'href="#menu"' not in page or 'id="menu"' in page


def test_structured_data_matches_the_page():
    page, _ = build(_rich())
    blob = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    data = json.loads(blob.group(1))
    assert data["@type"] == "LocalBusiness"
    assert data["name"] == "The Heritage Table"
    assert data["telephone"] == "(469) 664-0100"
    assert data["geo"]["latitude"] == 33.1506


def test_structured_data_omits_what_we_could_not_confirm():
    """Schema is the same facts in a crawler's shape, not an extra set."""
    unverified = _rich()
    unverified["facts"] = [{"field": "phone", "value": "(000) 000-0000",
                            "confidence": "unverified"}]
    page, _ = build(unverified)
    blob = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert "telephone" not in json.loads(blob.group(1))


def test_motion_is_cancelled_for_anyone_who_asks():
    page, _ = build(_rich())
    assert "prefers-reduced-motion" in page
    assert "[data-reveal]{opacity:1!important" in page.replace("\n", "")


def test_images_reserve_their_space():
    """Layout shift as photos load is the cheapest tell that a site was thrown
    together."""
    page, _ = build(_rich())
    assert "aspect-ratio" in page
    assert 'loading="lazy"' in page


def test_the_map_needs_no_api_key():
    page, _ = build(_rich())
    assert "openstreetmap.org/export/embed.html" in page
    assert "marker=33.1506" in page


def test_a_phone_gets_a_thumb_reachable_action():
    page, _ = build(_rich())
    assert 'class="callbar"' in page
    assert page.count('href="tel:4696640100"') >= 2       # header, hero, call bar


def test_reviews_do_not_smuggle_claims_past_the_guard():
    """A review is the customer's claim, quoted and attributed — allowed. The
    guard must still catch anything the generator adds around it."""
    brief = _rich()
    brief["testimonials"] = [
        {"rating": 5, "author": "A", "text": "Family-run since 1994 and lovely."},
        {"rating": 5, "author": "B", "text": "Great food."},
    ]
    page, _ = build(brief)
    assert unsupported(page, material_from_brief(brief)) == []


def test_back_to_top_is_not_wired_through_an_inline_handler():
    """Inside an onclick attribute the element is in scope, so `scrollTo`
    resolves to the button's own Element.scrollTo and scrolls the button
    instead of the page. The button looked fine and did nothing."""
    page, _ = build(_rich())
    assert 'class="top"' in page
    assert "onclick" not in page.split('class="top"')[1][:120]
    assert 'querySelector(".top")' in page


def test_the_body_is_not_made_into_a_scroll_container():
    """overflow-x on BODY makes the body its own scroller, and window.scrollTo
    can then no longer scroll the page back up."""
    page, _ = build(_rich())
    body_rule = re.search(r"\nbody\{(.*?)\}", page, re.S).group(1)
    assert "overflow-x" not in body_rule
    assert "overflow-x:clip" in page


def test_a_count_of_zero_never_reaches_the_page():
    """A proud "0 services offered" loses the room."""
    bare = _rich()
    bare["published"] = {**bare["published"], "services": [], "products": [],
                         "menu_items": []}
    page, _ = build(bare)
    assert ">0<" not in page
    assert "services offered" not in page


def test_a_dense_offer_section_uses_their_photography():
    """A grid of bare titles is the tell of a generated page: every word true
    and the section empty."""
    many = _rich()
    many["published"] = {**many["published"],
                         "services": ["Dinner", "Brunch", "Catering", "Private hire",
                                      "Wine list"]}
    page, _ = build(many)
    offers = page[page.index('id="services"'):page.index("</section>",
                                                          page.index('id="services"'))]
    assert 'data-density="dense"' in offers
    assert "has-art" in offers
    assert "/photo/7/" in offers


def test_the_offer_heading_follows_the_trade():
    food = _rich()
    food["trade"] = "Restaurant"
    assert "What we cook and serve" in build(food)[0]

    trade = _rich()
    trade["trade"] = "Roofing contractor"
    trade["published"] = {**trade["published"], "menu_items": []}
    assert "How we can help" in build(trade)[0]


def test_two_offerings_do_not_get_a_grid_built_for_four():
    """auto-fit collapses its empty tracks, so two items become two half-width
    slabs with dead space down the middle. The sparse case must not use it."""
    page, _ = build(_rich())          # the fixture has exactly two services
    offers = page[page.index('id="services""'.replace('""', '"')):]
    assert 'data-density="sparse"' in page
    assert "offers-editorial" in page
    assert "listing" in page
    # the card grid is not what laid this out
    assert '<div class="offers">' not in offers.split("</section>")[0]


def test_type_scales_inversely_with_how_much_there_is():
    sparse, _ = build(_rich())
    dense_brief = _rich()
    dense_brief["published"] = {**dense_brief["published"],
                                "services": ["A", "B", "C", "D", "E"]}
    dense, _ = build(dense_brief)
    assert "--density-scale:1.25" in sparse
    assert "--density-scale:0.85" in dense
    # and the scale is actually wired into a font-size, not just declared
    assert "calc(clamp(28px,4.6vw,52px) * var(--density-scale))" in sparse


def test_three_offerings_hold_three_across():
    """Exactly three should not stretch into slabs, nor drop to a sparse split."""
    three = _rich()
    three["published"] = {**three["published"], "services": ["A", "B", "C"]}
    page, _ = build(three)
    assert 'data-density="balanced"' in page
    assert "repeat(3,minmax(0,1fr))" in page


def test_density_never_conjures_a_section_out_of_nothing():
    """The data-safety rule outranks the layout rule: no items, no section."""
    none = _rich()
    none["published"] = {**none["published"], "services": [], "products": []}
    page, _ = build(none)
    assert 'id="services"' not in page
    assert 'data-density="empty"' not in page
