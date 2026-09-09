# Phase 1 — widening the corpus, and the binding claim it was for

Pre-registered in `.reviews/slice-b-predictions.md` before any screenshot was
looked at. Bound condition: **at least one pair judged "same" from a
whole-page screenshot.** It passed.

## Changed

    tools/make_fixtures.py    eight new WANTED entries, weighted toward
                              crowded trades; `freeze_vision` now detects and
                              reports a page-stage claims-gate rejection
                              instead of silently freezing an ungated
                              direction (see "A real bug found along the way")
    tests/fixtures/pairs.json  twelve fresh whole-page verdicts, held out by
                              the existing hash rule
    tests/sitegen/test_diversity_budget.py
                              the all-pairs static-collision test rewritten:
                              it no longer claims the gate guarantees zero
                              collisions everywhere, it pins the CURRENT
                              named set and explains why that is different
                              from a regression
    tests/sitegen/test_forbidden_defaults.py
                              MATCHES extended by one -- a third instance of
                              the same known default, not a new kind
    tests/test_the_instrument_reproduces.py
                              every pinned constant and its dependent test
                              re-pinned for the widened corpus; the
                              single-axis degeneracy check RESTORED per its
                              own retirement condition
    tools/quality_census.py   baseline re-pinned, same-trade worst pair now a
                              genuine same-verdict pair for the first time

## Eight real businesses, no fabrication

`barbecue-rich` (Hard Eight BBQ, Coppell), `restaurant-casual` (Whisk Crepes
Cafe, Plano), `roofer-rich` (Bert Roofing, Dallas), `hvac-rich` (ARS/Rescue
Rooter Dallas), `hvac-second` (One Hour Air Conditioning & Heating, Plano),
`salon-rich` (Drybar, Plano), `dentist-rich` (Plano Dental Loft), `law-rich`
(The Ammons Law Firm, Frisco). All resolved through the live Google
Places/Yelp/OSM directories with real ratings, review counts and
photographs. Weighted toward the buckets already crowded: `trade` +3,
`food` +2, `desk` +1, `groom` +1, `care` +1 -- sameness is a same-TRADE
question, and one of each of eight new trades would have widened the corpus
without testing anything.

Two initial picks (Baker Brothers Plumbing, Kraft & Associates) were dropped
and replaced -- see below.

**Confirmed: the existing eleven fixtures are unchanged.** No `--redecide`
ran. Every original fingerprint (`first_screen`, `type_treatment`,
`architecture`, `signature`) checked field-by-field against the values
pinned before this round -- byte-identical, twice, before and after the
fixture swap that followed.

## A real bug found along the way

Two of the first eight picks (Baker Brothers Plumbing, Kraft & Associates)
carried an unverifiable tenure claim straight from their own site copy --
"Since 1945", "more than 45 years", "an average of 25 years" -- and the
claims gate correctly rejected the page stage for both. But `page_result`
was checked nowhere: `_stage_page` returns `{"rejected": True, ...}` rather
than raising, `freeze_vision`'s loop finished normally, `direction` stayed
persisted (a separate stage from `page`), and the tool wrote a
`design_direction` into the fixture as if the page built from it had been
approved. Every fingerprint/census/agreement computation in this project
reads `design_direction` directly and none of them re-checks the claims
gate, so a rejected design would have measured as an accepted one
everywhere downstream -- `BRIEF` SS4's "no unverified fact ships" holding for
every fixture except silently not these two.

Fixed at the source: `freeze_vision` now raises when the page stage comes
back rejected, and both call sites in `main()` catch it and report `FAILED`
with the finding, matching how a `BuildFailed` is already handled. The two
businesses were replaced (ARS/Rescue Rooter Dallas, The Ammons Law Firm) --
picking different real businesses was the honest fix; editing their scraped
copy to dodge the gate would not have been.

Also patched, for the same reason: `identity.Decision.unresolved` -- "record
an unresolved collision rather than shipping one silently" -- was returned by
`_stage_direction` and read by nothing in `make_fixtures.py`. Whether any of
the six statically-colliding pairs below were flagged unresolved at build
time cannot be recovered after the fact -- that information was never
captured, and is gone. Captured going forward (`payload["_gate_unresolved"]`,
printed as `UNRESOLVED COLLISION` when true).

## The binding claim: PASSED

