# Review — Slice B: the gate's rule, and the pictures it was judged against

Branch `slice-b-identity`. Follows the review of `f3ce823`.

## The three findings in that review, all confirmed against the code

**`rebuild_opening` went around the gate.** One call site of `identity.decide`,
in `_stage_direction`. `rebuild_opening` called `opening_spec` directly and
handed the answer to `_build_opening`, which records the fingerprint
unconditionally — so a rebuild shipped an ungated decision and then stood as
precedent for every site after it. It is also the path most likely to need the
gate: it fires right after vision unblocks a build, when the first direction was
decided on the thinnest material.

Fixed, and guarded structurally rather than by example:
`test_every_path_that_records_history_went_through_the_gate` walks
`pipeline.py`'s AST and fails any function that builds an opening without
deciding it through the gate or replaying a persisted direction. A test of that
one function would have said nothing about the next caller.

**`GATE_ENABLED = False` gated one line of a report.** No other reference
anywhere. The census went on printing "the diversity gate is off" under the pair
the gate had just moved. Deleted; the line is now recomputed — the census asks
`collisions()` how many same-trade pairs it would reject and prints the answer.

**The rule did not check what the brief says it checks.** `BRIEF` §2.5 asks for
"four axes including at least one weighted highly"; `collisions()` checked
STRUCTURAL. Those are not the same set — `section_order` and `compositions`
weigh 0.5, `leads_with` 1.0, so the rule could be satisfied entirely below the
fold with `first_screen` (2.5) and `mood` (2.0) untouched. That is exactly how
`bare-trade`/`law` passed.

## Choosing "weighted highly" without picking it

Five readings, scored against the blind verdicts:

    one axis at or above 2.0                 12/13
    four axes that are not colour or subject  11/13
    two axes chosen outright                  10/13
    one axis above the mean weight (1.25)      9/13
    structural only (what shipped)             9/13

Above-the-mean fails because it admits `hero_subject`, which is what the
business happens to have rather than what anybody chose. Recorded as measured,
on thirteen verdicts against four alternatives, so a later corpus can overturn
it.

The rule is now versioned — `fingerprint.rule_version()` — separately from the
distance. Every frozen direction is an answer the rule accepted, so a baseline
taken under one rule is not comparable to a corpus decided under another.

## Two things found by looking, which is the part that should worry us

**The committed contact sheet was not the corpus that shipped.** Captured at
20:04; the fixtures beside it in the same commit were re-frozen at 20:13. Five
of eleven pictures were of pages the gate had already moved. The vector is
printed under every thumbnail, so this was always machine-checkable and nothing
checked it: `_judged_against` says "re-look at the sheet" in prose, and
`labels_version` hashes the verdicts rather than the rendering. A guard now
compares the printed vectors to the corpus; run against the sheet as committed
it flags seven of eleven fixtures.

**The committed row was a 720-pixel rendering, not a half-scale picture.**
`WIDTHS` shot `thumb` in a 720-wide window. 720 is below the 820 breakpoint
where the split hero stacks, the header changes and the columns collapse. So
**every blind verdict this project has taken was a judgement of a narrower page
than the product ships**, while the README said "half-scale first viewports".
The table now carries a device scale and `thumb` is the `fold` viewport at half
the pixels.

The first fault made me nearly file a wrong finding: on the stale sheet
`barbecue` and `restaurant-rich` still looked like one page, and I had reported
in the previous handoff that the gate separated them. The gate had; the picture
had not been retaken.

**And a real defect on a shipped page, found the same way.** The split hero's
type column was sized to half and then centred — `.wrap` carries
`margin-inline:auto` — so its right half sat under the photograph. On
`restaurant-rich`, the only page that opened that way, the heading, the
paragraph and four nav links ran across the picture. The comment above the rule
said the type was "clipped to its own half". Clipped by padding now, which uses
the centring instead of fighting it. The bar over a split hero also painted dark
ink across the photograph; it gets its own ground.

## What the honest numbers are

    same-trade mean   62% -> 70% distance
    worst pair        bare-trade/law 35%  ->  contractor-bare/roofer 45%
    gate              0 of 10 same-trade pairs would collide
    agreement         "40 of 40"  ->  19 of 33
    tests             751

The agreement figure did not regress. It was scored against verdicts read off
the wrong pictures. Re-judged blind against half-scale desktop folds of the
corpus as re-decided, the vector orders 19 of 33 cross-comparisons correctly.

## The finding, and the answer to the question the last handoff left open

I asked whether `bare-trade`/`law` at 35% meant the rule was too loose or type
treatment was needed. It was the rule, and correcting it separated that pair.
But the corpus it produced answers the type-treatment question directly, and
in the opposite direction from where I started:

**All three pairs a person calls one studio share a skeleton and a typeface and
differ in colour.**

    dentist / law       band of photograph, serif name on cream, ruled row of
                        figures, one button, a band of that colour at the foot.
                        Teal against burgundy.
    hvac / roofer       the same page with and without a picture strip: heavy
                        condensed type on a pale ground, same ruled line, same
                        button, same coloured foot.
    threadbare / hvac   both open on the name alone at the width of the screen,
                        black condensed capitals on off-white.

The vector has no axis for the typeface and reaches colour through `mood` at
weight 2.0, so it ranks all three further apart than pairs a person calls
different. Type treatment is axis two on evidence rather than on the ordering,
and **agreement, not the mean, is the number it has to move.**

## What I would want a second opinion on

**The ground truth is downstream of the gate, and that is a loop.** Changing the
rule re-decides the corpus, which re-renders the pages, which invalidates the
labels, which are what validates the rule. I broke it this round by re-judging
after the corpus settled, and the settled corpus satisfies its own gate — but
nothing stops the next rule change from starting the loop again, and a rule
tuned against labels taken from a corpus that rule produced is fitting with
extra steps. The three surviving verdicts before the re-judge could not
discriminate between four candidate rules; after it, thirteen could. That worked
here and it is not a method.

**`mood` at 2.0 may be the thing that is wrong**, not the missing type axis.
Most of what `mood` does visibly is colour, and the judging rule these labels
were taken under says colour alone is not a different site. If that is right the
fix is a re-weighting rather than an axis, and building type treatment first
would hide it.

**The census still flags the closest-by-distance pair as "the case B has to
fix".** That pair is now `contractor-bare`/`roofer`, which a person judged
*different*. The case to fix is the inversion list. The flag is a leftover from
before there was an agreement metric.
