"""Reading a business's own site: carry their content, leave the junk behind."""

from __future__ import annotations

import pytest

from app.workbench.extract import (
    _clean_service,
    extract_from_html,
    menu_page_urls,
    merge,
    social_belongs_to,
    story_score,
    strip_leading_heading,
)

pytestmark = pytest.mark.unit

_HTML = """
<html><head>
<title>The Heritage Table | Frisco</title>
<meta name="description" content="A true neighborhood restaurant on Main Street.">
<meta property="og:image" content="/img/hero.jpg">
</head><body>
<nav><a href="/">Home</a><a href="/about">About</a></nav>
<h1>The Heritage Table</h1>
<h2>Chef's Tasting Menu</h2>
<h2>Blackland Prairie Cuisine</h2>
<h2>James Beard Awards 2024</h2>
<p>We are a neighborhood restaurant serving seasonal food from local farms, and we
have been part of downtown Frisco for more than a decade now, cooking honestly.</p>
<ul><li>Private dining room</li><li>Seasonal menu</li></ul>
<p>Sunday - Wednesday: 5pm - 9pm</p>
<p>Thursday - Saturday: 5pm - 10pm</p>
<a href="https://www.opentable.com/r/heritage">Book a table</a>
<a href="/order-online">Order Online</a>
<a href="https://www.instagram.com/heritage">Instagram</a>
<a href="https://www.godaddy.com/domainsearch">Book this domain</a>
<img src="/img/dining.jpg"><img src="/img/bar.png">
</body></html>
"""


@pytest.fixture
def extracted():
    return extract_from_html(_HTML, "https://theheritagetable.com/")


def test_extracts_identity_and_description(extracted):
    assert "Heritage Table" in extracted.title
    assert "neighborhood restaurant" in extracted.description


def test_extracts_the_about_paragraph(extracted):
    assert "seasonal food from local farms" in extracted.about


def test_extracts_services_but_not_navigation_or_awards(extracted):
    assert "Chef's Tasting Menu" in extracted.services
    assert "Blackland Prairie Cuisine" in extracted.services
    assert "Private dining room" in extracted.services
    # awards are social proof, not an offering
    assert not any("Beard" in s or "Award" in s for s in extracted.services)
    # navigation is not an offering
    assert not any(s.lower() in {"home", "about"} for s in extracted.services)


def test_extracts_hours(extracted):
    assert any("Sunday" in h for h in extracted.hours)
    assert any("Thursday" in h for h in extracted.hours)


def test_keeps_real_customer_actions(extracted):
    kinds = {a["kind"] for a in extracted.actions}
    assert "Book / Reserve" in kinds       # OpenTable is a real booking provider
    assert "Order Online" in kinds         # on their own site


def test_drops_registrar_and_builder_links():
    """A 'book this domain' link at GoDaddy is not a customer action."""
    extracted = extract_from_html(
        '<a href="https://www.godaddy.com/domainsearch">Book this domain</a>',
        "https://acme.com/")
    assert extracted.actions == []


def test_extracts_socials_and_images(extracted):
    assert {s["name"] for s in extracted.socials} == {"Instagram"}
    assert extracted.images  # og:image is promoted to the front
    assert extracted.images[0].endswith("/img/hero.jpg")


def test_offsite_images_are_ignored():
    extracted = extract_from_html(
        '<img src="https://cdn.other.com/x.jpg"><img src="/mine.jpg">',
        "https://acme.com/")
    assert all("other.com" not in i for i in extracted.images)


@pytest.mark.parametrize("junk", [
    "Home", "Privacy Policy", "How It Works", "Disclaimer", "Our Team",
    "call us at 972-555-0148", "a", "x" * 80,
])
def test_service_junk_is_rejected(junk):
    assert _clean_service(junk) is None


def test_merge_folds_a_contact_page_in(extracted):
    contact = extract_from_html(
        "<h2>Catering</h2><p>Monday - Friday: 9am - 5pm</p>", "https://x.com/contact")
    merged = merge(extracted, contact)
    assert "Catering" in merged.services
    assert any("Monday" in h for h in merged.hours)


