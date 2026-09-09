# Phases C, D, F, G — the signature device, the forbidden defaults, the keyless
# path, and the point at which eleven fixtures stop being able to measure

## Phase C — the evidence named the device, not colour structure

`unreachable()` was zero, so no comparison was out of reach and no axis was
forced. The four "same" verdicts decided it instead, unanimously: every pair a
stranger called one studio shared **exactly `first_screen` and `architecture`**
and differed only on paint, lettering, or what the business published.

That ruled out the next two items in §2.1's order on evidence rather than
preference. **Colour structure**: all four pairs differed on `accent` and on
`mood` and were called one studio anyway. **Section edges**: `architecture`
already decides the separator — `ledger` rules a line, `banded` changes ground,
`gallery` leaves whitespace — and a second axis for it would be `layout_bias`
again.

What was left was four pages sharing an opening and an arrangement with
**nothing else designed on them**.

## Phase D — the signature device

`app/site/signature.py`, twelve devices from §2.3's list plus `none`, exactly
one per site. Hero treatments are excluded because §2.3 excludes them — those
are positions on axis one.

    ledger  quote  marquee  stamp  index  ticker
    margin_note  offset  edge_type  corner_inset  scroll_gallery  duotone

Availability is a real constraint: `threadbare` can carry four, `contractor-bare`
nine, most thirteen. A device chosen for a business without the material renders
nothing rather than an empty band.

Proven the way the last two axes had to be: the class attribute is stripped
before comparing, every available device renders a different page, and
`test_the_device_never_reaches_the_first_screen` holds §2.3's own rule.

**`signature` is deliberately NOT in `REQUIRED_HIGH`.** Putting it there would
presume the answer to the claim it was built to test.

### The binding claim: PASSED, and narrower than it looks

Two pairs shared `first_screen` and `architecture` after the re-decide, and both
are judged different:

    barbecue (duotone) / restaurant-bare (quote)     different
    bare-trade (quote) / contractor-bare (ticker)    different

**Both turn on the same device.** `quote` gives a whole screen to one review at
display size and changes the page's proportions; `duotone`, `ticker`, `stamp`,
`margin_note` are bands of ordinary height. So the evidence is about `quote`
more than about devices in general, and the judging rule added to `pairs.json`
says exactly that: a device counts when it changes the page's proportions, on
the same test the type-setting rule uses.

### The `min()` prediction held

`weight_of()` was annotated years-of-commits ago with the prediction that the
signature device is where visibility and decidedness disagree in the other
direction. It does: `VISIBILITY` 1.0, `DECIDEDNESS` 3.0 — the most decided thing
on the page, seen once while scrolling — and `min()` suppresses it to 1.0. It is
the first entry to extend `DECIDEDNESS` past `first_screen`'s 2.5, because
nothing about the material forces it beyond whether it can be built at all.

## And then the corpus ran out of things to disagree about

Judged whole-page after the device landed, **none of the twenty pairs is one a
stranger calls one studio.** Zero "same" verdicts.

    agreement   0 of 0

That is §2's governing requirement met on this corpus — and the instrument
exhausted. Agreement is a RANK: every "different" pair must outrank every "same"
pair, and with no "same" pair there is nothing to rank. **No further axis can be
validated on eleven fixtures.** What that needs is more businesses, not more
axes.

The single-axis degeneracy check is gone rather than adapted, and
`test_the_corpus_has_no_pair_a_stranger_calls_one_studio` records why: with
every verdict "different", any axis whose value is unique per fixture explains
all twenty for free. `section_order` and `compositions` both score 20 of 20 that
way and neither means anything.

## Phase F — the forbidden defaults, encoded

`app/site/defaults.py` checks all nine of §2.4 mechanically against the rendered
page and the resolved theme. Two fixtures match, both the entry §2.4 lists
first:

    barbecue          warm cream + serif display + terracotta
    restaurant-rich   warm cream + serif display + terracotta

§2.4 predicts this — "the six existing moods sit close to several of these" —
and a check that passed everything on its first run would mean it was written to
pass. `test_the_check_can_actually_fire` asserts every rule against a page built
to break it, so the list cannot become nine no-ops.

**Not wired into the audit as a build gate**, and that is deliberate: gating
would reject two fixtures today, and escaping the mood presets that put them
there is its own piece of work.

## Phase G — the keyless path varies by business

`fallback_opening` mapped a business purely by trade keyword, so two roofers on
one street got byte-identical sites — §2's exact failure, through the door
marked "no key". The trade still chooses the mood, which is the one thing a
trade genuinely implies; a stable hash of the business name chooses the accent,
the opening, the type treatment, the arrangement and the device, from what that
business can actually carry. Seeded the way `identity.py` seeds perturbation, so
there is one technique and not two.

    Status Roofing LLC     industrial · yellow · split · stamped · ledger  · stamp
    Lone Star Roofing Co   industrial · violet · type  · stamped · stacked · margin_note

Deterministic — the same brief gives the same answer every time, which is the
replay invariant.

## Phase E — NOT DONE, and the reason is the 0 of 0 above

Palette from the business's own photographs would re-decide the corpus, and
**the instrument currently cannot say whether that made anything better or
worse.** Building it now would mean shipping a change to what every site looks
like with no way to validate it, which is the mistake this run exists to avoid.
It needs a wider corpus first.

## Numbers

    agreement   0 of 0 — no "same" pair left to rank
                ruler d2f37ed7, rule 95f4d93e, labels a9beee08,
                held-out 7fbd905e
    census      same-trade 55% distance = 45% identical, 7 scored pairs
                closest pair contractor-bare / roofer at 45%, judged DIFFERENT
    unreachable 0
    gate        0 of 55 pairs collide under its own rule
    tests       769

## Literal output

### `make check`

```
........................................................................ [ 65%]
........................................................................ [ 74%]
........................................................................ [ 84%]
........................................................................ [ 93%]
.................................................                        [100%]
769 passed in 13.22s
```

### `tools/quality_census.py` (tail)

```
                     compositions=

  AGREEMENT  0/0 (0%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels a9beee08]
    FRESHLY RE-PINNED. The previous reading of "41 of 64" was scored against labels d69c25ec — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 80% across 55 pairs
  SAME TRADE         mean 55% distance = 45% identical, across 7 pairs
                     (44% identical across all 10 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 55% (45% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      45%  contractor-bare vs roofer  <-- judged DIFFERENT
      45%  hvac vs roofer  <-- judged DIFFERENT
      55%  barbecue vs restaurant-rich  <-- judged DIFFERENT
    (the diversity gate is ON — 0 of 7 same-trade pairs would collide)

  closest pairs — these are the ones that look like one tool:
      45%  contractor-bare  vs roofer           same on: architecture, hero_subject, leads_with, mood, type_treatment
      45%  hvac             vs roofer           same on: first_screen, mood, signature, type_treatment
      52%  restaurant-bare  vs salon            same on: first_screen, mood, type_treatment
      55%  barbecue         vs restaurant-rich  same on: accent, architecture, hero_subject, leads_with, mood
      55%  bare-trade       vs law              same on: action, leads_with, mood, type_treatment
```
