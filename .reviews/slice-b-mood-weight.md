# Review — the `mood` weight question, measured and closed without a change

No code changed. No corpus re-decide, no hashes moved. This is a record of a
measurement that says do not make the change, which is worth committing for the
same reason a failed pre-registration is.

## First, the plan and the branch disagree, and the branch is ahead

The round was scoped against a state two commits behind `slice-b-identity`:

| the plan assumes | the branch at `8f6d56a` |
|---|---|
| `HIGH_WEIGHT` is `2.0` | it is **2.5** |
| `mood` satisfies "weighted highly" | `highly_weighted()` is `{first_screen, type_treatment}` — **`mood` is already out** |
| axis two is step 3, not yet built | `type_treatment` is **built, in `AXES`, committed and pushed** |
| record is in `.reviews/slice-b-high-weight.md` | that file does not exist; the record is in `slice-b-gate-rule.md`, `slice-b-axis-2.md`, `slice-b-predictions.md` and `BRIEF` §1 |
| scope refers to `next-steps.md` | that file does not exist in this repo |

**The goal of part 1 is already met, by the other route.** `mood` was removed
from the required set not by lowering `mood` but by giving the set a second
member: `type_treatment` also weighs 2.5, so raising `HIGH_WEIGHT` no longer
collapses `highly_weighted()` onto `first_screen` alone. That is precisely the
failure that sank the first attempt, and it is why the second one shipped.

## What the proposed change would actually do now

`mood` no longer touches the gate, so lowering its weight changes only the
distance. Measured on the shipped corpus and labels, no re-decide:

    as shipped (mood 2.0/2.0)  agreement 21/36  held-out 0/2  unreachable 2
    mood 1.5/1.5               agreement 24/36  held-out 1/2  unreachable 2
    mood 1.0/1.0               agreement 28/36  held-out 1/2  unreachable 2
    mood 0.5/0.5               agreement 30/36  held-out 2/2  unreachable 2

    inversions, at every weight above:
        barbecue/restaurant-bare, bare-trade/contractor-bare, dentist/hvac

**The score moves nine points and the defect does not move at all.** Same two
unreachable comparisons, same three inversions, at every weight. That is the
signature of fitting: the number improves because the number is a function of
the weights, and nothing a person can see changes.

The held-out column is the part that should worry us most. It goes 0/2 → 2/2 as
`mood` falls, so tuning `mood` against the tuning set until the held-out set
agrees is available, easy, and would look like validation. **That is exactly the
corruption the held-out set exists to prevent**, arriving as a plausible
instruction rather than as a temptation. Not doing it is the whole point of
having built it.

This is also the path already searched: two hundred thousand weightings, best
28/33, reached only by zeroing three axes, recorded as rejected.

## The two bound conditions cannot be evaluated as written

**`dentist`/`law` is not in the label set.** It was retired — not re-judged —
when the axis-two re-decide moved nine of the eleven folds. It is not currently
an inversion because it is not currently a verdict. "Leaves the inversion list"
has nothing to test against.

**Part 3's claim names the wrong pairs.** `agreement.unreachable()` reporting
zero for `hvac`/`roofer`, `threadbare`/`hvac` and `dentist`/`law` describes the
pre-axis-two corpus. The current unreachable comparisons are
`barbecue`/`restaurant-bare` and `dentist`/`hvac`, `threadbare` is excluded from
every score by `agreement.UNSCORED`, and `dentist`/`law` is retired.

## The side question, answered

*Do six-axis differences still count as collisions — the failure mode that sank
`HIGH_WEIGHT = 2.5` the first time?*

Yes, by design, and the gate is not blind:

    synthetic: 6 axes moved (accent, action, compositions, leads_with, mood,
               section_order), high axes moved: NONE  ->  collides
    shipped corpus: 0 of 55 pairs collide

Six low-weight axes moving is still a collision, because the rule requires a
highly weighted axis as well as four axes and a structural one. What sank the
first attempt was the opposite failure — the requirement being unmeetable rather
than too loose — and `test_the_gate_is_satisfiable` is what now catches that in
milliseconds.

## The open question this leaves, unchanged from the axis-two handoff

`type_treatment` must be worth 2.5 for the gate to stay satisfiable, and the
evidence says it should be worth very little in the distance: the pairs a person
calls one studio differ on it. **The two weights disagree for the first time**,
which is the case `weight_of`'s `min()` was annotated as waiting for.

The move that follows is structural rather than fitted: separate the gate's
required-axis set from the distance's weighting, so an axis can be mandatory for
variety without being expensive in the metric. That changes the shape of the
instrument, so it is a fork for review — and it is a different change from
reweighting `mood`, which this file recommends against.
