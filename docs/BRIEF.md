# Lead & Site Workbench — standing brief (version 2)

Replaces the version-one brief and its five appendix amendments. Those had
begun to contradict each other; everything still in force is folded in here and
the rest is gone. Read this file and the branch, not the conversation that
produced them.

## 1. Where the work stands

*Kept current as part of every handoff commit. It is the entry point for anyone
arriving cold, and a status section that goes stale turns a two-minute
orientation into a directory crawl.*

**Done — Slice A.** Hero selection fixed and proven; vision labelling with no
human step; alt text everywhere; `app/core/claims.py`; operator-wins-by-
construction on photo labels; `rebuild_opening`; a derived floor so a condemned
photograph leads nothing.

**Done — Slice F, part one.** Eleven self-sufficient fixtures (their own
photographs and their vision labels folded in, so a clean clone measures the
same system); the quality census with its two assertions; the fingerprint,
computed from decisions and weighted by visibility × decidedness; the contact
sheet, a fold-cropped second sheet, and a committable half-scale copy; the
rank-based agreement metric; ruler *and* label versioning, with the census
refusing to compare across either; the `messages` table and its prose boundary,
enforced by an AST test; the build in stages, each answer persisted.

**Done — Slice B, axis one.** The first-screen contract: five positions, what
each business can support, and a standing test that every axis changes the page
and no axis is a function of another.

**Done — Slice B, the diversity budget.** The gate in `app/site/identity.py` —
ask again naming what is taken, perturb deterministically, record an
unresolvable collision. Its rule now matches §2.5: four axes, one structural,
**and one weighted highly**. It ran on `_stage_direction` only; `rebuild_opening`
went around it and recorded the ungated answer as precedent, which an AST test
now forbids for every caller.

**Bugs closed along the way.** The duplicate hero; plan-versus-page
disagreement; the preview port mismatch; a business name read as a website, and
the trade-word top-level domains that broke that same fix; the media type
hardcoded to JPEG, which lost every PNG and WebP a business publishes; a
photograph vision could not fetch blocking a build forever; a rejected page
remembered as a finished stage; `layout_bias`, a phantom axis that was a pure
function of `mood`; `compositions` encoding `section_order` inside itself;
labels frozen under one lead id silently matching nothing under another; the
split hero's type column centred rather than pinned, so it ran under the
photograph on the one page that opened that way; a `GATE_ENABLED = False` that
gated one line of a report and went on printing "the gate is off" after it was
turned on.

**The measurement apparatus was measuring the wrong pictures.** Two faults,
both found by looking rather than by a test, both now tested. The committed
contact sheet was captured before the fixtures beside it were re-frozen, so
five of eleven pages in it no longer existed. And its committed row was shot in
a 720-pixel window rather than shrunk from the 1440-pixel one — below the
breakpoint where the split hero stacks and the columns collapse — so **every
blind verdict this project has ever taken was read off a narrow rendering.**
The labels were re-judged against what ships. The agreement figure fell from
"40 of 40" to 19 of 33 with no code regression: the old number was scored
against the wrong pictures.

**The instrument's current reading.**

    agreement   0 of 0 — no "same" pair is left to rank
                ruler d2f37ed7, rule 95f4d93e, labels edc76612,
                held-out e3b0c442
    census      same-trade 55% distance = 45% identical, 30 scored pairs
                closest pair barbecue / restaurant-casual at 28%, DIFFERENT
    unreachable 0
    gate        0 of 30 same-trade pairs collide (down from 6)
    forbidden defaults  2 fixtures match (§2.4)
    tests       775
    fixtures    19 (11 original + 8 added widening the corpus)
    verdicts    10 live, all judged whole-page against the current rendering

**Done — the ground truth moved off the fold, axis three (page architecture),
the signature device (§2.3), the forbidden defaults (§2.4), and the keyless
path varying by business (§2.6).** Unchanged from the prior reading of this
section; see the handoffs in `.reviews/`: `slice-b-whole-page.md`,
`slice-b-axis-3.md`, and `slice-b-signature-device.md` (which also covers
the forbidden defaults and the keyless path).

**Done — the corpus widened from 11 to 19 real fixtures.** The instrument had
run out of businesses to disagree about (zero of twenty whole-page verdicts
judged "same"). Eight real businesses added via `tools/make_fixtures.py`,
weighted toward the trades already crowded — sameness is a same-trade
question. Two real bugs surfaced and fixed along the way: `freeze_vision`
silently froze a `design_direction` from a page the claims gate had rejected
(now raises); `identity.Decision.unresolved` was returned by the pipeline and
read by nothing (now captured and printed). Five same-trade pairs came back
"same," the strongest a trade trio rendering one page in three colours — see
`.reviews/slice-b-phase-1-widen.md`.

**Done — §2.2, palette from the business's own photographs.** Reads the
vision pass's own `dominant_colours` (already validated, already paid for)
rather than re-sampling pixels, mapped onto the existing closed `ACCENT_NAMES`
enum by hue distance — no new runtime dependency, no bypass of the existing
contrast repair. Offered as a candidate in the identity prompt, never a
constraint. The whole corpus was re-decided under it (a real API-credit
exhaustion hit mid-attempt and was recovered — see the handoff). Same-trade
mean improved 49% identical to 45%, and every one of the five same-trade
"same" pairs from the widening — including the trade trio — broke apart, none
of it credited to palette in isolation since the whole identity call was
re-asked. See `.reviews/slice-b-palette.md`.

**THE INSTRUMENT IS EXHAUSTED AGAIN, MORE STRONGLY.** Zero of the ten
carefully-checked whole-page verdicts is "same" — §2's requirement met, and
agreement is 0 of 0 for the same reason as before the corpus was widened. No
further axis can be validated on this corpus without either growing it again
or changing what "validate" means (whole-page judging is itself a choice with
a cost, not a solved problem — see the open question this leaves).

