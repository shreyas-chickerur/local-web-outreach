"""What the page says, and whether anything said it first.

This is the inventory, not a gate. It never refuses a build. It walks a
finished page, writes down every claim it can find, and says for each one
whether the brief or the capture of the business's own site supports it,
contradicts it, or is silent. The silence is the interesting part: a
fabricated date and a true-but-unstated one look identical from here, and
pretending otherwise is how a checker starts lying to the person reading it.

So the verdicts are deliberately few:

  corroborated  the source says this, and the source's words are attached
  contradicted  a field the brief marked verified says something else
  unsourced     nothing either way

`contradicted` is narrow on purpose. It only fires on the handful of fields
the brief actually verifies against two independent sources — address, phone,
hours — because those are the only places a machine can be sure, and a
checker that cries wolf gets ignored exactly when it is right.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from html import unescape

# Text that carries a factual assertion: a number, a date, a credential, an
# award, a superlative, a span of years. Prose without one of these is style,
# and style is not this module's business.
CLAIMY = re.compile(
    r"\d"
    r"|award|nominee|nominated|winner|james beard|michelin"
    r"|licensed|insured|certified|accredited|bonded|registered"
    r"|since|established|est\.|founded|family-owned|family owned"
    r"|voted|rated|best|first|only|oldest|largest"
    r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
    r"|thirty|forty|fifty|hundred|thousand)\b",
    re.IGNORECASE,
)

_TAG = re.compile(r"<[^>]+>")
_DROP = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS = re.compile(r"\s+")


_BLOCK = re.compile(
    r"</?(?:p|div|li|ul|ol|section|article|header|footer|nav|figure|figcaption"
    r"|h[1-6]|br|tr|td|th|blockquote|dd|dt|button|a)\b[^>]*>",
    re.IGNORECASE)


def _plain(html: str) -> str:
    """The page as a reader meets it: no markup, no scripts, no styles.

    Block boundaries become line breaks first. Without that the whole page
    collapses into one string, and a claim check that reads one string finds
    one enormous sentence in which every atom is present somewhere — which
    is the same as checking nothing.
    """
    text = _DROP.sub(" ", html)
    text = _BLOCK.sub("\n", text)
    text = unescape(_TAG.sub(" ", text))
    return "\n".join(_WS.sub(" ", line).strip() for line in text.split("\n"))


_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
    "hundred": "100", "thousand": "1000",
}


def _stem(word: str) -> str:
    """Enough of a word to survive a change of tense or number.

    The source says the family "purchased" the property and the page says
    "purchases". That is the same fact, and a checker that calls it unsourced
    trains the reader to ignore it.
    """
    for ending in ("ing", "ies", "ed", "es", "s"):
        if len(word) > len(ending) + 3 and word.endswith(ending):
            return word[: -len(ending)] + ("y" if ending == "ies" else "")
    return word


def _fold(text: str) -> str:
    """Compare on meaning, not on typography.

    Menus are full of curly apostrophes, en dashes and accented producers;
    a capture written with straight quotes must still match a page that
    renders them properly, or every dish becomes an unsourced claim.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"')
                .replace("—", "-").replace("–", "-")
                .replace(" ", " ").replace("&amp;", "&")
                .replace("&mdash;", "-").replace("&ndash;", "-")
                .replace("&middot;", ".").replace("&rsquo;", "'"))
    text = _WS.sub(" ", unescape(text).lower())
    # "fifteen Texas farms" and "15 named" are the same claim.
    return re.sub(r"\b[a-z]+\b",
                  lambda m: _NUMBER_WORDS.get(m.group(0), m.group(0)), text)


# The pieces of a sentence a source has to contain for the sentence to count
# as supported: figures, years, money, and capitalised names. Ordinary words
# are skipped — every page contains "the".
# Figures, capitalised names, and long ordinary words. The last of those
# is what catches a paraphrase: "has been somebody's livelihood for a
# century" contains no number and no proper noun, and a checker reading
# only those would wave it through.
_ATOM = re.compile(r"\b\d[\d,.:/|-]*\b|\b[A-Z][A-Za-z'&.-]{2,}\b|\b[a-z][a-z'-]{6,}\b")
_STOP = frozenset("""
the and for with from this that they them their there here what when where
our your a an of in on at to by is are was were be been it its as or but
not no all any each every some more most other than then also into out up
down over under again further once about against between through during
before after above below only own same so too very can will just should now
dinner lunch menu menus page site website home about contact hours open
""".split())


