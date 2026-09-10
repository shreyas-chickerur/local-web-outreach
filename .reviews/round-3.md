# Round 3 — the review-count contradiction, the sampled review's findings,
# and acting on the content census

Full exploratory account, including false starts, is in
`.reviews/slice-b-predictions.md` under "Round 3, Phase 1" through
"Phase 4". This is the close-out: what landed, every binding claim and
whether it passed, what the contradiction scan found corpus-wide, and the
final numbers, with literal tails.

## What landed, phase by phase

**Phase 1 — the review-count contradiction (BRIEF §4).** `hvac` printed
two verified facts that contradicted each other: its own "about" text
claimed "over 20,000 5 star reviews" against a corroborated Google count
of 6,203, two sections away on the same page. Fixed
(`app/site/contradiction.py`): a sentence stating a review count that
contradicts the corroborated value is dropped, never rewritten — this
system never authors prose. New BRIEF §4 invariant. Standing test
(`tests/test_no_contradicted_fact_ships.py`), confirmed to fail against
the unfixed code and pass restored. Content-only, no redecide.

**Corpus-wide contradiction scan, as instructed.** Every fixture's
`about` text, block text, and services list, searched for a stated
review count against that fixture's corroborated `Material.reviews`.
**`hvac` was the only hit** — roughly 3.2x over (20,000 claimed against
6,203 actual). A broader scan for years-in-business/customer-count/
jobs-completed claims found two mentions (`dentist`: "10 years";
`law-rich`: "100+ years") with no structured field anywhere in this
system to reconcile either against — disclosed, not fixed, since there
is nothing to check them against.

**Phase 2 — the sampled design review's three claimed defects,
confirmed one at a time before anything changed.**
- `law`'s nav floating over the attorney's photo with no scrim: **real**,
  confirmed directly. `.hero.first-proof` disables its dark overlay
  because its type sits below the photo, not over it — a sound reason
  for the type, never extended to the fixed nav bar that floats above
  the whole page regardless. Fixed: the bar gets a solid ground for this
  position too.
- A paragraph "hidden behind a stats banner": did **not** reproduce at
  the stated location (the quoted sentence belongs to a feature block
  nowhere near the stats band). Investigating anyway found a related,
  **real** bug: `_review_card`/`_review_feature` truncate a quote at
  `text[:340]`, no word boundary, no ellipsis — `law`'s second
  testimonial was cut mid-word ("outstanding" → "outta"), almost
  certainly what the review actually saw. Fixed with a word-boundary
  truncation.