def test_empty_html_is_handled():
    assert extract_from_html("", "https://x.com/").is_empty()


@pytest.mark.parametrize("src", [
    "/img/james-beard-semifinalist-2024.png",   # award badge — social proof
    "/assets/logo.svg.png",
    "/i/facebook-icon.png",
    "/x/5-stars.jpg",
    "/ui/arrow-right.png",
])
def test_badges_logos_and_icons_are_not_site_photos(src):
    """An award badge as the hero image is both ugly and a social-proof claim."""
    extracted = extract_from_html(f'<img src="{src}">', "https://acme.com/")
    assert extracted.images == []


def test_award_og_image_is_not_promoted_to_hero():
    html = ('<head><meta property="og:image" content="/img/james-beard-award.png"></head>'
            '<img src="/img/dining-room.jpg">')
    extracted = extract_from_html(html, "https://acme.com/")
    assert extracted.images
    assert "dining-room" in extracted.images[0]


# ------------------------------- menus -------------------------------------- #
def test_extracts_priced_menu_items():
    html = """<ul>
      <li>Short Rib $32 braised eight hours with root vegetables</li>
      <li>Gulf Snapper $28</li>
      <li>Chicken Fried Steak $24 cream gravy</li>
    </ul>"""
    items = extract_from_html(html, "https://acme.com/").menu_items
    names = {i["name"] for i in items}
    assert "Short Rib" in names and "Gulf Snapper" in names
    short_rib = next(i for i in items if i["name"] == "Short Rib")
    assert short_rib["price"] == "$32"
    assert "braised eight hours" in short_rib["description"]


def test_menu_item_price_may_sit_on_its_own_line():
    items = extract_from_html("<div>Wagyu Burger</div><div>$26.00</div>",
                              "https://acme.com/").menu_items
    assert items and items[0]["name"] == "Wagyu Burger"
    assert items[0]["price"] == "$26.00"


def test_prose_with_a_price_is_not_a_menu_item():
    items = extract_from_html(
        "<p>Home</p><p>$5</p>", "https://acme.com/").menu_items
    assert all(i["name"].lower() != "home" for i in items)


def test_extracts_a_pdf_menu_to_embed():
    """Restaurants usually publish the menu as a PDF or photo, not HTML."""
    html = '<a href="/uploads/HT-Dinner-Menu.pdf">HT Dinner Menu</a>'
    media = extract_from_html(html, "https://acme.com/").menu_media
    assert media and media[0]["kind"] == "pdf"
    assert media[0]["url"].endswith("HT-Dinner-Menu.pdf")


def test_unrelated_pdfs_are_not_treated_as_menus():
    html = '<a href="/uploads/privacy-policy.pdf">Privacy Policy</a>'
    assert extract_from_html(html, "https://acme.com/").menu_media == []


def test_products_are_not_listed_as_services():
    """A bottle of sauce is revenue, but it is not a service.

    Hutchins BBQ sells seasoning and sauce alongside catering; listing those as
    "services" made the brief wrong about what the business does.
    """
    html = """<html><body>
      <h2>Catering</h2><h2>Brisket Seasoning</h2>
      <h2>Hutchins BBQ Sauce</h2><h2>Original Rib Rub</h2>
    </body></html>"""
    site = extract_from_html(html, "https://example.com/")
    assert site.services == ["Catering"]
    assert site.products == ["Brisket Seasoning", "Hutchins BBQ Sauce",
                             "Original Rib Rub"]


def test_page_furniture_is_not_an_offering():
    """Every one of these came off a real homepage and was read as a service."""
    html = """<html><body>
      <h2>Weed Control &amp; Fertilization</h2>
      <h2>What Our Clients Say</h2><h2>Frequently Asked Questions</h2>
      <h2>Lawn Watering Guide - Tips &amp; Walkthrough</h2>
      <h2>Conserve Water,</h2><h2>Talk to a lawn expert</h2>
      <h2>Areas We Serve</h2><h2>Mckinney, Texas</h2>
      <h2>Instagram Facebook TikTok Yelp</h2><h2>UPCOMING EVENTS</h2>
    </body></html>"""
    site = extract_from_html(html, "https://example.com/")
    assert site.services == ["Weed Control & Fertilization"]