def _atoms(sentence: str) -> dict[str, str]:
    """The checkable pieces of a sentence: {what we match on: what it says}.

    The match is on a stem so a change of tense does not invent a finding, but
    a person is shown the word they will actually see on the page. Telling
    somebody to check \u201cnoth\u201d because the page says \u201cnothing\u201d
    is how a tool loses their trust.
    """
    found: dict[str, str] = {}
    for raw in _ATOM.findall(sentence):
        atom = _stem(_fold(raw).strip(".,:;|"))
        spelled = raw[:1].isalpha() and atom.isdigit()
        if not atom or atom in _STOP or len(atom) < 3:
            # A bare small number ("5", "12") is far too common to carry meaning
            # on its own; it only counts inside a longer figure. A number the
            # page spelled out is different — "fifteen farms" is a claim, and
            # somebody chose to write it.
            if not spelled and not (atom.isdigit() and len(atom) >= 4):
                continue
        found.setdefault(atom, raw.strip(".,:;|"))
    return found


@dataclass
class Finding:
    """One thing to look at, and enough to look at it with.

    Three fields carry the weight. `locator` says WHERE — a tag, a selector, a
    filename — because "images with no width and height" is a chore and
    "<img src=short-rib.jpg>, and five others" is a task. `quote` is what the
    page has now and `evidence` is what it should have instead, so the two can
    be set side by side and read rather than interpreted.
    """

    stage: str                 # 'claim' or 'technical'
    verdict: str               # corroborated | contradicted | unsourced |
                               # assembled | wording | defect | unmeasured
    title: str
    detail: str = ""
    locator: str = ""          # where on the page, for a person to read
    # Where on the page, for the annotation layer to find. Either
    # "css:<selector>", "text:<needle>", or "page" for something that lives in
    # the head and has nothing visible to point at.
    anchor: str = "page"
    quote: str = ""            # what the page has
    evidence: str = ""         # what the source says, or what it should be
    resources: list[dict] = field(default_factory=list)

    def as_row(self) -> dict:
        return {"stage": self.stage, "verdict": self.verdict, "title": self.title,
                "detail": self.detail, "locator": self.locator,
                "anchor": self.anchor, "quote": self.quote,
                "evidence": self.evidence, "resources": json.dumps(self.resources)}


_FIGURE = re.compile(r"^\d|^[A-Z0-9]")


def _unsourced(sentence: str, missing: dict[str, str],
               links: list[dict]) -> Finding:
    """Say what to check, not just that something is wrong.

    The title used to be the whole sentence, which left the reader to work out
    which word was the problem. It now names the word, and the detail says what
    kind of thing it is: a figure or a name somebody could ring up and confirm,
    or the page's own wording, which no source will ever settle.
    """
    words = sorted(set(missing.values()))
    shown = ", ".join(f"\u201c{w}\u201d" for w in words[:3])
    more = f" and {len(words) - 3} more" if len(words) > 3 else ""
    # A figure or a proper noun is something a person can ring up and confirm —
    # including a figure the page spelled out, which folds to digits. An
    # ordinary lower-case word is the page's own prose, and no amount of
    # checking will produce a source for it.
    checkable = [word for stem, word in missing.items()
                 if any(ch.isdigit() for ch in stem + word)
                 or word[:1].isupper()]

    if checkable:
        return Finding(
            stage="claim", verdict="unsourced",
            title=f"Check {shown}{more}",
            detail=(f"The page says {shown}{more}. Nothing in the brief or in "
                    "the capture of their own site contains it, in any spelling "
                    "— not as a figure, not spelled out. The generator wrote it: "
                    "either it came from somewhere nobody recorded, or it is "
                    "invented. Confirm it against their site or ask them, then "
                    "say which."),
            anchor="text:" + sentence[:80], quote=sentence, resources=links)

    # Nothing here is a figure or a name, which means no source will ever
    # settle it. Asking somebody to "verify" the word "livelihood" wastes their
    # afternoon; what they can do is read the sentence and decide whether it
    # should stay. That is a different job, so it gets a different verdict and
    # sits in its own group rather than among the facts.
    return Finding(
        stage="claim", verdict="wording",
        title=f"Read it — {shown}{more} is the page's own phrasing",
        detail=("This is not a fact the business published, so there is nothing "
                "to check it against. Decide whether it is a fair thing to say "
                "in their voice, and rewrite it if it is not."),
        anchor="text:" + sentence[:80], quote=sentence, resources=links)


