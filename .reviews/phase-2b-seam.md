# Phase 2b — closing the hole the port opened, before Phase 3

Branch `slice-b-identity`, from `9b7b6c5` (the Phase 2 handoff). Five
commits: `f6d139f` (reproduce the three gaps, red first), `da8a756`
(Step 1, plantings), `92b611e` (Step 2, fix by rule), `f031306` (Step
3, honest corpus rerun), `7c0446a` (Step 4, the real design page).
`.reviews/FEEDBACK-FROM-SHREYAS.md` left untracked throughout, as
asked. No browser was used at any point in this round — every step
below is pure Python, reading source markup or the design export's own
JSON directly.

## §0 — the three reproductions, before anything changed

All three reproduced exactly as given, in `f6d139f`, before `Step 2`
touched any gate:

1. **The credential invariant.** The exact threadbare snippet given,
   against `threadbare.json` (`material.about is None`,
   `material.blocks == ()`, confirmed, not assumed): the old gate
   found 9 findings; the ported gate found 0.
2. **The invented number.** `<p>4.9 average rating from 90,000 Google
   reviews</p>` against real `material.reviews = 6203`: every gate
   returned `[]`.
3. **The design page.** Nothing in the tree referenced
   `tests/fixtures/seam/hvac-claude-design.html` — Phase 2's 40-finding
   classification existed only as prose in `.reviews/phase-2-seam.md`.

## §1 — Numbers

**Planted** (`tests/fixtures/seam/*-foreign.html` + threadbare, classes
1-7d, 4b, plus control pages):

| Business | Classes planted | Caught by fixed gate | Control false positives |
|---|---|---|---|
| hvac-foreign | 1-6, 4b, 7a-7d | all | 0 |
| restaurant-casual-foreign | 1-6, 4b, 7a-7d | all | 0 |
| threadbare-foreign | 1, 2, 7a-7d (6 plantings, no bag-of-words gap) | all | 0 |

