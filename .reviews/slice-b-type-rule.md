# Phase 0 — the type-setting rule, and what closing the blind spot revealed

Pre-registered in `.reviews/slice-b-predictions.md` before the rule was
written. No re-decide: no fold changed, so no held-out verdict went stale and
none was re-judged. `held_out_version` is unchanged at `3ca286cc`, which is the
proof of that.

## Changed

    tests/fixtures/pairs.json    the type-setting rule in `_why`, written
                                 BEFORE any verdict was looked at; one verdict
                                 moved under it
    tests/test_the_instrument_reproduces.py
                                 test_the_blind_spot_did_not_clear replaced by
                                 test_the_blind_spot_cleared_and_the_labels_
                                 went_degenerate — it pins both halves
    tools/quality_census.py      labels re-pinned, previous reading recorded

## The rule, as written into `pairs.json`

> A difference in how the name is SET — its size, its case, the spacing of its
> letters — is not by itself a different site either, and for the same reason.
> The words differ between any two businesses, so the lettering always differs;
> what a stranger recognises is the arrangement, and a setting applied to the
> same arrangement is the same page in another font. It counts only when it
> MOVES the type somewhere else on the screen, or changes what shares the
> screen with it — that is a change of arrangement rather than of setting.

Stated before looking, because the two verdicts it exists to resolve contradict
each other and whichever way it is written it decides one of them.

## The claim: `unreachable()` reaches ZERO

    before   unreachable 2   (barbecue/restaurant-bare and dentist/hvac, each
                              containing restaurant-bare/restaurant-rich)
    after    unreachable 0

**The axis-two blind spot was a labelling artefact.** It was never evidence
about axes. Exactly one verdict moved under the rule —
`restaurant-bare`/`restaurant-rich`, from "different" to "same" — and that was
the verdict that contradicted the other two.

**So axis two's justification no longer holds.** Type treatment was built to
close this blind spot. The axis is real and it stays — it renders, it varies the
corpus, it is required by the gate for satisfiability — but the case for
whatever comes next has to be made fresh from evidence, not inherited from it.

## And the finding that matters more than the claim

**All thirteen verdicts are now exactly "do they share `first_screen`".**

    restaurant-bare / restaurant-rich  same       shares first_screen
    barbecue        / restaurant-rich  same       shares first_screen
    barbecue        / restaurant-bare  same       shares first_screen
    dentist         / hvac             same       shares first_screen
    bare-trade      / contractor-bare  same       shares first_screen
    ...and all eight "different" pairs do not share it.

That is not a coincidence and it is not a bad rule. With colour, subject and
type setting all discounted by the judging rules, **the only arrangement the
generator can vary is which of five first screens it opens on.** Within a
position there is exactly one arrangement, so a fold verdict has nothing else to
rest on.

Labels that restate one axis measure self-consistency, not validity. That is the
contamination `pairs.json` was rewritten once to escape — arriving this time
through the back door rather than through vocabulary. Until the corpus has a
**second arrangement dimension**, agreement cannot validate anything.

That is the evidenced case for page architecture, and it did not come from
`BRIEF` §2.1's ordering.

## Numbers

    agreement   27 of 40 (tuning 19 of 24, held out 0 of 2)
                ruler 4616d461, rule a83a0283, labels c6ea7551
    census      same-trade 51% distance = 49% identical, 7 scored pairs
    unreachable 0
    tests       757

Ruler and rule unchanged — no code that decides anything moved.

## Assumptions I could not verify

That the rule is the right one. It is defensible and it was written blind, but
it decides a genuine ambiguity: a stranger might well read `HUTCHINS BBQ` in
heavy capitals and `The Heritage Table` in a light serif as two studios. The
rule says the arrangement is what they recognise, on the grounds that the
lettering differs between any two businesses anyway. If that is wrong, the
degeneracy above is an artefact of the rule rather than of the corpus.

## Questions I want answered before the next slice

Whether the held-out three can say anything at 0 of 2. They currently disagree
with the vector on both comparisons and there are not enough of them to know if
that is signal.

## Literal output

### `make check`

```
........................................................................ [ 66%]
........................................................................ [ 76%]
........................................................................ [ 85%]
........................................................................ [ 95%]
.....................................                                    [100%]
757 passed in 7.10s
```

### `tools/quality_census.py` (tail)

```
    restaurant-bare/restaurant-rich (52%) should be closer than contractor-bare/roofer (44%) and is not
    bare-trade/contractor-bare (64%) should be closer than contractor-bare/hvac (56%) and is not
    bare-trade/contractor-bare (64%) should be closer than dentist/restaurant-rich (56%) and is not
    FRESHLY RE-PINNED. The previous reading of "21 of 36" was scored against labels 7e49403b — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
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

  closest pairs — these are the ones that look like one tool:
      36%  barbecue         vs restaurant-rich  same on: accent, first_screen, hero_subject, leads_with, mood
      44%  contractor-bare  vs roofer           same on: hero_subject, leads_with, mood, type_treatment
      48%  bare-trade       vs law              same on: accent, action, mood, type_treatment
      52%  restaurant-bare  vs restaurant-rich  same on: action, first_screen, hero_subject, leads_with
      56%  contractor-bare  vs hvac             same on: action, mood, type_treatment
```
