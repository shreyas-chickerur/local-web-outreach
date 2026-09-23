# Round 4 — copy selection with real provenance, Slice E instrumented
# before it was built, the full Slice G sweep, and the ground truth rebuilt

Full exploratory account, including false starts, is in
`.reviews/slice-b-predictions.md` under "Round 4, Phase 1" through "Phase
3". This is the close-out: what landed, every binding claim and whether it
passed, and the final numbers, with literal tails.

Phase 4 (Slice H, the conversational workspace) was explicitly conditional
on Phases 1-3 landing clean with room left in the session for a substantial
feature build. They landed clean; the room did not — three phases of real
investigation (a live-API model call bug, a headless-Chrome measurement
artifact traced by controlled before/after capture, two corpus-wide render
bugs found and fixed by class, fifteen blind visual judgements) is what
this round actually was. Per the round's own instruction ("if Phases 1-3
consumed the session, STOP and say so rather than starting it badly"),
Slice H is deferred to its own round rather than started here.

## What landed, phase by phase

**Phase 1 — the rest of Slice D.** `app/site/provenance.py`: every visible
prose sentence (five sourced containers — about text, feature blocks, menu
item descriptions, the award block, review quotes) checked as
verbatim-or-prefix-cut source, a whitelisted generic-copy phrase (empty
today, honestly), or a corroborated field value — kept SEPARATE from the
existing claims-gate (`app.core.claims`), which catches a different
problem (an unbacked assertion, not untraceable text). `app/site/
copyselect.py`: a real model call selects and orders sentences by INDEX
into the exact candidates offered, never by retyping — verbatim provenance
is true by construction, not by luck. Frozen per lead alongside vision and
the design direction, matching BRIEF §4's own invariant list. Caught and
fixed before any fixture was frozen wrong: the model API's tool-use schema
rejects a colon in a property name (`feature:0` → `feature_0`), found on
the first live call. 100% (687/687) verbatim provenance across the real
19-fixture corpus; 85% (389/459) selection ratio. Content-only — no axis
moved; screenshots recaptured (`--widths page,fold`, since this changes
what ships on every page).

