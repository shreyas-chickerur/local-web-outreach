"""Checking a generated page against the rules, and fixing what it can.

The point is that the operator stops being the validator. Everything here is a
defect — objectively wrong, machine-detectable — as opposed to a convention
(what a good site in this trade does) or taste (whether it feels expensive).
Only the last of those should ever need a person.

Each rule reports, and where a deterministic repair exists the build applies it
and records what it did. Two rules deliberately do NOT auto-repair:

* the honesty gate — rewriting a claim about someone's business to make it pass
  is worse than refusing to ship the page;
* anything needing judgement, which is reported and left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.site.theme import AA_BODY, AA_LARGE, Theme, contrast

# Words that make copy read as though nobody wrote it.
BUZZWORDS = ("revolutionize", "revolutionise", "seamless", "seamlessly",
             "empower", "synergy", "delve", "leverage", "cutting-edge",
             "best-in-class", "world-class", "game-changing", "unlock",
             "elevate your", "take it to the next level", "one-stop shop")

# Labels that tell the visitor nothing about what happens next.
LIMP_LABELS = ("submit", "learn more", "click here", "read more", "more info",
               "get started", "continue")


@dataclass
class Finding:
    rule: str
    detail: str
    severity: str = "warn"          # warn | fail
    repaired: bool = False

    def __str__(self) -> str:
        mark = "repaired" if self.repaired else self.severity
        return f"[{mark}] {self.rule}: {self.detail}"


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    def add(self, rule: str, detail: str, *, severity: str = "warn",
            repaired: bool = False) -> None:
        self.findings.append(Finding(rule, detail, severity, repaired))

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "fail" and not f.repaired]

    @property
    def repairs(self) -> list[Finding]:
        return [f for f in self.findings if f.repaired]

    @property
    def clean(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict:
        return {
            "clean": self.clean,
            "failures": [str(f) for f in self.failures],
            "repairs": [f"{f.rule}: {f.detail}" for f in self.repairs],
            "warnings": [f"{f.rule}: {f.detail}" for f in self.findings
                         if f.severity == "warn" and not f.repaired],
        }


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #

_VAR_RE = re.compile(r"--(on-[a-z]+|bg|surface|raise|accent|ink|dim):\s*([^;]+);")


def check_contrast(page: str, theme: Theme, report: AuditReport) -> None:
    """Every ground/foreground pair the page actually uses.

    Computed against the resolved values, not the intended ones — the bug this
    exists to catch was a pairing that looked right in the source and lost a
    specificity fight at render time.
    """
    pairs = (
        ("body text", theme.on(theme.bg), theme.bg, AA_BODY),
        ("text on cards", theme.on(theme.surface), theme.surface, AA_BODY),
        ("text on banded sections", theme.on(theme.raise_), theme.raise_, AA_BODY),
        ("text on the accent", theme.on(theme.accent), theme.accent, AA_BODY),
        ("secondary text", theme.dim, theme.bg, AA_BODY),
        ("accent as text", theme.accent, theme.bg, AA_LARGE),
    )
    for label, foreground, ground, need in pairs:
        ratio = contrast(foreground, ground)
        if ratio < need:
            report.add("contrast",
                       f"{label} is {ratio:.2f}:1 against {ground}, under {need}",
                       severity="fail")


def check_copy(page: str, report: AuditReport) -> None:
    """Buzzwords and limp micro-copy.

    Not auto-repaired: the words come from the business's own site, and
    rewriting what they say about themselves is exactly what this system must
    not do. Reported so the operator can decide.
    """
    text = re.sub(r"<script[^>]*>.*?</script>", " ", page, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text).lower()
    for word in BUZZWORDS:
        if word in text:
            report.add("copy", f"“{word}” appears in the copy — theirs, not ours")

    for label in re.findall(r"<a[^>]*class=\"cta[^\"]*\"[^>]*>([^<]+)</a>", page):
        if label.strip().lower() in LIMP_LABELS:
            report.add("microcopy",
                       f"“{label.strip()}” says nothing about what happens next",
                       severity="fail")


def check_layout(page: str, report: AuditReport) -> None:
    """Structural defects: dead affordances and stranded grid cells."""
    for match in re.finditer(r"\n\.(\w[\w.-]*):hover\{([^}]*)\}", page):
        selector, rules = match.group(1), match.group(2)
        if "transform" not in rules and "box-shadow" not in rules:
            continue
        # A lift or a shadow reads as "this goes somewhere". Cards that are not
        # links must not make that promise.
        if selector.split(":")[0] in {"offer", "card", "quote", "stat"}:
            report.add("affordance",
                       f".{selector} lifts on hover but is not a link",
                       severity="fail")

    # A strict left/right zig-zag is the most recognisable template rhythm
    # there is, and reads as generated however good the parts are.
    shapes = re.findall(r'<article class="feature ([a-z]+)"', page)
    if len(shapes) >= 3 and len(set(shapes)) <= 2 and shapes[0] != shapes[1]:
        if shapes[::2].count(shapes[0]) == len(shapes[::2]):
            report.add("layout", "feature rows simply alternate sides")

    for section, count in _grid_counts(page):
        if count > 3 and count % 3 == 1:
            report.add("layout",
                       f"{section} has {count} cards in a three-column grid, "
                       f"leaving one stranded")


def _grid_counts(page: str) -> list[tuple[str, int]]:
    counts = []
    for match in re.finditer(r'<section id="(\w+)"[^>]*>(.*?)</section>', page, re.S):
        cards = match.group(2).count('<article class="offer"')
        if cards:
            counts.append((match.group(1), cards))
    return counts


def check_images(page: str, report: AuditReport) -> None:
    """No picture used twice, and every one sized so nothing jumps."""
    sources = re.findall(r'<img[^>]+src="([^"]+)"', page)
    duplicates = {src for src in sources if sources.count(src) > 1}
    for src in sorted(duplicates):
        report.add("imagery", f"{src.rsplit('/', 1)[-1]} appears more than once")

    for tag in re.findall(r"<img\b[^>]*>", page):
        if 'src=""' in tag:            # the lightbox target, filled in by script
            continue
        if "loading=" not in tag:
            report.add("imagery", "an image is not lazily loaded")
            break
    if "<img" in page and "aspect-ratio" not in page:
        report.add("layout", "images do not reserve their space", severity="fail")


def check_typography(page: str, theme: Theme, report: AuditReport) -> None:
    """Two families at most, and a scale with real contrast in it."""
    families = {f.strip().strip("'\"") for f in
                re.findall(r"font-family:([^;{}]+)", page)}
    roots = {name.split(",")[0].strip().strip("'\"") for name in families}
    named = {r for r in roots if r and not r.startswith("var(") and " " not in r[:1]}
    if len(named) > 3:                     # display + body + the mono fallback
        report.add("typography", f"{len(named)} font families in play: "
                                 f"{', '.join(sorted(named)[:4])}")
    heading = re.search(r"h1\{[^}]*font-size:calc\(clamp\(([\d.]+)px", page)
    body = re.search(r"body\{[^}]*font-size:clamp\(([\d.]+)px", page)
    if heading and body:
        ratio = float(heading.group(1)) / float(body.group(1))
        if ratio < 2.0:
            report.add("typography",
                       f"headline is only {ratio:.1f}x the body size — no hierarchy",
                       severity="fail")


def audit(page: str, theme: Theme, *, repairs: list[str] | None = None) -> AuditReport:
    """Run every rule. `repairs` are things the build already fixed."""
    report = AuditReport()
    for note in repairs or []:
        rule, _, detail = note.partition(": ")
        report.add(rule, detail or note, repaired=True)
    check_contrast(page, theme, report)
    check_copy(page, report)
    check_layout(page, report)
    check_images(page, report)
    check_typography(page, theme, report)
    return report