def test_stylesheet_is_not_followed_as_a_page():
    """A theme shipped "menu-addon.css"; the crawler fetched it as the menu."""
    html = ('<a href="/wp-content/plugins/kadence/mega-menu/menu-addon.css">x</a>'
            '<a href="/menus/">Menus</a>')
    assert menu_page_urls(html, "https://example.com/") == [
        "https://example.com/menus/"]


def test_schema_org_gives_the_business_its_own_voice():
    """Their own site publishing a phone is what lets a lone directory listing
    reach two-source confirmation instead of staying unverified forever."""
    html = """<html><body>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
      {"@type":"Restaurant","name":"Test Co","telephone":"(972) 377-2046",
       "address":{"@type":"PostalAddress","streetAddress":"9225 Preston Rd",
                  "addressLocality":"Frisco","addressRegion":"TX",
                  "postalCode":"75033"},
       "openingHours":["Mo-Su 11:00-21:00"]}]}
    </script></body></html>"""
    site = extract_from_html(html, "https://example.com/")
    assert site.phone == "(972) 377-2046"
    assert site.address == "9225 Preston Rd, Frisco, TX 75033"
    assert site.hours


def test_a_tel_link_is_the_fallback_phone():
    site = extract_from_html('<a href="tel:+14694962778">Call</a>',
                             "https://example.com/")
    assert site.phone is not None and "469" in site.phone


def test_broken_json_ld_does_not_take_the_page_down():
    """Half the web ships malformed structured data."""
    html = '<script type="application/ld+json">{not json,,}</script><h2>Catering</h2>'
    assert extract_from_html(html, "https://example.com/").services == ["Catering"]


def test_the_about_text_is_the_one_that_reads_like_a_story():
    """Taking the longest paragraph put a private-events booking pitch under a
    heading that said "Our story" — the section told the reader nothing about
    the business."""
    html = """<html><body>
      <p>Plan your next event with us! Our venue options include a private
         dining room seating 40-46 guests. Click link here to inquire, or call
         us at 469-664-0100 or email info@example.com to make a reservation for
         fewer than fifteen guests in the main room downstairs today.</p>
      <p>We opened in 2014 with one idea: cook everything from scratch and buy
         from farms we know. Our chef grew up here and still writes the menu
         around what the season gives us.</p>
    </body></html>"""
    site = extract_from_html(html, "https://example.com/")
    assert site.about is not None
    assert site.about.startswith("We opened in 2014")


def test_a_page_with_no_story_gets_no_about_text():
    """A heading promising a story with no story under it is worse than no
    section at all."""
    html = """<html><body>
      <p>Orders placed before 2pm ship the same business day. Standard delivery
         takes 3-5 business days. Click here to view our full shipping and
         returns policy for more information about your order.</p>
    </body></html>"""
    assert extract_from_html(html, "https://example.com/").about is None


def test_a_heading_that_ran_into_the_paragraph_is_removed():
    """Extraction catches the heading above a block, so the about section
    opened with "UPCOMING EVENTS" before it said anything."""
    assert strip_leading_heading(
        "UPCOMING EVENTS Beyond our restaurants we bring our craft to festivals."
    ).startswith("Beyond our restaurants")
    assert strip_leading_heading(
        "Why Choose Us? Locally owned since 2009 and proud of it."
    ).startswith("Locally owned")
    assert strip_leading_heading("We opened in 2014.") == "We opened in 2014."


