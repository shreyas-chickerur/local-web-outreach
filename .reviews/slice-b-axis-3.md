# Phase 2 — page architecture. The axis is real. The binding claim FAILED.

Held to the claim as registered: **after this lands, the count of live verdicts
determined by `first_screen` alone must fall below the total.**

    before   16 of 16
    after    12 of 12

It did not fall. Reporting the actual number, not a looser version of the
claim. Not claiming `unreachable()` staying at zero, and not claiming the
agreement figure — neither was the claim, and a tenth axis raising the mean is
not credit per `BRIEF` §3.

## The axis is built and it is provably in force

    app/site/architecture.py   five arrangements: stacked, banded, ledger,
                               column, gallery — rhythm, measure, ground,
                               separator. Not which sections exist.
    app/site/render.py         `arrange()` applied to the sections, never the
                               hero
    app/site/styles.py         keyed on attributes the renderer writes onto the
                               sections, not on a class on the body
    app/site/opening.py        offers only the arrangements a business's
                               section count can carry

`threadbare`, with nothing on it, is offered `stacked` and nothing else. An
arrangement is a relationship between sections and it needs sections to hold one
between.

Proven the way phase 1 said to prove it, not with the plain equality test:

* `test_every_architecture_renders_a_different_page` strips `class="..."` before
  comparing, and all ten pairs of values differ. This is the check `photo` and
  `facts` failed for two commits in the axis weighted heaviest.
* `test_the_hero_is_untouched_by_the_arrangement` holds that the arrangement
  never reaches into the first screen — one decision, one axis.
* `test_changing_one_axis_changes_the_page` and the no-axis-is-a-function-of-
  another sweep both extended to it.
* The gate: **0 of 55 pairs collide** in the corpus re-decided under it.

Two defects caught by my own tests while building it, both fixed before
shipping: the visibility weight was set at 1.5 and the first-screen manifest
correctly refused it, since this table scores WHERE a difference is seen and
every scrolled entry in it is 1.0; and the hero comparison matched a `<header>`
inside a CSS comment before it matched the hero.

## Why the claim failed, and it is not the axis's fault

**The ground truth is read from the first viewport. This axis lives below it —
by design, and my own test asserts it.**

Measured rather than argued. Rendering the same page under four arrangements and
capturing the fold at 1440x820:

    stacked vs banded    identical bytes: False
    stacked vs ledger    identical bytes: True
    stacked vs gallery   identical bytes: False

`ledger` is byte-identical to `stacked` above the fold. `banded` and `gallery`
differ only in the sliver of the next section that reaches the bottom edge,
which reads as colour — and the judging rule discounts colour by name.

So no verdict taken from a fold picture can rest on this axis, and the count
could not have fallen however good the axis was.

## Which corrects what Phase 1 concluded

Phase 1 said the generator has one arrangement dimension. The truer statement is
that **the instrument only looks at one screen**, so it can only ever validate
first-screen axes. Page architecture, section edges, and most of the signature
device are all below the fold. As things stand none of them can be judged, and
building them would produce three more axes with the same result.

That is why the run stops here rather than continuing to phases 3 through 8. It
is not a setback to route around: continuing would mean building axes whose
claims cannot be tested, which is the shape of the mistake this project has
already made twice.

## The held-out third is empty, for the fourth time

Every fold in the corpus moved under the re-decide, so all four live held-out
verdicts were retired by rule. It has now been emptied by every change that has
shipped since it was created. The mechanism works exactly as designed and the
design cannot survive the work it oversees: every axis re-decides the corpus,
every re-decide moves the folds, every fold that moves retires the verdicts
about it. Pinned as empty in
`test_the_held_out_third_is_empty_and_that_is_the_finding`, because a held-out
score reported from nothing is worse than none.

## Numbers

    agreement   19 of 27 (tuning 19 of 27, held out 0 of 0)
                ruler aece36b7, rule 95f4d93e, labels dafe510d,
                held-out e3b0c442
    census      same-trade 51% distance = 49% identical, 7 scored pairs
                closest pair hvac / roofer at 37%, judged SAME
    unreachable 0
    gate        0 of 55 pairs collide
    tests       760

## Questions I want answered before anything else is built

Whether the ground truth should move off the fold. Judging whole-page
screenshots would let below-the-fold axes be validated, and it would change what
"would a stranger say these came from one tool" means — a stranger scrolls, but
the owner being shown the laptop mostly does not. That is a change to the
instrument's definition, not a tuning, and it decides whether phases 3 through 8
are measurable at all.

## Literal output

### `make check`

```
........................................................................ [ 66%]
........................................................................ [ 75%]
........................................................................ [ 85%]
........................................................................ [ 94%]
........................................                                 [100%]
760 passed in 9.07s
```

### `tools/quality_census.py` (tail)

```
    restaurant-rich/salon (74%) should be closer than contractor-bare/hvac (52%) and is not
    barbecue/restaurant-bare (56%) should be closer than contractor-bare/roofer (41%) and is not
    barbecue/restaurant-bare (56%) should be closer than restaurant-bare/restaurant-rich (48%) and is not
    FRESHLY RE-PINNED. The previous reading of "39 of 55" was scored against labels 69061e09 — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 80% across 55 pairs
  SAME TRADE         mean 51% distance = 49% identical, across 7 pairs
                     (46% identical across all 10 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 51% (49% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      37%  hvac vs roofer  <-- judged SAME
      41%  contractor-bare vs roofer  <-- judged DIFFERENT
      48%  restaurant-bare vs restaurant-rich  <-- judged DIFFERENT
    (the diversity gate is ON — 0 of 7 same-trade pairs would collide)

  closest pairs — these are the ones that look like one tool:
      37%  hvac             vs roofer           same on: first_screen, leads_with, mood, section_order, type_treatment
      41%  contractor-bare  vs roofer           same on: architecture, hero_subject, leads_with, mood, type_treatment
      48%  contractor-bare  vs law              same on: action, first_screen, leads_with, type_treatment
      48%  restaurant-bare  vs restaurant-rich  same on: action, architecture, hero_subject, leads_with, type_treatment
      52%  barbecue         vs restaurant-rich  same on: accent, architecture, hero_subject, leads_with, mood
```
