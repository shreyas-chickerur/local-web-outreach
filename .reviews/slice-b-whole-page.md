# Phase A — the ground truth moves off the fold, and Phase B settles with it

No re-decide: the corpus is untouched, `ruler aece36b7` and `rule 95f4d93e` are
unchanged. What changed is what a verdict is a judgement OF.

## Changed

    tools/contact_sheet.py        a whole-page capture per fixture, and
                                  pages.html; the fold row stays
    tests/fixtures/pairs.json     the definition, the re-checked rules, every
                                  old verdict RETIRED, twenty fresh ones
    tests/test_the_instrument...  the degeneracy test replaced by its opposite;
                                  the sheet guard RESTORED (see below)
    tests/sitegen/test_agreement  the re-judgement guard widened to cover
                                  retirement

## Phase A's binding claim: PASSED

    fold judging        12 of 12 verdicts decided by first_screen alone
    whole-page judging  15 of 20 by first_screen, and no axis decides all 20

Reported for every axis, not only `first_screen`, because a ground truth that
merely swapped which single axis decides everything would have bought nothing:

    architecture   18/20      accent          16/20
    first_screen   15/20      compositions    16/20
    section_order  15/20      hero_subject    16/20
    action         14/20      leads_with      12/20
    mood           11/20      type_treatment   8/20

`architecture` is now the axis that explains most verdicts, at 18 of 20. Under
fold judging it explained nothing it was not already given by `first_screen`.

## Phase B: page architecture's claim, re-checked — PASSES

Phase 2 registered that the count of verdicts decided by `first_screen` alone
must fall below the total. Under fold judging it was 12 of 12 and it failed.
Under whole-page judging it is **15 of 20**.

**The axis was already built and correct; the instrument was blind to it.** That
is the finding, and it is worth more than the pass: `ledger` is byte-identical
to `stacked` above the fold, so no fold verdict could ever have rested on the
axis however well it was built.

## The rules, re-checked rather than carried over

The check found one thing the fold hid. Colour is still discounted where it is
paint — two pages identical down their length in different accents are one tool
painted twice — but **a ground that alternates down the page is not colour, it
is arrangement.** A stack of slabs against an even field reads as a different
page in the same hue. The test is whether the colour changes with position.

Type setting still does not make a different site on its own; that rule was
about the lettering and the lettering is the same whole-page.

Newly in scope because the fold could not see them: the rhythm of the bands, the
measure the text is set to, and whether bands are separated by rules, by ground
changes, or by whitespace alone.

## Every old verdict retired, none re-judged

The old ones are judgements about a different thing, not stale judgements about
the same thing, so they are retired with that reason and twenty fresh verdicts
taken. Four "same", sixteen "different".

The held-out third holds **twelve scorable comparisons** — the phase asked for
four to five, and it has been empty or near-empty four times running because too
few pairs were judged. Twenty judged pairs is what fixed that, not a change to
the split.

## A guard I deleted, and restored

`test_the_committed_sheet_shows_the_corpus_that_shipped` was gone. The axis-three
phase rewrote the tail of that file and truncated everything after the test it
was replacing, and `make check` went green because the guard was absent rather
than because it passed. That is this project's recurring defect, committed by me
in the file that exists to catch it. Restored, with the story in its docstring.

## Numbers

    agreement   41 of 64 (tuning 14 of 20, held out 6 of 12)
                ruler aece36b7, rule 95f4d93e, labels d69c25ec,
                held-out d2d1b7e0
    census      same-trade 51% distance = 49% identical, 7 scored pairs
    unreachable 0, recomputed cold against the new verdicts
    tests       761

The agreement figure is not comparable to the 19 of 27 before it, and the census
says so in the output: different verdicts, taken of a different thing.

## Literal output

### `make check`

```
........................................................................ [ 66%]
........................................................................ [ 75%]
........................................................................ [ 85%]
........................................................................ [ 94%]
.........................................                                [100%]
761 passed in 8.99s
```

### `tools/quality_census.py` (tail)

```
    restaurant-rich/salon (74%) should be closer than contractor-bare/law (48%) and is not
    FRESHLY RE-PINNED. The previous reading of "19 of 27, judged from the fold" was scored against labels dafe510d — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 80% across 55 pairs
  SAME TRADE         mean 51% distance = 49% identical, across 7 pairs
                     (46% identical across all 10 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 51% (49% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      37%  hvac vs roofer  <-- judged DIFFERENT
      41%  contractor-bare vs roofer  <-- judged DIFFERENT
      48%  restaurant-bare vs restaurant-rich
    (the diversity gate is ON — 0 of 7 same-trade pairs would collide)

  closest pairs — these are the ones that look like one tool:
      37%  hvac             vs roofer           same on: first_screen, leads_with, mood, section_order, type_treatment
      41%  contractor-bare  vs roofer           same on: architecture, hero_subject, leads_with, mood, type_treatment
      48%  contractor-bare  vs law              same on: action, first_screen, leads_with, type_treatment
      48%  restaurant-bare  vs restaurant-rich  same on: action, architecture, hero_subject, leads_with, type_treatment
      52%  barbecue         vs restaurant-rich  same on: accent, architecture, hero_subject, leads_with, mood
```
