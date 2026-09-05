"""Reading an instruction with a model, and refusing to trust it with prose.

The phrase parser in `iterate.py` matches a fixed vocabulary. Measured against
what an operator actually types (`tools/feedback_census.py`), it understands
about a fifth of it — and the residue is not exotic. "The back to top button
does not work" and "the copy is too long" are ordinary sentences that no table
of phrases will ever cover, because the space of things a person can say about
a page is not enumerable.

So a model reads the sentence. What matters is *where* in the pipeline it sits.

    evidence   what is true about this business   ← corroborated, never invented
    decisions  what the site should be            ← judgement; the model works here
    render     HTML from decisions                ← deterministic, unchanged

The project reached for determinism everywhere because the evidence stage
genuinely needs it. Decisions are a different kind of thing: there is no fact to
get wrong in choosing between a warm palette and a cool one.

Three properties keep this safe:

* **The model emits enum values and integers. Never text.** Every field below is
  checked against a closed set, and the call-to-action *label* is looked up from
  the same table the phrase parser uses rather than being written by the model.
  There is no channel through which a model-authored sentence reaches the page.
* **Anything unrecognised is dropped and reported.** A value not in the set is
  not a smaller change, it is no change plus a line in the diagnostics.
* **The content gate still runs last.** `unsupported()` checks the rendered page
  against the corroborated material immediately before the write, exactly as it
  did before. A model in the loop makes that gate more important, not less.

What the model cannot do is widen the renderer. "Make the logo bigger" has no
field to write to, and the honest answer is to say so and record it — which is
what `unsupported` in the returned dict is for. Understanding and capability are
different problems and this file only solves the first.
"""

from __future__ import annotations

import httpx

from app.adapters import claude
from app.site.iterate import CTA_PHRASES, DEFAULT_SPEC, MOODS
from app.site.plan import SECTION_RULES
from app.site.theme import ACCENT_NAMES

SECTIONS = tuple(key for key, _, _ in SECTION_RULES)
CTA_KINDS = tuple(dict.fromkeys(kind for _, kind, _ in CTA_PHRASES))
# The label belongs to the kind, not to the model. This is the seam that stops
# model-written words reaching a button.
CTA_LABEL = {kind: label for _, kind, label in reversed(CTA_PHRASES)}

# What an instruction can be. The distinction the phrase parser could not make:
# a complaint is not an edit, and treating one as the other is how "the hours
# look cramped" used to make the hours bigger.
KINDS = ("style", "defect", "content", "unsupported")

SYSTEM = """\
You turn one instruction from a website operator into decisions for a static
site generator. You never write copy, headings, or any text that appears on the
page — you only choose from fixed sets of options.

Classify the instruction first:

- "style"       a change to how the site looks or is organised, expressible in
                the fields below.
- "defect"      a report that something is broken, ugly, wrong, or badly placed
                — including questions like "why is this here?" or "what is this
                contrast?". These are bug reports, not edits. Do not change any
                field for these; describe the defect instead.
- "content"     a request to change what the site SAYS about the business
                (facts, wording, claims). You cannot do this: business facts
                come only from corroborated sources. Say what was asked.
- "unsupported" a genuine style request that none of the fields below can
                express. Say plainly what the generator would need to be able
                to do.

Only "style" may set fields. When an instruction mixes a style change with a
complaint, classify it "style", apply the change, and note the complaint.

Fields carry forward: omit a field to leave it as it is. Set it only when the
instruction actually asks for that change.

Write `understood` as short plain phrases addressed to the operator, e.g.
"led with the gallery", "accented navy". Write `unsupported` as what the
generator cannot do, e.g. "cannot change the size of the logo".
"""


def _tool() -> dict:
    return {
        "name": "decide",
        "description": "The decisions this instruction resolves to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": list(KINDS)},
                "mood": {"type": "string", "enum": list(MOODS),
                         "description": "The overall feel of the page."},
                "accent": {"type": "string", "enum": list(ACCENT_NAMES),
                           "description": "The accent colour — the 10% in "
                                          "60-30-10. Not the background."},
                "lead_with": {"type": "string", "enum": list(SECTIONS),
                              "description": "Section hoisted to the top."},
                "emphasis": {"type": "array", "items":
                             {"type": "string", "enum": list(SECTIONS)}},
                "suppress": {"type": "array", "items":
                             {"type": "string", "enum": list(SECTIONS)},
                             "description": "Sections to drop entirely."},
                "cta": {"type": "string", "enum": list(CTA_KINDS),
                        "description": "The primary action. The button's "
                                       "wording is fixed and not yours to set."},
                "next_hero_photo": {
                    "type": "boolean",
                    "description": "True if they want a different lead "
                                   "photograph than the current one."},
                "understood": {"type": "array", "items": {"type": "string"}},
                "unsupported": {"type": "array", "items": {"type": "string"}},
                "defect": {"type": "string",
                           "description": "What they say is wrong, in their "
                                          "terms. Only for kind=defect."},
            },
            "required": ["kind", "understood"],
        },
    }


