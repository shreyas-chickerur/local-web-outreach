"""Slice H, item 2b/2c (BRIEF §5): the reply to one instruction, grounded
in what actually happened and nothing else.

`reply_for(result)` takes exactly one argument, typed `IterationResult` —
`understood`, `unmet`, `changed`, `defects`, `repairs`, `unsupported`,
`contradictions`, `ignored_tokens`, `blast_radius`, `reader_error`,
`rejected`, `findings`, `unchanged`. None of those is the rendered page,
and there is no second parameter for one: the function's own signature is
the structural proof that it cannot be handed HTML even by a caller that
wanted to, which is what makes it unable to invent an outcome the
IterationResult does not already contain. Nothing here imports
`app.site.render` or reaches for a page — a fresh copy of this file
`grep`s clean, and `tests/sitegen/test_reply.py` checks it stays that way.

Deterministic and template-based rather than a live model call, on
purpose: every field it reads is already closed-vocabulary, plain-English
material (a phrase the model wrote about its OWN reasoning when it
produced the result, or a rule-derived string like
`"mood: 'quiet' -> 'warm'"`) — turning that into a sentence is the same
kind of work `tools/build_review.py`'s `_plain_outline()` already does,
not a second free-text generation pass that could drift from what
actually happened. It also means a reply is never blocked on a model
being reachable, which matters most exactly when `reader_error` is set.

A DEFECT BECOMES A QUESTION: an instruction the parser could not fully
satisfy (`unmet`, `unsupported`, `contradictions`, `ignored_tokens`) gets
a question back naming what specifically did not land, rather than a
result the operator has to interpret alone.
"""

from __future__ import annotations

from app.site.pipeline import IterationResult


def reply_for(result: IterationResult) -> str:
    """One assistant turn describing what `result` says happened.

    Order of precedence: an unreachable model is disclosed first, however
    else the instruction was still handled (the fallback reader ran) — an
    operator whose instructions suddenly get worse should be told why, not
    left guessing. A rejection is reported next, plainly, since nothing
    else in `result` describes a state that shipped. Everything else
    builds toward the same shape: say what changed (or that nothing did),
    then ask about whatever the instruction asked for that this could not
    do.
    """
    parts: list[str] = []

    if result.reader_error:
        parts.append(
            f"I couldn't reach the model just now ({result.reader_error}), "
            f"so I read that with the simpler word-matching fallback "
            f"instead of the fuller one.")

    if result.rejected:
        findings = "; ".join(result.findings) or "it didn't pass the content gate"
        parts.append(f"I couldn't make that change — {findings}.")
        return " ".join(parts)

    if result.kind != "style":
        parts.extend(_non_edit_reply(result))
        return " ".join(p for p in parts if p)

    if result.unchanged:
        parts.append("That's already how it looks — nothing changed.")
    elif result.version is not None:
        parts.append(_change_summary(result))
        if result.blast_radius:
            parts.append(
                f"That also moved {_list(result.blast_radius)}, which "
                f"you didn't ask for — let me know if that's not right.")
        if result.repairs:
            parts.append(f"I also had to adjust {_list(result.repairs)} to "
                         f"keep the text readable.")

    question = _question(result)
    if question:
        parts.append(question)

    return " ".join(p for p in parts if p) or "Got it — no changes to make."


def _change_summary(result: IterationResult) -> str:
    if result.changed:
        return f"Done — {_list(_plain_facets(result.changed))}."
    if result.understood:
        return f"Done — {_list(result.understood)}."
    return "Done."


def _plain_facets(changed: list[str]) -> list[str]:
    """`spec_diff`'s own `"facet: 'a' -> 'b'"` lines, without the arrow —
    a reply reads better as "mood moved to warm" than as debug output."""
    out = []
    for line in changed:
        facet, _, rest = line.partition(":")
        _, _, after = rest.partition("->")
        value = after.strip().strip("'\"") or rest.strip()
        out.append(f"{facet.strip()} is now {value}" if value else line)
    return out


def _non_edit_reply(result: IterationResult) -> list[str]:
    """A bug report, a request for different facts, or something outside
    what this can express — never answered by restyling the page."""
    out: list[str] = []
    if result.defect:
        out.append(f'You flagged: "{result.defect}."')
    if result.defects:
        out.append(f"Looking at the live page, I can confirm "
                   f"{_list(result.defects)}.")
    elif result.defect:
        out.append("I didn't find that on the current page — "
                   "can you point to where you're seeing it?")
    if result.unsupported:
        # Not `.capitalize()` — it lowercases every other capital in the
        # list along with the first letter, which corrupts a proper noun
        # in anything but the single-item case this would look right for.
        out.append(f"You also asked for {_list(result.unsupported)} — "
                   f"that's outside what I can build today, so it's queued "
                   f"rather than silently dropped.")
    return out


def _question(result: IterationResult) -> str:
    """The material an unmet instruction leaves behind, turned into a
    question rather than a list the operator has to interpret alone."""
    bits: list[str] = []
    if result.unmet:
        bits.append(f"couldn't do this: {_list(result.unmet)}")
    if result.contradictions:
        bits.append(f"asked for things that conflict: "
                    f"{_list(result.contradictions)}")
    if result.ignored_tokens:
        bits.append(f"didn't recognize: {_list(result.ignored_tokens)}")
    if not bits:
        return ""
    return f"I {'; '.join(bits)}. What did you mean?"


def _list(items: list[str]) -> str:
    return "; ".join(str(i) for i in items)
