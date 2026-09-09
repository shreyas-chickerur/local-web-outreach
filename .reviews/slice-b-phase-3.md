# Phase 3 — the review bundle

What the user actually opens. `tools/build_review.py`, new.

## 3a — standalone pages

`.reviews/review/<slug>.html`, all 19 fixtures, built from a fresh
`:memory:` session per fixture (not the shared `artifacts/fixtures.db` —
that db's `build_state` cache holds whatever a stage last actually computed,
which for a fixture's `direction` stage can be the live redecide itself,
cached before the frozen decision was written back to the fixture file; see
the module docstring). `read_by == "frozen"` is asserted per fixture before
writing anything — the same proof `test_the_instrument_reproduces.py` takes,
here as a precondition rather than a test: this bundle is guaranteed to make
zero model calls.

Photographs are copied into `.reviews/review/photos/` and referenced by a
relative path, never inlined — the correction made mid-session to
`tools/contact_sheet.py` (see its own handoff) applied here from the start.
Unlike the contact sheet (which links `.cache/photos` in place, since it's
gitignored and regenerated on demand), this bundle **copies**: its pages are
meant to be committed and opened stand-alone, and a relative path into a
gitignored cache outside its own directory would be dead on another clone.
`.reviews/review/photos/` is itself gitignored (`.gitignore`) for the same
reason `artifacts/` already is — a few hundred photographs at full width are
not history, and the pages that reference them (all ~70KB) stay small and
committed.

Total local size: 120MB, almost entirely the photographs (142 unique files,
~840KB average at the full `MAX_WIDTH=2400` fetch). Not the "few MB" first
hoped for — using the full-resolution cache rather than resizing down, no
image library being available to resize with. The two things that actually
mattered are both solved regardless of exact size: the HTML pages stay
small and readable (no risk of a truncated read), and nothing bulky is
committed to git.

## 3b — the index, in plain English

`.reviews/review/index.html`: one card per business — thumbnail (linked to
the already-committed `.reviews/sheet/<slug>-thumb.png`, not duplicated),
trade, rating, the model's own rationale verbatim, the signature device's
own justification when the device isn't `none`, and a plain-English list of
what's on the page (`_plain_outline()` — "the numbers", "trust signals",
"what they offer", never an axis name). No axis vocabulary appears anywhere
on this page.

## 3c — the workbench, confirmed against the fixture corpus

`WORKBENCH_DB=artifacts/fixtures.db .venv/bin/python -m app.web.server`,
opened in a real browser and clicked through. Confirmed working: the leads
list shows all 19 fixtures; opening a workspace shows the model's rationale,
the signature justification, the plan outline, and the photo-labelling UI;
the generated site itself serves correctly (`curl` confirmed `200` with real
HTML on `/site/<lead>/<version>`).

**One thing that looked broken and wasn't:** the embedded "Site preview"
iframe rendered blank in the automated browser tool used to check this.
`read_network_requests` showed `net::ERR_BLOCKED_BY_CLIENT` on the iframe's
own request — that tool's sandboxed environment blocking it, not the server;
confirmed by `curl` returning the same URL with a `200` and real HTML
outside that tool.

**Not exercised: sending a live iteration instruction through the UI.** That
calls the model, and I chose not to spend a real API call purely to verify
what `tests/sitegen/test_iterate.py` already covers with a mocked one. Stated
here rather than silently skipped.

**A real bug found this way, not by testing:** the plan panel and the
rendered preview disagreed on section order for most of the corpus,
BEFORE this session's fix — see `.reviews/plan-page-disagreement.md`,
committed separately. Also found in passing: a version's stored HTML is a
build-time snapshot (by design — versions are immutable), so a lead whose
version was built earlier in this session, before that fix, still serves
its stale HTML until rebuilt. Not a defect; the "frozen replay" contract
working as intended, applied to versions rather than to fixture directions.

## 3d — READ-ME-FIRST.md

Written directly, not generated. Names the weakest point (Slice C barely
started — three of nineteen fixtures carry any contractor fact, four of
nine facts exist at all), what's deliberately not built (the other five
facts, compositions beyond two sections, model-chosen headings), and which
numbers not to trust and why (same-trade mean has no prior reading to
compare against; agreement is 0/0 meaning "checked and not found," not
"untested"; ratings/review counts drift from the moment they were
researched).

## What this leaves

Nothing further needed for the user to open the sites and the workbench and
form an opinion this session set out to enable. The honest gaps are named in
`READ-ME-FIRST.md` rather than hidden by a bundle that only shows the good
angles.