def test_a_call_to_action_does_not_outscore_a_story():
    """Fifteen words of "call us, chat with our team" is almost all story words
    by density; it must not win on that."""
    cta = story_score("Call us 214-728-8894 Free estimate Get a Quote Chat with "
                      "our team — we will reply right here.")
    story = story_score("We opened in 2009 and our family has run the shop ever "
                        "since, cutting every board by hand in the workshop "
                        "behind the store because that is how we were taught.")
    assert story > cta


def test_lazy_loaded_images_are_found():
    """Most sites defer image loading, so matching only src= saw almost none of
    their photography — including the dish this restaurant is promoting."""
    html = '''<img src="/a.jpg"><img data-src="/b.jpg" title="Impractical Sandwich">
              <img data-lazy-src="/c.jpg"><img srcset="/d.jpg 800w, /e.jpg 1600w">
              <img src="data:image/gif;base64,R0lGOD">'''
    found = extract_from_html(html, "https://example.com/").images
    for name in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
        assert any(name in url for url in found), name
    assert not any(url.startswith("data:") for url in found)


def test_the_pages_own_sections_are_carried_over():
    """Rebuilding from a fixed list of sections threw away the parts of their
    site that say the most: their philosophy, their awards, their suppliers."""
    html = """<html><body>
      <h2>Philosophy</h2><p>A culture is built on the food it consumes, and we
         try to cook in a way that respects where every ingredient came from
         before it reached this kitchen.</p>
      <h2>James Beard Awards 2024</h2>
      <h2>Nominated for Best Chef - Texas</h2><p>A fine dining experience.</p>
      <h2>A Few of Our Partners</h2>
      <h3>1836 Farms</h3><p>Terrell - black Angus beef</p>
      <h3>Windy Meadows</h3><p>Campbell - pastured poultry</p>
      <h3>Comeback Creek</h3><p>Pittsburg - vegetables</p>
    </body></html>"""
    blocks = {b["kind"]: b for b in extract_from_html(html, "https://x.com/").blocks}
    assert "Philosophy" == blocks["story"]["heading"]
    assert blocks["award"]["kicker"] == "James Beard Awards 2024"
    assert "Best Chef" in blocks["award"]["heading"]
    assert blocks["partners"]["heading"] == "A Few of Our Partners"
    assert [e["name"] for e in blocks["partners"]["entries"]] == [
        "1836 Farms", "Windy Meadows", "Comeback Creek"]


def test_a_nav_heading_is_not_mistaken_for_a_section():
    html = "<h2>Main menu</h2><p>Home About Contact Privacy Terms Sitemap</p>"
    assert extract_from_html(html, "https://x.com/").blocks == []


def test_a_social_link_must_be_a_profile_not_a_post():
    """Linking a business's Instagram to one reel from 2022 is worse than not
    linking it at all."""
    for path in ("/reel/Ce7AuUJ/", "/p/abc123/", "/explore/tags/food/"):
        html = f'<a href="https://www.instagram.com{path}">Instagram</a>'
        assert extract_from_html(html, "https://x.com/").socials == []
    html = '<a href="https://www.instagram.com/theheritagetable/">Instagram</a>'
    assert extract_from_html(html, "https://x.com/").socials[0]["name"] == "Instagram"


def test_a_host_is_matched_exactly_not_by_suffix():
    """prairiefarmsteadtx.com ends with "x.com", and was being published on a
    restaurant's site as its X account."""
    html = '<a href="https://prairiefarmsteadtx.com/">Prairie Farmstead</a>'
    assert extract_from_html(html, "https://x.com/").socials == []


def test_a_profile_belongs_to_the_business_or_it_is_not_theirs():
    """A restaurant crediting fourteen farms links fourteen other businesses'
    accounts, every one a valid profile on the right host."""
    assert social_belongs_to("https://instagram.com/theheritagetable/",
                             "The Heritage Table")
    assert social_belongs_to("https://instagram.com/hutchinsbbq", "Hutchins BBQ")
    assert not social_belongs_to("https://instagram.com/knobhillfarmtx/",
                                 "The Heritage Table")
    assert not social_belongs_to("https://instagram.com/1836farms/",
                                 "The Heritage Table")
