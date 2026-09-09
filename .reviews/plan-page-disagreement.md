# A real "plan-versus-page disagreement" bug, found building the review bundle

`BRIEF.md`'s own history already lists "plan-versus-page disagreement" as a
bug closed once. This is that bug's shape again, in a different function,
found by accident while verifying Phase 3's standalone pages rendered
correctly — the workbench's own "Site preview" iframe didn't show what I
expected from the plan panel next to it, and pulling that thread found a real
defect rather than a rendering-tool quirk.

## The bug

`app/site/render.py` had two separate implementations of the same section-
ordering rule:

- `app/site/plan.py`'s `apply_order()` — used by `plan_for()`, which builds
  the plan the operator reviews. Its input list explicitly excludes `"hero"`.
- `render.py`'s own `_order()` — used by `build_from_spec()`, which renders
  the actual page. Its input list included `"hero"`.

Both apply the same rule: an instruction naming a section to emphasise moves
it to page position 2 if it currently sits later than that (`index > 2`).
With `"hero"` sitting at index 0 in `_order()`'s list and absent from
`apply_order()`'s, every other section's index was off by one between the
two — so the `>2` check fired at a different point, and a page whose plan
said "reviews before services" could render "services before reviews"
instead, or vice versa, whenever an instruction named two sections.

Checked against the real 19-fixture corpus: **seventeen of nineteen**
fixtures' rendered section order disagreed with their own plan. This is not
a rare edge case — the identity call sets `emphasis` on almost every fixture,
and the corpus has enough sections that the off-by-one crosses the boundary
constantly.

## The fix

Deleted `_order()`'s own copy of the reordering rule; it now filters out
`"hero"` the same way `plan_for` does and calls `apply_order()` directly.
One implementation, not two. New standing test:
`test_the_rendered_page_matches_the_plan_the_operator_reviewed`
(`tests/sitegen/test_render.py`) — confirmed it fails against the pre-fix
code (reverted and re-ran it) and passes against the fix.

## What this touched

**The fingerprint and every pinned number are unaffected.** `fp.of()`'s
`section_order`/`compositions` axes are computed from `plan_for()`'s plan,
which was never buggy — only the actually-rendered HTML disagreed with it.
RULER, RULE, LABELS, SAME_TRADE_MEAN and AGREEMENT (the tuple) are all
unchanged from Phase 1/2's pinned values.

**The whole-page screenshots were stale.** Sixteen of nineteen fixtures'
rendered order changed once the fix landed, and `artifacts/contact-sheet/
pages.html` is what every blind verdict in `tests/fixtures/pairs.json` was
judged from. All sixteen live verdicts from Phase 1 were retired and
re-judged against the corrected rendering rather than carried forward
unread. **Every verdict's actual conclusion held** — all sixteen were, and
remain, DIFFERENT — because the differences driving each of them
(`first_screen`, `architecture`, section presence/absence, the signature
device) are untouched by section-order reshuffling. Only the `why` prose
changed, in the cases where it had described a specific sequence that no
longer holds. `HELD_OUT` moved (it hashes the reasoning, not just the
verdict); `LABELS` did not (it hashes verdicts only, and no verdict flipped).

One case worth naming: `dentist`/`law` — the original `why` claimed "both
give a full screen to quotation," which was wrong independent of this bug
(`law`'s signature is `stamp`, not `quote`; only `dentist` carries a
quotation block). Caught while re-verifying against the corrected rendering
and fixed in the same pass.

**The contact sheet and review bundle were rebuilt** after the fix
(`tools/contact_sheet.py --force`, `tools/build_review.py`) so nothing
downstream is describing the pre-fix page. Eight of nineteen committed
fold thumbnails changed (`.reviews/sheet/*-thumb.png`) — the reordering
reached above the fold for those.

## Why this matters beyond the numbers

The numbers were never wrong. What was wrong is the thing `plan.py`'s own
docstring calls the point of having a plan at all: *"You can correct a plan
before it becomes a page."* For most of this corpus, correcting the plan
would not have corrected the page — the operator's own workbench was showing
one section order in "The plan" panel and rendering a different one in "Site
preview," silently, for as long as this bug existed. That is a trust failure
in the one piece of UI this whole project is building toward, and it is
fixed now rather than shipped past.
