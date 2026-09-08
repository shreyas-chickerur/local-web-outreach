# Handoff — Slice B, axis two (type treatment), and the reweight it unblocked

Branch `slice-b-identity`. One fork: the corpus was re-decided once, the ruler,
the rule and the labels all moved, and a pre-registered claim resolved.

## What shipped

**Axis two, type treatment** — `app/site/typetreatment.py`, following the
`firstscreen` pattern exactly: a module owning what each treatment means and
what a business can carry, `opening.py` offering only what the NAME can take,
`fingerprint.of()` reading it off the resolved spec. Five treatments — `quiet`,
`banner`, `stamped`, `wide`, `centred` — size, case, alignment, tracking. Not
the typeface pair; that stays an `identity.py` concern and a later item.

Availability is constrained by the name, not the photographs, which is a
different kind of availability from the first screen's and worth stating:
"Milestone Electric Air Plumbing" cannot be set in opened-out capitals.

**`HIGH_WEIGHT = 2.5`, which last commit reverted as unmeetable.** It left
`first_screen` alone in the required set — five positions against a window of
ten, so once the window held all five nothing could satisfy the gate. Type
treatment weighs 2.5 too, so the set is now `{first_screen, type_treatment}`:
twenty-five combinations against a window of ten.
`test_the_gate_is_satisfiable` holds that arithmetic. `mood` drops out, which
was the point — it was the axis that let `dentist` and `law` through sharing an
opening, because what `mood` does visibly between two pages is the colour.

The corpus re-decided under both: **zero of fifty-five pairs collide** under its
own gate.

## The pre-registered claim: FAILED

`agreement.unreachable()` reports **two**. The claim was zero, and pass/fail was
that number and nothing else.

The reason is worth more than a pass would have been. The pairs a person calls
one studio share their GEOMETRY and differ in type treatment, colour and
subject — and the judge discounts all three. So the vector now carries a
2.5-weight term exactly where a person sees no difference: the failure mode
`accent` and `hero_subject` already had, and the shape of blind spot the axis
was added to fix.

Scored with `type_treatment` removed from the vector on the same corpus and
labels, the number was the same. The axis did not move it either way — the
corpus and the labels did.

Pinned as a failure in `test_the_blind_spot_did_not_clear` rather than deleted.

## The held-out third emptied for the second time

All six live held-out verdicts were retired, not re-judged: the re-decide moved
nine of the eleven folds. That is the rule working, and it is also the
mechanism failing at what it was built for — **every axis re-decides the corpus,
and a held-out set of pair verdicts cannot survive a re-decide.** It has now
been emptied by both changes since it was created.

Three of the six new verdicts fall into it by the hash rule, so it is repopulated
— but they were judged after this rule shipped, so they cannot validate this
pass. They read 0 of 2. The first change they can honestly score is the next
one, and only if that change does not re-decide the corpus.

## The label set had to be rebuilt, and that is a weakness in this reading

After the retirements the set was seven live verdicts, which
`test_the_committed_pairs_are_readable_and_name_real_fixtures` rightly calls too
few to say anything. Six more were judged, selected as the closest unjudged
scoreable pairs by distance — a rule, not a preference, and one that biases
towards finding pairs that look alike. Thirteen verdicts, four "same".

## Numbers

    ruler 4616d461 · rule a83a0283 · labels 7e49403b · held-out 3ca286cc

    agreement          21/36   (tuning 15/21, held out 0/2)
    same-trade scored  51% distance = 49% identical, 7 pairs
    unreachable        2       <- the claim, and it failed
    gate               0 of 55 pairs collide
    tests              757

The mean went the wrong way, 38% -> 49% identical. Expected rather than excused:
nine axes describe more difference than eight, so a ninth raises the mean for
arithmetic reasons and the mean means less. That is why the claim was written
about the blind spot instead.

## The fork I would want reviewed before anything else

`type_treatment` needs to be worth 2.5 for the gate to stay satisfiable, and the
evidence says it should be worth very little in the distance. **The two weights
disagree for the first time** — which is exactly the case `weight_of`'s `min()`
is annotated as waiting for, arriving from a different direction than expected.
Separating the gate's required-axis set from the distance's weighting is the
obvious move and it is a change to the shape of the instrument, so it is a fork,
not a tidy-up. Thirteen verdicts is not enough to fit a weight against and that
path was searched and rejected once already.

## Literal output

### `make check`

```
........................................................................ [ 28%]
........................................................................ [ 38%]
........................................................................ [ 47%]
........................................................................ [ 57%]
........................................................................ [ 66%]
........................................................................ [ 76%]
........................................................................ [ 85%]
........................................................................ [ 95%]
.....................................                                    [100%]
757 passed in 7.00s
```

### `tools/quality_census.py` (tail)

```
                     section_order=
                     compositions=

  AGREEMENT  21/36 (58%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels 7e49403b]
    bare-trade/contractor-bare (64%) should be closer than contractor-bare/roofer (44%) and is not
    barbecue/restaurant-bare (60%) should be closer than contractor-bare/roofer (44%) and is not
    dentist/hvac (60%) should be closer than contractor-bare/roofer (44%) and is not
    bare-trade/contractor-bare (64%) should be closer than restaurant-bare/restaurant-rich (52%) and is not
    barbecue/restaurant-bare (60%) should be closer than restaurant-bare/restaurant-rich (52%) and is not
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
              so it is further apart under any weights. Only a new axis reaches these.
    barbecue/restaurant-bare (same) contains restaurant-bare/restaurant-rich (different) — extra: action
    dentist/hvac             (same) contains restaurant-bare/restaurant-rich (different) — extra: action

  closest pairs — these are the ones that look like one tool:
      36%  barbecue         vs restaurant-rich  same on: accent, first_screen, hero_subject, leads_with, mood
      44%  contractor-bare  vs roofer           same on: hero_subject, leads_with, mood, type_treatment
      48%  bare-trade       vs law              same on: accent, action, mood, type_treatment
      52%  restaurant-bare  vs restaurant-rich  same on: action, first_screen, hero_subject, leads_with
      56%  contractor-bare  vs hvac             same on: action, mood, type_treatment
```
