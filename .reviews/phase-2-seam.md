# Phase 2 — prove the seam: do the gates catch fabrications in foreign markup?

One question: given a page whose markup our renderer did not write, does
every gate still catch a fabrication? Answered by building a planted-
fabrication corpus, a shared rendered-DOM reader, a port of the three
gates onto it, and one real designed page for `hvac` — in that
order, one commit per step (`0ec0920`, `e52a2b5`, `dc7b273`, `80b5b21`,
`81061b7`, `2977b1a`).

## Changed

  app/site/visible.py            NEW — visible_text_runs()/needs_render()/
                                  render(): the one rendered-DOM reader
                                  every gate now shares
  app/site/seam_gates.py         NEW — unsupported_sentences()/
                                  unexplained_prose()/contradicted_review_
                                  counts()/gate(): the three gates ported
                                  onto visible.py, sentence-level
  app/site/provenance.py         _own_sentences -> own_words, _SENTENCE_RE
                                  -> SENTENCE_RE (public, no behaviour
                                  change) — reused by seam_gates.py rather
                                  than copied
  app/site/contradiction.py      REVIEW_COUNT_RE, contradicts() made
                                  public — imported by seam_gates.py and
                                  by tests/test_no_contradicted_fact_
                                  ships.py, which used to carry its own
                                  second copy of both
  tests/fixtures/seam/           NEW — 2 planted-fabrication pages + 2
                                  control pages + manifests (Step 1); 1
                                  real designed page (Step 4)
  tests/sitegen/test_seam_*.py   NEW — the baseline reproduction, the
                                  Step 1 red baseline, the ported-gate
                                  tests, visible.py's own tests
  tools/seam_corpus_check.py     NEW — one real browser session:
                                  verifies render(), class 5 for real,
                                  and re-runs the ported gate against all
                                  19 real fixtures

## Decisions

  Read the RENDERED DOM, never source markup — the roadmap's locked
  decision, confirmed necessary by the round's own reproduction: a
  script-injected fabrication and an entire bundled design-tool canvas
  are both invisible to source-markup regex, present the moment a real
  browser runs the page. — forecloses any gate design that reads
  `page: str` from `build_from_spec()`'s return value directly.

  Chrome-detection by TAG AND SHAPE (nav/button/a/label/form; a heading
  of ≤3 words; ≤4 words with no terminal punctuation; a run built
  entirely of corroborated field values + a fixed connective-word list)
  — not by CSS class, which only render.py's own output ever carries.
  — forecloses any future gate relying on `class="prose"`-style markers
  to find real content; the class-based version already proved blind on
  foreign markup.

  unsupported_sentences() now checks the SENTENCE a claim lives in, not
  just whether the claim PHRASE appears anywhere in the material — closes
  the bag-of-words gap the round's own reproduction named (a customer
  review's incidental "certified technicians" no longer launders an
  unrelated business assertion). — forecloses any future "does this word
  appear somewhere" shortcut in a content gate.

  own_words() widened, locally to seam_gates.py, with every corroborated
  structured field (address, phone, hours, rating, reviews, socials,
  quote authors, menu price) and every scraped block HEADING/KICKER/
  ENTRY, not just body text — found necessary re-running the port
  against the real 19-fixture corpus, which reads stat tiles, footers
  and section headings the old five-class gate never touched at all. —
  provenance.py's own own_words() (used by the OLD gate) is untouched;
  the widening lives only where the new surface is actually read.

  The real designed page was NOT told about the gates, and was
  given the WHOLE brief rather than a summary — the round's own
  instruction, held to exactly, so the 40-finding result reflects a real
  design session's ordinary output, not one primed to avoid detection or
  starved of material.

  No conversion pipeline for the bundled canvas export — one regex to
  locate the `srcdoc` attribute the editor's own JS set at runtime,
  `html.unescape()`, then the SAME `visible_text_runs()` every other page
  in this round used. — forecloses building any general design-tool-
  canvas-to-page extractor as part of this round; if Phase 3 needs one,
  it is new, deliberate work, not something this round backed into.

## Numbers

