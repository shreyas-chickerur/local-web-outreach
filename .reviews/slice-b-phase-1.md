# Phase 1 — grow the judged corpus, and why it cannot be grown usefully yet

Phase 1's target was a held-out third with 4–5 scorable comparisons. It reached
**three**, and the shortfall is not the point — what judging turned up is.

## Changed

    app/site/render.py     `facts` renders the rating at display size with the
                           name second; it was rendering `photo`
    app/site/styles.py     the tally, and its spacing
    tests/sitegen/test_axes_are_real.py
                           test_every_first_screen_position_renders_a_different
                           _first_screen — strips the class attribute first
    tests/fixtures/pairs.json
                           three stale verdicts re-judged, one held-out verdict
                           RETIRED, four new pairs judged

## The defect judging found

`first_screen` declares five positions. Two rendered the same first screen:

    above-the-fold markup differences between photo and facts: 2
       -<header class="hero first-photo type-quiet has-photo" id="top"
       +<header class="hero first-facts type-quiet has-photo" id="top"

The class attribute, and nothing else. The CSS then centred the block, shrank
the heading and spaced the figures — a setting applied to the same arrangement.
`barbecue` and `contractor-bare` were one page.

This is `layout_bias` again, which `BRIEF` §3 already records, in the axis the
vector weights heaviest at 2.5 — so every distance across a photo/facts pair was
overstated by a quarter, and `first_screen` has been the deciding term in every
verdict this project has taken.

`test_a_first_screen_axis_changes_the_first_screen` passed it: a class name is
markup. The new test strips `class="..."` before comparing, so a position has to
earn its difference in what renders. It failed on `('photo', 'facts')` before
the repair and passes on all ten pairs after it.

**The repair, not a weight drop.** `BRIEF` §2.1 says what the position is for —
"the numbers first, at a size that reads as the point of the screen" — and the
renderer led with the name. It now opens on the rating at display size with the
count as a caption and the name second. Nothing invented: `rating` and `reviews`
are read off `Material` exactly as the small version read them.

No fingerprint moved, so no re-decide and no ruler or rule change. The pictures
for `bare-trade` and `contractor-bare` did move, so verdicts about them went
stale — three re-judged, and `bare-trade`/`contractor-bare` RETIRED because it
was held out. That cost was stated in the pre-registration before the repair was
written.

## The finding that stops Phase 1 being worth completing

**All sixteen live verdicts are exactly "do they share `first_screen`".**

It was thirteen of thirteen before the repair and it is sixteen of sixteen
after, and repairing `facts` did not break it — it restored it, by making a
position that was pretending to be distinct actually distinct.

That is not a bad judging rule. With colour, subject and type setting all
discounted, **the generator has exactly one arrangement dimension**: which of
five first screens it opens on. Within a position every page has the same
arrangement, so a fold verdict has nothing else to rest on.

Judging more pairs cannot fix that. Every verdict added is one bit already
determined by the vector, and a larger label set of determined verdicts makes
agreement look better supported while measuring the same single axis. That is
self-consistency, not validity — the contamination `pairs.json` was rewritten
once to escape, arriving through the structure of the corpus rather than through
the wording of the verdicts.

**So Phase 2's evidence check has one answer: page architecture.** Not because
`BRIEF` §2.1 lists it fourth, and not by elimination — because the instrument
cannot say anything at all until the corpus has a second arrangement dimension,
and that is what page architecture is.

## Numbers

    agreement   39 of 55 (tuning 27 of 32, held out 0 of 3)
                ruler 4616d461, rule a83a0283, labels 69061e09,
                held-out f4ed374b
    census      same-trade 51% distance = 49% identical, 7 scored pairs
    unreachable 0
    tests       758

Ruler and rule unchanged: nothing that decides anything moved, only what one
position renders.

## Assumptions I could not verify

That `roofer`/`salon` is a "same" verdict. Both rule the screen down the middle
with the same elements in the left half; one carries a button and the other does
not. It is the closest call in the set and it is now in the held-out third,
where I cannot revisit it.

## Questions I want answered before the next slice

Whether the held-out third is worth keeping in its current form. It has been
emptied or gutted three times now, it reads 0 of 3, and every verdict in it is
determined by one axis. It may be measuring nothing until the corpus is wider.

## Literal output

### `make check`

```
........................................................................ [ 66%]
........................................................................ [ 75%]
........................................................................ [ 85%]
........................................................................ [ 94%]
......................................                                   [100%]
758 passed in 7.62s
```

### `tools/quality_census.py` (tail)

```
    roofer/salon (80%) should be closer than restaurant-rich/salon (64%) and is not
    FRESHLY RE-PINNED. The previous reading of "27 of 40" was scored against labels c6ea7551 — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
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
