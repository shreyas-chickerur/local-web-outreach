# Round 5 — the stale review bundle fixed, Slice H built, and the last
# open questions in BRIEF §5 given real answers

Full exploratory account, including false starts, is in
`.reviews/slice-b-predictions.md` under "Round 5, Phase 1", "Phase 2",
and "if room". This is the close-out: what landed, every binding claim
and whether it passed, and the final numbers, with literal tails.

## What landed, phase by phase

**Phase 1 — the stale review bundle, urgent, done first.** Confirmed the
reported defect (`dentist.html` reading "What we cook and serve") and
found the actual scope was larger than reported: the committed bundle
(`.reviews/review/*.html`) was last touched at Round 3's own close-out —
before Round 4's first commit — so all nineteen pages predated the
entire round, not just the five with a visibly wrong heading. Added the
guard nothing had (`tests/tools/test_build_review.py::
test_the_committed_review_bundle_shows_the_corpus_that_shipped`),
confirmed failing against the stale bundle (all nineteen slugs) before
regenerating, confirmed passing after. `READ-ME-FIRST.md` now names the
three unreachable comparisons and the twelve weight-budget xfails as
known-open.

**Phase 2 — Slice H, the conversational workspace, BRIEF §5's last
unbuilt slice.** Nothing already built was rebuilt: reading
`pipeline.py`'s `_build_opening()` before starting found item 2a (the
workspace opens on the model's rationale) already fully working since
Slice F, just untested — a standing test was added instead of a feature
that already existed. `app/site/reply.py`'s `reply_for(result:
IterationResult) -> str` is the new work: structurally proven never to
see the rendered page (the function's own signature has no place for
one), deterministic and template-based over already-closed-vocabulary
material rather than a second live model call, turning an unmet,
contradicted, or unrecognised instruction into a question rather than a
passive list, and disclosing a `reader_error` rather than leaving the
operator to guess why the read got worse. `app/store/preferences.py`
accumulates an exact phrase said on three or more distinct leads and
offers it to the next lead's opening call as a consideration — proven,
not assumed, to leave the fixture corpus untouched, since
`opening_spec()` returns a frozen `design_direction` before it ever
looks at `preferences` for any brief that carries one.

**If room, all three investigated with real data, no code changed:**

- **3a.** The three unreachable comparisons all trace to one
  self-contradiction across four of the live verdicts, not a missing
  axis — confirmed by applying the exact test the last time this
  happened (an order-swap and a small extra element were each
  independently sufficient to call three pairs "different", but were
  both present and dismissed in the one pair called "same"). No axis
  built on the strength of this; `roofer`/`hvac-rich` flagged as the one
  verdict most worth a fresh look in a future judging round.
- **3b.** Sampled three of the twelve weight-budget xfails with real
  data fetched at the smallest currently-offered responsive tier (800px,
  live Google Places API) rather than arguing from architecture alone.
  One (`barbecue-rich`) clears the budget at that size — a pure
  measurement artifact, since no tool in this project has ever served
  photos width-aware locally. Two (`law-rich`, `roofer`) do not clear it
  even then — genuine weight. Not one answer for all twelve; recommended
  as its own scoped pass (fix the measurement harness, then decide
  per-fixture) rather than guessed at with most of the evidence missing.
- **3c.** Re-confirmed directly: no fixture's vision data carries a
  before/after pairing. Unchanged since Round 4, still correctly
  unbuilt.

## Every binding claim, pass or fail

| Phase | Claim | Result |
|---|---|---|
| 1 | Freshness guard fails against the stale bundle | **PASSED** (confirmed, all 19 stale — worse than reported) |
| 1 | Freshness guard passes after regeneration | **PASSED** |
| 2 | The reply builder cannot see the rendered page (structurally) | **PASSED** (signature + `IterationResult` field check + AST scan) |
| 2 | An unmet instruction produces a question, not a silent no-op | **PASSED** |
| — | Slice H's preference accumulation does not move the fixture corpus | **PASSED** (proven: frozen brief ignores `preferences`; full suite unchanged) |

No claim failed. One BRIEF entry (§1's Round 4 reading, "unreachable 0")
was found factually wrong during this round's own 3a investigation and
corrected in place rather than silently edited.

## Final numbers

    agreement   22/26 (85%) full, 9/11 (82%) held-out only (unchanged —
                no new judging this round)
                ruler a762bcc9, rule 254e171b, labels 122e6ec8,
                held-out 7aa64298
    same-trade  61.52% distance = 38.48% identical (unchanged)
                closest pair barbecue/barbecue-rich at 17%, judged "same"
    unreachable 3, all tracing to roofer/hvac-rich — diagnosed this
                round as a labels contradiction, not an axis gap
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults   3 fixtures match (§2.4), unchanged
    content census        77% of published material reaches the page,
                unchanged
    provenance            100% (687/687) verbatim-or-prefix-cut;
                85% (389/459) selection ratio, unchanged
    performance LCP/CLS/INP within budget on 19/19; weight within
                budget on 7/19 — the 12 breaches given a real, mixed,
                evidence-based answer this round (see 3b), not resolved
    tests       965 passed, 12 xfailed
    fixtures    19
    verdicts    2 live (unchanged), 12 held out

## What of BRIEF §5 remains open after this round

Every slice named in §5 (B through H) now has real, tested, disclosed
work behind it. What remains open, plainly:

- **Slice C's ninth contractor fact (before-and-after)** — genuinely
  blocked on material this corpus does not have, not on effort.
- **Slice C's compositions** — `gallery`, `about`, and `hours` still
  have exactly one layout each; BRIEF §5 asked for two to four per
  section.
- **The model choosing a heading from a table** — still deterministic
  per trade, a disclosed scope reduction, not a defect.
- **The three unreachable comparisons** — diagnosed, not resolved;
  `roofer`/`hvac-rich` wants a fresh, careful re-judge, not a
  same-session flip.
- **The weight-budget xfails** — a real, mixed answer, not a fix; the
  measurement harness itself needs the same class of correction Round 3
  already made once for narrow-viewport capture before the remaining
  nine of twelve can be read honestly.
- **Growing the corpus past nineteen fixtures** — untouched, and every
  number in this file is only as informative as a nineteen-business
  sample allows.

## make check (literal tail)

```
$ .venv/bin/ruff check app tests
All checks passed!

