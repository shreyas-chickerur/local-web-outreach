# A licensure claim, unverified — found, fixed, closed the loop

Six of nineteen fixtures shipped a page asserting "Licensed & insured" /
"Admitted to the bar" / "Registered practice" from `signature.py`'s `stamp`
device, chosen by `trade_kind` alone with nothing checking whether it was
true of the business. Reported by a user review of the corpus; verified
against the repo before any change, then fixed at both layers — the device
that printed the claim, and the gate that should have rejected it and did
not.

## What was verified before changing anything

- `signature.py`'s `stamp` branch: confirmed, chooses the mark from
  `m.trade_kind` alone, no corroboration check.
- `app.core.claims.reads_as_claim()` on the three strings the device prints:
  confirmed all three returned `False` — the gate's own pattern had no entry
  for credential language at all.
- `contractorfacts.found()` against each of the six named fixtures' own
  published text (`about` + scraped `blocks`): confirmed none corroborates
  the credential their page asserts.
      hvac-rich     free_estimate only
      hvac-second   emergency only
      law-rich      emergency only
      law           nothing
      roofer-rich   warranty, free_estimate
      threadbare    nothing (no about text, no content blocks, one photo)

## 1. The gate pattern, widened

`app/core/claims.CLAIM_RE` gained credential/licensure language: `licensed`,
`bonded`, `insured`, `certified`, `accredited`, `board-certified`, `admitted
to the bar`, `state bar`, `registered practice` (and near variants) — a
pattern over the language, not the three exact strings `stamp` happened to
print.

**Verification across the whole corpus after widening:** exactly the six
named fixtures produced `unsupported()` findings, and nothing else did.
Zero false positives anywhere in the other thirteen fixtures.

    hvac-rich            ['insured']
    hvac-second          ['insured']
    law-rich             ['Admitted to the bar']
    law                  ['Admitted to the bar']
    roofer-rich          ['Licensed', 'insured']
    threadbare           ['Licensed', 'insured']

Every finding is `stamp`'s own uncorroborated text. Nothing else in the
corpus was flagged — no legitimate business's real credential copy, no alt
text, got caught by the wider net. `tests/ -k "vision or alt_text or claim"`
(26 tests) unaffected.

## 2. The stamp device, corroborated or absent

`app/site/contractorfacts.py` gained two facts so `care` and `desk` have
something to check against, alongside the existing `trade` one:
`admitted_to_bar` (desk), `registered_practice` (care) — plus `STAMP_FACT`,
a `trade_kind -> fact key` map.

`signature.py`: `available()` now calls `_stamp_corroborated(m)` instead of
checking `trade_kind` alone — `stamp` is only offered when the fact its
trade_kind needs is actually found in the business's own text. `render()`'s
mark now comes from `contractorfacts.label_for()`, not a second hardcoded
copy of the same three strings.

**Decision: dropped from `available()`, not rendered with a substitute.** A
device the material cannot support is not a choice — matches every other
device's own rule (`quote` needs `m.quotes`, `marquee` needs three
services). No generic placeholder, no invented corroboration.

**Verified: all six named fixtures lose the mark**, confirmed by direct
check (`stamp` absent from `available()`, `data-device="stamp"` absent from
the rendered page, `unsupported()` empty) — matching the report's predicted
outcome exactly, not a case where "something is wrong."

## 3. The redecide

