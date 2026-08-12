"""Render a generated site's content model as a real, viewable web page.

Phase 4 produces a *content model* — verified facts with claim ids, plus the
business's own self-attested content. This turns it into the page a prospect
actually opens, so it has to look like something worth paying for: editorial
type, a full-bleed hero, a numbered offerings grid, a clickable gallery, and a
dark closing band.

Everything on the page is third-party data, so every value is escaped. It renders
ONLY what the model contains: no verified fact, no fact on the page.
"""

from __future__ import annotations

import json
from html import escape

from app.render.styles import css_for
from app.render.theme import palette_for, voice_for

# Small inline runtime: sticky-nav state, scroll reveal, and a gallery lightbox
# with keyboard control. No external requests — the page must stand alone.
_JS = """
(function(){
  var nav=document.querySelector('.nav');
  if(nav){var onScroll=function(){nav.classList.toggle('solid',window.scrollY>60)};
    onScroll();addEventListener('scroll',onScroll,{passive:true});}

  var els=[].slice.call(document.querySelectorAll('.reveal'));
  if('IntersectionObserver' in window && els.length){
    var io=new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){e.target.classList.add('in');
        io.unobserve(e.target);} });},{rootMargin:'0px 0px -8% 0px',threshold:.08});
    els.forEach(function(el){io.observe(el)});
  } else { els.forEach(function(el){el.classList.add('in')}); }

  var box=document.querySelector('.lightbox');
  if(!box) return;
  var img=box.querySelector('img'), srcs=JSON.parse(box.dataset.srcs||'[]'), i=0;
  function show(n){ i=(n+srcs.length)%srcs.length; img.src=srcs[i]; }
  function open(n){ show(n); box.classList.add('open');
    document.body.style.overflow='hidden'; box.querySelector('.x').focus(); }
  function close(){ box.classList.remove('open'); document.body.style.overflow=''; }
  document.querySelectorAll('.gallery button').forEach(function(b,n){
    b.addEventListener('click',function(){open(n)});
  });
  box.querySelector('.x').addEventListener('click',close);
  box.querySelector('.prev').addEventListener('click',function(e){
    e.stopPropagation();show(i-1)});
  box.querySelector('.next').addEventListener('click',function(e){
    e.stopPropagation();show(i+1)});
  box.addEventListener('click',function(e){ if(e.target===box) close(); });
  addEventListener('keydown',function(e){
    if(!box.classList.contains('open')) return;
    if(e.key==='Escape') close();
    if(e.key==='ArrowLeft') show(i-1);
    if(e.key==='ArrowRight') show(i+1);
  });
})();
"""


def _stars(value: str) -> str:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return ""
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    return "★" * full + ("½" if half else "") + "☆" * (5 - full - half)


def _find(sections: list[dict], stype: str) -> dict:
    return next((s for s in sections if s.get("type") == stype), {})


def _collect_facts(sections: list[dict]) -> dict[str, dict]:
    """field -> fact, across every fact-bearing section."""
    out: dict[str, dict] = {}
    for section in sections:
        for fact in section.get("facts", []) or []:
            field = fact.get("field")
            if field and field not in out:
                out[field] = fact
    return out


def _section(title: str, eyebrow: str, inner: str, *, band: str = "") -> str:
    return (
        f'<section class="{band}"><div class="wrap">'
        f'<div class="section-head reveal">'
        f'<div class="eyebrow">{escape(eyebrow)}</div>'
        f'<h2 class="section-title">{escape(title)}</h2></div>'
        f"{inner}</div></section>"
    )


