# Phase 1 — closing out Slice B

Five items, one batched `--redecide` at the end, then sixteen pairs judged
blind against the rendered markup. This is the handoff; the binding claims and
their resolutions are in `.reviews/slice-b-predictions.md`.

## 1a — the gate bug

`restaurant-bare` and `salon-rich` collided on exactly three axes — mood,
accent, hero_subject — no structural axis, no required-high axis. An
unambiguous, unnoticed collision. Cause: the diversity gate's `recent()` only
compared a new fixture against the last ten generated (`WINDOW = 10` in
`app/store/fingerprints.py`), and these two fixtures were generated far enough
apart that they never shared a window.

Fix: `WINDOW` widened 10 → 60 — three times the current 19-fixture corpus,
65/125 spare combinations against the required-high cardinality at the time.
`recent(limit: int | None = WINDOW)` — `None` means unbounded.

**Unbounded was tried first and reverted.** Comparing against the whole
corpus sounds more correct and is a worse design: `test_the_gate_is_satisfiable`
failed immediately with `TypeError: '>' not supported between instances of
'int' and 'NoneType'`, and the deeper problem it caught is that an unbounded
window guarantees eventual *permanent* gate failure by pigeonhole, once
total-sites-ever-built exceeds the required-high cardinality — nothing ever
ages out. Bounded-but-wide is the actual fix, not a compromise on the way to
one. Full reasoning is in `app/store/fingerprints.py`'s module comment.

New standing test: `test_no_collision_survives_anywhere_in_the_corpus`
(`tests/sitegen/test_diversity_budget.py`) — every pair in the whole 19-fixture
corpus, not just same-trade. **Passes.**

## 1b — cross-trade pairs judged

Judged 16 pairs blind against `artifacts/contact-sheet/*-page.png`
(whole-page, 1440×6000), most of them cross-trade, selected by closest
fingerprint distance among pairs sharing two or more of the required-high
axes — the same rule the corpus's own history uses for this ("closest
unjudged scoreable pairs by distance"). **All sixteen came back DIFFERENT.**
Zero same-trade or cross-trade collisions found. See `tests/fixtures/pairs.json`
for the full list and each verdict's `why`.

The closest pair the corpus has ever produced under any ruler: `law` vs
`law-rich` at 26% distance, sharing eight of eleven axes (action, architecture,
hero_subject, leads_with, mood, signature, type_treatment, typeface) — and
still visibly different, because `law` opens as a full-bleed darkened
photograph with the rating shouted over it, while `law-rich` opens as a plain
band of unmarked photograph with the firm's name waiting below it on a quiet
page. First screen carried the whole difference and it was enough.

