"""BRIEF §5, and BRIEF §4's own invariant list ("design system,
compositions, copy selection, vision, signature device" — persist every
model answer and never re-ask on rebuild): the model selects and orders
the business's own sentences, and never authors one.

Given named groups of source sentences, returns which indices to keep
and in what order, per group — never retyped text. Returning indices
makes verbatim provenance true by construction: the rendered sentence is
always `sentences[i]` from the exact list handed in, never the model's
own retelling of it, so there is nothing for `app.site.provenance` to
catch here by design, not by luck.

Frozen once per lead (see `tools/make_fixtures.py`'s `freeze_vision`,
which now folds this in too) and replayed — never re-asked on a rebuild,
the same guarantee every other model answer in this system already
carries.
"""

from __future__ import annotations

import re

from app.adapters import claude


def groups_for(material) -> dict[str, list[str]]:
    """The prose groups this lead has to select from — the exact
    candidates `_about()`/`_features()` derive at render time, before any
    selection or length trim, so a frozen answer's indices always point
    at the same sentence they were chosen from.
    """
    from app.site.render import drop_dangling, feature_candidates

    groups: dict[str, list[str]] = {}
    story = material.blocks_of("story")
    about_text = story[0]["text"] if story else material.about
    if about_text:
        groups["about"] = [
            s.strip() for s in re.split(
                r"(?<=[.!?])\s+", drop_dangling(about_text).strip())
            if s.strip()]

    for i, block in enumerate(feature_candidates(material)):
        sentences = [
            s.strip() for s in re.split(
                r"(?<=[.!?])\s+", drop_dangling(block["text"]).strip())
            if s.strip()]
        if sentences:
            groups[f"feature_{i}"] = sentences
    return groups

SYSTEM = (
    "You are choosing which of a business's own sentences to keep on their "
    "generated website, and in what order. You may only select from the "
    "sentences given — you never write a new one, rephrase one, or combine "
    "parts of two into one. For each named group, return the indices of the "
    "sentences worth keeping, in the order they should read, dropping "
    "filler, repetition, or anything that reads as generic. Keep at least "
    "one sentence per group unless every single one is pure filler.")


def _tool(groups: dict[str, list[str]]) -> dict:
    return {
        "name": "select_copy",
        "description": "Which sentences to keep, per group, and their order.",
        "input_schema": {
            "type": "object",
            "properties": {
                name: {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": f"indices into this group's {len(sentences)} "
                                   f"sentences (0-{len(sentences) - 1}), in "
                                   f"the order to show them",
                }
                for name, sentences in groups.items()
            },
            "required": list(groups.keys()),
        },
    }


def select(groups: dict[str, list[str]], *,
           client=None) -> dict[str, list[int]]:
    """`{group_name: [sentence, ...]}` in, `{group_name: [index, ...]}` out.

    Empty (never a guess) without a key, without groups, or if the call
    fails — the caller's own fallback is the same deterministic ordering
    that shipped before this existed, so an empty result here is a
    complete, valid answer, not a partial one.
    """
    groups = {name: list(sentences) for name, sentences in groups.items()
             if sentences}
    if not groups or not claude.available():
        return {}
    listing = "\n\n".join(
        f"{name} ({len(sentences)} sentences):\n" + "\n".join(
            f"  [{i}] {s}" for i, s in enumerate(sentences))
        for name, sentences in groups.items())
    try:
        answer = claude.structured(
            SYSTEM, listing, _tool(groups), client=client,
            max_tokens=1024, timeout=20.0)
    except claude.ClaudeError:
        return {}

    result: dict[str, list[int]] = {}
    for name, sentences in groups.items():
        indices = answer.get(name)
        if not isinstance(indices, list):
            continue
        valid = [i for i in indices if isinstance(i, int)
                and 0 <= i < len(sentences)]
        if valid:
            result[name] = valid
    return result
