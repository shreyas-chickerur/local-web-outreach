"""Phase 3, Step 3: fills `master_prompt.md`'s template for one business,
from the brief, the playbook, the art direction, the real photographs, and
`copyselect.py`'s own candidate sentence groups — never a new copy source.
Asserts no `{{...}}` token survives, the same defect this round names as
the exact one that hid Milestone's call button and stars in Phase 2.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.design.art_direction import ArtDirection
from app.design.playbooks import content_hash as playbook_hash
from app.site.theme import TYPEFACE_PAIRS

TEMPLATE_PATH = Path(__file__).parent / "master_prompt.md"
_TOKEN_RE = re.compile(r"\{\{[^}]+\}\}")


def template_hash() -> str:
    return hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest()[:12]


def _numbered_copy_list(groups: dict[str, list[str]]) -> str:
    lines = []
    for name, sentences in groups.items():
        lines.append(f"**{name}**")
        for i, sentence in enumerate(sentences):
            lines.append(f"  [{i}] {sentence}")
    return "\n".join(lines)


def _photo_list(photo_vision: dict, photo_labels: dict) -> str:
    lines = []
    for path, info in photo_vision.items():
        label = photo_labels.get(path, info.get("subject", ""))
        hero = " (hero candidate)" if info.get("is_hero_candidate") else ""
        lines.append(f"- `{path}` — {label}: {info.get('alt_text', '')}{hero}")
    return "\n".join(lines)


def fill(*, business: str, business_name: str, trade: str, town: str,
         service_area: str, section_order: str, required_elements: str,
         direction: ArtDirection, photo_vision: dict, photo_labels: dict,
         copy_groups: dict[str, list[str]]) -> str:
    pair = TYPEFACE_PAIRS[direction.type_pair]
    template = TEMPLATE_PATH.read_text()
    values = {
        "business_name": business_name,
        "trade": trade,
        "trade_lower": trade.lower(),
        "town": town,
        "service_area": service_area,
        "section_order": section_order,
        "mood": direction.mood,
        "mood_why": direction.mood_why,
        "type_pair_voice": pair.voice,
        "type_pair_display": direction.type_pair.split("-")[0],
        "type_pair_body": direction.type_pair.split("-")[-1],
        "base": direction.base,
        "ink": direction.ink,
        "accent": direction.accent,
        "accent_name": direction.accent_name,
        "photo_treatment": direction.photo_treatment,
        "signature_device": direction.signature_device,
        "signature_why": direction.signature_why,
        "section_rhythm": " -> ".join(direction.section_rhythm),
        "photo_list": _photo_list(photo_vision, photo_labels),
        "copy_list": _numbered_copy_list(copy_groups),
        "required_elements": required_elements,
    }
    filled = template
    for key, value in values.items():
        filled = filled.replace("{{" + key + "}}", value)
    leftover = _TOKEN_RE.findall(filled)
    if leftover:
        raise ValueError(f"unresolved template tokens: {leftover}")
    return filled


def persist(business: str, filled: str) -> Path:
    path = Path("tests/fixtures/design") / f"{business}.prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"<!-- filled from master_prompt.md ({template_hash()}) and "
        f"playbooks/home_services.md ({playbook_hash('home_services')}) -->\n"
    )
    path.write_text(header + filled)
    return path