def render_site(content: dict, *, draft: bool = True) -> str:
    """Return a complete, self-contained HTML document for a site model."""
    name = escape(str(content.get("business_name", "")))
    industry = str(content.get("industry", "generic"))
    palette = palette_for(industry)
    eyebrow, closing_line, cta_label = voice_for(industry)
    css = css_for(palette)

    sections = content.get("sections", []) or []
    hero = _find(sections, "hero")
    facts = _collect_facts(sections)
    subheading = escape(str(hero.get("subheading", "") or ""))
    tagline = content.get("tagline")

    # --- hero -------------------------------------------------------------
    actions = content.get("actions") or []
    action_btns = "".join(
        f'<a class="btn btn-on-photo" href="{escape(str(a.get("url", "#")))}">'
        f'{escape(str(a.get("kind") or a.get("label", "")))}</a>'
        for a in actions[:2]
    )
    photo = content.get("hero_image")
    hero_body = (
        f'<div class="eyebrow">{escape(eyebrow)}</div>'
        f'<h1 class="display">{name}</h1>'
        f'<p class="sub">{subheading or escape(str(tagline or ""))}</p>'
        f'<div class="cta-row">'
        f'<a class="btn btn-primary btn-lg" href="#contact">{escape(cta_label)}</a>'
        f"{action_btns}</div>"
    )
    if photo:
        hero_html = (
            f'<header class="hero">'
            f'<div class="bg" style="background-image:url(&quot;{escape(str(photo))}&quot;)">'
            f'</div><div class="scrim"></div>'
            f'<div class="inner"><div class="wrap">{hero_body}</div></div></header>'
        )
    else:
        hero_html = (
            f'<header class="hero hero--plain"><div class="inner"><div class="wrap">'
            f"{hero_body}</div></div></header>"
        )

    # --- body sections ----------------------------------------------------
    body: list[str] = []
    bands = ["", "band-tint"]
    band_i = 0

    def next_band() -> str:
        nonlocal band_i
        band = bands[band_i % 2]
        band_i += 1
        return band

    offerings = _find(sections, "offerings")
    if offerings.get("items"):
        cards = "".join(
            f'<div class="offer reveal"><span class="num">{n:02d}</span>'
            f'<span class="name">{escape(str(item))}</span></div>'
            for n, item in enumerate(offerings["items"], start=1)
        )
        body.append(_section(str(offerings.get("heading", "What we offer")),
                             "What we do", f'<div class="offer-grid">{cards}</div>',
                             band=next_band()))

    story = _find(sections, "story")
    rating_fact = facts.get("rating")
    if story.get("body") or rating_fact:
        left = (f'<div class="story reveal"><p>{escape(str(story.get("body", "")))}</p></div>'
                if story.get("body") else "")
        right = ""
        if rating_fact:
            value = escape(str(rating_fact.get("value", "")))
            right = (
                f'<div class="stat-card reveal"><div class="big">{value}</div>'
                f'<div class="stars">{_stars(str(rating_fact.get("value", "")))}</div>'
                f'<div class="cap">Average customer rating, verified across '
                f"independent review sites.</div></div>"
            )
        body.append(_section(str(story.get("heading", "About us")), "Our story",
                             f'<div class="story-grid">{left}{right}</div>',
                             band=next_band()))

    hours = _find(sections, "opening_hours")
    if hours.get("items"):
        rows = ""
        for item in hours["items"]:
            text = str(item)
            when, _, times = text.partition(":")
            rows += (
                f'<div class="row"><span class="when">{escape(when.strip())}</span>'
                f'<span class="dots"></span><span>{escape(times.strip())}</span></div>'
                if times else
                f'<div class="row"><span class="when">{escape(text)}</span></div>'
            )
        body.append(_section(str(hours.get("heading", "Hours")), "When we're open",
                             f'<div class="hours reveal">{rows}</div>', band=next_band()))

    gallery = _find(sections, "gallery")
    images = [str(u) for u in (gallery.get("images") or [])]
    if images:
        tiles = "".join(
            f'<button type="button" aria-label="Open image {n}">'
            f'<img src="{escape(u)}" alt="" loading="lazy"></button>'
            for n, u in enumerate(images, start=1)
        )
        body.append(_section(str(gallery.get("heading", "Gallery")), "A look inside",
                             f'<div class="gallery reveal">{tiles}</div>', band=next_band()))

    lightbox = ""
    if images:
        srcs = escape(json.dumps(images), quote=True)
        lightbox = (
            f'<div class="lightbox" data-srcs="{srcs}" role="dialog" aria-modal="true">'
            f'<button class="x" aria-label="Close">✕</button>'
            f'<button class="arrow prev" aria-label="Previous">‹</button>'
            f'<img src="" alt="">'
            f'<button class="arrow next" aria-label="Next">›</button></div>'
        )

    # --- closing / contact ------------------------------------------------
    cards = ""
    if facts.get("address"):
        cards += (f'<div class="contact-card"><div class="k">Find us</div>'
                  f'<div class="v">{escape(str(facts["address"]["value"]))}</div></div>')
    if facts.get("phone"):
        phone = str(facts["phone"]["value"])
        digits = "".join(c for c in phone if c.isdigit() or c == "+")
        cards += (f'<div class="contact-card"><div class="k">Call</div>'
                  f'<div class="v"><a href="tel:{escape(digits)}">{escape(phone)}</a>'
                  f"</div></div>")
    for action in actions[:2]:
        cards += (f'<div class="contact-card"><div class="k">'
                  f'{escape(str(action.get("kind", "Online")))}</div>'
                  f'<div class="v"><a href="{escape(str(action.get("url", "#")))}">'
                  f'{escape(str(action.get("label", "Open")))}</a></div></div>')

    socials = content.get("socials") or []
    socials_html = ""
    if socials:
        links = "".join(
            f'<a href="{escape(str(s.get("url", "#")))}">{escape(str(s.get("name", "")))}</a>'
            for s in socials
        )
        socials_html = f'<div class="socials">{links}</div>'

    closing = (
        f'<section class="closing" id="contact"><div class="wrap">'
        f'<div class="section-head reveal" style="margin-inline:auto;text-align:center;'
        f'align-items:center">'
        f'<div class="eyebrow" style="color:#fff;opacity:.8">Get in touch</div>'
        f'<h2 class="section-title">{escape(closing_line)}</h2>'
        f'<p class="lede">We\'d love to hear from you.</p></div>'
        f'<div class="contact-grid reveal">{cards}</div></div></section>'
    )

    draft_badge = '<div class="draft">Draft proposal · private</div>' if draft else ""

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="{escape(str(tagline or subheading or name))}">
<title>{name}</title>
<style>{css}</style>
</head><body>
<nav class="nav"><div class="wrap bar">
  <a class="brand" href="#top">{name}</a>
  <div class="nav-links"><a href="#contact">Contact</a></div>
</div></nav>
<a id="top"></a>
{hero_html}
{"".join(body)}
{closing}
<footer><div class="wrap bar">
  <span>© {name}</span>
  {socials_html}
</div></footer>
{lightbox}
{draft_badge}
<script>{_JS}</script>
</body></html>"""
