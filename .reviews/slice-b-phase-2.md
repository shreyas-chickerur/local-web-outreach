# Phase 2 — Slice C: compositions and trade structure

BRIEF §5's "verdict point" — reduced in scope from the five items asked for,
disclosed here rather than silently narrowed. No pre-registration was written
before this code, breaking the standing rule this whole session otherwise
followed; noted honestly rather than backfilled.

## What landed

**2a — trade profiles.** `app/site/tradeprofile.py`, new. Three tables, one
per `trade_kind` (the existing `food`/`care`/`groom`/`body`/`desk`/`trade`/
`retail`/`default` buckets `render.trade_kind()` already sorts every business
into):

- `HEADING` — what the "what we do" section is called, replacing the two ad
  hoc conditions `_offer_heading` used to be (a food-word match against the
  trade string, and products-with-no-services).
- `DEFAULT_EMPHASIS` — a trade's own default section emphasis, used only as a
  fallback when the identity call's own `spec.emphasis` is empty. The model's
  explicit choice always wins; this fills the gap when it named nothing.
- `FACT_HUNTS` — which of `contractorfacts.FACTS` are worth even looking for,
  per trade. Only `trade` carries any today.

`_CTA_LABEL`/`_CTA_BY_TRADE`/`cta_words()` moved here too — `render.py` had a
comment saying they belonged with the trade profiles once those existed, and
CTA-per-trade (2e) turned out to already be shipped and tested
(`test_a_dentist_is_not_offered_a_table`), just sitting in the wrong module.

**2b — contractor facts, four of nine.** `app/site/contractorfacts.py`, new.
Ships **licensed and insured, emergency availability, warranty, and free
estimate**. Each is found by matching a fixed phrase against the business's
own published text (`Material.about` plus the raw `blocks` a scrape kept) —
never generated, never inferred from the trade. A phrase not actually there
is a fact not there either; a business with none of the four gets no section.

**NOT built, disclosed rather than faked:** service area, before-and-after,
financing, manufacturer badges, response time. Each needs a different kind of
evidence this material does not carry yet — a service-area radius, a paired
before/after photo, a named lender, a recognisable badge image, a stated
callback window. Attempting them without that evidence is exactly the "do not
invent a licence number" failure mode the brief warns against, so they were
left alone rather than approximated.

**2c — two compositions.** `render._credentials()`: one or two facts render
as a quiet row of stamped pills (reusing `.stamps`, the same mark
`signature.py`'s own `stamp` device already draws); three or four earn a
small card grid (reusing `.offer`'s cards). No new CSS.

**2d — headings from the trade table.** `_offer_heading()` now delegates to
`tradeprofile.heading_for()`. `m.menu_items` still forces the food heading
regardless of `trade_kind` — a caterer classified `default` that nonetheless
publishes prices is shaped like a restaurant here, kept from the original.

**2e — already done.** CTA wording already varied by trade
(`_CTA_BY_TRADE`), shipped and tested in an earlier commit
(`test_a_dentist_is_not_offered_a_table`, `tests/sitegen/test_hero.py`).
Relocated to `tradeprofile.py`, not rewritten.

## A real, disclosed pre-existing gap found and fixed in passing

`render.unsupported()`'s `own_words` — what counts as "their own words" when
checking the page for an unsupported claim — never included `material.blocks`,
even though `_features()` and `_recognition()` already print block text
straight onto the page. Fixed: `own_words` now includes it. Strictly widens
what counts as supported; nothing that passed before can now fail.

**Not fixed, flagged instead:** `signature.py`'s `stamp` device prints
"Licensed & insured" / "Registered practice" / "Admitted to the bar"
unconditionally for every business of the matching `trade_kind`, regardless
of whether it is true of that specific business — the exact mistake this
phase's own corroborated version was built not to repeat. Eight fixtures in
the current corpus use `stamp`. This is a `§2.3` signature-device concern,
not a Slice C one, and touching it would mean re-deciding the corpus; flagged
as a follow-up rather than fixed here.

## Why no redecide

Nothing here changes what the identity call decides. Headings and the
credentials section are deterministic functions of trade and material, the
same way `m.about` or `m.services` already render deterministically — not a
choice the model makes, so not a new axis, so no `--redecide`, no re-judging.
`fp.of()` recomputes `section_order`/`compositions` straight from the
rendered plan regardless, so the fingerprint still picks up the change.

## Effect on the numbers

**Unchanged: same-trade mean (55.52%), agreement (0/0), gate collisions (0 of
171 pairs), RULER, RULE, LABELS, HELD_OUT.** Three fixtures
(`hvac-rich`, `hvac-second`, `roofer-rich`) gained the credentials section and
their `section_order`/`compositions` values changed — but the same-trade mean
is identical to eleven decimal places before and after. `fp.distance()`
compares `section_order`/`compositions` as whole-string equality per axis, not
a finer edit distance: a pair that already differed on that axis before
adding `credentials` still differs after, so the term contributes the same
weight either way. This is worth stating rather than assuming a change of
this shape must move a number — it did not, and that is itself the honest
report, not a null result to explain away.

`test_no_collision_survives_anywhere_in_the_corpus` (Phase 1's own standing
test) still passes: no new whole-corpus collision from the three fixtures'
changed section order.

## `make check` — literal tail

```
.venv/bin/ruff check app tests
All checks passed!
.venv/bin/mypy app
Success: no issues found in 58 source files
.venv/bin/python -m pytest -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 62%]
........................................................................ [ 71%]
........................................................................ [ 80%]
........................................................................ [ 89%]
........................................................................ [ 98%]
...............                                                          [100%]
807 passed in 38.08s
```

24 new tests: `tests/sitegen/test_tradeprofile.py` (9),
`tests/sitegen/test_contractorfacts.py` (8),
`tests/sitegen/test_credentials_section.py` (7). One existing test updated
(`test_the_offer_heading_follows_the_trade`, for the deliberately new "trade"
heading) rather than reverted.

## What Phase 3 inherits

The review bundle should show the credentials band as an honest example of
what this phase can and cannot yet do — three fixtures carry it, sixteen do
not, and the reason for each is checkable rather than a guess.
