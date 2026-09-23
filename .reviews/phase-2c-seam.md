# Phase 2c — two regressions in Phase 2b, closed and proven

Branch `slice-b-identity`, from `c39e1cb` (the Phase 2b handoff). Part A
proper: `829ab37` (Step 0, both reproductions, red first), `3400dcb`
(Step 1, both fixes by rule), `753861c` (Step 2, class 8 planted, the
superset test widened), `99c3170` (Step 3, a real-corpus regression the
Step 1 fix itself introduced, found and closed before it shipped),
`0b653df` (Part A handoff). Before Part B, three more asked for
directly: CLAIM_RE's `#1` fixed and `top[- ]rated` added (with planted
classes 9-10), the 12 known baseline gaps in
`test_seam_planted_corpus.py` converted to `xfail(strict=True)`, and
the `_corroborated_numbers()` coincidences enumerated with their real
sentences — see the addendum after §5.
`.reviews/FEEDBACK-FROM-SHREYAS.md` and `Claude outputs/` left
untracked throughout, as asked.

## §0 — both reproductions, before anything changed

Both reproduced exactly as given, in `829ab37`, before `Step 1` touched
any gate:

1. **The credential invariant, one level up.** The exact snippet given
   against `hvac.json`'s material: `render.unsupported()` (old) returns
   `['best in', 'award-winning']`; `seam_gates.gate()` (new) returned
   `[]`.
2. **The review-count floor.** `contradicts(100, 136)` was `True` with
   no way to say otherwise; `roofer-rich`'s real, shipped page dropped
   both "100+ Google reviews" and "100+ verified reviews", confirmed by
   building the page end to end (`build_from_spec`) and finding "100+"
   absent, "136" present.

Both matched the round's own description exactly. Nothing differed.

## §1 — Changed

  `app/site/seam_gates.py`  `_credential_backed()` (bool) replaced by
    `_credential_backed_remainder()` (returns the sentence with only the
    backed span(s) removed); `unsupported_sentences()` runs CLAIM_RE on
    the remainder instead of skipping the whole sentence;
    `unexplained_prose()` only exempts the sentence when the remainder
    is pure connective glue (`_is_pure_connective_remainder`). The
    exact-label case (`_LABEL_TO_KEY`) is checked FIRST and wins
    outright — needed because two of ten labels ("Financing available",
    "Workmanship warranty") only partially match their own trigger
    pattern, and computing every span first let the smaller regex span
    win the overlap (see Step 3 below).

  `app/site/contradiction.py`  `REVIEW_COUNT_RE` gained named groups
    `bound` ("over"/"more than") and `plus` ("+"); `contradicts()` takes
    a `lower_bound` flag and only treats a floor claim as contradicting
    when it sits ABOVE the corroborated count beyond tolerance.
    `reconcile()` and `seam_gates.contradicted_review_counts()` both
    pass the flag through.

  `tests/sitegen/test_phase_2c_reopened_gaps.py`  new — the two
    reproductions from §0, held as the standing regression guard for
    this round the way `test_seam_reopened_gaps.py` holds Phase 2b's.

  `tests/test_no_contradicted_fact_ships.py`  updated for the new
    named groups; added the two-direction tests plus the real hvac
    "over 20,000" case.

  `tests/fixtures/seam/hvac-foreign.{html,manifest.json}`  planted
    class 8, "credential-laundered claim" — the exact given sentence.

  `tests/sitegen/test_seam_gates.py`  the superset test widened with
    two more sweeps (every real fixture's own rendered page; a
    generated matrix of every corroborated credential × every CLAIM_RE
    shape); a new regression test pinning that every fact's own label,
    alone, is fully backed (the Step 3 bug, held directly).

  `tests/sitegen/test_seam_design_page.py`,
    `.reviews/phase-2-design-page-findings.md`  the credential fix
    reaches the real designed page too — pin moved 42 → 48, all 6
    new findings classified (all real; 0 invented).

  `.reviews/phase-2b-seam.md`  corrected in place, dated, original
    sentence kept — the "pre-existing" attribution for the
    `roofer-rich` snapshot failures was wrong.

  `app/core/claims.py`  `CLAIM_RE` gained `(?<!\w)#1\b` as its own
    alternative outside the shared `\b(...)\b` group (fixing the dead
    `#1` case) and `top[- ]rated` inside it (new).

  `tests/sitegen/test_seam_reopened_gaps.py`  the threadbare claim
    count pinned by `test_gap_1_the_credential_invariant_stays_closed`
    moved 9 → 10, since "#1" is now its own real CLAIM_RE finding.

  `tests/fixtures/seam/{hvac,restaurant-casual}-foreign.{html,
    manifest.json}`  classes 9 ("top rated") and 10 ("top-rated")
    planted on both, both invented, both confirmed absent from the real
    material first.

  `tests/sitegen/test_seam_gates.py`  `_CLAIM_RE_EXAMPLES` updated:
    "Ranked#1" (the workaround for the dead alternative) replaced with
    the now-natural "voted #1"; "top rated"/"top-rated" added.

  `tests/sitegen/test_seam_planted_corpus.py`  `_KNOWN_GATE_GAPS`
    added; `_cases()` attaches `xfail(strict=True)` to exactly those 12
    (business, class) pairs. Module docstring rewritten — the file is
    no longer "expected to be red," it names its own known gaps.