# ---------------------------------------------------------------- the claims


def _sentences(text: str) -> list[str]:
    """One line per block of the page, then split long prose on sentences."""
    out: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) <= 3:
            continue
        for part in re.split(r"(?<=[.!?])\s+", line) if len(line) > 220 else [line]:
            part = part.strip()
            if len(part) > 3:
                out.append(part)
    return out


def _verified_fields(brief: dict) -> dict[str, str]:
    out = {}
    for fact in brief.get("facts") or []:
        if fact.get("confidence") == "verified" and fact.get("value"):
            out[str(fact.get("field"))] = str(fact["value"])
    return out


def inventory(html: str, brief: dict, capture: str,
              sources: list[dict] | None = None) -> list[Finding]:
    """Every claim the page makes, with the source's own words where there is one."""
    haystack = _fold(capture) + " " + _fold(json.dumps(brief, default=str))
    # A passage is a line, or a blank-line separated block: a claim split over
    # two printed lines of the same paragraph is still one thing somebody said.
    lines = [ln for ln in capture.splitlines() if ln.strip()]
    passages = list(lines)
    # A menu entry and its dietary tag often sit on neighbouring lines. Three
    # consecutive lines still count as one thing somebody wrote; the whole
    # capture does not.
    passages += [" ".join(lines[i:i + 3]) for i in range(len(lines) - 1)]
    passages += [b for b in re.split(r"\n\s*\n", capture) if b.strip()]
    links = sources or []

    findings: list[Finding] = []
    seen: set[str] = set()
    for sentence in _sentences(_plain(html)):
        if not CLAIMY.search(sentence):
            continue
        key = _fold(sentence)
        if key in seen or len(key) < 8:
            continue
        seen.add(key)

        atoms = _atoms(sentence)
        if not atoms:
            continue
        missing = {a: word for a, word in atoms.items() if a not in haystack}

        if not missing:
            # Every atom exists somewhere in the sources. That is not the same
            # as the SENTENCE being sourced: "opened in 2013" and "fifteen
            # farms" can both be true while the sentence joining them is
            # something nobody said. So the sentence only counts as
            # corroborated when one passage carries all of it; when the parts
            # are scattered, it is assembled, and a person decides.
            quote = ""
            for passage in passages:
                if all(a in _fold(passage) for a in atoms):
                    quote = passage.strip()
                    break
            if quote:
                findings.append(Finding(
                    stage="claim", verdict="corroborated",
                    title=sentence[:120],
                    detail="One passage in the source carries every figure and name "
                           "in this sentence.",
                    anchor="text:" + sentence[:80],
                    quote=sentence, evidence=quote[:400], resources=links))
            else:
                findings.append(Finding(
                    stage="claim", verdict="assembled",
                    title="Check the sentence — its parts come from "
                          "different places",
                    detail="Every figure and name in it appears in the source, "
                           "but no one passage says the whole thing. The join "
                           "is the page's, not the business's, so read it and "
                           "decide whether it is a fair summary.",
                    anchor="text:" + sentence[:80],
                    quote=sentence, resources=links))
        else:
            findings.append(_unsourced(sentence, missing, links))
    return findings