- A duplicated CTA "cropped at the mobile edge": **not a page defect**.
  Chrome's headless `--screenshot` CLI mode silently clamps any
  requested width under 500px to exactly 500 — confirmed by
  instrumenting the page to print `window.innerWidth` from inside the
  actual capture process. Every "mobile" screenshot this project has
  ever taken, including the ones the design review judged, was laid out
  110px wider than labelled and cropped on output. Fixed properly: a
  real sub-500px capture path over the DevTools protocol
  (`tools/contact_sheet.py`'s `_cdp_session`/`evaluate_in_page`), reached
  over a raw WebSocket rather than a new dependency. Verifying the fix
  with a genuine narrow viewport found a **real** version of the same
  defect class on a different fixture: `law-rich`'s hero actions row
  clipped a button because `.hero.first-proof .proof`'s three-column
  grid has an actual 570px minimum and nothing capped the hero's own
  grid track below it. Fixed with one declaration
  (`.hero .wrap{min-width:0}`).

  Standing test (`tests/test_no_element_collides_with_another.py`):
  corpus-wide, at the three review widths, using the fixed capture path
  so "mobile" is a genuine 390px. Confirmed to fail against the
  `law-rich` regression and pass restored.

  Re-ran the sampled review (12 model calls) against the fixed tooling:
  the nav and truncation findings are gone; the CTA finding's wording
  changed from "cropped" to a pure duplication/hierarchy observation,
  consistent with the tooling-artifact explanation. Content-only, no
  redecide.

**Phase 3 — acting on the content census (BRIEF §5).**
- **3a.** A business's own photography, never once selected
  (`own_site_photos` measured 0 of 4 used). `Material.images` reversed
  to own-first; hero scoring gained a small `own_photo` term
  (`HERO_WEIGHTS["own_photo"] = 0.2`) that only breaks a close tie.
  Verified directly: **zero fingerprint values moved** from this change
  alone across all 19 fixtures — content-only.
- **3b.** `menu_media` (a menu PDF or photo, extracted since Slice A,
  never read — `Material` did not even carry the field). Added it;
  `_menu()` links to it directly or appends it beside parsed items.
  **Moves the corpus** — `restaurant-rich` gained a `menu` section it
  never had.
- **A fifth, unplanned fix, found verifying 3b touched nothing it
  shouldn't:** `law-rich` was rendering "12 dishes on the menu" at
  prices of $812, $55, $49 — every one a line off the firm's own
  settlement-results page. `extract_menu_items` anchors on any bare
  dollar amount, which does not know what business it is reading. A
  corpus scan found **5 of 19 fixtures** affected (`law-rich`,
  `dentist`, `hvac-rich`, `hvac-second`, `roofer-rich`) — a promo, a
  coupon, a financing banner, and an insurance estimate, none a menu.
  Fixed by gating menu content on `trade_kind == "food"` at both places
  it reaches the page (`_stats()`, `_menu()`).
- **3c.** `block:feature`'s 4-block cap, the single biggest census drop.
  Checked items 5+ fixture by fixture before moving the number: some
  corpora are a genuine FAQ or service list cut off arbitrarily; a
  smaller amount is testimonial-shaped content a scraper mis-filed,
  starting around item 7, not item 5. Raised to 6. Content-only,
  confirmed against the forbidden-defaults test and page-length byte
  counts before the redecide.
- **3d.** `fact:address`/`fact:phone` dropped as unverified: 19 total,
  **12 genuine conflicts** (two sources actually disagree — correctly
  still dropped, unchanged) and **7 a single, uncontested Google
  Business Profile claim**. A GBP listing is verified against the
  business by Google before it goes live — a real corroboration of a
  different kind. Scoped to exactly these two fields, a lone Google
  claim now verifies on its own (`app/workbench/corroborate.py`).
  **Moves the corpus** — four fixtures gained a `contact` section they
  did not have.
- **A bug in the census tool itself**, found verifying 3a's "no
  fingerprint moved" claim: `content_census.py`'s grand-total was
  double-counting an explicit subset row (`own_site_photos`) into
  OVERALL, on top of the "photos" row it is a subset of — every
  corpus-wide percentage this project has quoted carried a small,
  consistent overcount (766 instead of the true 762) that happened to
  still round to the same headline "73%" either way. Fixed, along with
  two lines that had gone stale the moment 3b/3c shipped (`menu_media`'s
  row still said "read by no section builder"; the feature-cap row
  still said "4").
- **One redecide**, covering 3b and 3d (3a and 3c verified content-only).
  Zero collisions on the first attempt, across all 171 pairs. Re-pinned
  all eleven constants. No judging round.

**Phase 4 — surfacing the census in the workspace (Slice D item 3).**
Moved the measurement (`measure()`, `FixtureCensus`) from
`tools/content_census.py` into `app/site/census.py` — a real library
module, since the live server has no business depending on `tools/`.
Verified byte-for-byte identical CLI output before and after the move.
`workspace()` now returns a `census` list for the lead's frozen opening
direction, computed by the identical function the corpus-wide report
calls. New "What didn't reach the page" panel in the workbench UI.
Verified live against the real, persistent `workbench.db` with the dev
server running — a real lead with 46 built versions, not a fixture.

**Not this round, disclosed rather than silently dropped:** a judging
round (two passes running now with none — recommended, overdue);
Slice G in full plus auto-repair (Phase 5, explicitly conditional on
"room" in the round's own instructions — a substantial undertaking on
its own, deferred rather than compressed into this round; see
"On Phase 5" below); Slice E, Slice H; growing the corpus; the rest of
Slice D (model-selected copy, a provenance check).

## Every binding claim, pass or fail

| Phase | Claim | Result |
|---|---|---|
| 1 | Standing test fails unfixed, passes fixed | **PASSED** |
| 1 | No redecide needed (content-only) | **PASSED** |
| 2 | Nav-over-photo real, confirmed directly | **CONFIRMED REAL** |
| 2 | "Hidden behind banner" reproduces as stated | **DID NOT REPRODUCE** — real bug found nearby instead |
| 2 | CTA-crop real at a genuine mobile viewport | **DID NOT REPRODUCE** — tooling floor, root-caused |
| 2 | Standing collision test fails unfixed, passes fixed | **PASSED** |
| 2 | Re-run confirms findings gone | **PASSED** |
| 3a | Own-photo preference moves no fingerprint value alone | **PASSED** |
| 3b | Menu fallback moves the corpus | **CONFIRMED** (as expected) |
| 3c | Feature cap raise is content-only | **PASSED** |
| 3c | No forbidden-default regression from the cap | **PASSED** |
| 3d | Lone-Google verification moves the corpus | **CONFIRMED** (as expected) |
| 3 | Zero collisions after the one redecide | **PASSED** (171 pairs) |
| 3 | Content census improves, attributable to named fixes | **PASSED** (73% → 77%, double-count fixed first) |
| 4 | `workspace()` census fails without the field, passes with it | **PASSED** |
| 4 | Moving `measure()` changes no CLI output | **PASSED** (byte-identical) |

No claim failed outright; two Phase 2 claims and one Phase 3-adjacent
assumption did not hold exactly as stated, and each was traced to a
real, different finding rather than forced to fit the prediction.

## Final numbers

    agreement   0 of 0 — no judging round this round, two rounds running
                ruler a762bcc9, rule 254e171b, labels e3b0c442,
                held-out e3b0c442
    same-trade  61.52% distance = 38.48% identical (was 56.10%/43.90%)
                closest pair barbecue / barbecue-rich at 17% (reported,
                not judged)
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults   3 fixtures match (§2.4): barbecue-rich,
                barbecue, restaurant-rich
    content census        77% of published material reaches the page
                (was 73%; that 73% was itself measured against a
                denominator this round found the census tool was
                double-counting — corrected before trusting either
                number)
    tests       849
    fixtures    19
    verdicts    0 live

## On Phase 5

Not attempted. The round's own instructions made it explicitly
conditional ("only if Phases 1-4 land cleanly and there is room"), and
on inspection both halves are substantial undertakings in their own
right, not a quick tail-end addition:

- **5a, the full Slice G sweep + auto-repair**: 57 model calls plus
  designing and implementing an auto-repair mechanism for whichever
  findings turn out to be mechanically fixable — a real feature, not a
  bigger version of the sample already run.
- **5b, rebuilding the ground truth**: judging blind, from actual
  rendered markup, enough pairs that the held-out third holds 4-5
  scorable comparisons — meaning a meaningfully larger judged set than
  that, done carefully (this project has caught itself misjudging from
  a thumbnail twice already), not rushed.

Recommended as a follow-up round rather than compressed into this one.

## make check (literal tail)

```
.venv/bin/ruff check app tests
All checks passed!
.venv/bin/mypy app
Success: no issues found in 60 source files
.venv/bin/python -m pytest -q
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 25%]
........................................................................ [ 33%]
........................................................................ [ 42%]
........................................................................ [ 50%]
........................................................................ [ 59%]
........................................................................ [ 67%]
........................................................................ [ 76%]
........................................................................ [ 84%]
........................................................................ [ 93%]
.........................................................                [100%]
849 passed in 221.10s (0:03:41)
```

## tools/quality_census.py (literal tail)

```
    threadbare       first_screen=type type_treatment=stamped architecture=stacked signature=none typeface=oswald-barlow mood=industrial accent=brown leads_with=contact action=call hero_subject=-
                     section_order=contact
                     compositions=contact:none

  AGREEMENT  0/0 (0%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels e3b0c442]
    FRESHLY RE-PINNED. The previous reading of "0 of 0" was scored against labels 9ed8ff8e — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 80% across 171 pairs
  SAME TRADE         mean 62% distance = 38% identical, across 30 pairs
                     (38% identical across all 36 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 62% (38% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      17%  barbecue-rich vs barbecue
      34%  bare-trade vs law-rich
      34%  law-rich vs law
    (the diversity gate is ON — 0 of 30 same-trade pairs would collide)

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