## §2 — Decisions

  **Class 8 not planted on `restaurant-casual`** — its real material
  (`about`/`blocks`) corroborates zero `contractorfacts` credentials
  (checked directly: `_material_contractor_facts()` on its real about+
  blocks text returns `frozenset()`), so this exact bug shape has no
  real credential there to launder a claim with. Fabricating one in the
  fixture's own "real" material to force the planting to fit would
  itself be the kind of invention this project's gates exist to catch,
  and the fixture is pinned by four other tests (render snapshots,
  pairs, performance and capture baselines) a synthetic edit would
  also perturb. Forecloses: a fourth planted-manifest business would be
  needed to genuinely exercise class 8 twice; not attempted this round.

  **`_corroborated_numbers()` left unchanged** — investigated, not
  fixed. The round's own rule ("stands alone as the field value, or
  sits in the same run as the field it came from") reads as "drop the
  hours/address digit-fallback, trust the sentence-level `bare in own`
  check instead." Tried it; broke the real corpus's own zero-findings
  invariant on **13 of 19 fixtures** — corrected here from an earlier
  "8", which was read off a `tail`-truncated run and never actually
  verified against the full corpus-check output before being reported;
  the addendum below has every one of the 13, each number, and its real
  sentence. Cause: `visible_text_runs()` merges adjacent unpunctuated
  sibling text into one run (`roofer-rich`'s own page reads "10021
  Cayuga Dr Fri 7:30am to 5pm" as a single sentence), so the
  sentence-level check cannot see hours or address in isolation the way
  the flat per-field set can. A correct fix needs a number tied to
  which field backs it, not a flat set — bigger than this bullet's
  "small" framing. Forecloses: the coincidences enumerated in the
  addendum remain live; a wholly-fabricated small number riding with no
  other uncorroborated wording in the same sentence would still pass
  `unbacked_numbers()` today. Flagging for the next slice, not deciding
  it silently.

  **CLAIM_RE's `#1` alternative — fixed this round, not the one
  before.** Reported, not fixed, in Part A proper (see the superseded
  paragraph this replaces, kept in the commit history rather than
  deleted): `\b#1\b` requires a word character glued directly onto `#`
  with no space, so "voted #1" / "the #1" never matched. Fixed as its
  own alternative, `(?<!\w)#1\b`, outside the shared `\b(...)\b` group
  — a negative lookbehind for a word character, not `\b`, is the right
  boundary when the token itself starts with a non-word character.
  `top[- ]rated` added the same edit; CLAIM_RE never had this
  superlative at all. Two consequences pinned rather than left to drift:
  `test_seam_reopened_gaps.py`'s threadbare claim count moved 9 → 10
  (the button's own "#1" is now its own finding); the real 19-fixture
  corpus stays at zero (checked directly, `tools/seam_corpus_check.py`).
  Planted classes 9 ("top rated") and 10 ("top-rated") added to `hvac`
  and `restaurant-casual`, both invented, both confirmed absent from
  the real material first.

  **`test_seam_planted_corpus.py`'s 12 known gaps converted to
  `xfail(strict=True)`.** Each of the 12 (formerly 13; `class7d`'s "#1"
  planting now passes here too, on the currently-wired gate, once
  CLAIM_RE could see it) is named individually in `_KNOWN_GATE_GAPS`
  with the class and business, not a blanket marker — a `strict` XPASS
  is a failure, so fixing one of these in the currently-wired gate
  without updating this file breaks the build, the same protection a
  wrong "pre-existing" label was supposed to give and, per §0 of the
  Phase 2b handoff, didn't. The file is now green on a normal run (22
  passed, 12 xfailed) instead of "expected red."

## §3 — Numbers

**Planted classes caught, including class 8, 9, 10:**

| Business | Classes planted | Caught by fixed gate |
|---|---|---|
| hvac-foreign | 1-6, 4b, 7a-7d, 8, **9, 10** (14 total) | all 14 |
| restaurant-casual-foreign | 1-6, 7a-7d, **9, 10** (12 total) | all 12 |
| threadbare-foreign | 1, 2, 7a-7d (6 total, no bag-of-words gap, no script) | all 6 |

(Class 5 needs a real render; caught via the same simulated post-script
DOM Phase 2b used, for hvac and restaurant-casual — threadbare has no
`<script>` to carry one. Classes 9/10 — "top rated"/"top-rated" — added
before Part B, after CLAIM_RE gained that alternative.)

**Superset test counts:**

| Sweep | Count | Result |
|---|---|---|
| Planted (3 manifests, every planting) | 32 sentences | 0 missing |
| Real fixture pages (all 19, every visible sentence) | 1,930 sentences | 0 missing |
| Generated (every corroborated `contractorfacts` credential of every real fixture × every CLAIM_RE alternative, one sentence each) | 18 credentials × 25 claim shapes = 450 combinations | 0 laundered |

**Snapshot and review-bundle tests, `9b7b6c5` versus now:**

| Test | at `9b7b6c5` | at `c39e1cb` (Phase 2b handoff) | now |
|---|---|---|---|
| `test_render_snapshots.py::test_every_fixture_still_renders_the_pinned_bytes` | pass | **fail** | pass |
| `test_build_review.py::test_the_committed_review_bundle_shows_the_corpus_that_shipped` | pass | **fail** | pass |

Neither re-pinned. `roofer-rich`'s rendered bytes now carry "100+"
again, unchanged otherwise (confirmed by running the render three times
in a row before this round started, and it is deterministic).

**Full-suite failure list, deselecting the browser-gated tests
(3 in `test_chrome_cdp.py`/`test_site_fetch.py`, the DOM script-render
test, the collision-at-every-width test, the synthetic-INP-click
test — 8 total, same list as Round 8's / Phase 2b's precedent):**

`uptime` before running: `3.98 2.98 2.67` — under 6. Full run, Part A
proper (before the CLAIM_RE fix / xfail conversion): **13 failed, 1532
passed, 3 skipped, 8 deselected, 9 xfailed** in 150s. Same run, after
the three pre-Part-B changes below: **0 failed, 1577 passed, 3 skipped,
8 deselected, 21 xfailed** in 97s. `ruff check app tests` and `mypy
app` both clean at every step.

The 13 (now resolved into 12 named `xfail(strict=True)` cases plus one
that now genuinely passes) were all in
`tests/sitegen/test_seam_planted_corpus.py` — the file's own docstring
said it measures the OLD, currently-wired gate and was expected to be
red. Status at `9b7b6c5`, checked by actually running that file there
(not assumed):

| Test | Status at `9b7b6c5` | Status now |
|---|---|---|
| `hvac-class2`, `hvac-class3`, `hvac-class5`, `hvac-class6` | **fails** (same 4 classes, pre-existing) | `xfail(strict=True)` |
| `restaurant-casual-class2`, `-class3`, `-class5`, `-class6` | **fails** (same 4 classes, pre-existing) | `xfail(strict=True)` |
| `hvac-class4b`, `hvac-class7b` | **did not exist** — added by Phase 2b's own Step 1, after `9b7b6c5` | `xfail(strict=True)` |
| `restaurant-casual-class7a`, `restaurant-casual-class7b` | **did not exist** — same reason | `xfail(strict=True)` |
| `hvac-class7d` | **did not exist** — same reason | **passes now**, unmarked — CLAIM_RE's `#1` fix reaches the currently-wired gate too, since `render.unsupported()` imports the same `CLAIM_RE` object |

The 8 that existed at `9b7b6c5` fail there too, unchanged — genuinely
pre-existing. The 4 that didn't exist yet (once `class7d` is set aside)
cannot be "pre-existing at `9b7b6c5`" by definition; they are, however,
byte-identical failures to what `c39e1cb` (Phase 2b's own handoff,
before this round touched anything) already had — confirmed by running
this same file in a worktree at `c39e1cb` and diffing the failure list,
which matched exactly, before any of this round's fixes landed. Phase
2c added zero new failures to this file; it only closed one
(`class7d`) as a side effect of fixing CLAIM_RE, and converted the
other 12 from "expected red, unmarked" to "expected red, named and
enforced."

None of the 15 failures phase-2b-seam.md counted are gone except the 2
Part A fixed (`test_render_snapshots.py`, `test_build_review.py`) and
the 1 the CLAIM_RE fix closed as a side effect (`hvac-class7d`) — 15 −
3 = 12, matching the 12 now named in `_KNOWN_GATE_GAPS`.

## §4 — Assumptions I could not verify

None beyond what §2 already states as open (the `_corroborated_numbers()`
fix). Both reproductions and both fixes were verified directly against
running code and the real fixture corpus, not taken on faith. One
number I stated without full verification and had to correct myself
(the "8 of 19" `_corroborated_numbers()` claim, actually 13) — noted in
§2 and the addendum rather than quietly overwritten.

## §5 — Questions I want answered before the next slice

- Should a fourth planted-manifest business (one that genuinely
  corroborates a `contractorfacts` credential AND is not `hvac`) be
  added so class 8 has two independent proofs the way classes 1-7 do?
- Is the `_corroborated_numbers()` gap worth a real fix now — tying a
  corroborated number to which field backs it, rather than a flat set —
  given the addendum below shows it is not rare (13 of 19 real
  fixtures carry at least one coincidental pass)?

(The CLAIM_RE `#1` question from the version of this document Part A
shipped is answered — fixed below, before Part B.)

## Addendum — before Part B: CLAIM_RE, the baseline file, the coincidences

Three more things asked for directly, none of them Part B:

**1. CLAIM_RE's `#1` fixed, `top[- ]rated` added.** See §1/§2 above.

**2. `test_seam_planted_corpus.py` made green.** See §2/§3 above —
`_KNOWN_GATE_GAPS`, 12 named `xfail(strict=True)` cases.

**3. Every number that only passes `_corroborated_numbers()` by
coincidence, on every real fixture where one exists — corrected to
13, not 8.** The "8" in Part A's own commit message and code comment
was read off a `tail`-truncated `tools/seam_corpus_check.py` run and
never checked against the full output before being reported to you —
that was a mistake, corrected here with the complete run. "Coincidence"
means: this exact number only appears in `_corroborated_numbers()`
because of the flat hours/address digit-run fallback (§2); with only
rating, reviews, phone digits, menu prices and the renderer's own
computed counts (`len(menu_items)`/`len(services)`) in the set, this
number would not be backed. The sentence is the real, rendered sentence
this number appears in today, quoted verbatim (truncated past ~150
chars):

| Fixture | Coincidental number(s), with the real sentence they ride in |
|---|---|
| `barbecue-rich` | `688`, `11`, `00`, `22` in `"★ 4.6 · 18702 Google reviews 688 Freeport Pkwy Fri-Sat 11:00-22:00"`; `688`, `75019,` in `"Address 688 Freeport Pkwy, Coppell, TX 75019, USA Phone (972) 471-5462"` and the footer `"© Hard Eight BBQ 688 Freeport Pkwy, Coppell, TX 75019, USA (972) 471-5462"` |
| `barbecue` | `9225`, `11`, `00`, `21` in `"★ 4.8 · 13880 Google reviews 9225 Preston Rd Mon-Tue-Wed-Thu-Fri-Sat-Sun 11:00-21:00"`; `9225`, `75033,` in the address line and footer |
| `bare-trade` | `400`, `203,`, `75036,` in `"Address 400 Stonebrook Pkwy Ste 203, Frisco, TX 75036, USA"` and the matching footer |
| `contractor-bare` | `5566`, `75033,` in `"4.7 stars 57 reviews 5566 Main St, Frisco, TX 75033, USA ..."` (repeated 3x in one run), the address line, and the footer |
| `dentist-rich` | `3920`, `9`, `00` in `"3920 McDermott Rd Ste b Wed: 9:00am to 4:00pm"`; `3920`, `75025,` in the address line and footer |
| `hvac-rich` | `8765`, `104`, `7`, `00`, `5`, `30` in `"8765 Stockard Dr Ste 104 Monday – Friday 7:00 AM to 5:30 PM"`; `8765`, `104,`, `75034,` in the address line and footer |
| `hvac-second` | `1608`, `09`, `00`, `17` in `"★ 4.9 · 1226 Google reviews 1608 Whitlock Ln Unit J Mo,Tu,We,Th,Fr,Sa,Su 09:00-17:00"`; `1608`, `75006,` in the address line and footer |
| `law-rich` | `3700`, `77006,` in `"Address 3700 Montrose Blvd, Houston, TX 77006, USA Phone (281) 801-5617"` and the footer |
| `restaurant-bare` | `8240`, `175` in `"★ 5.0 · 45 Google reviews 8240 Preston Rd Ste 175"`; `8240`, `175,`, `75024,` in the address line and footer |
| `restaurant-rich` | `7110`, `5`, `9` in `"★ 4.6 · 676 Google reviews 7110 Main St Sunday – Wednesday: 5pm – 9pm"`; `7110`, `75033,` in the address line and footer |
| `roofer-rich` | `10021`, `7`, `30`, `5` in `"10021 Cayuga Dr Fri 7:30am to 5pm"`; `10021`, `75228,` in the address line and footer |
| `roofer` | `1927`, `100,`, `75036,` in `"Address 1927 Old Witt Rd Ste 100, Frisco, TX 75036, USA Phone (469) 424-4623"` and the footer |
| `threadbare` | `8655`, `75034,` in `"Address 8655 Brookhollow Blvd, Frisco, TX 75034, USA Phone (945) 289-8844"` and the footer |

(`bare-trade`, `contractor-bare`, `law-rich`, `roofer`, `threadbare`
have no hours line rendered as a bare fact stat the way the others do,
so their coincidences are address-only. `dentist`, `hvac`, `law`,
`restaurant-casual`, `salon`, `salon-rich` carry none — their address/
hours text happens to always sit in a sentence that also passes the
`bare in own` check on its own.)

What this actually means, read plainly: every one of these is the
business's OWN real street number, suite number, zip code, phone
digit, or clock time, printed in its own real context (an address chip,
a footer copyright line, a stat band). None is a fabricated claim
slipping through — the coincidence is structural (the flat set doesn't
know WHY a number is backed, only THAT some field somewhere produces
it), not a live instance of a false claim shipping today. The risk
named in `.reviews/NEXT-ROUND.md` — a wholly invented small number,
with no other uncorroborated wording in its sentence, riding on one of
these values — remains theoretical on this corpus; nothing above is
itself the failure mode, only the surface it could hide behind.

## Verdict

Both regressions reproduce exactly as given, are fixed by rule (a
credential exempts its own matched span, never the sentence; a floor
claim contradicts only when it sits above the corroborated count), and
are proven — not just asserted — by a superset test run over the
hand-built manifests, all 19 real fixtures' own rendered pages, and 450
generated credential-plus-claim combinations, plus the two standing
end-to-end reproductions. `test_render_snapshots.py` and
`test_build_review.py` pass again without re-pinning anything. One
real-corpus regression the credential fix itself introduced (a
partially-matching device label) was found and closed before it
shipped. Before Part B: CLAIM_RE's `#1` alternative is fixed and
`top[- ]rated` added, each with two real planted cases; the 12 known
gaps in `test_seam_planted_corpus.py` are named individually and
enforced with `xfail(strict=True)`; and the `_corroborated_numbers()`
coincidence is fully enumerated (13 real fixtures, corrected from an
earlier, unverified "8"). The full suite is now genuinely green: **0
failed**, 1577 passed, 21 xfailed (12 of them the named baseline gaps),
lint and typecheck clean. Part B's gate conditions are met — the
widened superset test passes, class 8 is caught, and the
snapshot/review-bundle tests pass without re-pinning.
