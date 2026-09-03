"""Build a site out of what we actually know about a business.

The governing rule is the one from the requirements: **no unverified fact
ships**. A site is shown to an owner, so a sentence they know to be false ends
the conversation on the spot — a fabricated "serving the neighbourhood since
1994" is worse than a plain page.

That is enforced structurally rather than by care:

* every value on the page comes from `sources()` — their own published site, or
  a fact two independent sources agreed on, or something you confirmed yourself;
* nothing is written that asserts anything not in that set. Generic copy is
  allowed ("Book a table"); specific claims are not ("family run for 30 years");
* a section with no data is not rendered at all, rather than filled with a
  placeholder that reads as a claim.

`unsupported()` re-checks the finished page against the allowed values and is
run by the tests, so a future section cannot quietly start inventing.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from app.site.spec import SECTIONS, SiteSpec, parse_spec
from app.site.theme import Theme, theme_for


@dataclass
class Material:
    """Everything the page is allowed to say, gathered in one place."""

    name: str
    tagline: str | None = None
    about: str | None = None
    services: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    menu_items: tuple[dict, ...] = ()
    hours: tuple[str, ...] = ()
    photos: tuple[str, ...] = ()
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    socials: tuple[dict, ...] = ()
    rating: float | None = None
    reviews: int | None = None
    trade: str | None = None            # "Restaurant", from the directory


def material_from_brief(brief: dict) -> Material:
    """Pull the usable content out of a brief.

    Facts are taken only when corroborated or confirmed by you: a phone number
    one directory guessed is exactly the sort of thing that is wrong, and a
    wrong phone number on a demo site is the end of the meeting.
    """
    published = brief.get("published") or {}
    trusted = {f["field"]: f["value"] for f in brief.get("facts", [])
               if f.get("confidence") in ("verified", "operator_verified")
               and f.get("value")}
    ratings = brief.get("ratings") or []
    best = max(ratings, key=lambda r: (r.get("reviews") or 0), default=None)
    return Material(
        name=brief.get("name") or "",
        tagline=published.get("tagline"),
        about=published.get("about"),
        services=tuple(published.get("services") or ()),
        products=tuple(published.get("products") or ()),
        menu_items=tuple(published.get("menu_items") or ()),
        hours=tuple(published.get("hours") or ()) or (
            (trusted["hours"],) if "hours" in trusted else ()),
        photos=tuple(published.get("photos") or ()),
        address=trusted.get("address"),
        phone=trusted.get("phone"),
        email=(published.get("emails") or [None])[0],
        socials=tuple(published.get("socials") or ()),
        rating=best.get("value") if best else None,
        reviews=best.get("reviews") if best else None,
    )


def e(value) -> str:
    return html.escape(str(value or ""), quote=True)


_NO_DATA = {
    "menu": "they publish no prices we could read — often the menu is a PDF or "
            "a photo",
    "gallery": "there are not enough photos on their site to build one",
    "services": "their site does not list what they offer in a readable way",
    "hours": "no source publishes their opening hours",
    "about": "their site has no about text",
    "contact": "we have no address, phone or email to show",
}


def _order(spec: SiteSpec, available: set[str]) -> list[str]:
    order = [s for s in SECTIONS if s in available]
    for asked in ([spec.lead_with] if spec.lead_with else []) + spec.emphasis:
        if asked and asked not in available:
            spec.unmet.append(f"no {asked} section: {_NO_DATA.get(asked, 'no data')}")
    if spec.lead_with in order:
        order.remove(spec.lead_with)
        order.insert(1 if "hero" in order else 0, spec.lead_with)
    for section in reversed(spec.emphasis):
        if section in order and order.index(section) > 2:
            order.remove(section)
            order.insert(min(2, len(order)), section)
    return order


_CTA_LABEL = {"call": "Call us", "book": "Book a table", "order": "Order online",
              "quote": "Get a quote", "visit": "Find us"}


def _cta(material: Material, spec: SiteSpec) -> str:
    """Only offer an action we can actually wire up."""
    if spec.cta in ("call", None) and material.phone:
        digits = re.sub(r"[^\d+]", "", material.phone)
        return (f'<a class="cta" href="tel:{e(digits)}">Call {e(material.phone)}</a>')
    if material.phone:
        digits = re.sub(r"[^\d+]", "", material.phone)
        return (f'<a class="cta" href="tel:{e(digits)}">'
                f'{e(_CTA_LABEL.get(spec.cta or "call", "Call us"))}</a>')
    if material.address:
        query = e(f"{material.name} {material.address}")
        return (f'<a class="cta" href="https://www.google.com/maps/search/?api=1&amp;'
                f'query={query.replace(" ", "+")}" target="_blank" rel="noopener">'
                f'Find us</a>')
    return ""


def _hero(m: Material, spec: SiteSpec, t: Theme) -> str:
    photo = m.photos[0] if m.photos else None
    # Their own words if they have any; otherwise the trade, which is a fact
    # from the directory, not a claim we made up.
    sub = m.tagline or (f"{m.trade} in {m.address.split(',')[1].strip()}"
                        if m.trade and m.address and "," in m.address else m.trade)
    return f'''<header class="hero{' has-photo' if photo else ''}"
  {f'style="background-image:{t.hero_overlay},url(&quot;{e(photo)}&quot;)"' if photo else ''}>
  <div class="wrap">
    <h1>{e(m.name)}</h1>
    {f'<p class="sub">{e(sub)}</p>' if sub else ''}
    {_cta(m, spec)}
  </div>
</header>'''


def _services(m: Material, t: Theme) -> str:
    items = list(m.services) + list(m.products)
    if not items:
        return ""
    cards = "".join(f'<li>{e(item)}</li>' for item in items[:9])
    return f'''<section id="services"><div class="wrap">
  <h2>What we do</h2><ul class="grid">{cards}</ul></div></section>'''


def _menu(m: Material, t: Theme) -> str:
    if not m.menu_items:
        return ""
    rows = []
    for item in m.menu_items[:14]:
        parts = [f'<span class="n">{e(item.get("name"))}</span>']
        if item.get("price"):
            parts.append(f'<span class="p">{e(item["price"])}</span>')
        if item.get("description"):
            parts.append(f'<span class="d">{e(item["description"])}</span>')
        rows.append(f"<li>{''.join(parts)}</li>")
    return f"""<section id="menu"><div class="wrap">
  <h2>On the menu</h2><ul class="menu">{''.join(rows)}</ul></div></section>"""


def _gallery(m: Material, t: Theme) -> str:
    if len(m.photos) < 2:
        return ""
    shots = "".join(f'<img src="{e(src)}" alt="" loading="lazy">'
                    for src in m.photos[1:9])
    return f'''<section id="gallery"><div class="wrap">
  <h2>Inside</h2><div class="shots">{shots}</div></div></section>'''


def _about(m: Material, t: Theme) -> str:
    if not m.about:
        return ""
    return f'''<section id="about"><div class="wrap narrow">
  <h2>About</h2><p>{e(m.about)}</p></div></section>'''


def _hours(m: Material, t: Theme) -> str:
    if not m.hours:
        return ""
    rows = "".join(f"<li>{e(line)}</li>" for line in m.hours[:7])
    return f'''<section id="hours"><div class="wrap narrow">
  <h2>Opening hours</h2><ul class="hours">{rows}</ul></div></section>'''


def _contact(m: Material, t: Theme) -> str:
    bits = []
    if m.address:
        query = e(m.address).replace(" ", "+")
        bits.append(f'<a href="https://www.google.com/maps/search/?api=1&amp;query={query}"'
                    f' target="_blank" rel="noopener">{e(m.address)}</a>')
    if m.phone:
        bits.append(f'<a href="tel:{e(re.sub(r"[^0-9+]", "", m.phone))}">{e(m.phone)}</a>')
    if m.email:
        bits.append(f'<a href="mailto:{e(m.email)}">{e(m.email)}</a>')
    for social in m.socials[:4]:
        bits.append(f'<a href="{e(social.get("url"))}" target="_blank" rel="noopener">'
                    f'{e(social.get("name"))}</a>')
    if not bits:
        return ""
    return f'''<section id="contact"><div class="wrap narrow">
  <h2>Find us</h2><div class="contact">{"".join(bits)}</div></div></section>'''


_BUILDERS = {"services": _services, "menu": _menu, "gallery": _gallery,
             "about": _about, "hours": _hours, "contact": _contact}


def _css(t: Theme) -> str:
    return f'''
:root{{--bg:{t.bg};--surface:{t.surface};--ink:{t.ink};--dim:{t.dim};
  --accent:{t.accent};--accent-ink:{t.accent_ink};--line:{t.line};--r:{t.radius};}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:{t.body};
  font-size:17px;line-height:1.6;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 24px}}
.wrap.narrow{{max-width:720px}}
h1,h2{{font-family:{t.display};font-weight:700;letter-spacing:-.02em;margin:0 0 14px}}
h1{{font-size:clamp(38px,7vw,68px);line-height:1.05}}
h2{{font-size:clamp(24px,3.4vw,34px)}}
section{{padding:62px 0;border-top:1px solid var(--line)}}
section:nth-child(even){{background:var(--surface)}}
.hero{{padding:110px 0 96px;background:var(--surface);background-size:cover;
  background-position:center}}
.hero.has-photo{{color:#fff}}
.hero.has-photo .wrap{{max-width:1080px}}
.hero.has-photo h1,.hero.has-photo .sub{{max-width:20ch}}
.hero.has-photo .sub{{max-width:34ch}}
.hero.has-photo h1{{text-shadow:0 2px 24px rgba(0,0,0,.45)}}
.hero .sub{{font-size:clamp(17px,2.2vw,22px);opacity:.92;margin:0 0 26px;max-width:36ch}}
.cta{{display:inline-block;background:var(--accent);color:var(--accent-ink);
  text-decoration:none;font-weight:700;padding:15px 30px;border-radius:var(--r);
  transition:transform .16s ease,filter .16s ease}}
.cta:hover{{transform:translateY(-2px);filter:brightness(1.06)}}
.grid{{list-style:none;padding:0;margin:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}}
.grid li{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:20px 22px;font-weight:600}}
section:nth-child(even) .grid li{{background:var(--bg)}}
.menu{{list-style:none;padding:0;margin:0;display:grid;gap:2px}}
.menu li{{display:grid;grid-template-columns:1fr auto;gap:6px 18px;padding:15px 0;
  border-bottom:1px solid var(--line);align-items:baseline}}
.menu .n{{font-weight:650}}
.menu .p{{font-family:ui-monospace,monospace;color:var(--accent);font-weight:700}}
.menu .d{{grid-column:1/-1;color:var(--dim);font-size:15px}}
.shots{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}}
.shots img{{width:100%;height:210px;object-fit:cover;border-radius:var(--r);display:block}}
.hours{{list-style:none;padding:0;margin:0;columns:2;column-gap:34px}}
.hours li{{padding:7px 0;border-bottom:1px solid var(--line);break-inside:avoid}}
.contact{{display:flex;flex-direction:column;gap:10px;font-size:18px}}
.contact a{{color:var(--accent);text-decoration:none}}
.contact a:hover{{text-decoration:underline}}
footer{{padding:34px 0;color:var(--dim);font-size:13px;text-align:center;
  border-top:1px solid var(--line)}}
@media (max-width:640px){{.hours{{columns:1}} section{{padding:44px 0}}}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
'''


def build(brief: dict, spec_text: str = "") -> tuple[str, SiteSpec]:
    """Return (html, spec). Deterministic: the same inputs give the same page."""
    material = material_from_brief(brief)
    spec = parse_spec(spec_text)
    theme = theme_for(spec.mood)

    sections = {key: builder(material, theme) for key, builder in _BUILDERS.items()}
    available = {"hero"} | {k for k, v in sections.items() if v}
    body = _hero(material, spec, theme)
    for key in _order(spec, available):
        if key != "hero":
            body += "\n" + sections[key]

    return (f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(material.name)}</title>
{f'<meta name="description" content="{e(material.tagline)}">' if material.tagline else ''}
<style>{_css(theme)}</style></head>
<body>
{body}
<footer><div class="wrap">{e(material.name)}
  {f"&middot; {e(material.address)}" if material.address else ""}</div></footer>
</body></html>''', spec)


# --------------------------------------------------------------------------- #
# The guard. Run by the tests against every generated page.
# --------------------------------------------------------------------------- #

_CLAIM_RE = re.compile(
    r"\b(since \d{4}|est\.? ?\d{4}|\d+\+? years|award[- ]winning|voted|"
    r"best in|number one|#1|family[- ]owned|family[- ]run|trusted by|"
    r"\d+ (?:happy )?(?:customers|clients)|five[- ]star|5[- ]star)\b",
    re.IGNORECASE)


def unsupported(page: str, material: Material) -> list[str]:
    """Claims on the page that nothing in the material supports.

    Generic copy is fine. A specific assertion about the business is not,
    unless it came from their own words.
    """
    own_words = " ".join(str(x) for x in (
        material.tagline or "", material.about or "",
        " ".join(material.services), " ".join(material.products),
        " ".join(str(i.get("name", "")) for i in material.menu_items))).lower()
    text = re.sub(r"<[^>]+>", " ", page)
    return [claim for claim in {m.group(0) for m in _CLAIM_RE.finditer(text)}
            if claim.lower() not in own_words]