**Five same-trade pairs are judged "same"** -- nonzero, so agreement is
computable again:

    barbecue / barbecue-rich       one smoked-meat photograph, one wordmark,
                                   one gallery grid, painted in the same rust
    dentist / dentist-rich         identical down to the accent -- a rating,
                                   a quotation, a card grid, a teal stats band
    hvac-rich / roofer             (
    hvac-rich / roofer-rich          )  the same page in three colours: photo
    roofer / roofer-rich           (  hero, stats band, a row of stamped
                                       "licensed & insured" pills, one card
                                       grid, one review layout, one gallery

Twelve pairs judged in total, five same and seven different. The seven
different ones include the closest DISTINCT pair the corpus has produced
(`law` vs `law-rich`, 31% distance -- both attorneys, both open on a rating
over a portrait, and diverge completely past that point) and a case the
type-setting rule was written for (`restaurant-casual` vs `salon-rich`: same
opening position, same gallery-heavy arrangement, same scrolling-strip
device -- differing in a banner treatment so large it overlaps the rest of
the screen, which the rule's own exception covers: "counts when it moves the
type... or changes what shares the screen with it").

## A structural finding this surfaced: the gate's window doesn't cover 19

Six same-trade pairs collide under the static all-pairs collision check --
the same rule `identity.decide()` runs, but checked against every fixture
ever built rather than only the last `WINDOW` (10). At eleven fixtures this
distinction didn't matter (the corpus fit inside the window); at nineteen it
does. Three of the six are the roofer/HVAC trio above, which the blind
judging independently confirmed as genuinely one design in three colours --
so the static check and the human eye agree here, for once.

What the static check cannot say, and the rewritten test says so explicitly:
whether each pair was ever compared live and the retry-then-perturb sequence
gave up (`unresolved=True`, shipped anyway per SS2.5's own design), or
whether the two were simply never in the same rolling window. That
distinction was never captured for these six and cannot be recovered now --
which is exactly the gap the `_gate_unresolved` fix above closes for
everything frozen after it.

## Two exact ties, not inversions

Agreement is 133 of 135, not 135 of 135. Both misses are the same pair on
one side: `hvac-rich`/`roofer` (held out, judged same) sits at EXACTLY the
same distance -- 31.03%, to four decimal places -- as `bare-trade`/`law-rich`
and `law`/`law-rich` (tuning, judged different), because all three move the
identical set of axes relative to their own comparison. `score()` requires
the same-pair strictly closer, so an exact tie counts as a miss even though
nothing is ranked backwards. Held-out and tuning each score perfectly on
their own (6 of 6, 84 of 84) and only collide against each other.

## Numbers

    agreement   133 of 135 (tuning 84 of 84, held out 6 of 6)
                ruler d2f37ed7, rule 95f4d93e (both UNCHANGED -- no redecide)
                labels ed8c7716, held-out 09779c1d
    census      same-trade mean 49% distance = 51% identical, 30 scored pairs
                closest pair dentist / dentist-rich at 7%, judged SAME
    unreachable 0
    gate        6 of 30 same-trade pairs collide under the static all-pairs
                check (not the live rolling-window guarantee)
    fixtures    19 (11 original + 8 new)
    verdicts    32 live (25 tuning, 7 held out)
    tests       769

## Literal output

### `make check`

```
........................................................................ [ 46%]
........................................................................ [ 56%]
........................................................................ [ 65%]
........................................................................ [ 74%]
........................................................................ [ 84%]
........................................................................ [ 93%]
.................................................                        [100%]
769 passed in 21.86s
```

### `tools/quality_census.py` (tail)

```
                     compositions=

  AGREEMENT  133/135 (99%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels ed8c7716]
    hvac-rich/roofer (31%) should be closer than bare-trade/law-rich (31%) and is not
    hvac-rich/roofer (31%) should be closer than law/law-rich (31%) and is not
    FRESHLY RE-PINNED. The previous reading of "0 of 0" was scored against labels a9beee08 — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 77% across 171 pairs
  SAME TRADE         mean 49% distance = 51% identical, across 30 pairs
                     (49% identical across all 36 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 49% (51% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
       7%  dentist-rich vs dentist  <-- judged SAME
      14%  barbecue-rich vs barbecue  <-- judged SAME
      21%  hvac-rich vs roofer-rich  <-- judged SAME
    (the diversity gate is ON — 6 of 30 same-trade pairs would collide: dentist-rich/dentist, barbecue-rich/barbecue, hvac-rich/roofer-rich, roofer-rich/roofer, bare-trade/law-rich, hvac-rich/roofer)

  closest pairs — these are the ones that look like one tool:
       7%  dentist-rich     vs dentist          same on: accent, action, architecture, first_screen, hero_subject, leads_with, mood, signature, type_treatment
      14%  barbecue-rich    vs barbecue         same on: accent, architecture, first_screen, hero_subject, leads_with, mood, signature, type_treatment
      21%  hvac-rich        vs roofer-rich      same on: architecture, first_screen, hero_subject, leads_with, mood, signature, type_treatment
      24%  roofer-rich      vs roofer           same on: action, architecture, first_screen, leads_with, mood, signature, type_treatment
      31%  bare-trade       vs law-rich         same on: action, architecture, first_screen, leads_with, mood, type_treatment
```
