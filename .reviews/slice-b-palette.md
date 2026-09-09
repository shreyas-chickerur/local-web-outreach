# Phase 2 -- palette from the business's own photographs (SS2.2)

Pre-registered in `.reviews/slice-b-predictions.md` before `app/site/palette.py`
was written. Primary claim: the same-trade mean distance improves. It did.

## Changed

    app/site/palette.py        new module -- maps each photo's already-vetted
                               `dominant_colours` (from the vision pass) onto
                               the closed `ACCENT_NAMES` enum by hue distance
    app/site/opening.py        offers up to a handful of sampled accents in
                               the identity prompt, ordered by prominence, a
                               logo/badge photo (the nearest thing to a
                               declared brand colour this system has) ranked
                               first when one exists -- not a constraint, the
                               model still validates against the full enum
    tools/make_fixtures.py     `freeze_vision` now raises on a page-stage
                               claims-gate rejection instead of silently
                               freezing the direction anyway (found and fixed
                               mid-round -- see below); two businesses were
                               swapped for real ones with cleaner copy
    tests/sitegen/test_palette.py   six new tests
    tests/fixtures/pairs.json  every prior verdict RETIRED (every fold moved
                               under the redecide); ten fresh whole-page
                               verdicts taken
    tests/test_the_instrument_reproduces.py, tools/quality_census.py
                               every pinned constant re-derived; the
                               "no pair a stranger calls one studio" state
                               restored (see below)

## Why colours are read, not sampled from pixels

`SS2.2` asks to sample dominant colours from a business's photographs. That
work is already done: the vision pass records `dominant_colours` -- up to
four validated hex values per photo, strongest first -- on every fixture,
right now. A second colour-extraction pipeline over cached JPEG bytes would
duplicate it and would need an image-decoding dependency this project has
deliberately kept at two runtime deps for its whole life. Reading the field
that already exists is the smaller, more honest change.

No declared-brand-colour field exists anywhere in this system's data model.
The nearest corroborated equivalent is a photograph vision flagged
`is_logo_or_badge` -- a business's own logo or signage -- so its colours rank
first when one exists.

Every sampled hex maps onto the SAME closed `ACCENT_NAMES` set `identity.py`
already validates against, by hue distance, with a saturation and lightness
floor so a photograph's own shadow-and-highlight padding cannot masquerade
as a decision. Total reuse of the existing contrast machinery: `accent`
stays a name, `Theme.recoloured()` derives saturation and lightness from the
theme and chooses a contrast-safe ink exactly as it already did. Confirmed
against the real corpus: the model picked a sampled accent in fifteen of
nineteen fixtures, and reached past the list for the other four -- exactly
the non-forcing behaviour the prompt asks for.

## A real, external blocker hit mid-redecide, and how it was recovered

Partway through the first `--redecide` attempt, the Anthropic account ran out
of credit (`HTTP 400: Your credit balance is too low`). Nine of nineteen
fixtures had already fallen to the keyless fallback path by the time this was
caught, silently NOT consulting the palette signal at all. The eleven
git-tracked original fixtures were reverted to their exact pre-redecide state
via `git checkout` (safe -- Phase 1's widening had never touched them, and
HEAD reflected exactly that state). The eight new fixtures from Phase 1 could
not be recovered the same way (untracked, no snapshot taken before the
attempt) -- the user added credit, and the whole corpus was re-decided again,
cleanly, from the restored baseline. All nineteen came back `read_by=claude`,
no fallback, no gate rejection.

## A second real bug found and fixed along the way

