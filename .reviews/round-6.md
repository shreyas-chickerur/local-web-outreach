# Round 6 — correctness bugs fixed, the weight budget measured
# honestly, his own review checklist dry-run, and every taste call
# left to him

Full exploratory account, including false starts, is in
`.reviews/slice-b-predictions.md` under "Round 6, Phase 1", "Phase 2",
and "Phase 3". This is the close-out: what landed, every binding claim
and whether it passed, and the final numbers, with literal tails.

Governing rule this round, stated at the start and held to throughout:
**only work with a right answer.** No redecide, no new verdicts, no
visual change to any page, no compression, no gallery caps, no budget
change, no new heading wording. Everything requiring taste, product
judgment, or a verdict about how the sites look was written up as a
decision with evidence instead of made: `.reviews/DECISIONS-FOR-SHREYAS.md`.
Baseline captured before touching anything: ruler `a762bcc9`, rule
`254e171b`, labels `122e6ec8`, held-out `7aa64298`,
`render_snapshots.json` sha256
`554cdf5df2aeb45c1ec0684d103979191899e519ef1df5a7206f4a9ff0233765`.

## What landed, phase by phase

**Phase 1 — correctness bugs in the artifact he opens.** Confirmed the
diagnosed og:image bug exactly: `render.absolute()` correctly builds
`http://127.0.0.1:8099/photo/1/6`; `build_review._copy_photographs`'s
regex matched inside that absolute URL (the seven characters after the
port number), corrupting it to `...8099photos/<hash>.jpg` on 17 of 19
committed pages. Fixed with a negative lookbehind excluding the one
context that was ever wrong, metadata-only, invisible on the page.
Fixed the freshness guard's false alarm on an empty photo cache — it
now skips with a clear message instead of failing. Verified every page's
own photographs genuinely load offline (not just exist on disk) with
the project's own trusted headless-Chrome technique: two apparent
failures were investigated and explained (a lightbox's intentionally
empty `src`, an external partner-logo SVG never meant to be proxied),
and one genuine gap was found in the CHECKING technique, not the bundle
(a horizontal `.scrollstrip` gallery needs its own scroll to trigger
`loading="lazy"`).

**Phase 2 — the weight-budget harness, measured honestly, decided
nothing.** Two real bugs fixed: every `/photo/` reference was measured
on disk at the largest tier regardless of what a mobile `srcset` would
actually select, and every externally-hosted image (a business's own
"recent jobs" photos, pulled straight from their live site) was
silently never counted at all. Fixed with real DevTools Network-domain
measurement. A third, unrelated, previously-unknown bug was found
blocking the very re-measurement this needed: a synthetic click used to
sample INP could actually navigate the tab away on `bare-trade`, whose
both CTAs are plain external links to a Google Maps search — fixed with
a capture-phase click guard, verified in both directions via `git
stash`. Re-measured all 19 fixtures: 7 genuine breaches, down from the
old, wrongly-measured 12 — five clear now that never should have
breached, two (`roofer`, `restaurant-rich`) are far worse than the old
number ever showed. `KNOWN_BREACHES` updated to match, mechanically.
Building the decisions file's own per-fixture table found two of the
seven reason strings were themselves wrong about which contributor
(gallery vs. external) actually dominates — corrected, the same
"measure honestly" discipline applied to a descriptive string instead
of a number.