```
planted fabrications   before the port: 4 of 12 caught (both businesses
                        agree exactly) — class 1 (invented year) and
                        class 4 (review-count contradiction, but only by
                        CLAIM_RE's five-star SHAPE riding along, not a
                        real contradiction check — see test_seam_
                        baseline.py's third test). Classes 2 (bag-of-
                        words credential), 3 (paraphrase, changed
                        specific), 5 (script-injected), 6 (wholly
                        invented, no claim words) all missed, both
                        businesses.
                        after the port: 12 of 12 caught, including class
                        5 confirmed with an ACTUAL script execution
                        (tools/seam_corpus_check.py), not the
                        hand-simulated stand-in the pure-Python suite
                        uses for speed.

control page            before: 0 false positives (both businesses).
                        after: 0 false positives (both businesses) — the
                        port is not more aggressive than the original on
                        genuine verbatim/prefix-cut content.

old corpus              19 fixtures. First real-DOM run: every fixture
                        that shipped with 0 findings came back with
                        3-43 NEW findings each — traced, one by one, to
                        gaps in the PORT (quote-wrapper punctuation the
                        old regex never included; own_words() missing
                        corroborated structured fields and block
                        headings/entries the old five-class gate never
                        read), never to a fixture needing a content
                        change. Final run: 19 of 19 fixtures at 0 new
                        findings. Zero of the ~230 total first-pass
                        findings were reclassified as genuine
                        fabrications the old gate had missed — all were
                        port false positives, all fixed in
                        app/site/seam_gates.py.

real design page        40 findings, all 40 hand-read and classified:
                          true fabrication:                    0
                          true statement, not verbatim          40
                            (every one traces to real material given
                            to the design session, reworded as fresh
                            marketing copy)
                          gate false positive:                  0
                        fabrications found by reading, not flagged by
                        any gate:                                0

tests                   66 in the seam suite (test_seam_baseline.py,
                        test_seam_planted_corpus.py, test_visible.py,
                        test_seam_gates.py): 56 passed, 8 deliberately
                        red (test_seam_planted_corpus.py's Step 1
                        baseline — measures TODAY's unported gates on
                        purpose, not meant to go green), 2 skipped
                        (class 5's real-render case, covered by a
                        passing simulated-DOM test in the same file AND
                        by tools/seam_corpus_check.py's real run).
                        Full suite: 1064 passed, 8 failed (the same
                        deliberate baseline), 2 skipped, 9 xfailed
                        (7 pre-existing weight-budget breaches + 2
                        fingerprint/contact-sheet retirements from
                        Round 8), 8 deselected — the real-Chrome-gated
                        tests (7 pre-existing + this round's new
                        render() test) were run individually instead,
                        all passing, rather than let a routine `make
                        check` launch a browser.
```

## Verdict

**The verification layer transfers, with two named gaps closed by this
round and one real limit disclosed, not softened.** Ported onto a
rendered-DOM reader with sentence-level matching, all three gates catch
every class of planted fabrication on foreign markup, including a
fabrication that exists only after a script runs — and the ported gate
is clean on the real 19-fixture corpus, so nothing was weakened to get
there. The one real limit: the gates enforce verbatim-or-prefix-cut
provenance, and a real design session writes fresh copy, not retyped
sentences — so on an honest, well-sourced design the gates currently
read as near-total noise (40 of 40 flagged, 0 fabricated) rather than
signal. That is not evidence the gates are broken; it is evidence they
were built for a pipeline (`copyselect.py`'s index-into-candidates
selection) that guaranteed verbatim provenance by construction, and a
generative design layer does not make that guarantee. Closing it is
Phase 3's problem, not proof the seam does not hold.

## Assumptions I could not verify

- That `srcdoc` unwrapping is a reliable extraction method for every
  design-tool canvas export, not just this one page — verified once,
  on one page, in this round's own resource budget (no second design
  session to cross-check against).
- That a real design session, asked with a different framing or a
  thinner brief, would stay as fully grounded as this one did. This
  round gave the whole brief and a detailed, structured prompt; a
  thinner prompt was not tested.
- That `_BOILERPLATE_WORDS` and `_is_all_facts_and_boilerplate` in
  `seam_gates.py`, tuned against this specific 19-fixture corpus's real
  stat tiles and footers, generalize to a business or a `render.py`
  section builder not yet in the corpus.

## Questions I want answered before the next slice

- Does the verbatim-or-prefix-cut standard itself change for
  design-session output, or does Phase 3 build a real
  provenance/selection mechanism for it (something like
  `copyselect.py`'s index-into-candidates guarantee, adapted to
  whatever the design tool's own output shape turns out to be)? The 40-of-
  40 result is a real number today; it should not still be 40-of-40 once
  Phase 3 exists.
- Should `unsupported_sentences`/`unexplained_prose`/
  `contradicted_review_counts` become the standing gate (replacing
  `render.unsupported()`/`provenance.unexplained_sentences()` in
  `pipeline._gate()`) now that they are verified clean on the whole
  corpus, or wait for Phase 3's own pipeline to land first?
- `_corroborated_facts()`'s coverage (address/phone/hours/rating/
  reviews/socials/quote-authors/menu price/block heading+kicker+entries)
  was built by reading what the real corpus actually renders — is there
  a MATERIAL field that legitimately reaches a page that this list still
  misses, that just did not happen to appear in these 19 fixtures?