**Done — Slice B's close-out (this project's own Phase 1).** The gate bug:
`restaurant-bare`/`salon-rich` collided on exactly three axes (mood, accent,
hero_subject — no structural axis, no required-high axis), unnoticed because
the diversity gate compared only against the last ten fixtures generated and
the two missed each other's window. Fixed by widening `WINDOW` 10 → 60 in
`app/store/fingerprints.py` (`recent()` now takes `limit: int | None`) — three
times the current corpus rather than unbounded. Unbounded was tried first and
reverted: `test_the_gate_is_satisfiable` fails immediately, because an
unbounded window guarantees eventual permanent gate failure by pigeonhole once
total-sites-ever-built exceeds the required-high cardinality, so bounded-but-
wide is the real fix, not a compromise on the way to one. A standing test,
`test_no_collision_survives_anywhere_in_the_corpus`, now checks every pair in
the whole corpus rather than same-trade only.

Typeface landed as axis twelve — ~20 named `TypefacePair`s in
`app/site/theme.py`, chosen by the identity call from a closed set by name,
never as independent face picks. Added to REQUIRED_HIGH, justified by the same
evidence every other member of that set was: fold-visible axes are what a
blind verdict actually rests on.

The signature device's justification (§2.3) now reaches the workspace: one
sentence, persisted with the rest of the plan, replayed rather than re-asked
on rebuild, never reaching the rendered page (`app/site/opening.py`,
`app/web/server.py`, `app/web/index.html`).

One `--redecide` covered all three changes. Sixteen pairs judged blind against
the rendered markup afterward — cross-trade this time, not just same-trade,
and five chosen by distance to repopulate the held-out third from empty.
**All sixteen came back DIFFERENT**, including the closest same-trade pair
this corpus has ever produced (`law`/`law-rich`, 26% distance, sharing eight
of its eleven axes) and one pair briefly misjudged "same" against a shrunk
thumbnail and corrected once the actual rendered markup was read
(`bare-trade`/`dentist` — the same shape of near-miss as `dentist`/
`dentist-rich` the round before, caught the same way: by reading the markup,
not by trusting a glance at a small picture). See `.reviews/slice-b-phase-1.md`.

**The instrument's current reading.**

    agreement   0 of 0 — no "same" pair is left to rank, sixteen checked
                ruler a762bcc9, rule 254e171b, labels 1f0df47d,
                held-out de28526d
    census      same-trade 56% distance = 44% identical, 30 scored pairs
                closest pair law / law-rich at 26%, DIFFERENT
    unreachable 0
    gate        0 of 171 pairs collide, whole corpus (was 0 of 30 same-trade)
    forbidden defaults  1 fixture matches (§2.4, down from 2)
    tests       783
    fixtures    19
    verdicts    16 live, all judged whole-page against the current rendering,
                five held out

**Slice C started, not finished (superseded below)** — see §5 and
`.reviews/slice-b-phase-2.md`: trade profiles, four of nine contractor
facts as a corroborated section, two compositions.

**Done — a real plan-versus-page bug, found and fixed.** `render.py` carried
two separate implementations of the same section-reordering rule — one used
by the plan the operator sees first, one by the actual rendered page — that
disagreed on 17 of 19 fixtures because one counted the hero into its index
and the other didn't. Fixed by deleting the duplicate. See
`.reviews/plan-page-disagreement.md`. Every pinned number is unaffected
(the fingerprint reads the plan, which was never buggy); the sixteen
Phase 1 verdicts were re-judged against the corrected rendering and every
conclusion held.

