"""One signature device per site, and never two.

`BRIEF` §2.3. The evidence for building it now is in the whole-page verdicts
rather than in the ordering: every pair a stranger calls one studio shares
exactly `first_screen` and `architecture`, and differs only on things the
judging rules discount — the paint, the lettering, and what the business
happened to publish. Four pages with the same opening and the same arrangement
and **nothing else designed on them**. The device is the remaining lever that is
designed, is not colour, is not lettering, and is not the arrangement.

Devices that are hero treatments are not devices — those are positions on axis
one, and §2.3 says so. Everything here is a mark on the page below the opening.

Each one is a band, and each renders different markup rather than the same band
under a different name. The project has shipped a value whose only difference
from another was the class attribute once, in the axis weighted heaviest, and
`test_every_device_renders_something_different` is what stops a second.

What each needs is a real constraint, not a formality: a device that cannot be
built from this business's material is not a choice, it is an empty band.
"""

from __future__ import annotations

from app.site.render import Material, e

# Ordered. The fingerprint compares positionally and the census prints them.
DEVICES: tuple[str, ...] = (
    "none",            # nothing supportable — the floor, not a choice
    "ledger",          # ruled tabular figures, the printed-document mark
    "quote",           # one review at display size, full bleed
    "marquee",         # a repeating strip of what they offer
    "stamp",           # a repeated licence or warranty mark
    "index",           # a numbered index of the page down the margin
    "ticker",          # a thin running line of facts
    "margin_note",     # a note set in the margin against the body
    "offset",          # one block knocked out of the grid
    "edge_type",       # the name at display size running off the edge
    "corner_inset",    # a type block inset into the corner of a photograph
    "scroll_gallery",  # a strip of pictures that runs off the side
    "duotone",         # a strip in two tones with one full-colour break
)

DEFAULT = "none"


def available(m: Material, sections: int) -> list[str]:
    """The devices this business's material can carry."""
    can = ["none"]
    if m.rating and m.reviews:
        can += ["ledger", "ticker"]
    if m.quotes:
        can.append("quote")
    if len(m.services) + len(m.products) >= 3:
        can.append("marquee")
    if m.trade_kind in ("trade", "care", "desk"):
        can.append("stamp")
    if sections >= 4:
        can.append("index")
    if m.about:
        can += ["margin_note", "offset"]
    if len(m.name or "") <= 30:
        can.append("edge_type")
    if m.images:
        can.append("corner_inset")
    if len(m.images) >= 4:
        can += ["scroll_gallery", "duotone"]
    return [device for device in DEVICES if device in can]


def render(device: str, m: Material) -> str:
    """The device as a band, from corroborated material only.

    Nothing here writes a sentence about the business. Every string is either a
    fixed label or a value already on `Material`, which is what keeps the
    claims gate satisfied without a second check.
    """
    if device not in available(m, 99):
        # Chosen for a business that cannot carry it: render nothing rather
        # than an empty band or an exception. The identity call is offered only
        # what is available, and a replayed direction from an older corpus is
        # the case this catches.
        return ""
    if device == "ledger":
        rows = [("Rating", f"{m.rating}"), ("Reviews", f"{m.reviews}")]
        if m.services or m.products:
            rows.append(("Services", f"{len(m.services) + len(m.products)}"))
        if m.hours:
            rows.append(("Open", m.hours[0]))
        cells = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>"
                        for k, v in rows)
        return (f'<section class="device" data-device="ledger"><div class="wrap">'
                f'<table class="ledgerfig">{cells}</table></div></section>')
    if device == "quote":
        said = str(m.quotes[0].get("text") or "")[:220].strip()
        return (f'<section class="device" data-device="quote">'
                f'<div class="wrap"><blockquote class="bigquote">'
                f'{e(said)}</blockquote></div></section>')
    if device == "marquee":
        words = [*m.services, *m.products][:8]
        run = "".join(f"<span>{e(w)}</span>" for w in words) * 2
        return (f'<section class="device" data-device="marquee">'
                f'<div class="runner">{run}</div></section>')
    if device == "stamp":
        mark = {"trade": "Licensed &amp; insured", "care": "Registered practice",
                "desk": "Admitted to the bar"}[m.trade_kind]
        marks = "".join(f"<span>{mark}</span>" for _ in range(4))
        return (f'<section class="device" data-device="stamp">'
                f'<div class="wrap"><div class="stamps">{marks}</div>'
                f'</div></section>')
    if device == "index":
        return ""  # rendered as a margin index by `decorate`, not as a band
    if device == "ticker":
        bits = [f"{m.rating} stars" if m.rating else "",
                f"{m.reviews} reviews" if m.reviews else "",
                m.address or "", m.hours[0] if m.hours else ""]
        line = "".join(f"<span>{e(b)}</span>" for b in bits if b) * 3
        return (f'<section class="device" data-device="ticker">'
                f'<div class="tickline">{line}</div></section>')
    if device == "margin_note":
        return (f'<section class="device" data-device="margin_note">'
                f'<div class="wrap"><aside class="marginnote">'
                f'<b>{e(m.name)}</b></aside>'
                f'<p class="notebody">{e(m.about)}</p></div></section>')
    if device == "offset":
        return (f'<section class="device" data-device="offset">'
                f'<div class="wrap"><div class="knock">'
                f'<p>{e(m.about)}</p></div></div></section>')
    if device == "edge_type":
        return (f'<section class="device" data-device="edge_type">'
                f'<div class="runoff">{e(m.name)}</div></section>')
    if device == "corner_inset":
        return (f'<section class="device" data-device="corner_inset">'
                f'<div class="insetshot" style="background-image:'
                f'url(&quot;{e(m.images[0])}&quot;)">'
                f'<div class="insetblock"><b>{e(m.name)}</b></div>'
                f'</div></section>')
    if device == "scroll_gallery":
        tiles = "".join(
            f'<img src="{e(url)}" alt="{e(m.alt_for(url))}" loading="lazy">'
            for url in m.images[:8])
        return (f'<section class="device" data-device="scroll_gallery">'
                f'<div class="scrollstrip">{tiles}</div></section>')
    if device == "duotone":
        tiles = "".join(
            f'<img src="{e(url)}" alt="{e(m.alt_for(url))}" loading="lazy"'
            f'{"" if n == 1 else " data-tone=on"}>'
            for n, url in enumerate(m.images[:4]))
        return (f'<section class="device" data-device="duotone">'
                f'<div class="tonestrip">{tiles}</div></section>')
    return ""


def decorate(body: str, device: str, order: list[str]) -> str:
    """The devices that are not a band of their own.

    `index` numbers the page's own sections down the margin, so it has to be
    applied to the assembled body rather than inserted into it.
    """
    if device != "index":
        return body
    import re

    count = {"n": 0}

    def number(match: re.Match[str]) -> str:
        count["n"] += 1
        return f'{match.group(0)[:-1]} data-index="{count["n"]:02d}">'

    return re.sub(r"<section\b[^>]*>", number, body)
