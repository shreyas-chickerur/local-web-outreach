"""The gate: a site that repeats a recent one is re-decided.

Deferred in the brief on the grounds that "with eight axes it would reject
nearly everything". That was true when written and stopped being true when the
first-screen contract landed — measured against the corpus, one same-trade pair
in ten collided, not nine. The premise was checked and had expired.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site import fingerprint as fp
from app.site import identity, theme
from app.store import db, fingerprints, leads

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")


def brief_of(slug: str) -> dict:
    return {**json.loads((FIXTURES / f"{slug}.json").read_text()), "lead_id": 1}


@pytest.fixture
def conn():
    with db.session(":memory:") as connection:
        yield connection


@pytest.fixture
def other(conn):
    """A second real lead to hang history on — `fingerprints.lead_id` is a
    foreign key, so an invented id is a constraint violation rather than a
    stand-in."""
    return leads.save_brief(conn, {**brief_of("salon"), "name": "Somewhere Else"})


def test_a_replayed_direction_is_not_re_gated(conn, other):
    """The gate ran when it was first decided. Re-gating a replay is re-asking
    by another name: it costs a call a keyless reviewer cannot make, and it
    makes the answer depend on the order the corpus is loaded in."""
    brief = brief_of("barbecue")
    lead = leads.save_brief(conn, brief)
    # A history that the frozen direction would collide with.
    fingerprints.remember(
        conn, other, 1, fp.metric_version(),
        dict(identity.print_of(brief, brief["design_direction"]).values))
    made = identity.decide(conn, lead, brief)
    assert made.config["read_by"] == "frozen"
    assert made.attempts == 1
    assert not made.perturbed


def test_with_no_history_nothing_is_gated(conn):
    brief = {k: v for k, v in brief_of("barbecue").items()
             if k != "design_direction"}
    lead = leads.save_brief(conn, brief)
    made = identity.decide(conn, lead, brief)
    assert made.clean


def test_a_lead_does_not_have_to_differ_from_itself(conn):
    """Rebuilding one site should not collide with its own previous version."""
    brief = brief_of("barbecue")
    lead = leads.save_brief(conn, brief)
    values = dict(identity.print_of(brief, brief["design_direction"]).values)
    fingerprints.remember(conn, lead, 1, fp.metric_version(), values)
    assert fingerprints.recent(conn, fp.metric_version(),
                               exclude_lead=lead) == []


def test_a_vector_from_a_different_ruler_is_not_compared_against(conn, other):
    """The same rule the census follows: a measurement taken with a different
    instrument is not a comparison, it is a category error."""
    fingerprints.remember(conn, other, 1, "deadbeef", {"mood": "warm"})
    assert fingerprints.recent(conn, fp.metric_version()) == []
    assert len(fingerprints.recent(conn, "deadbeef")) == 1


def test_perturbation_is_deterministic(conn):
    """Same business, same answer, every build — the replay invariant. A
    perturbation that wandered would make a rebuild produce a different site."""
    brief = brief_of("barbecue")
    config = dict(brief["design_direction"])
    previous = [dict(identity.print_of(brief, config).values)]
    once, axis_one = identity.perturb(brief, config, previous)
    twice, axis_two = identity.perturb(brief, config, previous)
    assert once == twice and axis_one == axis_two


def test_perturbation_moves_off_what_is_already_taken(conn):
    brief = brief_of("barbecue")
    config = dict(brief["design_direction"])
    taken = [{"first_screen": config.get("first_screen", "photo")}]
    moved, axis = identity.perturb(brief, config, taken)
    assert axis, "nothing moved"
    assert moved[axis] != config.get(axis)


def test_without_a_key_the_gate_perturbs_rather_than_asking(conn, other,
                                                           monkeypatch):
    """Asking would fall through to the trade table, which is not a different
    answer — it is a worse one. Perturbation is the degraded path and it still
    varies by business, which is what the brief requires of it."""
    monkeypatch.setattr(identity.claude, "available", lambda: False)
    brief = {k: v for k, v in brief_of("barbecue").items()
             if k != "design_direction"}
    lead = leads.save_brief(conn, brief)
    asked = {"n": 0}
    real = identity.opening.opening_spec

    def counted(b, **kw):
        asked["n"] += 1
        return real(b, **kw)

    monkeypatch.setattr(identity.opening, "opening_spec", counted)
    collide = [dict(identity.print_of(brief, real(brief)).values)]
    for values in collide:
        fingerprints.remember(conn, other, 1, fp.metric_version(), values)
    identity.decide(conn, lead, brief)
    assert asked["n"] == 1, "the gate asked again with no key to ask with"


def test_the_corpus_no_longer_has_a_pair_the_gate_would_reject():
    """What the gate was built to fix, measured rather than asserted. The
    reviewer's number before it ran: one same-trade pair in ten collided."""
    from app.site.pipeline import spec_from_config
    from app.site.render import material_from_brief, plan_for, trade_kind

    prints, trades = {}, {}
    for path in sorted(FIXTURES.glob("*.json")):
        brief = {**json.loads(path.read_text()), "lead_id": 1}
        spec = spec_from_config(brief["design_direction"])
        prints[path.stem] = fp.of(plan_for(brief, spec), spec,
                                  material_from_brief(brief))
        trades[path.stem] = trade_kind(brief.get("trade"))

    slugs = sorted(prints)
    colliding = [
        (a, b) for i, a in enumerate(slugs) for b in slugs[i + 1:]
        if trades[a] == trades[b]
        and fp.collisions(prints[a], [prints[b]],
                          axes=fp.REQUIRED_AXES)]
    assert not colliding, f"the gate let these through: {colliding}"


