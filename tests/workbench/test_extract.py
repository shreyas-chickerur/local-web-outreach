"""Reading a business's own site: carry their content, leave the junk behind."""

from __future__ import annotations

import pytest

from app.workbench.extract import (
    _clean_service,
    extract_from_html,
    menu_page_urls,
    merge,
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
