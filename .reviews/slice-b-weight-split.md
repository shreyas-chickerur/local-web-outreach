# Decision — the gate's required set is split from the distance's weighting

Decided, implemented, and **provably output-neutral**: both hashes are
unchanged, so nothing was re-decided and nothing was re-pinned.

    before   ruler 4616d461   rule a83a0283
    after    ruler 4616d461   rule a83a0283

## The two shapes, and which one this takes

**Split them.** `fingerprint.REQUIRED_HIGH` is now an explicit set that
`collisions()` reads through `required_high()`, independent of `weight_of()`.
`HIGH_WEIGHT` and `highly_weighted()` are gone — one definition, not two.

The alternative — leave them coupled and document that some axes will be
mis-weighted in one job to satisfy the other — was rejected for a reason
specific to this instrument rather than on taste. The coupling does not merely
mis-weight; it makes a whole class of change unconsiderable. While
`type_treatment` had to weigh 2.5 or the gate became unmeetable, no argument
about what it should be worth in the distance could be heard on its merits.
That is not a tolerable compromise, it is a question the code was preventing
anyone from asking.

## Why they are not the same question

    the GATE asks      is this site's DECISION SET different enough from the
                       last ten that the generator is not repeating itself?
    the DISTANCE asks  would a stranger say these two pages came from one tool?

`type_treatment` is where they came apart, and the evidence is in the judged
text rather than in a score. Four blind verdicts describe a type difference and
dismiss it:

    barbecue / restaurant-bare     "One name is shouted and the other is spaced
                                    out"                              -> SAME
    dentist / hvac                 "one set in a serif and one in heavy
                                    capitals"                         -> SAME
    bare-trade / contractor-bare   "the only thing that changes is whether the
                                    name is a serif or blocky capitals" -> SAME
    barbecue / restaurant-rich     "One is shouted in capitals and nothing else
                                    about it changes"                 -> SAME

And the gate needs exactly that axis: with `first_screen` alone required, five
positions against a window of ten is unmeetable — the arithmetic that reverted
`HIGH_WEIGHT = 2.5` once already, now held by
`test_the_gate_is_satisfiable`.

So an axis can be **mandatory for variety and cheap in the metric**. While the
two were one number, that sentence had nowhere to live. This is the case
`weight_of`'s `min()` comment anticipated, arriving from a third direction: not
visibility against decidedness, but either of them against what the gate must
require to stay satisfiable.

## What the split costs, and what holds it

Listed rather than derived is a hand-kept set, which is the "two definitions of
one thing" shape this project keeps catching. Two things hold it:

* `test_the_gate_is_satisfiable` — the required axes must describe more
  distinct sites than the comparison window holds. It failed on the derived
  version in milliseconds and it fails on a careless addition to the list the
  same way.
* A stated membership principle: the required axes are ones a page's **form**
  depends on, not its palette. `mood` and `accent` are deliberately absent
  because what they change is the colour, and the judging rule written blind at
  the top of `pairs.json` says a difference in colour alone is not a different
  site.

## No weight was changed, and that is deliberate

The split makes reweighting `type_treatment` possible. It was not done.
Measured, the freedom is tempting and that is the problem:

    as shipped (visibility 3.0)     agreement 21/36  held-out 0/2  unreachable 2
    type_treatment visibility 1.5   agreement 28/36  held-out 1/2  unreachable 2
    type_treatment visibility 1.0   agreement 30/36  held-out 2/2  unreachable 2

Nine points of agreement, and **the held-out set goes 0/2 to 2/2** — a change
chosen by watching the tuning number would arrive looking validated. That is
the exact corruption the held-out set exists to prevent, and it is the same
shape as the `mood` reweight refused last round, so refusing it here is
consistency rather than caution. `unreachable()` does not move at any weight,
because it is a set relation: the defect stays put while the score improves,
which is the signature of fitting.

## What it would take to settle the weight honestly

Not more argument. Judgements taken *before* the weights are chosen and never
used to choose them — which is what the held-out third is, and it currently
holds three verdicts and two comparisons. Two comparisons cannot separate two
candidate weightings.

The non-circular path: judge more pairs of the **current** corpus, with no
re-decide, so the existing verdicts stay valid and the set grows; hold a third
of the new ones out by the same hash rule; then pre-register the two candidate
weights and spend the held-out set once. That is a round of work in itself and
it is the honest price of the answer.

## Literal output

Neither hash moved, so the census reads exactly as it did before the split —
which is the point of including it.

### `make check`

```
........................................................................ [ 66%]
........................................................................ [ 76%]
........................................................................ [ 85%]
........................................................................ [ 95%]
.....................................                                    [100%]
757 passed in 7.02s
```

### `tools/quality_census.py` (tail)

```
    dentist/hvac (60%) should be closer than restaurant-bare/restaurant-rich (52%) and is not
    FRESHLY RE-PINNED. The previous reading of "14 of 22" was scored against labels 371f24fa — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 79% across 55 pairs
  SAME TRADE         mean 51% distance = 49% identical, across 7 pairs
                     (46% identical across all 10 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 51% (49% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      36%  barbecue vs restaurant-rich  <-- judged SAME
      44%  contractor-bare vs roofer  <-- judged DIFFERENT
      48%  bare-trade vs law
    (the diversity gate is ON — 0 of 7 same-trade pairs would collide)

  BLIND SPOT  2 comparison(s) no weighting can reach — the 'same' pair differs on a superset of the 'different' pair's axes,
              so it is further apart under any weights. Two causes look identical here: an axis the vector lacks, or two verdicts that contradict
              each other. Check whether the 'different' pair's axes are a SUBSET of the 'same' pair's before reading it as evidence about axes.
    barbecue/restaurant-bare (same) contains restaurant-bare/restaurant-rich (different) — extra: action
    dentist/hvac             (same) contains restaurant-bare/restaurant-rich (different) — extra: action

  closest pairs — these are the ones that look like one tool:
      36%  barbecue         vs restaurant-rich  same on: accent, first_screen, hero_subject, leads_with, mood
      44%  contractor-bare  vs roofer           same on: hero_subject, leads_with, mood, type_treatment
      48%  bare-trade       vs law              same on: accent, action, mood, type_treatment
      52%  restaurant-bare  vs restaurant-rich  same on: action, first_screen, hero_subject, leads_with
      56%  contractor-bare  vs hvac             same on: action, mood, type_treatment
```