Two of the eight new businesses -- one during the interrupted attempt, one
before it -- carried an unverifiable tenure claim straight from their own
site copy ("family-owned... since 1975", similar to Phase 1's "Since 1945").
The claims gate correctly rejected both pages, and `make_fixtures.py` had no
handling for that at all: `_stage_page` returns `{"rejected": True}` rather
than raising, so the freeze loop finished normally and would have written a
`design_direction` into the fixture as if the page built from it had cleared
the gate. Fixed at the source: `freeze_vision` now raises on a rejection, and
both call sites in `main()` catch it and report `FAILED` with the finding.
Both businesses were replaced with real ones whose copy does not carry the
claim (`Legacy Plumbing`, a straightforward one-location shop, rather than a
national-franchise "our history" page).

## A visual-reading correction, made mid-round

Judging from whole-page screenshots at pace, `dentist`/`dentist-rich` was
briefly misjudged "same" from memory of an EARLIER rendering rather than the
current one -- exactly the failure this project's own sheet-staleness guard
exists to catch, arriving through a human doing the same thing the guard
checks for in a file. Caught by cross-checking the actual rendered HTML
(hero class, section list, signature device) rather than trusting the next
screenshot glance, and every other verdict this round was re-verified the
same way before being finalised. Corrected to DIFFERENT; the `why` texts for
several other pairs were also rewritten where they had misattributed a
detail (e.g. "no photograph" for a fixture that has one) even though the
final verdict happened to be right.

## The binding claim: PASSED, harder than asked

**Same-trade mean improved**: 49% identical before this redecide, 45% after.
And the count of same-trade pairs a stranger calls one studio went from five
to ZERO among the ten pairs checked -- every one of this project's strongest
prior "same" verdicts broke apart: `barbecue`/`barbecue-rich` (identical on
every printed axis before this), `roofer`/`roofer-rich`, and the trade trio
built on `hvac-rich` that used to render one page in three colours.

**Not credited to palette sampling in isolation.** The whole identity call
was re-asked and the diversity gate's retry-then-perturb sequence ran fresh
for every fixture regardless of what the prompt carried; no control redecide
(without palette) was run to isolate the two effects. What can be said:
offering a photograph-grounded colour candidate cost nothing measured here,
and the resulting corpus is more varied than the one before it.

**Secondary metric, reported either direction as pre-registered:** the
forbidden-defaults count (SS2.4) held steady at two. Membership moved --
`barbecue` escaped the warm-cream-serif-terracotta default this round
(sampled amber) and `restaurant-rich` matched it instead (sampled
terracotta) -- both for the same honest reason: their own photographs are
genuinely brown/rust-toned, and a palette faithful to real material can land
on the same default for the right reason.

## And agreement is 0 of 0 again, for the reason it was before Phase 1

Zero "same" verdicts means nothing to rank against. The single-axis
degeneracy check has nothing to check with zero same verdicts (any axis
unique per fixture would explain all ten for free), so it is retired again
-- the "no pair a stranger calls one studio" test is restored in its place,
matching the pattern this project already established once.

## Numbers

    agreement   0 of 0 -- no "same" pair to rank
                ruler d2f37ed7, rule 95f4d93e (both UNCHANGED)
                labels edc76612, held-out e3b0c442
    census      same-trade 55% distance = 45% identical, 30 scored pairs
                closest pair barbecue / restaurant-casual at 28%, DIFFERENT
    unreachable 0
    gate        0 of 30 same-trade pairs collide (down from 6 before palette)
    forbidden defaults  2 fixtures match (membership moved, count held)
    tests       775

## Literal output

### `make check`

```
........................................................................ [ 65%]
........................................................................ [ 74%]
........................................................................ [ 83%]
........................................................................ [ 92%]
.......................................................                  [100%]
775 passed in 21.19s
```

### `tools/quality_census.py` (tail)

```
                     compositions=

  AGREEMENT  0/0 (0%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels edc76612]
    FRESHLY RE-PINNED. The previous reading of "3 of 9" was scored against labels 719276b9 — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 78% across 171 pairs
  SAME TRADE         mean 55% distance = 45% identical, across 30 pairs
                     (43% identical across all 36 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 55% (45% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      28%  barbecue vs restaurant-casual  <-- judged DIFFERENT
      31%  contractor-bare vs hvac-rich  <-- judged DIFFERENT
      31%  hvac-second vs hvac  <-- judged DIFFERENT
    (the diversity gate is ON — 0 of 30 same-trade pairs would collide)

  closest pairs — these are the ones that look like one tool:
      28%  barbecue         vs restaurant-casual same on: accent, first_screen, hero_subject, leads_with, mood, type_treatment
      31%  contractor-bare  vs hvac-rich        same on: action, first_screen, leads_with, mood, signature, type_treatment
      31%  hvac-second      vs hvac             same on: accent, action, first_screen, leads_with, mood, type_treatment
      31%  restaurant-bare  vs salon-rich       same on: action, architecture, compositions, first_screen, leads_with, section_order, signature, type_treatment
      38%  bare-trade       vs law              same on: accent, action, first_screen, mood, type_treatment
```