$ .venv/bin/mypy app
Success: no issues found in 65 source files

$ .venv/bin/python -m pytest -q
........................................................................ [ 66%]
................................x...x...................x...x...x...x... [ 73%]
....x...x...x.......x...x...x........................................... [ 81%]
........................................................................ [ 88%]
........................................................................ [ 95%]
.........................................                                [100%]
=========================== short test summary info ============================
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[barbecue-rich-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[barbecue-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[hvac-rich-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[hvac-second-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[hvac-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[law-rich-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[restaurant-bare-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[restaurant-casual-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[restaurant-rich-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[roofer-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[salon-rich-weight] - large photo gallery, predates Slice E
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[salon-weight] - large photo gallery, predates Slice E
965 passed, 12 xfailed in 257.40s (0:04:17)
```

## tools/quality_census.py (literal tail)

```
  AGREEMENT  22/26 (85%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels 122e6ec8]
    roofer/hvac-rich (69%) should be closer than law/law-rich (34%) and is not
    roofer/hvac-rich (69%) should be closer than dentist/law (37%) and is not
    roofer/hvac-rich (69%) should be closer than contractor-bare/hvac-rich (40%) and is not
    roofer/hvac-rich (69%) should be closer than roofer-rich/hvac-rich (63%) and is not
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 80% across 171 pairs
  SAME TRADE         mean 62% distance = 38% identical, across 30 pairs
                     (38% identical across all 36 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 62% (38% identical) — no better than the baseline
                     <-- the number Slice B has to move
      17%  barbecue-rich vs barbecue  <-- judged SAME
      34%  bare-trade vs law-rich
      34%  law-rich vs law  <-- judged DIFFERENT

  BLIND SPOT  3 comparison(s) no weighting can reach — the 'same' pair differs on a superset of the 'different' pair's axes,
              so it is further apart under any weights. Two causes look identical here: an axis the vector lacks, or two verdicts that contradict
              each other. Check whether the 'different' pair's axes are a SUBSET of the 'same' pair's before reading it as evidence about axes.
    roofer/hvac-rich         (same) contains dentist/law              (different) — extra: architecture, compositions, hero_subject, type_treatment
    roofer/hvac-rich         (same) contains roofer-rich/hvac-rich    (different) — extra: architecture
    roofer/hvac-rich         (same) contains law/law-rich             (different) — extra: action, architecture, hero_subject, type_treatment

  closest pairs — these are the ones that look like one tool:
      17%  barbecue-rich    vs barbecue         same on: accent, first_screen, hero_subject, leads_with, mood, signature, type_treatment, typeface
      34%  bare-trade       vs law-rich         same on: accent, action, architecture, leads_with, mood, type_treatment, typeface
      34%  law-rich         vs law              same on: action, architecture, first_screen, hero_subject, mood, signature, type_treatment
      37%  dentist          vs law              same on: architecture, compositions, first_screen, hero_subject, mood, signature, type_treatment
      40%  contractor-bare  vs hvac-rich        same on: action, architecture, leads_with, mood, type_treatment, typeface
```

## tools/content_census.py (literal tail)

```
  block:partners                      1/2     50%
  block:story                         1/1     100%
  fact:address                       13/19    68%
  fact:hours                          0/14    0%
  fact:phone                         12/18    67%
  hours_lines                        31/31    100%
  menu_items                         27/27    100%
  menu_media                          3/8     38%
  photos                            194/261   74%
  reviews                            90/90    100%
  services+products                 106/108   98%
  socials                            10/10    100%
  OVERALL                           588/762   77%

TOP RULES BY HOW MUCH THEY DROP
    45  photos: 5 never spent by a hero, gallery, offer card or feature block
    32  block:feature: 8 beyond the 6-block cap
    15  photos: 3 never spent by a hero, gallery, offer card or feature block
    10  fact:hours: published.hours already had entries
     7  block:feature: 2 under the 18-word minimum, 5 beyond the 6-block cap
     7  block:feature: 7 beyond the 6-block cap
     7  block:feature: 6 under the 18-word minimum, 1 beyond the 6-block cap
     6  fact:phone: no source for it was verified
     6  fact:address: no source for it was verified
     6  block:feature: 6 beyond the 6-block cap
```

## tools/perf_census.py (literal tail)

```
  barbecue-rich      LCP=    232ms  CLS=0.000  INP=    24ms  weight=   7189KB  BREACH: weight
  barbecue           LCP=    204ms  CLS=0.000  INP=    40ms  weight=   6527KB  BREACH: weight
  bare-trade         LCP=    216ms  CLS=0.000  INP=    32ms  weight=     71KB
  contractor-bare    LCP=    156ms  CLS=0.000  INP=    16ms  weight=   2001KB
  dentist-rich       LCP=    208ms  CLS=0.000  INP=    24ms  weight=   1895KB
  dentist            LCP=    216ms  CLS=0.000  INP=    56ms  weight=     69KB
  hvac-rich          LCP=    204ms  CLS=0.000  INP=    24ms  weight=   2633KB  BREACH: weight
  hvac-second        LCP=    196ms  CLS=0.000  INP=    40ms  weight=   3917KB  BREACH: weight
  hvac               LCP=    240ms  CLS=0.000  INP=     0ms  weight=   3177KB  BREACH: weight
  law-rich           LCP=    336ms  CLS=0.000  INP=    32ms  weight=   8250KB  BREACH: weight
  law                LCP=    184ms  CLS=0.000  INP=    32ms  weight=     70KB
  restaurant-bare    LCP=    252ms  CLS=0.000  INP=    24ms  weight=   4515KB  BREACH: weight
  restaurant-casual  LCP=    156ms  CLS=0.000  INP=    16ms  weight=   4792KB  BREACH: weight
  restaurant-rich    LCP=    252ms  CLS=0.000  INP=    16ms  weight=   3010KB  BREACH: weight
  roofer-rich        LCP=    376ms  CLS=0.000  INP=    48ms  weight=     70KB
  roofer             LCP=    276ms  CLS=0.000  INP=    32ms  weight=   7788KB  BREACH: weight
  salon-rich         LCP=    300ms  CLS=0.000  INP=    32ms  weight=   4182KB  BREACH: weight
  salon              LCP=    164ms  CLS=0.000  INP=     0ms  weight=   2992KB  BREACH: weight
  threadbare         LCP=     96ms  CLS=0.000  INP=     0ms  weight=     59KB

budgets: LCP<2500ms  INP<200ms  CLS<0.1  weight<2MB
```
