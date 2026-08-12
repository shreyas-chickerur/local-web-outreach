"""Render a generated site's content model as a real, viewable web page.

Phase 4 produces a *content model* — grounded facts with claim ids. Until now
nothing turned it into HTML, so the "preview link" pointed at a domain that does
not exist and neither the operator nor a prospect could actually see the site
they were being asked to approve or buy.

The renderer is deliberately plain-Python (no template engine) and escapes every
value, because everything on this page comes from third-party data. It renders
ONLY what the content model contains: if a fact was not verified it is not here.
"""

from __future__ import annotations

from html import escape

_PALETTE = {
    "restaurant": ("#1c1917", "#b45309", "#fffbeb"),
    "service": ("#0f172a", "#0369a1", "#f0f9ff"),
    "generic": ("#111827", "#4338ca", "#eef2ff"),
}

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;
     color:%(ink)s;background:#fff;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
header.nav{display:flex;align-items:center;justify-content:space-between;
     padding:20px 0;border-bottom:1px solid #e5e7eb}
header.nav .brand{font-weight:700;font-size:1.05rem;letter-spacing:-.01em}
header.nav a.cta{background:%(accent)s;color:#fff;text-decoration:none;
     padding:10px 18px;border-radius:8px;font-weight:600;font-size:.9rem}
.hero{background:%(tint)s;padding:88px 0 80px;text-align:center}
.hero h1{font-size:clamp(2.2rem,5vw,3.4rem);line-height:1.1;letter-spacing:-.03em;
     font-weight:800;margin-bottom:16px}
.hero p{font-size:clamp(1.05rem,2vw,1.3rem);color:#4b5563;max-width:640px;margin:0 auto}
.hero .actions{margin-top:32px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.btn{display:inline-block;text-decoration:none;padding:14px 26px;border-radius:9px;
     font-weight:600}
.btn-primary{background:%(accent)s;color:#fff}
.btn-ghost{border:1px solid #d1d5db;color:%(ink)s}
section.block{padding:64px 0;border-bottom:1px solid #f3f4f6}
section.block h2{font-size:1.6rem;letter-spacing:-.02em;margin-bottom:28px;font-weight:700}
.facts{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.fact{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px}
.fact .label{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
     color:#6b7280;font-weight:700;margin-bottom:6px}
.fact .value{font-size:1.12rem;font-weight:600}
.rating{display:flex;align-items:baseline;gap:10px}
.rating .stars{color:%(accent)s;font-size:1.3rem;letter-spacing:2px}
.cta-band{background:%(ink)s;color:#fff;padding:64px 0;text-align:center}
.cta-band h2{font-size:1.9rem;letter-spacing:-.02em;margin-bottom:12px;font-weight:700}
.cta-band p{color:#d1d5db;margin-bottom:26px}
.cta-band .btn-primary{background:#fff;color:%(ink)s}
footer{padding:36px 0;color:#6b7280;font-size:.85rem;text-align:center}
.draft-ribbon{position:fixed;top:16px;right:-46px;transform:rotate(45deg);
     background:#b91c1c;color:#fff;padding:7px 60px;font-size:.72rem;font-weight:700;
     letter-spacing:.09em;z-index:99;box-shadow:0 2px 8px rgba(0,0,0,.2)}
@media(max-width:640px){.hero{padding:60px 0 56px}section.block{padding:44px 0}}
"""


def _stars(value: str) -> str:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return ""
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    return "★" * full + ("½" if half else "") + "☆" * (5 - full - half)


def _fact_html(fact: dict) -> str:
    label = escape(str(fact.get("label", "")))
    value = escape(str(fact.get("value", "")))
    if fact.get("field") == "rating":
        value = (f'<span class="rating"><span class="stars">{_stars(fact.get("value", ""))}'
                 f"</span><span>{value} out of 5</span></span>")
    return (f'<div class="fact"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>')


def render_site(content: dict, *, draft: bool = True) -> str:
    """Return a complete HTML document for a generated site's content model."""
    name = escape(str(content.get("business_name", "")))
    industry = str(content.get("industry", "generic"))
    ink, accent, tint = _PALETTE.get(industry, _PALETTE["generic"])
    css = _CSS % {"ink": ink, "accent": accent, "tint": tint}

    sections = content.get("sections", [])
    hero: dict = next((s for s in sections if s.get("type") == "hero"), {})
    cta: dict = next((s for s in sections if s.get("type") == "cta"), {})
    body: list[str] = []

    for section in sections:
        stype = section.get("type")
        if stype in {"hero", "cta"} or not section.get("facts"):
            continue
        facts = "".join(_fact_html(f) for f in section["facts"])
        body.append(
            f'<section class="block"><div class="wrap">'
            f'<h2>{escape(str(section.get("heading", "")))}</h2>'
            f'<div class="facts">{facts}</div></div></section>'
        )

    ribbon = '<div class="draft-ribbon">DRAFT · PRIVATE</div>' if draft else ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{name}</title>
<style>{css}</style>
</head><body>
{ribbon}
<div class="wrap"><header class="nav">
  <span class="brand">{name}</span>
  <a class="cta" href="#contact">Get in touch</a>
</header></div>

<div class="hero"><div class="wrap">
  <h1>{name}</h1>
  <p>{escape(str(hero.get("subheading", "")))}</p>
  <div class="actions">
    <a class="btn btn-primary" href="#contact">Get in touch</a>
    <a class="btn btn-ghost" href="#details">See details</a>
  </div>
</div></div>

<a id="details"></a>
{"".join(body)}

<div class="cta-band" id="contact"><div class="wrap">
  <h2>{escape(str(cta.get("heading", "Get in touch")))}</h2>
  <p>{escape(str(cta.get("body", "")))}</p>
  <a class="btn btn-primary" href="#contact">Contact us</a>
</div></div>

<footer><div class="wrap">© {name}. Private proposal — not indexed.</div></footer>
</body></html>"""