def contradictions(html: str, brief: dict,
                   sources: list[dict] | None = None) -> list[Finding]:
    """Only where the brief is certain: two independent sources agreed."""
    page = _fold(_plain(html))
    out: list[Finding] = []
    for field_name, value in _verified_fields(brief).items():
        if field_name not in ("phone", "address"):
            continue
        digits = re.sub(r"\D", "", value)
        if field_name == "phone":
            present = digits[-10:] in re.sub(r"\D", "", _plain(html))
        else:
            head = _fold(value.split(",")[0])
            present = head in page
        if not present:
            out.append(Finding(
                stage="claim", verdict="contradicted",
                title=f"The page does not carry the verified {field_name}",
                detail=f"The brief has {field_name} as {value!r}, corroborated by two "
                       f"independent sources, and it does not appear on the page.",
                quote="", evidence=value, resources=sources or []))
    return out


# ------------------------------------------------------------- the mechanics


_ANCHOR = re.compile(r'href="#([^"]+)"')
_HREF = re.compile(r'href="([^"]*)"')
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def _hours_schedule(value: str) -> tuple[list[dict], str]:
    """Turn "Mon-Wed 5pm-9pm · Thu-Sat 5pm-10pm" into what a search engine reads.

    Returns the specification and a plain sentence about whatever could not be
    parsed, because a half-read set of hours published as fact is worse than
    none: the page would tell Google the kitchen is open on a night it is not.
    """
    days = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
            "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}
    order = list(days)
    spec, unread = [], []
    for chunk in re.split(r"[·|,;]", value or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = re.match(
            r"(?i)([a-z]{3})[a-z]*\.?\s*(?:[-–—]\s*([a-z]{3})[a-z]*\.?)?\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[-–—]\s*"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", chunk)
        if not match:
            unread.append(chunk)
            continue
        first, last, h1, m1, mer1, h2, m2, mer2 = match.groups()
        first, last = first.lower(), (last or first).lower()
        if first not in days or last not in days:
            unread.append(chunk)
            continue
        span = order[order.index(first):order.index(last) + 1] or [first]

        def clock(hour: str, minute: str | None, meridiem: str) -> str:
            value = int(hour) % 12 + (12 if meridiem.lower() == "pm" else 0)
            return f"{value:02d}:{minute or '00'}"

        spec.append({"@type": "OpeningHoursSpecification",
                     "dayOfWeek": [days[d] for d in span],
                     "opens": clock(h1, m1, mer1), "closes": clock(h2, m2, mer2)})
    note = ("Could not read: " + "; ".join(unread)) if unread else ""
    return spec, note


def structured_data(html: str, brief: dict) -> list[Finding]:
    """What a search engine can read about this business, against what we know.

    Not a box-ticking "no JSON-LD" complaint. The brief already holds the
    address, phone and hours, corroborated. So either the page carries them in
    machine-readable form and they agree with the brief, or the finding shows
    the exact block that should be there, built from those same facts. The
    reviewer compares two things rather than being told a standard is unmet.
    """
    facts = {f.get("field"): f for f in (brief.get("facts") or [])}

    def value(field_name: str) -> str:
        return str((facts.get(field_name) or {}).get("value") or "")

    name = str(brief.get("name") or "")
    street, city, region, postcode = "", "", "", ""
    address = value("address")
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 3:
        street, city = parts[0], parts[1]
        tail = parts[2].split()
        region = tail[0] if tail else ""
        postcode = tail[1] if len(tail) > 1 else ""

    schedule, unread = _hours_schedule(value("hours"))
    block: dict = {"@context": "https://schema.org", "@type": "Restaurant",
                   "name": name}
    if brief.get("website_url"):
        block["url"] = brief["website_url"]
    if value("phone"):
        block["telephone"] = value("phone")
    if address:
        block["address"] = {"@type": "PostalAddress", "streetAddress": street,
                            "addressLocality": city, "addressRegion": region,
                            "postalCode": postcode, "addressCountry": "US"}
    if brief.get("latitude") and brief.get("longitude"):
        block["geo"] = {"@type": "GeoCoordinates", "latitude": brief["latitude"],
                        "longitude": brief["longitude"]}
    if schedule:
        block["openingHoursSpecification"] = schedule

    missing = [n for n, present in (("name", name), ("address", address),
                                    ("phone", value("phone")),
                                    ("hours", bool(schedule)))
               if not present]
    where = [{"label": "Paste the block here to test it",
              "url": "https://search.google.com/test/rich-results"},
             {"label": "What each field means",
              "url": "https://schema.org/Restaurant"}]

    ready = json.dumps(block, indent=2)
    existing = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                         html, re.DOTALL)

    if not existing:
        detail = ("Search engines read this block, not the visible page, when they "
                  "decide whether to show the hours, the address and a reservation "
                  "link directly in a result. There is no block on the page. The "
                  "brief already holds what it needs, so the version below is built "
                  "from the same corroborated facts — check it, then it can be "
                  "pasted into the page's head.")
        if missing:
            detail += (" The brief has nothing for: " + ", ".join(missing)
                       + ", so those are absent from the block too.")
        if unread:
            detail += " " + unread + " — left out rather than guessed."
        return [Finding("technical", "defect",
                        "Nothing on this page tells Google what business it is",
                        detail, locator="<head> — no application/ld+json block",
                        quote="(nothing on the page)", evidence=ready,
                        resources=where)]

    # There is a block: check it against the brief rather than praising it.
    try:
        published = json.loads(existing.group(1))
    except ValueError:
        return [Finding("technical", "defect",
                        "The structured-data block is not valid JSON",
                        "A search engine will skip it entirely.",
                        locator="<script type=\"application/ld+json\">",
                        quote=existing.group(1)[:400], evidence=ready,
                        resources=where)]

    found: list[Finding] = []
    checks_ = (("telephone", value("phone"), "phone"),
               ("name", name, "name"))
    for key, expected, label in checks_:
        got = str(published.get(key) or "")
        if expected and _fold(got) != _fold(expected):
            found.append(Finding(
                "technical", "contradicted",
                f"The structured data gives a different {label} from the brief",
                "This is what a search engine will believe, and it disagrees with "
                "the two sources that corroborated the brief.",
                locator=f"application/ld+json → {key}",
                quote=got or "(absent)", evidence=expected, resources=where))
    if not found:
        found.append(Finding(
            "technical", "corroborated",
            "The structured data agrees with the brief",
            "Name, phone and address in the machine-readable block match the "
            "corroborated facts.",
            locator="application/ld+json",
            quote=json.dumps(published, indent=2)[:600], evidence=ready,
            resources=where))
    return found


def _attr(tag: str, name: str) -> str:
    """One attribute's value, or an empty string. Never None: every caller
    here goes straight on to strip or split it."""
    found = re.search(rf'{name}="([^"]*)"', tag)
    return found.group(1) if found else ""


def mechanics(html: str, brief: dict | None = None) -> list[Finding]:
    """Defects a browser is not needed to see — each one saying where it is."""
    brief = brief or {}
    out: list[Finding] = []

    ids = set(re.findall(r'id="([^"]+)"', html))
    for target in sorted({a for a in _ANCHOR.findall(html) if a not in ids}):
        label = re.search(rf'href="#{re.escape(target)}"[^>]*>([^<]{{0,60}})', html)
        out.append(Finding(
            "technical", "defect", f"The link to \u201c{target}\u201d goes nowhere",
            "Clicking it does nothing: no element on the page carries that id.",
            locator=f'<a href="#{target}"> — '
                    f'{(label.group(1).strip() if label else "")!r}',
            anchor=f'css:a[href="#{target}"]',
            quote=f'href="#{target}"',
            evidence=f'an element with id="{target}"'))

    for href in [h for h in _HREF.findall(html) if h.strip() in ("", "#")]:
        out.append(Finding(
            "technical", "defect", "A link with no destination",
            "It looks clickable and does nothing.",
            locator=f'href="{href}"', anchor=f'css:a[href="{href}"]',
            quote=f'href="{href}"',
            evidence="a real destination, or plain text instead of a link"))

    # Photographs, one finding per picture, each pinned to that picture. A
    # single row saying "6 of 6 images" is a number; six pins on six
    # photographs is a list of things somebody can actually go and fix.
    home = re.sub(r"^https?://(?:www\.)?([^/]+).*", r"\1",
                  str(brief.get("website_url") or "")) or None
    for tag in _IMG.findall(html):
        src = _attr(tag, "src")
        file = src.rsplit("/", 1)[-1][:52] or "(no src)"
        alt = _attr(tag, "alt")
        faults, why = [], []
        if not alt.strip():
            faults.append("no alt text")
            why.append("Alt text is what a screen reader reads aloud, and what "
                       "stands in when the picture does not load.")
        if "width=" not in tag or "height=" not in tag:
            faults.append("no width and height")
            why.append("Without them the browser cannot hold the space before "
                       "the picture arrives, so the page jumps as it loads.")
        if home and home in src:
            faults.append("served by the old site")
            why.append(f"It loads from {home} — the site this page replaces. "
                       "Until the file is copied across, this page depends on "
                       "that server staying up.")
        if not faults:
            continue
        out.append(Finding(
            "technical", "defect", f"{file} — {', '.join(faults)}",
            " ".join(why), locator=tag[:160],
            anchor=f'css:img[src="{src}"]',
            quote=tag[:300],
            evidence=f'<img src="{file}" width="1600" height="1000" '
                     f'alt="{alt or "what the picture shows"}" loading="lazy">'))

    title = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    description = re.search(r'<meta name="description" content="([^"]*)"', html)
    page_title = (title.group(1).strip() if title else "")
    page_text = description.group(1) if description else ""

    if not description:
        out.append(Finding(
            "technical", "defect", "The page has no description",
            "Google writes its own from whatever it finds on the page, and what it "
            "picks is usually the navigation.",
            locator="<head> — no <meta name=\"description\">",
            quote="(absent)",
            evidence='<meta name="description" content="…">'))
    elif len(page_text) > 160:
        out.append(Finding(
            "technical", "defect",
            f"The description is {len(page_text)} characters; results cut near 160",
            "Everything after the marker is thrown away in the search result, so "
            "the sentence should end before it.",
            locator='<meta name="description">',
            quote=page_text[:160] + "  ⟵ cut  " + page_text[160:],
            evidence=page_text[:157].rsplit(" ", 1)[0] + "."))

    if 'property="og:' not in html:
        out.append(Finding(
            "technical", "defect",
            "Sharing this link shows no title, no picture and no words",
            "Paste the address into a message, a post or a group chat and it "
            "arrives as a bare address. These four lines are what fills in the "
            "card that appears instead.",
            locator="<head> — no og: tags",
            quote="(nothing on the page)",
            evidence=(f'<meta property="og:title" content="{page_title}">\n'
                      f'<meta property="og:description" content="{page_text[:120]}">\n'
                      '<meta property="og:image" content="…a photograph, 1200×630…">\n'
                      '<meta property="og:type" content="restaurant">'),
            resources=[{"label": "See how a link will look",
                        "url": "https://www.opengraph.xyz/"}]))

    if 'rel="canonical"' not in html:
        out.append(Finding(
            "technical", "defect",
            "No canonical address, so duplicates of this page compete with it",
            "The same page is usually reachable several ways — with and without "
            "www, with tracking parameters on the end. This line names one of "
            "them as the real one, so the others do not split its ranking.",
            locator="<head> — no <link rel=\"canonical\">",
            quote="(absent)",
            evidence=f'<link rel="canonical" href="{brief.get("website_url") or "…"}">'))

    headings = re.findall(r"<h([1-6])\b", html)
    if headings.count("1") != 1:
        found = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        out.append(Finding(
            "technical", "defect",
            f"The page has {headings.count('1')} level-one headings",
            "A page says what it is once. More than one, or none, and a search "
            "engine has to guess which is the subject.",
            locator="<h1>", anchor="css:h1",
            quote="\n".join(_WS.sub(" ", _TAG.sub("", h)).strip() for h in found)
                  or "(none)",
            evidence="exactly one <h1>, carrying the name of the business"))

    out.extend(structured_data(html, brief))
    return out


# The old name, kept so nothing that imported it breaks.
def markup(html: str) -> list[Finding]:
    return mechanics(html, {})


def external_hosts(html: str) -> list[str]:
    return sorted({re.sub(r"^https?://([^/]+).*", r"\1", h)
                   for h in _HREF.findall(html) if h.startswith("http")})