(2 cases skip, not fail: class 5 needs a rendered DOM, which this
round's no-browser rule puts out of scope and Phase 2 already covers;
threadbare has no `<script>` at all to carry a script-injected
planting, matching the round's own given snippet.)

**Superset test**: yes, with no exceptions.
`test_the_ported_gate_is_a_superset_of_the_old_gate_on_every_planted_page`
computes the OLD gate and the FIXED gate on all 3 manifests and asserts
every old finding is a substring-match somewhere in the new findings.
Passes for all 3. This is the actual proof behind "not weakened" — not
an assertion, a test.

**Real fixtures**: all 19 at `old=0 new=0`, reproducibly
(`tools/seam_corpus_check.py`, pure Python, rerun fresh for this
handoff — not just recalled from `tools/seam_corpus_check_results.json`,
which came back byte-identical). This zero is earned: every fix that
got it there traced to a real, documented gap in the RULE (a
deterministic heading never recognised as chrome, a phone number's
digit groups never corroborated individually, a review's platform
attribution, a star-glyph run, a bare carousel-index number, a
credential label that doesn't match its own trigger regex) — never to
loosening what counts as a claim or an unbacked number. Checked after
every single fix, not just at the end: the planted corpus never
regressed while the real corpus was being cleaned up.

**Boilerplate list** (`_BOILERPLATE_WORDS` / `is_template_chrome`'s old
mechanism): deleted outright, not narrowed — see `app/site/seam_gates.py`
lines 51-77 for the full audit, one line per entry:
- 9 words were the actual masking risk (directly enabled gap 2 — each
  sits right next to the fabricated number in "N average rating from M
  [word] reviews"): `average, rating, stars, star, from, across,
  google, reviews, review`.
- ~25 more were deleted with them but were never themselves adjacent to
  a claim or a number in any traced incident — removed because the
  whole exempt-by-word-list mechanism is gone, not because any one was
  independently risky.
- A SEPARATE, narrower list (`_FOOTER_GLUE_WORDS`) reintroduces most of
  the review/rating words plus day-names/am/pm/menu-footer words for
  `_is_all_facts_and_footer_glue()` — safe now, unlike Phase 2's
  version, because `unbacked_numbers()` independently and
  unconditionally checks every number in the same text regardless of
  whether this check passes.

**Design page**: 42 findings, pinned
(`tests/sitegen/test_seam_design_page.py`), classified in
`.reviews/phase-2-design-page-findings.md` — **25 verbatim, 16 true
reworded, 1 changed specific, 0 invented.** The one changed-specific
call ("100,000 homes ... across the Plano area") is confirmed
independently: the source number carries no location, and the brief's
own address fact is itself unresolved between Plano and Irving. The
Jeff Willie testimonial join is traced precisely, and the round's own
guess at its location does not hold up — see that document's own
section on it; short version: the SAME symptom shows up twice in this
fixture, and only one of the two (`published.blocks`, via
`app/workbench/extract.py`'s `read_blocks()`) is actually caused by
code in this tree. `testimonials[0]` (what the design page actually
quotes) goes through `app/workbench/brief.py` →
`app/adapters/gplaces.py`, which I read end to end and found builds
one output dict per raw API review with no join logic anywhere.

**Would reject today**: none of the 19. Wiring `seam_gates.gate()` into
`app/site/pipeline.py:510`'s `_gate()` (currently
`unsupported(html, material) + unexplained_sentences(html, material)`,
reading raw HTML) would mean calling
`seam_gates.gate(visible_text_runs(html), material)` instead — adding
`unbacked_numbers()` and `contradicted_review_counts()` on top of what
already runs, and changing the chrome/prose exemption rules. Per the
corpus check above, every one of the 19 real fixtures produces zero
findings under the fixed gate today, so wiring it in would reject none
of them. **Not wired in** — this is a decision for the user, not this
round.

**Tests**: 55 passed, 3 skipped across the round's own five files
(`test_seam_gates.py`, `test_seam_reopened_gaps.py`,
`test_seam_design_page.py`, `test_no_unverified_credential_ships.py`,
`test_no_contradicted_fact_ships.py`). Full `make check` results below.

## §2 — `make check`

`uptime` before starting: `load averages: 1.50 1.80 2.03` — well under
6, safe to run. `lint` (ruff) and `typecheck` (mypy) both clean. Full
`pytest -q` with the browser-gated tests deselected (same list as
Round 8's precedent: the three real-Chrome-launching tests in
`test_chrome_cdp.py`, the two real-Chrome-launching tests in
`test_site_fetch.py` — confirmed by reading the file: only these two
are `@pytest.mark.skipif(chrome() is None, ...)`, the other four in
that file are monkeypatched and left running normally — plus the DOM
script-render test, the collision-at-every-width test, and the
synthetic-INP-click test) finished in 76 seconds:

**1102 passed, 15 failed, 3 skipped, 8 deselected, 9 xfailed.**

All 15 failures are pre-existing and unrelated to this round's actual
gate changes (`app/site/seam_gates.py`, `app/site/contradiction.py`,
`app/site/provenance.py`) — none of the five Phase 2b commits touch
`app/site/render.py`, `app/site/styles.py`, or any real fixture brief:

- **13 in `tests/sitegen/test_seam_planted_corpus.py`.** This is
  Phase 2's own baseline file, its docstring says outright: "This file
  is the BASELINE, run against today's gates exactly as
  `pipeline._gate()` combines them... It is expected to be red: that
  is the point of this step." It measures the OLD, currently-wired
  gate (`unsupported()` + `unexplained_sentences()`, reading raw HTML)
  against every planting in the manifests — and was ALREADY red for
  the original classes 2, 3, 5, 6 before this round touched anything
  (that redness is Phase 2's own documented baseline). Phase 2b's Step
  1 added new plantings (4b, 7a-7d) to the same manifests, specifically
  designed to slip past the same old, currently-wired gate — the whole
  point of the round. So they show up red here too, for the identical,
  already-documented reason, not a new one. This file was never meant
  to go green; nothing in Phase 2b changes that.
- **1 in `tests/test_render_snapshots.py`, 1 in
  `tests/tools/test_build_review.py`.** Both name `roofer-rich`, and
  only `roofer-rich` — a fixture no Phase 2b commit touches, and not
  one of the 7 fixtures the prior "Re-freeze 7 fixtures" commit
  (`6b2209f`, same day, before this round started) re-froze either.
  Confirmed the render is deterministic (hashed 3 times in a row,
  identical each time) — this is a stale pinned snapshot from before
  this round, not new drift this round introduced. Left alone: out of
  this round's scope (`app/site/seam_gates.py`/`contradiction.py`/
  `provenance.py` only), and not something the round's instruction
  asked me to re-freeze.

None of the round's own seam work is implicated in any of the 15.

## Verdict

The port's three gaps are closed, closed by rule rather than by list,
and proven not weakened by an actual superset test — not just asserted
— against every planted page. The real 19-fixture corpus is clean, and
that zero is earned and documented, not tuned. The real Claude Design
page is reproducible without a browser and fully classified: zero
fabrications, one changed-specific claim, everything else true or
verbatim. Wiring the fixed gate into the pipeline today would reject
none of the 19 real fixtures — that decision is still yours to make.