Signature is axis eleven, so shrinking `stamp`'s availability changes what
the identity call could choose — a `--redecide` was required, not optional.
`test_the_gate_is_satisfiable` checked first (passed: the required-high
axes' combined room is unaffected, `signature` is not in `REQUIRED_HIGH`).

**First attempt produced a genuine unresolved collision**:
`hvac-rich`/`roofer-rich` matched on all four required-high axes
(`first_screen=proof`, `type_treatment=stamped`, `architecture=ledger`,
`typeface=oswald-barlow`), an unambiguous collision under the gate's own
rule. Not hidden — `roofer-rich`'s own frozen brief recorded
`"_gate_unresolved": true`, the retry-then-perturb sequence's honest "could
not resolve" signal. Diagnosed rather than compensated for: `hvac-rich` was
decided first in slug order and should have been in `roofer-rich`'s
comparison window (`WINDOW=60`, well within it), so this was the gate
correctly trying and failing to find a free combination for one business,
not a `WINDOW`/cardinality problem — `test_the_gate_is_satisfiable` already
confirmed the arithmetic has room, and Phase 1's own first redecide attempt
under the same `WINDOW` found zero collisions on its first try. Retried
rather than widening anything: a second full `--redecide` cleared with zero
collisions across all 171 pairs (`test_no_collision_survives_anywhere_in_
the_corpus` passes) and no fixture recorded `_gate_unresolved`.

**A side effect worth naming honestly: `stamp` is now unreachable in this
specific 19-fixture corpus.** Not broken — `available()` still offers it to
any business whose own text matches `licensed_insured` / `registered_
practice` / `admitted_to_bar` — but none of the nineteen real businesses'
scraped copy happens to contain those specific phrasings this round
(`signature=stamp` appears zero times in the post-redecide census; compare
`none` appearing nine times, `quote` twice, `ticker` twice, `corner_inset`
five times, `scroll_gallery` once). A business that verbally claims
licensing in different wording ("TX License #12345", "a fully licensed
Texas contractor") would not match today's patterns and would lose the
device even with a legitimate claim to make — the corroboration is
deliberately strict (exact phrase, not inferred), and strict-but-silent is
the correct failure mode for a licensure claim, but it does mean the device
is currently proven to REMOVE a false claim and not yet proven to CARRY a
true one on this corpus. Widening the patterns further, or finding a real
business whose site uses one of the covered phrasings, is future work, not
done here.

Eleven pairs re-judged against the corrected rendering (all fixtures
moved) — the closest by distance in the tuning set; held-out verdicts
retired only, per the standing rule, and not repopulated this round. All
eleven DIFFERENT. Full verdicts and `why` text in `tests/fixtures/pairs.json`;
constants re-pinned in `tests/test_the_instrument_reproduces.py` and
`tools/quality_census.py`.

## 4. The standing test

`tests/test_no_unverified_credential_ships.py`,
`test_no_fixture_asserts_a_credential_its_own_material_does_not_back` —
holds the invariant across the whole corpus (any device, any section, ever),
not the six strings. Confirmed it fails with the pre-fix `signature.py` (the
widened `claims.py` in place, `stamp` still unconditional) — reproduces the
exact six-fixture finding above — and passes with both halves of the fix.
Confirmed separately that reverting BOTH files together also fails to catch
it (the old `claims.py` doesn't recognise the claim at all), which is the
whole reason this was two fixes and not one.

## 5. make check — literal tail

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
........................................................................ [ 70%]
........................................................................ [ 79%]
........................................................................ [ 88%]
........................................................................ [ 97%]
....................                                                     [100%]
812 passed in 43.03s
```

Post-redecide, zero `unsupported()` findings across the whole corpus
(reconfirmed directly, not just via the standing test).

## Census — literal tail

```
  AGREEMENT  0/0 (0%) of cross-comparisons ordered correctly, 0 unsure and not scored  [labels 9ed8ff8e]
    FRESHLY RE-PINNED. The previous reading of "0 of 0" was scored against labels 1f0df47d — a different set of verdicts, so this is not that number having fallen. It is the first reading of a new one.
    threadbare excluded from every score — no design to compare, only an absence. See agreement.UNSCORED.

  PAIRWISE DISTANCE  mean 80% across 171 pairs
  SAME TRADE         mean 53% distance = 47% identical, across 30 pairs
                     (47% identical across all 36 pairs including threadbare — printed so the exclusion is visible, not so the better number is)
                     baseline 53% (47% identical) — FRESHLY RE-PINNED — this run IS the baseline, so there is nothing to compare yet. The next run is the first that can say better or worse.
                     <-- the number Slice B has to move
      34%  hvac-rich vs hvac  <-- judged DIFFERENT
      37%  barbecue vs restaurant-casual  <-- judged DIFFERENT
      37%  contractor-bare vs hvac-second  <-- judged DIFFERENT
    (the diversity gate is ON — 0 of 30 same-trade pairs would collide)

  closest pairs — these are the ones that look like one tool:
      34%  hvac-rich        vs hvac             same on: action, first_screen, hero_subject, leads_with, mood, signature, type_treatment
      37%  barbecue         vs restaurant-casual same on: architecture, first_screen, hero_subject, leads_with, mood, typeface
      37%  contractor-bare  vs hvac-second      same on: action, first_screen, mood, type_treatment, typeface
      37%  dentist-rich     vs dentist          same on: action, architecture, hero_subject, mood, type_treatment, typeface
      37%  hvac             vs roofer           same on: first_screen, mood, signature, type_treatment, typeface
```

## Numbers, before this fix / after

| | before | after |
|---|---|---|
| fixtures asserting an unverified credential | 6 | 0 |
| `CLAIM_RE` recognises credential language | no | yes |
| `stamp` corroboration check | none (trade_kind only) | `contractorfacts.STAMP_FACT` |
| RULER / RULE | a762bcc9 / 254e171b | unchanged |
| LABELS | 1f0df47d | 9ed8ff8e |
| HELD_OUT | 1c862e02 (16 verdicts, 5 held out) | e3b0c442 (empty — hash of nothing) |
| same-trade mean | 55.52% distance = 44% identical | 53.33% distance = 47% identical |
| closest same-trade pair | `law`/`law-rich`, 26% | `hvac`/`hvac-rich`, 34% |
| gate collisions, whole corpus | 0 of 171 | 0 of 171 (after one retried redecide) |
| unreachable | 0 | 0 |
| live verdicts | 16 (5 held out) | 11 (0 held out) |
| tests | 811 | 812 |

The same-trade mean moving is not itself the finding — BRIEF §3 gives no
credit for a redecide raising it and no blame for it falling as a side
effect of an unrelated fix. What matters is what did not move: zero
collisions, zero unverified claims, and every re-judged verdict's
conclusion held.