**One pair was misjudged and corrected.** `bare-trade`/`dentist` looked
identical for five bands in a row on the shrunk contact-sheet thumbnail — same
opening, same stats band, same full-screen quotation, same review grid, same
card grid — and I called it "same." Before writing it to `pairs.json` I
checked the actual rendered markup rather than trusting the thumbnail: one
page has `data-rule="on"` on every `<section>` (a hairline rule above every
band, per the `ledger` architecture's own CSS) and holds its text to an
`880px` measure throughout; the other has neither. Corrected to DIFFERENT with
a `why` describing what's actually on the page. This is the same shape of
near-miss the previous redecide hit on `dentist`/`dentist-rich` — caught the
same way, by reading the markup instead of glancing at a picture.

## 1c — held-out set repopulated

Five of the sixteen judged pairs are held out (hash of the two slugs, not
chosen): `dentist-rich`/`law-rich`, `hvac-rich`/`law-rich`, `bare-trade`/
`dentist`, `bare-trade`/`contractor-bare`, `barbecue-rich`/`restaurant-rich`.
All five DIFFERENT. Held-out third: `HELD_OUT = de28526d`.

**Agreement stays 0 of 0.** Not a defect to chase — a rank needs at least one
"same" pair to rank against, and after sixteen carefully-checked pairs,
including the five closest theoretical candidates for "same" in the whole
corpus, there is not one. This is the gate fix (1a) working: the diversity
budget is now wide enough that a stranger cannot find two fixtures that read
as one tool. The honest cost is that agreement cannot currently validate
anything on this corpus, same as before this phase.

Per the standing rule, no "same" verdict means the single-axis degeneracy
check (`test_the_blind_spot_cleared_and_the_labels_went_degenerate`, retired
in an earlier commit) stays retired — nothing came back to restore it against.

## 1d — typeface pair

`app/site/theme.py`: ~20 named `TypefacePair`s (display face, body face,
modular ratio, display steps, tracking, display/heading weight, voice),
6 matching the existing mood defaults and 14 new. `Theme.with_typeface(name)`
swaps display/body/modular_ratio/display_steps/tracking/weights; unrecognised
or absent name returns the theme unchanged. `theme_for(mood, accent, typeface)`
applies the override when given, else falls back to `DEFAULT_TYPEFACE[mood]`.

Identity call chooses by name from the closed set (`opening.py`'s tool schema
lists every pair's `voice`); `SiteSpec.typeface` defaults to `""`, meaning
"defer to the mood's own default pairing."

Added to `fingerprint.AXES`, `REQUIRED_HIGH`
(`{first_screen, type_treatment, architecture, typeface}`), VISIBILITY=3.0,
DECIDEDNESS=3.0. Proved with a class-stripped render test
(`test_changing_one_axis_changes_the_page["typeface"]`,
`test_a_first_screen_axis_changes_the_first_screen["typeface"]`).

**Caught its own bug on the way in**: `test_no_axis_is_a_function_of_another`
failed because the sweep never varied typeface independently of mood — every
unset typeface silently resolves through the mood default, so across the
sweep typeface *looked* like a pure function of mood even though the real
system lets either move independently. Fixed by adding an explicit `face`
dimension to the sweep's cross product.

## 1e — signature device justification

One sentence, generated alongside the rest of the identity call
(`signature_why` in the direction config), persisted with the plan
(`sites.recall_stage(..., "direction")`), read back on rebuild rather than
re-asked (`config.get("read_by") == "frozen"` replay guarantee, same as
`rationale`). Surfaced in the workspace: `app/web/server.py` extracts
`signature_why`/`signature_device` from `opening_notes`, `app/web/index.html`
renders it beside the existing rationale/why panels, only when the device
isn't `"none"` and the why-text is non-empty. Never reaches the rendered page
— same boundary `rationale` already keeps, proven by
`test_the_justification_never_reaches_the_rendered_page`.

## The redecide

One `--redecide` covering 1a + 1d + 1e together, per the batching rule. All 19
fixtures resolved `read_by=claude`, no claims-gate rejection, ruler and rule
unchanged (`a762bcc9` / `254e171b` — neither moved, since none of the three
changes touches a weight or an axis's own definition; the corpus was
re-decided because the gate's history and the typeface choice both feed the
direction call).

## Re-pinned this commit

- `tests/test_the_instrument_reproduces.py`: RULER `a762bcc9`, RULE `254e171b`,
  LABELS `1f0df47d`, HELD_OUT `de28526d`, SAME_TRADE_MEAN `0.5552`,
  AGREEMENT `(0, 0)` (value unchanged, labels underneath it moved)
- `tools/quality_census.py`: BASELINE_METRIC, BASELINE_RULE, BASELINE_LABELS,
  BASELINE_SAME_TRADE, BASELINE_WORST (now `law`/`law-rich`, 26%),
  BASELINE_LABELS_WAS `("edc76612", "0 of 0")`, BASELINE_IS_FRESH `True`
- `tests/sitegen/test_forbidden_defaults.py`: MATCHES dropped from two
  fixtures to one — `restaurant-rich`'s accent moved to `olive` during this
  redecide and it no longer matches "warm cream + serif display +
  terracotta"; `barbecue-rich` still does. Found by `make check`, not
  anticipated — a real, disclosed consequence of the redecide, not something
  I was tuning for.

## `make check` — literal tail

```
.venv/bin/ruff check app tests
All checks passed!
.venv/bin/mypy app
Success: no issues found in 56 source files
.venv/bin/python -m pytest -q
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 55%]
........................................................................ [ 64%]
........................................................................ [ 73%]
........................................................................ [ 82%]
........................................................................ [ 91%]
...............................................................          [100%]
783 passed in 33.71s
```

## Census — literal tail

```
  AGREEMENT  0/0 (0%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels 1f0df47d]
    FRESHLY RE-PINNED. The previous reading of "0 of 0" was scored against labels edc76612 — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 81% across 171 pairs
  SAME TRADE         mean 56% distance = 44% identical, across 30 pairs
                     (45% identical across all 36 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 56% (44% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      26%  law-rich vs law  <-- judged DIFFERENT
      34%  hvac-rich vs hvac-second  <-- judged DIFFERENT
      34%  hvac-second vs roofer-rich  <-- judged DIFFERENT
    (the diversity gate is ON — 0 of 30 same-trade pairs would collide)

  closest pairs — these are the ones that look like one tool:
      26%  law-rich         vs law              same on: action, architecture, hero_subject, leads_with, mood, signature, type_treatment, typeface
      31%  roofer-rich      vs threadbare       same on: first_screen, leads_with, mood, signature, type_treatment, typeface
      34%  hvac-rich        vs hvac-second      same on: action, architecture, leads_with, mood, signature, type_treatment, typeface
      34%  hvac-second      vs roofer-rich      same on: architecture, compositions, hero_subject, mood, signature, type_treatment, typeface
      40%  contractor-bare  vs hvac-rich        same on: action, architecture, leads_with, mood, type_treatment, typeface
```

## What this leaves for Phase 2 (Slice C)

The instrument is exhausted the same way it was before this phase, just on
firmer ground: zero collisions across the whole corpus rather than same-trade
only, and the closest theoretical "same" candidates checked by hand rather
than assumed safe. Nothing here changes what Slice C needs to build —
compositions and trade structure are BRIEF §5's actual "verdict point," and
this phase's job was making sure the measuring instrument is trustworthy
before Slice C's work gets measured against it.