def _prompt(sentence: str, current: dict) -> str:
    now = {key: current.get(key) for key in DEFAULT_SPEC if key != "instruction"}
    lines = [f"{key}: {value!r}" for key, value in sorted(now.items())]
    return ("The site currently resolves to:\n  " + "\n  ".join(lines)
            + f"\n\nThe operator says:\n  {sentence!r}")


def _enum(value: object, allowed: tuple[str, ...]) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def _enum_list(value: object, allowed: tuple[str, ...]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value
            if isinstance(item, str) and item in allowed]


def _texts(value: object, limit: int = 8) -> list[str]:
    """Diagnostics shown to the operator. Never rendered into a page."""
    if not isinstance(value, list):
        return []
    return [item.strip()[:200] for item in value[:limit]
            if isinstance(item, str) and item.strip()]


def apply_answer(answer: dict, current: dict) -> dict:
    """Validate a model answer and fold it into the configuration.

    Every value is checked against its closed set. This is the whole security
    boundary: a field the model invents, or a value outside the enum, changes
    nothing — it cannot fail open into free text.
    """
    spec: dict = {**DEFAULT_SPEC, **(current or {})}
    spec["emphasis"] = list(spec.get("emphasis") or [])
    spec["suppress"] = list(spec.get("suppress") or [])

    kind = _enum(answer.get("kind"), KINDS) or "unsupported"
    understood = _texts(answer.get("understood"))
    unsupported = _texts(answer.get("unsupported"))
    defect = answer.get("defect")
    defect = defect.strip()[:400] if isinstance(defect, str) else ""

    if kind != "style":
        # A complaint, a request for different facts, or something the renderer
        # cannot do. None of them is an edit, and pretending otherwise is the
        # misread this whole change exists to stop.
        return {**spec, "kind": kind, "understood": understood,
                "unsupported": unsupported, "defect": defect,
                "ignored_tokens": [], "contradictions": []}

    mood = _enum(answer.get("mood"), MOODS)
    if mood:
        spec["mood"] = mood
    accent = _enum(answer.get("accent"), ACCENT_NAMES)
    if accent:
        spec["accent"] = accent
    lead = _enum(answer.get("lead_with"), SECTIONS)
    if lead:
        spec["lead_with"] = lead
        spec["suppress"] = [s for s in spec["suppress"] if s != lead]
    for section in _enum_list(answer.get("emphasis"), SECTIONS):
        if section not in spec["emphasis"]:
            spec["emphasis"].append(section)
        spec["suppress"] = [s for s in spec["suppress"] if s != section]
    for section in _enum_list(answer.get("suppress"), SECTIONS):
        if section not in spec["suppress"]:
            spec["suppress"].append(section)
        spec["emphasis"] = [s for s in spec["emphasis"] if s != section]
        if spec["lead_with"] == section:
            spec["lead_with"] = None
    cta = _enum(answer.get("cta"), CTA_KINDS)
    if cta:
        # The wording comes from our table, never from the answer.
        spec["cta"] = {"kind": cta, "label": CTA_LABEL[cta]}
    if answer.get("next_hero_photo") is True:
        spec["hero_offset"] = int(spec.get("hero_offset") or 0) + 1

    return {**spec, "kind": kind, "understood": understood,
            "unsupported": unsupported, "defect": defect,
            "ignored_tokens": [], "contradictions": []}


def understand(sentence: str, current: dict, *,
               client: httpx.Client | None = None) -> dict:
    """One instruction, read by the model, validated, folded in.

    Raises `ClaudeError` when there is no key or the call fails, so the caller
    can fall back to the phrase parser rather than losing the instruction.
    """
    answer = claude.structured(SYSTEM, _prompt(sentence, current), _tool(),
                               client=client)
    return apply_answer(answer, current)