**Done — the review bundle.** `tools/build_review.py`: all 19 fixtures
rendered standalone with copied (never inlined) photographs,
`.reviews/review/index.html` naming every business in plain English
(rationale, signature justification, what's on the page — no axis names),
`.reviews/review/READ-ME-FIRST.md` naming the weakest point and which
numbers not to trust. The workbench confirmed running against the fixture
corpus. See `.reviews/slice-b-phase-3.md`.

**Done — an unverified licensure claim, found and fixed (BRIEF §4).**
`signature.py`'s `stamp` device printed "Licensed & insured" / "Registered
practice" / "Admitted to the bar" from `trade_kind` alone on six of
nineteen fixtures — `threadbare` (no about text, no content blocks, one
photograph) asserted a licence anyway. `app.core.claims.CLAIM_RE` had no
pattern for credential language, so the content gate could not have caught
it either. Both fixed: the pattern widened (verified against the whole
corpus — exactly those six fixtures flagged, nothing else); `stamp` now
requires `contractorfacts.STAMP_FACT` corroboration before `available()`
offers it, dropped rather than rendered with a substitute when absent.
Standing test: `tests/test_no_unverified_credential_ships.py`. Re-decided
the corpus (signature is axis eleven); one attempt produced a genuine
unresolved collision, honestly recorded by the gate itself
(`_gate_unresolved`) rather than hidden, cleared by a retry. Eleven pairs
re-judged, all DIFFERENT; held-out third now empty (retired, not
repopulated this round). **Residual, disclosed risk:** the corroboration
is strict exact-phrase matching, so `stamp` currently renders on nobody in
this corpus — proven to remove a false claim, not yet proven to carry a
true one. See `.reviews/slice-c-credential-claims.md`.

**Done — a cost-minimising first pass over the rest of Slice C, plus the
free items from §5 that never needed a redecide (`.reviews/first-pass.md`).**
The governing rule: all non-corpus-moving work lands first and free; every
corpus-moving change batches into exactly one redecide at the end; no
judging round, because agreement was already 0 of 0 and every prior
verdict was DIFFERENT, so judging again would spend money to reconfirm
what a redecide already implies.

Free (no redecide): `tools/content_census.py` — every heading, paragraph,
list, image and fact per fixture, against whether it reached the page and
which rule dropped it if not (Slice D's first step). 73% of published
material reaches the page overall; the worst single loss is block:feature
at 36% (a 4-block cap drops two thirds of it by volume); `fact:hours` is
0% reached corpus-wide (superseded by `published.hours` everywhere it
would fire); `menu_media` is read by no section builder at all. The rest
of Slice F: `pipeline.spec_diff`/`unexplained_changes` (a structural diff
and a blast-radius guard per iteration, surfaced in the workspace as "What
moved" / "Moved, but not asked for"); render snapshot tests over all 19
fixtures, pinned in `tests/fixtures/render_snapshots.json`.

One redecide, batching every corpus-moving item: the last four of nine
contractor facts (service area, financing, a named manufacturer
certification, response time — same corroborated-or-absent discipline as
the first four); a genuine third `services` composition ("feature",
exactly three items, no card — `density.py` had named this composition
since it was written, but `_services` rendered it identically to the
dense grid until now, an axis lying about a visible difference); a second
`reviews` composition (two or three, stacked, no card, with a
`plan_for()` override so 2-count reviews also report "feature" rather
than letting the axis lie the other way); per-trade gallery/contact
headings. Zero collisions across all 171 pairs on the first attempt.
Eleven live verdicts retired (every fold moved), none re-judged — the
deliberate no-judging choice above.

Sampled, not swept: `tools/design_review.py`, a minimal Slice G — one
restaurant, one trade contractor, one professional practice, and the
threadbare fixture, three widths each, one model call per screenshot (12
calls, not the 57 a full sweep over all 19 fixtures would cost). Found
real defects a rule-based test cannot: layout collisions (`law`'s nav
sitting on the attorney's face, body text hidden behind a stats banner;
duplicated CTA buttons cropped at the mobile viewport edge on `hvac` and
`restaurant-rich`), and — new class — `hvac`'s own "about" text claiming
"over 20,000 5 star reviews" against a structured review count of 6,203
two sections away: two real numbers from the same business's own listing
that contradict each other, which nothing here cross-checks. Findings
only, nothing fixed this pass; see `.reviews/first-pass.md` for the full
list and the recommendation on whether a full sweep is worth it.

**Not this pass, disclosed rather than silently dropped:** a judging
round; Slice E (backdrops, motion, video); Slice H (the conversational
workspace); growing the corpus past 19 fixtures; the full (not sampled)
Slice G sweep; before-and-after, the ninth contractor fact (needs a
paired photo nothing in this corpus's photo data carries).

**The instrument's current reading.**

    agreement   0 of 0 — no "same" pair is left to rank, none judged this
                pass (deliberate — see above)
                ruler a762bcc9, rule 254e171b, labels e3b0c442,
                held-out e3b0c442
    census      same-trade 56.10% distance = 43.90% identical, 30 scored
                pairs (was 53.33%/46.67% before this redecide)
    unreachable 0
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults  2 fixtures match (§2.4) — barbecue-rich and
                restaurant-rich (was barbecue-rich and law; law dropped
                out and restaurant-rich picked up the same default when
                the corpus was redecided — a fact about the redecide, not
                something tuned for)
    tests       838
    fixtures    19
    verdicts    0 live (eleven retired this redecide, none re-judged)

**Done — Round 3: the review-count contradiction, the sampled review's
findings, and acting on the content census (BRIEF §4, §5 — full account
in `.reviews/slice-b-predictions.md`).**

Phase 1: `hvac` printed two verified facts that contradicted each
other — its own "about" text claimed 20,000 reviews against a
corroborated 6,203 two sections away. A corpus-wide scan found this was
the only instance. Fixed (`app/site/contradiction.py`): a sentence
stating a review count that contradicts the corroborated value is
dropped, never rewritten. New BRIEF §4 invariant; standing test
(`test_no_contradicted_fact_ships.py`), confirmed against the reverted
code and restored. Content-only, no redecide.

Phase 2: confirmed each of the sampled design review's three claimed
defects before changing anything, per instruction. Two were real
(`law`'s nav floating over the attorney's photo with no scrim; a
review-quote truncation cutting a word in half) and fixed. The third
("duplicated CTA cropped at the mobile edge") was a tooling artifact —
Chrome's headless `--screenshot` mode silently clamps any requested
width under 500px to exactly 500, so every "mobile" screenshot this
project has ever taken was captured 110px wider than labelled and
cropped on output. Fixed properly with a real sub-500px capture path
over the DevTools protocol (`tools/contact_sheet.py`); verifying it
found a real version of the same defect class on `law-rich` (a CSS grid
with a genuine 570px minimum, wider than any phone) and fixed that too.
Standing test (`test_no_element_collides_with_another.py`) checks every
fixture at three widths for a clipped control or painted-over text.
Re-ran the sampled review against the fixed tooling: the nav and
truncation findings are gone; the CTA finding's description changed from
"cropped" to a pure duplication observation. Content-only, no redecide.

Phase 3: acted on the content census, item by item. A business's own
photography, never once selected (`Material.images` reversed to
own-first; a small, tie-breaking `own_photo` hero-scoring term) —
verified content-only, no fingerprint value moved. `menu_media`, read by
no section builder since Slice A because `Material` did not even carry
the field — now linked directly. Verifying that surfaced a real,
separate bug: `law-rich` was rendering a law firm's settlement amounts
as "12 dishes on the menu" — the generic price-anchored menu-item
extraction doesn't know what business it is reading. A corpus scan found
four more instances (a dental promo, a plumbing coupon, a financing
banner, an insurance estimate); fixed by gating menu content on
`trade_kind == "food"`. The `block:feature` cap raised 4 → 6, checked
fixture by fixture first (some corpora are a real FAQ cut off
arbitrarily; a smaller amount is testimonial content a scraper mis-filed,
starting around item 7, not item 5) — content-only. A lone, uncontested
Google Business Profile claim now verifies `address`/`phone` on its own
(genuine conflicts between sources, the larger share of what was
dropped, are unchanged). Also fixed: the census tool's own grand-total
was double-counting a subset row into its headline percentage, and two
of its lines had gone stale the moment the fixes above shipped — the
same "two copies drift apart" defect this project keeps finding, this
time in its own measurement tool. Content census: **73% → 77%**
(corrected denominator both readings). One redecide (the menu fallback
and the newly-verified contact facts move `section_order`); re-pinned;
zero collisions across 171 pairs; no judging round.

Phase 4: the content census surfaced in the workspace (Slice D item 3).
Moved the measurement itself (`measure()`, `FixtureCensus`) from
`tools/content_census.py` into `app/site/census.py` — a real library
module the live server can depend on — so `workspace()` calls the
identical function a corpus-wide report does, not a second
implementation of it. New "What didn't reach the page" panel in the
workbench UI. Verified against the real, persistent `workbench.db`, not
just fixtures.

**Not this round, disclosed rather than silently dropped:** a judging
round (two passes running now with none — recommended, not attempted);
the full 19-fixture Slice G sweep and auto-repair of its findings
(Phase 5, explicitly conditional on "room" — not attempted, a
substantial undertaking in its own right); growing the corpus; the rest
of Slice D (letting the model select and order its own sentences, a
provenance check).

**Done — Round 4 (Slice D's last item, Slice E, and Slice G in full).**
Full account in `.reviews/slice-b-predictions.md` ("Round 4, Phase
1/2/3"); tails pasted in `.reviews/round-4.md`.

Phase 1: the rest of Slice D. `app/site/provenance.py` — every visible
prose sentence checked as verbatim/prefix-cut source, a corroborated
field, or (an empty, honestly-disclosed) generic-copy whitelist, kept
as a SEPARATE layer beside the existing claims-gate rather than folded
into it. `app/site/copyselect.py` — a real model call selects and
orders sentences by INDEX into the exact candidates offered, never by
retyping, which makes verbatim provenance true by construction. Frozen
per lead alongside vision and the design direction. 100% (687/687)
verbatim provenance across the real corpus; 85% (389/459) selection
ratio. Content-only, no axis moved; screenshots recaptured.

Phase 2: Slice E, instrumented before it was built, per the round's own
standing rule. `tools/perf_census.py` — real LCP/CLS/INP from a headless
browser's own `PerformanceObserver`, not estimated. `app/site/
backdrop.py` — the preference ladder (their own video, dormant; a
sequence of their own uncondemned stills; an abstract palette gradient;
licensed stock, never reached, never fabricated) behind `first_screen
== "type"`. `tools/motion_preview.py` — a separate, human-review-only
capture tool with motion left on, verified to show a real crossfade;
the deterministic pipeline needs no change, since the pre-existing
global `prefers-reduced-motion` rule already covers any new animation.
Motion does NOT become axis thirteen — its only live effect is a
function of `first_screen`, failing the independence test every other
axis met. Twelve of nineteen fixtures breach the 2MB weight budget, all
pre-existing photo-gallery weight predating this phase; pinned as
disclosed `xfail(strict=True)` regressions in `tests/
test_performance_budgets.py`, the other 66 checks a real, green gate.

Phase 3a: the full Slice G sweep, 19 fixtures × 3 widths, 57 model
calls, 295 findings. Two real, deterministic, corpus-wide bugs found
and fixed by class rather than patched per finding: `_offer_heading()`
was picking the food-trade heading off a bare `if m.menu_items`,
ignoring `trade_kind` — the same over-trusting menu-item extraction
Round 3 already gated everywhere else, missed at this one call site —
caught live as "What we cook and serve" on a roofer, two HVAC
contractors, and a law firm; fixed to read `trade_kind` directly,
fixing a fifth instance (`dentist`) the sample never flagged. The
signature device's `quote` block had its own, independent, never-fixed
copy of a text-truncation bug Round 3 already fixed once elsewhere
(`_truncate_quote`); fixed the same way, plus a decorative curly-quote
styling issue found verifying it (toned down so the marks read as
punctuation, not stray letters). A WebGL map-embed error four findings
raised was run to ground and confirmed a pure `--disable-gpu` capture-
tooling artifact (every screenshot tool in this project passes that
flag; no real visitor's browser does) — disclosed, not "fixed", the
same finding shape as Round 3's CDP width-clamping discovery.

Phase 3b: rebuilt the ground truth from 0 live verdicts (131 retired
across two rounds). Fifteen fresh pairs, judged blind from whole-page
renderings recaptured this session. Agreement, reported plainly: 22/26
(85%) full, 9/11 (82%) held-out only — past the "4-5 scorable
comparisons" floor this phase was bound to, not engineered to just
clear it. Every inversion traces to one disclosed pair
(`roofer`/`hvac-rich`, judged "same" by a stranger's eye, placed 69%
apart by the vector) rather than being spread thin or argued away.

**Not this round, disclosed rather than silently dropped:** Slice H,
the conversational workspace — explicitly deferred; see §5. Growing the
corpus past 19 fixtures. The map embed's WebGL-under-`--disable-gpu`
finding is disclosed, not fixed — there is nothing in this project's
own code responsible for it.

**Done — Round 5.** The review bundle rebuilt after being found stale
for the whole round (not just the five fixtures where it was visibly
wrong), with the freshness guard `.reviews/review/` never had; Slice H
built in full; the three unreachable comparisons diagnosed as a labels
contradiction, not an axis gap; the twelve weight-budget xfails given a
real, mixed, evidence-based answer rather than left unexamined. Full
account: `.reviews/slice-b-predictions.md` ("Round 5, Phase 1/2, if
room"). This is also the correction to a factual error in the Round 4
entry directly above: it read "unreachable 0" — the three unreachable
comparisons were already present the moment Phase 3b's `roofer`/
`hvac-rich` verdict landed; that line was never re-checked against the
literal census tail before being written. Left as written, corrected
here, rather than edited quietly.

**The instrument's current reading.**

    agreement   22/26 (85%) full, 9/11 (82%) held-out only — one
                disclosed inversion, roofer/hvac-rich (69% by the
                vector, judged "same" by a stranger); Round 5 traced
                every inversion to a self-contradiction in the verdicts
                themselves, not a missing axis (§5, Slice G)
                ruler a762bcc9, rule 254e171b, labels 122e6ec8,
                held-out 7aa64298
    census      same-trade 61.52% distance = 38.48% identical, 30 scored
                pairs (unchanged — no redecide since Round 4)
                closest pair barbecue / barbecue-rich at 17%, JUDGED
                "same"
    unreachable 3, all tracing to roofer/hvac-rich — a labels
                contradiction, confirmed by Round 5's own check, not
                evidence for a fourteenth axis
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults  3 fixtures match (§2.4) — barbecue-rich,
                barbecue, and restaurant-rich (unchanged)
    content census  77% of published material reaches the page
                (unchanged since Round 4 Phase 1)
    provenance  100% (687/687) of rendered prose sentences
                verbatim-or-prefix-cut source; 85% (389/459) selection
                ratio (Round 4 Phase 1)
    performance LCP/CLS/INP all within budget on 19/19 fixtures; weight
                breaches 12/19 — Round 5 sampled three with real fetched
                data: one clears at the smallest existing responsive
                tier (pure measurement artifact), two do not even then
                (genuine weight) — not one answer for all twelve, see §5
    tests       965 passed, 12 xfailed
    fixtures    19
    verdicts    2 live, same-trade closest pair among them
                (barbecue/barbecue-rich); 12 held out

**Done — Round 6.** A hand-review pass, deliberately scoped to work with
a right answer only — no redecide, no new verdicts, no visual change to
any page. Two real correctness bugs fixed in the artifact he opens: the
og:image meta tag's absolute URL was corrupted on 17 of 19 committed
pages (`build_review._copy_photographs`'s regex matched inside
`render.absolute()`'s own output, glued a relative path onto the port
number); the freshness guard failed on any machine with an empty photo
cache, an environment artifact mistaken for staleness. Both fixed, every
page's own photographs verified to actually load offline (not just
exist on disk). The weight-measurement harness itself had two real
bugs — every `/photo/` reference measured at the largest tier
regardless of what a mobile `srcset` would select, and every
externally-hosted image (a business's own "recent jobs" photos) silently
never counted at all — fixed with real DevTools Network-domain
measurement; the honest number moved in both directions, five fixtures
that used to breach now clear and two are far worse than the old number
ever showed. A third, unrelated, previously-unknown bug was found and
fixed incidentally: a synthetic click used to sample INP could actually
navigate the tab away on a fixture whose CTA is a plain external link.
Dry-running his own review checklist found and fixed a fourth bug, in
the workbench itself: an operator-facing diagnostic string (why an
instruction can't be done) was hard-truncated with no word boundary,
the third independent occurrence of a defect class already fixed twice
before in this codebase. Every taste call this round could have made —
the `roofer`/`hvac-rich` disagreement, whether 2MB is the right weight
budget for an image-heavy trade, deterministic headings, the remaining
single-composition sections, the ninth contractor fact, growing the
corpus, what the agreement figure is and isn't evidence of — was
written up as a decision with evidence instead:
`.reviews/DECISIONS-FOR-SHREYAS.md`. Full account:
`.reviews/slice-b-predictions.md` ("Round 6, Phase 1/2/3").

**The instrument's current reading.**

    agreement   22/26 (85%) full, 9/11 (82%) held-out only — unchanged;
                no redecide this round (§5, Slice G, still open)
                ruler a762bcc9, rule 254e171b, labels 122e6ec8,
                held-out 7aa64298
    census      same-trade 61.52% distance = 38.48% identical, 30 scored
                pairs (unchanged — no redecide since Round 4)
                closest pair barbecue / barbecue-rich at 17%, JUDGED
                "same"
    unreachable 3, all tracing to roofer/hvac-rich — unchanged, still
                not re-judged (see decisions file item 1)
    gate        0 of 171 pairs collide, whole corpus
    forbidden defaults  3 fixtures match (§2.4) — barbecue-rich,
                barbecue, and restaurant-rich (unchanged)
    content census  77% of published material reaches the page
                (unchanged since Round 4 Phase 1)
    provenance  100% (687/687) of rendered prose sentences
                verbatim-or-prefix-cut source; 85% (389/459) selection
                ratio (unchanged since Round 4 Phase 1)
    performance LCP/CLS/INP all within budget on 19/19 fixtures; weight
                measured honestly this round (Round 6 Phase 2) — 7/19
                breach, down from the old, wrongly-measured 12/19; two
                (roofer, restaurant-rich) are worse than the old number
                ever showed, since it never counted external images at
                all; see decisions file item 2 for the full table and
                options, none taken this round
    tests       981 passed, 7 xfailed
    fixtures    19
    verdicts    2 live, same-trade closest pair among them
                (barbecue/barbecue-rich); 12 held out

## 2. The governing requirement

A generator's characteristic failure is that its output is recognisable as its
output. The operator sells the opposite: a site that looks like a person looked
at this business and made decisions about it. Sameness is a defect class on the
same footing as a contrast failure — machine-detectable, measured on every
build, gated. Two businesses in the same trade on the same street must produce
sites a stranger would not guess came from one tool.

### 2.1 The axes

A site's identity is a point in this space. Add them to the fingerprint in this
order, by visible difference per unit of work.

1. **First-screen contract** — what occupies the first 820 pixels and in what
   relationship. Positions: photograph-behind-type, type-only, split,
   facts-forward, and proof-forward (licence, rating, service area and a quote
   action leading, photography secondary or absent — a trade-driven position no
   restaurant would use). First because two pages identical above the fold are
   the same site to the owner being shown them, and because two positions
   nearly exist already.
2. **Type treatment** — size, case, alignment, tracking. Not the typeface pair.
   The theme already carries `modular_ratio`, `display_steps`, `tracking` and
   `display_weight`, currently frozen per mood. Those are the levers.
3. **Colour structure** — light paper, dark ground, two-tone bands, duotone.
   Everything except `night` is light paper today.
4. **Page architecture** — highest total impact, most expensive, mostly below
   the fold, which is why it is fourth and not first.
5. **Section edges**, then the **signature device**.

Also in the space and not yet axes: palette derivation, photographic treatment,
motion signature, density and rhythm, navigation treatment.

### 2.2 Palette from their own photographs

The cheapest convincing form of catering, and the bytes are already cached in
`.cache/photos`. Sample dominant colours from the chosen hero and the best two
or three gallery shots, cluster, and pass them to the identity call as
candidates the palette may be built from. A taqueria with cobalt walls gets a
cobalt site. Their logo or declared brand colour is a stronger candidate still.
Validate and repair after — a colour sampled from a photograph is a starting
point, not a licence to ship an unreadable pair.

### 2.3 One signature device per site

Build a library of twelve to twenty. Exactly one per site, never two. It must be
justified against the business in one sentence the operator can repeat to the
owner, recorded in the plan, shown in the workspace, and it participates in the
diversity budget. Devices that are hero treatments are not devices — they are
positions on axis one.

Candidates: oversized type running off the edge; a photograph bleeding behind a
transparent navigation bar; a hard-edged colour band breaking the grid; a
horizontally scrolling gallery; a sticky column against a scrolling one; a
numbered index down the margin; a full-bleed quotation at display size; a
rotated or offset element; an oversized opening capital; a supplier marquee; a
split hero at exactly half and half; a menu set as a printed card; a ruled
ledger with tabular figures (law, dental, accounting); a repeated stamp mark for
licence or warranty (trades); a before-and-after slider (trades); duotone
throughout with one full-colour break (weak but consistent photography); a thin
running fact ticker; a margin note column; a corner-inset type block over one
full-bleed photograph.

### 2.4 Forbidden defaults

Encode and check. A site matching one of these is a defect: warm cream with a
serif display and terracotta accent; near-black with one acid-green or vermilion
accent; a purple-to-blue gradient hero on white; Inter or Space Grotesk as the
safe face; uniform radius and shadow on every block; an accent rail on rounded
cards repeated down the page; emoji as section markers; everything centred; a
full-viewport hero that pushes the page out of the first screen. The six
existing moods sit close to several of these. They are fallbacks to escape, not
the target.

### 2.5 The diversity budget

Compare each new site's fingerprint against the last ten generated. Require
difference on at least four axes, at least one of them structural, **and at
least one weighted highly**. A collision fails the build and re-runs the
identity decision with the colliding axes named; cap the retries and fall back
to a deterministic perturbation so a build can never hang.

The third requirement shipped missing. `collisions()` checked STRUCTURAL and
nothing else, and those are not the same set: three of the four structural axes
weigh 1.0 or less, so the rule could be satisfied entirely below the fold while
`first_screen` and `mood` — the two heaviest things in the vector — stayed
identical. Two attorneys passed it sharing their opening, their feel, their
colour and their button. "Weighted highly" means at or above 2.0, which is the
only one of five readings that agrees with the blind verdicts 12 times in 13;
above the mean weight scores 9, and so does what shipped.

The gate's rule is versioned (`fingerprint.rule_version`) alongside the
distance. Every frozen direction in the corpus is an answer that rule accepted,
so changing it re-decides the corpus (`make_fixtures.py --redecide`), which
re-renders the pages, which invalidates the blind labels. **The ground truth is
downstream of the gate** and has to be re-taken whenever it moves.

**Enabled**, in `app/site/identity.py`, once the premise for deferring it was
re-checked and had expired. "With eight axes it would reject nearly everything"
was true at seven axes and false at eight: measured against the corpus after the
first-screen contract landed, one same-trade pair in ten collided, not nine.
Nobody had re-checked it against the axis that had actually shipped.

Three stages in order of preference: ask again naming what is taken; perturb
deterministically when the retries are spent; record an unresolved collision
rather than shipping one silently. Without a key it goes straight to
perturbation — asking would fall through to the trade table, which is not a
different answer but a worse one.

A replayed direction is never re-gated. The gate ran when it was first decided,
and re-running it on a rebuild is re-asking by another name: it costs a call a
keyless reviewer cannot make, and it makes the answer depend on the order the
corpus is loaded in.

### 2.6 The keyless path must vary too

Without a key the old fallback dropped almost everyone into `fresh`. Derive the
starting position from the trade and a stable hash of the business name, so two
roofers in one town do not get the same page. Deterministic, but not identical.

## 3. The instrument, and the rules it now runs by

These were learned the hard way and each has a test behind it. Do not relax
them.

* The fingerprint is computed from **decisions, never from rendered markup**.
  Hashing HTML scores structurally identical sites as different because the
  businesses use different words.
* Weight by **visibility** and by **decidedness**, as two separate weights.
  First screen counts most, scrolled content less. Separately, a difference a
  designer chose counts more than one the business's material forced — a
  restaurant with a menu and one without are not two studios at work. The two
  correlate across the current axes and Slice B breaks that correlation
  (photographic treatment is visible and material-driven). When they disagree,
  decidedness wins.
* **Every axis must be provably in force.** For each axis, changing it alone
  must change the rendered page; any axis claimed to be first-screen must
  change the first 820 pixels. `layout_bias` currently fails this — `editorial`
  and `structured` render an identical first screen. Either give it
  above-the-fold consequence or drop its weight.
* **No thresholds fitted on the data they score.** The agreement metric is
  rank-based: every "different" pair outranks every "same" pair, reported as
  correctly-ordered cross-pairs. If the gate later needs a pass or fail, derive
  the cut then and record that it was fitted and on how many pairs.
* **Judge pairs blind.** Verdicts come from screenshots with the fingerprint
  values out of view, and the reason is written as what a stranger would see —
  never an axis name. Labels written in the vector's vocabulary measure
  self-consistency, not validity.
* **A difference in colour or subject alone is not a different site.**
* **The ruler is versioned, and the labels are part of the ruler.** The census
  refuses to compare across a change of instrument. A re-judge makes the
  agreement score incomparable to the previous one; hash the label set
  alongside the distance.
* **An axis raises no credit for raising the mean.** It is judged only by
  whether the vector moved toward agreement with the blind labels.

The recurring defect in this codebase is **declared but not in force** — a dead
function, a dead literal, tests green because a key was in the environment, a
top-level-domain list breaking its own asymmetry, a phantom axis. Five
instances so far. Prefer a standing test over catching the sixth by eye.

## 4. Invariants

* No unverified fact ships. The gate runs last, immediately before the write.
* **Two corroborated facts must not contradict each other on one page.** A
  business's own marketing copy does not outrank a value this system
  independently corroborates — when a stated quantity (a review count, and
  anything else structured data pins in the future) disagrees with the
  corroborated one, the copy sentence making the claim is dropped, never
  rewritten, and never left standing beside the number it contradicts.
  Different from the invariant above: that one is about an assertion
  nothing backs; this one is about two backed assertions that disagree with
  each other. See `app.site.contradiction`,
  `tests/test_no_contradicted_fact_ships.py`.
* A rejection writes no version, leaves the previous version live, is recorded.
* **Deterministic replay.** Persist every model answer — design system,
  compositions, copy selection, vision, signature device — and re-render from
  it. Never re-ask on a rebuild. Note the page is a function of the spec *and*
  the brief, so store a hash of the resolved material to make a mismatch
  attributable.
* No key in a generated page.
* Business text is untrusted input. Fenced as evidence, every answer validated
  against closed sets. Same for vision output.
* Model prose is allowed in a workspace message and never on a page. Separate
  table, separate module, enforced structurally.
* The operator's judgement outranks the machine's and stays attributed.
* Everything degrades without a key, and the degraded path still varies by
  business.
* `make check` green. Change a test deliberately or not at all.

## 5. What is left

### Slice B — the design system per business

`app/site/identity.py`. One call, given the brief digest, the vision summary,
the colours sampled from their photographs, and the last ten fingerprints.
Returns a validated design system taking a position on every axis in 2.1, plus a
typeface pair chosen by name from a curated table you build of roughly twenty
families with metadata, plus the signature device with its justification, plus a
`rationale` the operator can repeat.

Constraints: output type stays `Theme`; every value validated and repaired,
never trusted, with contrast pairs moved until they pass and the repair
recorded; the six moods survive as presets and the keyless fallback; the whole
answer persists into `spec_json`.

Small fixes to clear first — **all now done**: the two weights, the per-axis
manifest test, `layout_bias` (dropped from the vector, see §1), the floor on
`pick_hero`, versioning the label set, and the "Book a table" dentist.

The floor reads **the sign of the `usable` term** — the one that only goes
negative when vision condemned the photograph, through a disqualifier or an
outright "not a hero candidate". Zero is where that term changes meaning, so
there is no threshold to choose. Below it the answer is no hero and the renderer
says so; `hero_offset` overrides, because the operator has seen the picture.

An earlier version of this section proposed comparing the whole score against
what an unlabelled photograph with neutral everything is worth, about 0.35. That
reading took the hero away from a merely mediocre picture — quality two of five
in a mixed-luminance frame — and mediocre is a reason to crop, as is shape. The
floor is for condemnation.

First point where sites should stop looking related.

### Slice C — compositions and trade structure

**Mostly done — see `.reviews/slice-b-phase-2.md` and
`.reviews/first-pass.md`.** Trade profiles (`app/site/tradeprofile.py`):
per-trade headings for "what we do", gallery, and contact, replacing ad
hoc conditions; a per-trade default section emphasis, used only when the
identity call named none; which contractor facts are worth hunting for,
per trade. The call-to-action label's trade dimension (2e) already
shipped, moved here from `render.py`.

Eight of the nine contractor facts, shipped as a corroborated
`credentials` section (`app/site/contractorfacts.py`): licensed and
insured, emergency availability, warranty, free estimate, service area,
financing, a named manufacturer certification, response time — each
found by matching the business's own published text, never generated.
`services` now has three compositions by count (pills, a "feature"
composition at exactly three items with no card, or a card grid);
`reviews` has two (a stacked "feature" composition at two or three
reviews, or a card grid at four or more). **Not built, disclosed rather
than faked:** before-and-after, the last fact — it needs a paired photo
(a labelled before, a labelled after, of the same job) this material does
not carry, and approximating one without it is the exact "invent a
licence number" failure the brief warns against. Checked again, a third
time, in Round 6: still no fixture carries the pairing; recommended
there (`.reviews/DECISIONS-FOR-SHREYAS.md` item 5) to mark this
closed-blocked rather than re-checked a fourth time, pending his
agreement on the phrasing. **Also not built:** `gallery`, `about`, and
`hours` still have exactly one composition each — Round 6 laid out what
a second composition for each would cost (item 4 of the same file),
built none of them.

Headings are deterministic per trade rather than something the identity
call picks from a table — a disclosed scope reduction from "the model
picks from", consistent with how the CTA table already worked before
this phase touched it. One redecide covered every corpus-moving item
above (`compositions`/`section_order` moved); same-trade mean rose from
53.33% to 56.10%, agreement stayed 0 of 0 with no judging round run this
pass (see §1).

Verdict point. First fair moment to ask whether someone pays a thousand
dollars. Closer, not reached — eight of nine contractor facts and three
section compositions beyond the original two are real progress, but
`gallery`/`about`/`hours` still have one layout each, the model still
does not choose among headings, and a fact still only fires when a
business's own copy happens to use a matching phrase.

### Slice D — content completeness and copy selection

**Done, all four items — see `.reviews/first-pass.md`,
`.reviews/slice-b-predictions.md` ("Round 3", "Round 4 Phase 1").**
`app/site/census.py`: every heading, paragraph, list, image and fact on
their site, against whether it reached the page and which rule dropped
it if not. 77% of published material reaches the page overall. Acted
on: a business's own photography gets a real look-in for hero and every
photo-consuming section; `menu_media` reaches the page; the
`block:feature` cap raised 4 → 6; a lone Google Business Profile claim
verifies address/phone on its own. Surfaced in the workspace: a "What
didn't reach the page" panel, reusing `app.site.census.measure()`
directly.

Item 4, done in Round 4 Phase 1: `app/site/provenance.py` — every
visible prose sentence checked as verbatim-or-prefix-cut source, a
whitelisted generic-copy member (empty today, honestly), or a
corroborated field value, kept as a SECOND layer beside the existing
claims gate rather than folded into it (they catch different problems —
an unbacked assertion versus untraceable text). `app/site/copyselect.py`:
the model selects and orders sentences by INDEX into the exact
candidates offered, never by retyping, so verbatim provenance is true by
construction. 100% (687/687) verbatim provenance, 85% (389/459)
selection ratio, across the real corpus.

### Slice E — backdrops, motion, video

**Done — see `.reviews/slice-b-predictions.md` ("Round 4, Phase 2").**
The instrumentation came first, per the round's own standing rule:
`tools/perf_census.py` measures real LCP/CLS/INP from a headless
browser's own `PerformanceObserver`, not estimated. `app/site/
backdrop.py`: the preference ladder — their own video (dormant, no
extraction path gathers one yet, disclosed rather than faked); a
sequence of 2+ of their own uncondemned stills; an abstract backdrop
generated from the palette; licensed stock last, never reached, never
fabricated (no source integrated). Fires behind `first_screen ==
"type"`. `tools/motion_preview.py`: a separate, human-review-only
capture tool, motion left on, verified against a real filmstrip. The
deterministic capture pipeline needed no change — a pre-existing global
`prefers-reduced-motion` rule already disables every animation, so
`--force-prefers-reduced-motion` continues to guarantee a poster frame.

Motion did **not** become fingerprint axis thirteen: its only live
rendering effect is a function of the existing `first_screen` axis,
failing the independence test every other axis had to meet
(`app/site/fingerprint.py`, written up beside the `layout_bias`
precedent). LCP/CLS/INP are within budget on all nineteen fixtures;
weight is not on seven of them, pinned as disclosed `xfail` in
`tests/test_performance_budgets.py`. That count used to read twelve,
wrongly: Round 6 found and fixed two real bugs in `tools/perf_census.py`
itself (every `/photo/` reference measured at the largest tier
regardless of what a mobile `srcset` would select; every
externally-hosted image silently never counted at all) and re-measured
honestly with the real DevTools Network domain — five of the old twelve
clear now, and two (`roofer`, `restaurant-rich`) are far worse than the
old number ever showed. See `.reviews/DECISIONS-FOR-SHREYAS.md` item 2
for the full per-fixture table and the options for the seven genuine
breaches, none acted on yet.

### Slice G — the design review

**Swept in full — see `.reviews/first-pass.md` and
`.reviews/slice-b-predictions.md` ("Round 3, Phase 2"; "Round 4, Phase
3a").** `tools/design_review.py --full`: all 19 fixtures, three widths,
57 model calls, closed categories, findings written to JSON for a diff
rather than read off stdout. The 4-fixture sample's own findings were
confirmed and fixed the round before this one. The full sweep (295
findings) found and fixed two further real, deterministic, corpus-wide
bugs by class: a mislabeled restaurant heading on a roofer and two HVAC
contractors (`_offer_heading()` missing a trade-kind gate three other
call sites already had), and a second, independent copy of a
text-truncation bug in the signature device's pull-quote (already fixed
once elsewhere). A fourth finding — a broken map embed on four fixtures
— was run to ground and confirmed a pure `--disable-gpu` capture-tooling
artifact, not a site defect, the same finding shape as the earlier
CTA-crop discovery. Auto-repair was by class, not per finding; the
remaining ~290 findings are photographic/design judgment calls tied to
specific source material, disclosed rather than chased.

The ground truth was also rebuilt this pass (Round 4 Phase 3b, Round 5's
own instructions call it "Slice H, the only untouched slice" — meaning
this one was already closed by the time that round began): from 0 live
verdicts to 15 fresh ones, judged blind from whole-page renderings.
Agreement 22/26 (85%) full, 9/11 (82%) held-out — see §1's current
reading.

Round 6 found and fixed two more real bugs in the committed review
artifact itself (`.reviews/review/`, the bundle a human reviewer
actually opens), neither a rendering change to any page: 17 of 19
pages carried a corrupted og:image URL (`build_review.
_copy_photographs`'s regex matched inside `render.absolute()`'s own
output, metadata-only, invisible on the page); the freshness guard
failed on any machine with an empty photo cache, an environment
artifact mistaken for staleness, now a clear skip instead. Every page's
own photographs were also verified to genuinely load offline, not just
exist on disk — two apparent failures were investigated and explained
(a lightbox's intentionally empty `src`, an external partner-logo SVG
never meant to be proxied), and one genuine gap was found in the
CHECKING technique, not the bundle (a horizontal `.scrollstrip` gallery
needs its own scroll to trigger `loading="lazy"`, not just a vertical
one).

### Slice H — the conversational workspace

**Done — see `.reviews/slice-b-predictions.md` ("Round 5, Phase 2").**
Close to Lovable, with one difference: the photographs are already
labelled and the site is already sellable when the screen opens, so
every exchange is a preference rather than a repair.

The conversation opens with the model's rationale (`app/site/pipeline.py`'s
`_build_opening()` — this was already built, since Slice F; it had no
standing test before this round). Every reply is grounded in the
`IterationResult` (`app/site/reply.py`, `reply_for()`) — the model sees
what happened, never the page, which is provable rather than merely
true: the function's own signature takes exactly one parameter, typed
`IterationResult`, and `IterationResult` itself carries no rendered-HTML
field. It asks back: `unmet`/`contradictions`/`ignored_tokens` become
"I ... What did you mean?" rather than a passive list; `reader_error`
(the model unreachable) is disclosed rather than left for the operator
to notice on their own. Repeated preferences accumulate across leads
(`app/store/preferences.py`, an exact phrase said on 3+ distinct leads)
and feed the opening design's prompt as a consideration, never a
constraint — proven, not just intended, to leave the fixture corpus
untouched: `opening_spec()` returns a frozen `design_direction` before
it ever looks at accumulated preferences, for every fixture, so there is
no redecide to make here and none was made.

### Rest of F

**Done — see `.reviews/first-pass.md`.** `pipeline.spec_diff(base, config)`:
structural diff surfaced per iteration, persisted and shown in the
workspace as "What moved". `pipeline.unexplained_changes(base, config)`:
a blast-radius guard flagging any facet that moved without the
instruction's own `understood` text naming it — a heuristic over free
text, not a proof, surfaced as a warning ("Moved, but not asked for")
rather than a rejection. Render snapshot tests
(`tests/test_render_snapshots.py`, `tests/fixtures/render_snapshots.json`)
over all 19 fixtures, catching wording changes invisible to the
fingerprint.

## 6. How we work from here

Ask for review at forks, not on a schedule. Specifically: before building on an
assumption that has not been measured; when a number moves and the cause is not
obvious; when a decision would change the shape of `spec_json`, delete a section
builder, remove a test, add a runtime dependency, or let model-written text
about a business reach a page. Otherwise carry on — the brief, the census, the
agreement metric and the standing tests are the review between checkpoints.

Write the handoff to a file, not to chat. At the end of a slice, commit
`.reviews/<slice>.md` and push. It is read from the branch, so nothing is
pasted. Keep it to this shape:

```
## Changed
  <file>  <one line: what and why>          # only what a reviewer must open

## Decisions
  <decision>  —  <reason>  —  <what it forecloses>

## Numbers
  agreement   N of M cross-pairs, ruler <hash>, labels <hash>
  census      <distance>, <worst pair>
  tests       <count>

## Assumptions I could not verify
## Questions I want answered before the next slice
```

Commit the census output and the contact sheets alongside it, so the numbers can
be re-read rather than restated.

Keep the handoff short. Narrative belongs in commit messages and docstrings,
which are already good. A reviewer needs what changed, what was decided, what
moved, and what is uncertain.
