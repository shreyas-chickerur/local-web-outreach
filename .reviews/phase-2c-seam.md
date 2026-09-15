# Phase 2c — two regressions in Phase 2b, closed and proven

Branch `slice-b-identity`, from `c39e1cb` (the Phase 2b handoff). Four
commits: `829ab37` (Step 0, both reproductions, red first), `3400dcb`
(Step 1, both fixes by rule), `753861c` (Step 2, class 8 planted, the
superset test widened), `99c3170` (Step 3, a real-corpus regression the
Step 1 fix itself introduced, found and closed before it shipped).
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
    reaches the real Claude Design page too — pin moved 42 → 48, all 6
    new findings classified (all real; 0 invented).

  `.reviews/phase-2b-seam.md`  corrected in place, dated, original
    sentence kept — the "pre-existing" attribution for the
    `roofer-rich` snapshot failures was wrong.

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
  invariant on 8 of 19 fixtures, because `visible_text_runs()` merges
  adjacent unpunctuated sibling text into one run (`roofer-rich`'s own
  page reads "10021 Cayuga Dr Fri 7:30am to 5pm" as a single sentence),
  so the sentence-level check cannot see hours or address in isolation
  the way the flat per-field set can. A correct fix needs a number tied
  to which field backs it, not a flat set — bigger than this bullet's
  "small" framing. Forecloses: the five named coincidences (4, 5, 8, 20,
  24 validating on `hvac` for unrelated reasons) remain live; a
  wholly-fabricated small number riding with no other uncorroborated
  wording in the same sentence would still pass `unbacked_numbers()`
  today. Flagging for the next slice, not deciding it silently.

  **CLAIM_RE's `#1` alternative reported, not fixed** — `\b#1\b`
  requires a word character glued directly onto `#` with no space
  (confirmed: `CLAIM_RE.search("voted #1")` is `None`; `CLAIM_RE.search
  ("Ranked#1")` matches). Dead code against any natural sentence.
  `app/core/claims.py` is not one of this round's files, and the
  expression is shared with the vision pass — widening it needs its own
  corpus-wide check this round's budget does not cover. Worked around
  in the generated sweep with the unnatural "Ranked#1"; every real
  planting using "#1" in this corpus (class 7d, both manifests) is
  actually caught via `unexplained_prose`'s whole-sentence traceability
  check, not via this CLAIM_RE alternative, so no real gap is open —
  the alternative itself is simply inert.

## §3 — Numbers

**Planted classes caught, including class 8:**

| Business | Classes planted | Caught by fixed gate |
|---|---|---|
| hvac-foreign | 1-6, 4b, 7a-7d, **8** (12 total) | all 12 |
| restaurant-casual-foreign | 1-6, 7a-7d (10 total) | all 10 |
| threadbare-foreign | 1, 2, 7a-7d (6 total, no bag-of-words gap, no script) | all 6 |

(Class 5 needs a real render; caught via the same simulated post-script
DOM Phase 2b used, for hvac and restaurant-casual — threadbare has no
`<script>` to carry one.)

**Superset test counts:**

| Sweep | Count | Result |
|---|---|---|
| Planted (3 manifests, every planting) | 28 sentences | 0 missing |
| Real fixture pages (all 19, every visible sentence) | 1,930 sentences | 0 missing |
| Generated (every corroborated `contractorfacts` credential of every real fixture × every CLAIM_RE alternative, one sentence each) | 18 credentials × 22 claim shapes = 396 combinations | 0 laundered |

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

`uptime` before running: `3.98 2.98 2.67` — under 6. Full run: **13
failed, 1532 passed, 3 skipped, 8 deselected, 9 xfailed** in 150s.
`ruff check app tests` and `mypy app` both clean.

All 13 failures are in `tests/sitegen/test_seam_planted_corpus.py` — the
file's own docstring says outright it measures the OLD, currently-wired
gate and is "expected to be red." Status at `9b7b6c5`, checked by
actually running that file there (not assumed):

| Failing test | Status at `9b7b6c5` |
|---|---|
| `hvac-class2`, `hvac-class3`, `hvac-class5`, `hvac-class6` | **fails** (same 4 classes, pre-existing) |
| `restaurant-casual-class2`, `-class3`, `-class5`, `-class6` | **fails** (same 4 classes, pre-existing) |
| `hvac-class4b`, `hvac-class7b`, `hvac-class7d` | **did not exist** — these plantings were added by Phase 2b's own Step 1, after `9b7b6c5` |
| `restaurant-casual-class7a`, `restaurant-casual-class7b` | **did not exist** — same reason |

The 8 that existed at `9b7b6c5` fail there too, unchanged — genuinely
pre-existing. The 5 that didn't exist yet cannot be "pre-existing at
`9b7b6c5`" by definition; they are, however, byte-identical failures to
what `c39e1cb` (Phase 2b's own handoff, before this round touched
anything) already had — confirmed by running this same file in a
worktree at `c39e1cb` and diffing the failure list, which matched
exactly. Phase 2c added zero new failures to this file. This round's
own new plantings (class 8, both manifests where it applies) pass.

None of the 15 failures phase-2b-seam.md counted are gone except the 2
this round fixed (`test_render_snapshots.py`,
`test_tools/test_build_review.py`) — 15 − 2 = 13, matching exactly.

## §4 — Assumptions I could not verify

None beyond what §2 already states as open (the numbers fix, the
CLAIM_RE dead alternative). Both reproductions and both fixes were
verified directly against running code and the real fixture corpus,
not taken on faith.

## §5 — Questions I want answered before the next slice

- Should a fourth planted-manifest business (one that genuinely
  corroborates a `contractorfacts` credential AND is not `hvac`) be
  added so class 8 has two independent proofs the way classes 1-7 do?
- Is the `_corroborated_numbers()` gap (§2) worth a real fix now —
  tying a corroborated number to which field backs it, rather than a
  flat set — or is the current flat-set behavior an acceptable,
  documented trade-off given how rarely a wholly-fabricated small
  number rides with no other uncorroborated wording in the same
  sentence?
- CLAIM_RE's `#1` alternative: worth a one-line fix (`(?<!\w)#1(?!\w)`
  or similar) now that it is confirmed dead, given it is shared with
  the vision pass and touches no file this round already changed?

## Verdict

Both regressions reproduce exactly as given, are fixed by rule (a
credential exempts its own matched span, never the sentence; a floor
claim contradicts only when it sits above the corroborated count), and
are proven — not just asserted — by a superset test now run over the
hand-built manifests, all 19 real fixtures' own rendered pages, and 396
generated credential-plus-claim combinations, plus the two standing
end-to-end reproductions. `test_render_snapshots.py` and
`test_build_review.py` pass again without re-pinning anything. One
real-corpus regression the credential fix itself introduced (a
partially-matching device label) was found and closed before it
shipped. The full suite's only 13 failures are `test_seam_planted_
corpus.py`'s own documented, unchanged baseline. Part B's gate
conditions are met — the widened superset test passes, class 8 is
caught, and the snapshot/review-bundle tests pass without re-pinning —
so Part B is unblocked, pending explicit go-ahead given its own budget
(6 design sessions, 6 screenshots, no retries) is real spend this
handoff should not authorize by itself.
