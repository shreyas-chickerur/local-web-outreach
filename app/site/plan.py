"""What the site will be, decided before any HTML exists.

The plan is the change that makes feedback cheap. Every decision that used to
be buried inside a rendering function — which sections appear, in what order,
what each is called, which photograph each gets, what the button says — is
resolved here into a small object you can read in one glance.

Three things follow from that:

* **You can correct a plan before it becomes a page.** Reviewing a dozen lines
  of structure is a different activity from reviewing a rendered site and
  describing what is wrong with it.
* **Feedback edits the plan, so it either lands or says why not.** An
  instruction that changes a field changes the page; one that cannot is
  reported rather than half-applied.
* **The renderer stops making decisions.** It emits what the plan says, which
  is what makes the output predictable from the plan alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.site.density import calculate_density_signal
from app.site.spec import SiteSpec


@dataclass
class PlannedSection:
    """One section, fully decided."""

    key: str
    eyebrow: str = ""
    heading: str = ""
    density: dict = field(default_factory=dict)
    items: list = field(default_factory=list)
    text: str = ""
    images: list[str] = field(default_factory=list)
    ground: str = "base"          # base | raise | accent
    note: str = ""                # why it looks the way it does

    def summary(self) -> str:
        bits = [self.key]
        if self.items:
            bits.append(f"{len(self.items)} items")
        if self.images:
            bits.append(f"{len(self.images)} photos")
        if self.density.get("profile"):
            bits.append(self.density["profile"])
        return " · ".join(bits)


@dataclass
class SitePlan:
    """The whole site, before it is a page."""

    name: str
    mood: str
    layout_bias: str = ""
    hero_photo: str | None = None
    hero_line: str = ""
    hero_facts: list[str] = field(default_factory=list)
    cta_kind: str | None = None
    cta_label: str = ""
    cta_href: str = ""
    sections: list[PlannedSection] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)   # asked for, no data
    unused_images: list[str] = field(default_factory=list)

    @property
    def order(self) -> list[str]:
        return [s.key for s in self.sections]

    def section(self, key: str) -> PlannedSection | None:
        return next((s for s in self.sections if s.key == key), None)

    def as_dict(self) -> dict:
        """The shape the operator reviews and the UI renders."""
        return {
            "name": self.name,
            "mood": self.mood,
            "layout": self.layout_bias,
            "hero": {"photo": self.hero_photo, "line": self.hero_line,
                     "facts": self.hero_facts},
            "cta": {"kind": self.cta_kind, "label": self.cta_label,
                    "href": self.cta_href},
            "sections": [{"key": s.key, "heading": s.heading,
                          "eyebrow": s.eyebrow, "items": len(s.items),
                          "photos": len(s.images),
                          "density": s.density.get("profile", ""),
                          "note": s.note} for s in self.sections],
            "dropped": self.dropped,
            "spare_photos": len(self.unused_images),
        }

    def outline(self) -> str:
        """One line per section — the thing worth reading before a render."""
        lines = [f"{self.name} — {self.mood} / {self.layout_bias}"]
        if self.cta_label:
            lines.append(f"  action: {self.cta_label} -> {self.cta_href}")
        for section in self.sections:
            lines.append(f"  {section.summary()}")
        for missing in self.dropped:
            lines.append(f"  (not built) {missing}")
        return "\n".join(lines)


def plan_density(items: list) -> dict:
    """Exposed so a caller can see why a section is laid out as it is."""
    return dict(calculate_density_signal(items))


def apply_order(keys: list[str], spec: SiteSpec) -> list[str]:
    """Ordering, in one place, so the rule is inspectable rather than implied."""
    order = [k for k in keys if k not in set(spec.suppress or ())]
    if spec.lead_with in order:
        order.remove(spec.lead_with)
        order.insert(1 if "hero" in order else 0, spec.lead_with)
    for section in reversed(spec.emphasis or []):
        if section in order and order.index(section) > 2:
            order.remove(section)
            order.insert(min(2, len(order)), section)
    return order


# --------------------------------------------------------------------------- #
# Resolving a plan from the material
# --------------------------------------------------------------------------- #

# What each section needs before it is worth building, and how it is titled.
# Keeping this as data rather than scattered `if` statements is what lets the
# plan explain itself.
SECTION_RULES: tuple[tuple[str, str, str], ...] = (
    ("stats", "", "By the numbers"),
    ("recognition", "Recognition", ""),
    ("services", "", ""),
    ("menu", "On the menu", "What we serve"),
    ("gallery", "Gallery", "Have a look around"),
    ("about", "About", ""),
    ("features", "", ""),
    ("partners", "Sourcing", ""),
    ("reviews", "Reviews", ""),
    ("hours", "Hours", ""),
    ("contact", "Visit", "Come and see us"),
)

NO_DATA = {
    "menu": "they publish no prices we could read",
    "gallery": "not enough photographs for a gallery",
    "services": "their site does not list what they offer",
    "reviews": "no reviews with text came back",
    "stats": "not enough numbers we can stand behind",
    "recognition": "no award is published on their site",
    "partners": "their site does not list who they buy from",
    "features": "their site has no other sections to carry over",
    "about": "their site has no text about themselves",
    "hours": "no source publishes their opening hours",
    "contact": "no address, phone or email to show",
}

# Which sections sit on the raised ground. Alternating is decided once, here,
# rather than by each section guessing.
RAISED = {"menu", "reviews", "hours", "recognition"}