def test_every_path_that_records_history_went_through_the_gate():
    """Structural, not by example.

    `rebuild_opening` called `opening_spec` directly and handed the answer to
    `_build_opening`, which records the fingerprint unconditionally — so a
    rebuild shipped an ungated decision and then stood as precedent for every
    site after it. Nothing failed; the history simply had a row in it that had
    never been checked against anything.

    A test of that one function would have said nothing about the next caller.
    This says it of all of them: if you build an opening, you decided it
    through the gate.
    """
    import ast

    source = Path("app/site/pipeline.py").read_text()
    tree = ast.parse(source)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        called = {c.func.id for c in ast.walk(node)
                  if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        # Reading the stored direction back is not a way around the gate — it
        # is the gate's own answer, persisted. The literal matters: recalling
        # some other stage would not be.
        replays = any(
            isinstance(c, ast.Call)
            and getattr(c.func, "attr", "") == "recall_stage"
            and any(isinstance(a, ast.Constant) and a.value == "direction"
                    for a in c.args)
            for c in ast.walk(node))
        if ("_build_opening" in called and not replays
                and not called & {"_stage_direction", "decide"}):
            offenders.append(node.name)
    assert not offenders, (
        f"{offenders} build an opening from a direction the diversity gate "
        f"never saw, and `_build_opening` records it as precedent anyway")


def test_a_rebuild_after_better_labels_is_gated(conn, other, monkeypatch):
    """The path the gate was most likely to be missing from.

    A rebuild fires right after vision unblocks a build — which is exactly when
    the first direction was decided on the thinnest material, and so the most
    likely to have landed on whatever everyone else got.
    """
    from app.site import pipeline

    brief = {k: v for k, v in brief_of("barbecue").items()
             if k != "design_direction"}
    lead = leads.save_brief(conn, brief)
    pipeline.open_site(conn, lead)

    seen: list[str] = []
    real = identity.decide

    def watched(connection, lead_id, brief_in):
        seen.append("gated")
        return real(connection, lead_id, brief_in)

    monkeypatch.setattr(identity, "decide", watched)
    pipeline.rebuild_opening(conn, lead)
    assert seen == ["gated"]


def test_the_gate_is_satisfiable():
    """A rule no site can meet is not a strict rule, it is a broken one.

    The gate asks a candidate to differ from EACH of the last `WINDOW` sites on
    at least one highly weighted axis. So the highly weighted axes have to be
    able to describe more distinct sites than the window holds — otherwise the
    pigeonhole does the deciding, every build past the first few is an
    unresolvable collision, and the corpus quietly fills with pages the gate
    would reject if anybody asked it.

    This was not hypothetical. When the set was derived from the weights, a
    `HIGH_WEIGHT` of 2.5 left `first_screen` alone in it: five positions against
    a window of ten. The corpus re-decided under it had eight of fifty-five
    pairs the gate itself rejected, and it took a full re-decide and a re-render
    to notice. This costs milliseconds.

    The set is listed now rather than derived, which removes the way it broke
    last time and adds a new one — a hand-kept list can be added to without
    anybody checking the arithmetic. That is what this holds.
    """
    from app.site import architecture, firstscreen, typetreatment
    from app.site.iterate import MOODS
    from app.store.fingerprints import WINDOW

    cardinality = {
        "first_screen": len(firstscreen.POSITIONS),
        "type_treatment": len(typetreatment.TREATMENTS),
        "architecture": len(architecture.ARRANGEMENTS),
        "mood": len(MOODS),
        "accent": len(theme.ACCENT_NAMES),
    }
    room = 1
    for axis in fp.required_high():
        assert axis in cardinality, (
            f"{axis} is weighted highly and this test cannot say how many "
            f"values it has. Add it to `cardinality` — a required axis whose "
            f"range is unknown is a rule whose satisfiability is unknown")
        room *= cardinality[axis]
    assert room > WINDOW, (
        f"the required axes {sorted(fp.required_high())} describe "
        f"{room} distinct sites and the gate compares against the last "
        f"{WINDOW}. Every build past the {room}th can only be an unresolved "
        f"collision. Widen the required set, add an axis to it, or shrink the "
        f"window — do not re-decide the corpus and find out.")