**Phase 2 — Slice E, instrumented before it was built.** The round's own
standing rule: "do not write the motion features until you can measure
them, or this repeats the page-architecture failure exactly."
`tools/perf_census.py`: real LCP/CLS/INP from a headless browser's own
`PerformanceObserver`/Event Timing APIs, not estimated from CSS or counted
statically; page weight from disk, not `file://` resource timing (which
reports no transfer for a protocol that never transfers). `app/site/
backdrop.py`: the preference ladder BRIEF asked for — their own video
(dormant, no extraction path gathers one, disclosed rather than faked), a
sequence of 2+ of their own uncondemned stills (reusing the same vision
floor the hero itself is scored against, so a backdrop can never show what
the hero refused to lead with), an abstract backdrop generated from the
palette, licensed stock (never reached — no source integrated, refuses
rather than fabricates). Fires behind `first_screen == "type"`.
`tools/motion_preview.py`: a separate, human-review-only capture tool,
motion deliberately left on, verified against a real filmstrip to show a
genuine crossfade (two different photographs of the same business, 5
seconds apart) rather than trusted from the CSS alone. The deterministic
pipeline needed NO change for this: a pre-existing global
`prefers-reduced-motion` rule in `app/site/styles.py` already disables
every animation everywhere, so `--force-prefers-reduced-motion` (already
used by every existing capture tool) continues to guarantee a poster-frame
screenshot with zero new plumbing. Motion does **not** become fingerprint
axis thirteen — its only live rendering effect (a stills/generated
backdrop instead of an empty one) is a function of the existing
`first_screen` axis, failing the independence test ("changing it alone
must change the rendered page") every other axis had to meet; written up
in `app/site/fingerprint.py` beside the `layout_bias` precedent. Twelve of
nineteen fixtures breach the 2MB weight budget — all pre-existing
photo-gallery weight predating this phase, confirmed the stills backdrop
adds no bytes of its own (it reuses already-counted images). Pinned as
`pytest.mark.xfail(strict=True)` in `tests/test_performance_budgets.py`: a
real regression gate on the other 66 (fixture, metric) checks, an
honestly-disclosed aspiration on the twelve, and a future fix would show
as a hard XPASS failure rather than a silent pass.

**Phase 3a — the full Slice G sweep.** `tools/design_review.py --full`:
19 fixtures × 3 widths, 57 model calls (up from the 12-call, 4-fixture
sample), findings written to JSON for a proper diff. 295 findings.
Most are photographic/design judgment calls tied to a specific source
photo or a specific business's own copy — real observations, not code
defects, and not chased; scanned instead for recurring PHRASE patterns
across independent fixtures, which is how a code defect actually
announces itself in a per-screenshot review. Two real, deterministic,
corpus-wide bugs found and fixed BY CLASS:

- `_offer_heading()` picked the food-trade heading off a bare `if
  m.menu_items`, ignoring `trade_kind` — the same over-trusting
  `extract_menu_items` anchor Round 3 already gated at every OTHER call
  site after it misread a law firm's settlement figures as "12 dishes on
  the menu." This one call site never got the gate. Caught live: "What we
  cook and serve" on a roofer, two HVAC contractors, and a law firm's own
  services section. Fixed to read `trade_kind` directly; a fifth instance
  (`dentist`) the sample never flagged came along for free, since the fix
  is at the root rather than a patch per finding.
- `signature.py`'s `quote` device had its own, independent, never-touched
  copy of a text-truncation bug Round 3 already fixed once for
  `_review_card`/`_review_feature` (`_truncate_quote`) — a bare
  `text[:220]`, no word boundary. On `hvac`'s real testimonial: "...
  knowledgeable. H", a lone capital letter glued to a decorative closing
  curly quote. Fixed by reusing `_truncate_quote`. Verifying the fix
  visually surfaced a second, independent styling issue: the decorative
  `::before`/`::after` curly-quote marks render at full body size and
  weight, legible as punctuation on close reading but misread as a
  doubled first letter ("CCody Roberts") by both the design review and a
  first glance at the same screenshot — toned down (accent colour, 0.6
  opacity, 0.6em) so they read as ornamental.

Run to ground, not "fixed": a WebGL map-embed error four findings raised
independently is a pure `--disable-gpu` capture-tooling artifact —
confirmed with a controlled before/after screenshot of the identical page,
only that one Chrome flag toggled. Every screenshot tool in this project
passes it; no real visitor's browser does. Same finding shape as Round 3's
CDP width-clamping discovery. Also confirmed and left alone: a
"duplicated page content" finding on `threadbare` (blank canvas below a
short page inside a fixed 6000px capture window, misread as repeated
content) and a "Boad Certified" misspelling on `law-rich` (verbatim in the
fixture's own scraped `services` data alongside genuine navigation-link
contamination — a source data quality issue, not a rendering bug).

**Phase 3b — rebuilding the ground truth.** The verdict set had sat at 0
live for two full rounds (131 retired). Fifteen fresh verdicts, judged
blind from whole-page renderings recaptured this same session, after
every Phase 3a fix had landed — never a thumbnail, never memory. Pairs
chosen before judging: some because the census's own "closest pairs" list
called them close, some for same-trade coverage; `is_held_out()` computed
on that already-fixed list, never used to pick which pairs to include.
Twelve of fifteen landed in the held-out third; eleven "different," one —
`roofer`/`hvac-rich` — "same" (identical hero recipe, identical section
set below it, only two sections swapping order and one small badge row).
Agreement, reported plainly: 22/26 (85%) full, 9/11 (82%) held-out only —
past the "4-5 scorable comparisons" floor, not engineered to just clear
it. Every inversion traces to the one disclosed pair. A further
diagnostic the census's own `unreachable()` check surfaced: `roofer`/
`hvac-rich` (same) differs on a strict SUPERSET of what `roofer-rich`/
`hvac-rich` (different) differs on, with `architecture` the one extra
axis — no reweighting of the current axes can ever place the "same" pair
closer than the "different" one; this specific inversion is a genuine
axis gap, not a weighting problem.

## Every binding claim, pass or fail

| Phase | Claim | Result |
|---|---|---|
| 1 | Provenance check fails on fabricated text, passes real corpus | **PASSED** |
| 1 | `test_no_unverified_credential_ships`/`test_no_contradicted_fact_ships` unchanged | **PASSED** |
| 1 | Copy selection passes by construction (indices, never retyped) | **PASSED** |
| 2 | Every fixture holds all four budgets, or a disclosed exception | **PASSED** (66 clean gates, 12 disclosed xfail) |
| 2 | Motion visible in the 2b capture path | **PASSED** (real crossfade, verified) |
| 3a | Sweep findings joined to the defects list, auto-repaired by class | **PASSED** (2 classes fixed, both with standing tests) |
| 3b | Held-out third holds 4-5 scorable comparisons | **PASSED** (11, not engineered to the floor) |

No claim failed. One finding (the WebGL map error) did not resolve as "a
bug to fix" — it resolved as "a tooling artifact to disclose," the same
outcome shape Round 3's CTA-crop investigation produced, arrived at the
same way: reproduced under controlled conditions before trusting it.

## Final numbers

    agreement   22/26 (85%) full, 9/11 (82%) held-out only
                ruler a762bcc9, rule 254e171b, labels 122e6ec8,
                held-out 7aa64298
    same-trade  61.52% distance = 38.48% identical (unchanged — no
                redecide this round); closest pair barbecue/
                barbecue-rich at 17%, JUDGED "same"
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults   3 fixtures match (§2.4): barbecue-rich,
                barbecue, restaurant-rich (unchanged)
    content census        77% of published material reaches the page
                (unchanged — Phase 1 touched selection WITHIN an
                already-counted field, not whether the field reaches
                the page)
    provenance            100% (687/687) verbatim-or-prefix-cut;
                85% (389/459) selection ratio
    performance           LCP/CLS/INP within budget, 19/19; weight
                within budget, 7/19 (12 disclosed, pre-existing)
    tests       940 passed, 12 xfailed
    fixtures    19
    verdicts    2 live (1 held out, same; 1 tuning, same); 11 held out
                and different; 1 tuning and different — 15 total,
                0 unsure

## On Phase 4 (Slice H)

Not attempted, per the round's own explicit stop condition. Four
sub-parts (opening rationale, replies grounded in `IterationResult` with
the page never shown to the model, a defect becoming a question rather
than a silent change, cross-lead preference accumulation) are a real
conversational-interface feature, not a tail-end addition to a session
that already ran a live model-call bug fix, a controlled tooling-artifact
investigation, two corpus-wide render-bug fixes, and fifteen careful blind
visual judgements. Recommended as its own round.

## make check (literal tail)

```
$ .venv/bin/ruff check app tests
All checks passed!

$ .venv/bin/mypy app
Success: no issues found in 63 source files

$ .venv/bin/python -m pytest -q
........................................................................ [ 68%]
........x...x...................x...x...x...x.......x...x...x.......x... [ 75%]
x...x................................................................... [ 83%]
........................................................................ [ 90%]
........................................................................ [ 98%]
................                                                         [100%]
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
940 passed, 12 xfailed in 220.89s (0:03:40)
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
    (the diversity gate is ON — 0 of 30 same-trade pairs would collide)

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