**Phase 3 — dry-running his own checklist himself, first.** `make
check`, `quality_census.py`, and `content_census.py` all ran clean,
matching Phases 1-2 exactly. `perf_census.py` itself ran clean, 19/19,
matching the committed baseline. Opening `.reviews/review/index.html`
and running both greps found nothing broken in the bundle. Testing the
workbench against the fixture corpus (`WORKBENCH_DB=artifacts/
fixtures.db`) confirmed everything his checklist specifically asks for:
it starts against the 19-fixture corpus ("My leads · 19"), the "what
didn't reach the page" panel renders real content on two different
leads, and a genuinely impossible instruction ("add a live chat widget
that books appointments automatically") sent through the real UI
correctly comes back as `kind: unsupported`, no version written, with a
plain-English explanation. Testing that last item live found a real
bug: the explanation was hard-truncated at 200 characters with no word
boundary, cutting the model's own sentence off mid-word — the THIRD
independent occurrence of this exact defect shape in this codebase
(`render._truncate_quote` and `signature.py`'s quote device were each
already found and fixed for it once). Fixed the same way, verified to
fail without the fix and pass with it via `git stash`. Two OTHER
apparent defects (broken review-bundle thumbnails, a blank live
preview iframe) were checked against the project's own trusted
headless-Chrome technique before being called real, and turned out to
be a testing-tool artifact both times — the same false-negative class
Phase 1c already found and disclosed, confirmed a second time rather
than mistaken for a product defect.

**Phase 4 — the decisions file.** Seven items, each with the question,
the measured evidence, the real options, the cost of each, a
recommendation, and what's needed from him:
`.reviews/DECISIONS-FOR-SHREYAS.md`. Most notably: item 3 found that
BRIEF §5's own premise ("headings are model-chosen from a table") is
already out of date — `app/site/tradeprofile.py` already carries a
deterministic per-trade heading table, disclosed in an earlier round;
the actual open question is narrower than the brief assumed. Item 2
lays out the full honest weight table from Phase 2 and the finding that
the 7 breaches split into two different problems with two different
owners (this project's own gallery choice vs. a business's own external
images) that likely deserve two different budgets, not one. Item 1
leaves the `roofer`/`hvac-rich` disagreement exactly as found — two
readings, not a re-judge. Nothing in this file changed a rendered page.

## Every binding claim, pass or fail

| Phase | Claim | Result |
|---|---|---|
| 1 | The og:image rewrite bug reproduces exactly as diagnosed | **CONFIRMED** |
| 1 | The fix leaves every legitimate rewrite (img, full srcset, CSS url) intact | **PASSED** |
| 1 | Freshness guard skips (not fails) on an empty photo cache, checked both directions | **PASSED** |
| 1 | Every page's own photographs are genuinely visible offline | **PASSED** — two apparent failures investigated and explained; one genuine gap found in the CHECK, not the bundle |
| 2 | The diagnosed wrong-tier `/photo/` measurement bug reproduces and is fixed | **CONFIRMED / PASSED** |
| 2 | External images are counted now; verified on a fixture known to carry them | **PASSED** |
| 2 | `bare-trade`'s hang is a real, previously-unknown click-navigation bug, not flakiness | **CONFIRMED** — reproduced 3x before the fix, resolved deterministically 3x after |
| 2 | The click-navigation fix is proven by a real-browser test that fails without it | **PASSED** — confirmed via `git stash` both directions |
| 2 | `KNOWN_BREACHES` matches the honestly measured reality, no stale or missing entries, reasons name the true dominant contributor | **PASSED** |
| 3 | The workbench starts against the fixture corpus | **PASSED** — "My leads · 19" |
| 3 | The "what didn't reach the page" panel renders real content | **PASSED**, checked on two leads |
| 3 | An impossible instruction returns a real explanation, not a silent failure | **PASSED** (after the truncation fix) |
| 3 | The truncation bug is real and the regression test fails without the fix / passes with it | **CONFIRMED** |
| 3 | Every apparent defect this phase surfaced was checked against a trusted method before being called real or dismissed | **PASSED** — one genuine bug fixed, two testing-tool false negatives confirmed as such |
| all | No page, composition, heading, photo, or budget changed | **PASSED** |
| all | Both hashes unchanged for the whole round | **PASSED** — identical to the values captured before Phase 1 began |

No claim failed. No bound condition was crossed.

## Final numbers

    agreement   22/26 (85%) full, 9/11 (82%) held-out only (unchanged —
                no redecide this round)
                ruler a762bcc9, rule 254e171b, labels 122e6ec8,
                held-out 7aa64298
    same-trade  61.52% distance = 38.48% identical (unchanged)
                closest pair barbecue/barbecue-rich at 17%, judged "same"
    unreachable 3, all tracing to roofer/hvac-rich — unchanged, still
                not re-judged (decisions file item 1)
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults   3 fixtures match (§2.4), unchanged
    content census        77% of published material reaches the page,
                unchanged
    provenance            100% (687/687) verbatim-or-prefix-cut;
                85% (389/459) selection ratio, unchanged
    performance LCP/CLS/INP within budget on 19/19; weight within
                budget on 12/19 (7 genuine breaches, down from the old,
                wrongly-measured 12/19 — see decisions file item 2)
    tests       981 passed, 7 xfailed
    fixtures    19
    verdicts    2 live (unchanged), 12 held out

## What of BRIEF §5 remains open after this round

Everything left open at Round 5's close remains open — this round
built no new product feature and re-judged nothing:

- **Slice C's ninth contractor fact (before-and-after)** — checked a
  third time, still genuinely blocked on material this corpus does not
  have. Recommended closed-blocked (decisions file item 5), pending his
  agreement.
- **Slice C's compositions** — `gallery`, `about`, and `hours` still
  have exactly one layout each; costed out, not built (decisions file
  item 4).
- **The model choosing a heading from a table** — found this round that
  a deterministic per-trade table already exists (`tradeprofile.py`);
  the real open question is narrower than previously stated (decisions
  file item 3).
- **The three unreachable comparisons / `roofer`-`hvac-rich`** —
  unchanged, still wants a fresh, careful re-judge, not a same-session
  flip (decisions file item 1).
- **The weight-budget breaches** — now honestly measured (7/19, not the
  old 12/19), and shown to be two different problems with two
  different owners, neither fixed (decisions file item 2).
- **Growing the corpus past nineteen fixtures** — untouched (decisions
  file item 6).

## make check (literal tail)

```
$ .venv/bin/ruff check app tests
All checks passed!

$ .venv/bin/mypy app
Success: no issues found in 65 source files

$ .venv/bin/python -m pytest -q
........................................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 21%]
........................................................................ [ 29%]
........................................................................ [ 36%]
........................................................................ [ 43%]
........................................................................ [ 51%]
........................................................................ [ 58%]
........................................................................ [ 65%]
.................................x...x...............................x.. [ 72%]
.............x.......x...x...x.......................................... [ 80%]
........................................................................ [ 87%]
........................................................................ [ 94%]
....................................................                     [100%]
=========================== short test summary info ============================
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[barbecue-rich-weight] - large photo gallery, genuine — gallery photos are the larger share (~1.5MB of 2.2MB)
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[barbecue-weight] - external feature-block images from the business's own live site are the larger share (~2.4MB of 4.3MB, vs ~1.7MB gallery) — corrected from an earlier, less precise 'photo gallery' label once the actual per-resource split was measured
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[law-rich-weight] - external feature-block images from the business's own live site are the larger share (~3.3MB of 4.9MB, vs ~1.5MB gallery) — corrected from an earlier, less precise 'photo gallery' label once the actual per-resource split was measured
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[restaurant-rich-weight] - external feature-block images from the business's own live site, genuine — the largest single contributor once measured honestly (~5.4MB of 6.5MB)
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[roofer-weight] - external feature-block images from the business's own live site, genuine — 14MB, the worst in the corpus, almost none of it the /photo/ proxy (~10MB external of 14MB)
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[salon-rich-weight] - large photo gallery, genuine — almost entirely gallery photos (~3.0MB of 3.0MB, no external images)
XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[salon-weight] - large photo gallery, genuine — gallery photos are the larger share (~1.3MB of 2.2MB)
981 passed, 7 xfailed in 217.09s (0:03:37)
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
  barbecue-rich      LCP=    180ms  CLS=0.000  INP=     0ms  weight=   2182KB  BREACH: weight
  barbecue           LCP=    160ms  CLS=0.000  INP=     0ms  weight=   4272KB  BREACH: weight
  bare-trade         LCP=    168ms  CLS=0.000  INP=     0ms  weight=    570KB
  contractor-bare    LCP=    116ms  CLS=0.000  INP=     0ms  weight=    718KB
  dentist-rich       LCP=    156ms  CLS=0.000  INP=     0ms  weight=   1089KB
  dentist            LCP=    144ms  CLS=0.000  INP=     0ms  weight=    424KB
  hvac-rich          LCP=    156ms  CLS=0.000  INP=     0ms  weight=   1982KB
  hvac-second        LCP=    136ms  CLS=0.000  INP=    24ms  weight=   1021KB
  hvac               LCP=    200ms  CLS=0.000  INP=     0ms  weight=   1276KB
  law-rich           LCP=    184ms  CLS=0.000  INP=     0ms  weight=   4898KB  BREACH: weight
  law                LCP=    144ms  CLS=0.000  INP=     0ms  weight=    816KB
  restaurant-bare    LCP=    180ms  CLS=0.000  INP=     0ms  weight=   1345KB
  restaurant-casual  LCP=    132ms  CLS=0.000  INP=     0ms  weight=   1823KB
  restaurant-rich    LCP=    180ms  CLS=0.000  INP=    24ms  weight=   6544KB  BREACH: weight
  roofer-rich        LCP=    216ms  CLS=0.000  INP=   144ms  weight=    667KB
  roofer             LCP=    248ms  CLS=0.000  INP=     0ms  weight=  14032KB  BREACH: weight
  salon-rich         LCP=    212ms  CLS=0.000  INP=    16ms  weight=   3039KB  BREACH: weight
  salon              LCP=    152ms  CLS=0.000  INP=    16ms  weight=   2165KB  BREACH: weight
  threadbare         LCP=    100ms  CLS=0.000  INP=     0ms  weight=     59KB

budgets: LCP<2500ms  INP<200ms  CLS<0.1  weight<2MB
```

Note: `hvac-rich`'s own weight is the one number in this table not
perfectly reproducible run to run (1682KB committed, 1982KB in two
separate re-runs during this round) — comfortably clear of the 2MB
budget either way, disclosed rather than smoothed over. Every other
fixture above matches the committed baseline to the byte.
