# Phase 3 — the design bridge, home services (hvac, roofer, roofer-rich)

Branch `slice-b-identity`. Continues from an independent check of the
machine at 04:00 UTC that found Part B's first pass (hvac) done on disk
but not committed, and several follow-on steps not done at all. This
handoff picks up from there rather than redoing hvac. Commits, in
order: `ca05280` (Step 0, `.gitignore` fix + committing what existed),
`825e375` (Step 1, hvac's critique recorded), `4ee0edc` (Step 2, photo
+ phone-width + authored-text fixes before spending sessions), `9916c5a`
(Step 3, roofer), `847bdf0` (Step 3, roofer-rich), `63920aa` (a lint
fix caught running Step 6's checks), `5033358` (Step 4-5, screenshots
and two gate-count corrections found while measuring).

## Step 0 — making the work committable

`.gitignore` line 23 was `design/`, which matches any directory named
`design` anywhere in the tree — it was silently swallowing
`app/design/` and `tests/fixtures/design/` on every `git add`, and no
root-level `design/` directory exists to protect. Narrowed to
`/design/`. `git ls-files app/design tests/fixtures/design`, rerun now
that every step is done:

```
app/design/art_direction.py
app/design/master_prompt.md
app/design/master_prompt.py
app/design/playbooks.py
app/design/playbooks/home_services.md
tests/fixtures/design/hvac-v1.html
tests/fixtures/design/hvac.art-direction.json
tests/fixtures/design/hvac.critique-v1.json
tests/fixtures/design/hvac.critique.json
tests/fixtures/design/hvac.html
tests/fixtures/design/hvac.prompt.md
tests/fixtures/design/roofer-rich-v1.html
tests/fixtures/design/roofer-rich.art-direction.json
tests/fixtures/design/roofer-rich.critique-v1.json
tests/fixtures/design/roofer-rich.critique.json
tests/fixtures/design/roofer-rich.html
tests/fixtures/design/roofer-rich.prompt.md
tests/fixtures/design/roofer-v1.html
tests/fixtures/design/roofer.art-direction.json
tests/fixtures/design/roofer.critique-v1.json
tests/fixtures/design/roofer.critique.json
tests/fixtures/design/roofer.html
tests/fixtures/design/roofer.prompt.md
tests/fixtures/design/screenshots/hvac-1440.png
tests/fixtures/design/screenshots/hvac-390.png
tests/fixtures/design/screenshots/roofer-1440.png
tests/fixtures/design/screenshots/roofer-390.png
tests/fixtures/design/screenshots/roofer-rich-1440.png
tests/fixtures/design/screenshots/roofer-rich-390.png
```

Nothing expected is missing. `.claude/launch.json` (a local
preview-server entry) stays uncommitted, as asked.

## Step 1 — hvac's own critique, recorded

`tests/fixtures/design/hvac.critique-v1.json` and `.critique.json`:
the Step 5 scoring call, run once against `hvac-v1.html` and once
against `hvac.html`, against the playbook and the art direction — not
a new design session. Found: the revision fixed two real copy-rule
violations (the Electrical and Air Conditioning cover cards, and the
job-story stat panel) by **deleting** the non-compliant text rather
than replacing it with compliant text — correct per the copy rule, a
regression in craft (two cards go from real body copy to a bare
heading; a stat grid becomes two paragraphs). Neither version fixes
the section-rhythm gap: `.quote-signature` (light) and `.cover`
(breathing) share the identical `--base` background in both.

## Step 2 — fixing what hvac's own check showed

**Photographs.** hvac's filled prompt hotlinked
`b2048518.assetcdn.net` — real photos of the real business, but not
local files, and only 2 of 6 supplied ever got used. Checked whether
local files were even reachable: this project already caches every
`place_photos` entry locally, keyed by
`app.adapters.photos._cache_path(name, width)`; all 10 photos for both
roofer and roofer-rich were already on disk at 2400px. Downsampled to
~1200px (`sips`) and embedded as real files in the seeded canvas via
`seed-canvas.mjs --image` (base64, per the design skill's own format —
there is no way to hand the sandboxed canvas a bare local path; base64
embedding *is* "local files" in this format). hvac is left hotlinked,
not revised again.

**Phone width — diagnosed by reading code, not by re-shooting.** Two
candidate causes, checked directly:
- hvac's own CSS has real `@media (max-width: 720/760/860px)` rules —
  the page is not unresponsive.
- `app.adapters.chrome_cdp.cdp_session` already passes
  `"mobile": True` to `Emulation.setDeviceMetricsOverride`, which sets
  a genuine 390px CSS layout viewport — the capture code is correct.

The actual cause: hvac's own `<head>` has no
`<meta name="viewport" content="width=device-width, initial-scale=1">`.
Without it, Chrome's mobile emulation mode falls back to rendering the
page at its own ~980px default virtual viewport and scaling the result
down to fit 390 physical pixels — which is exactly the squeezed
three-column screenshot showed. Confirmed by reading the extracted
design source directly (no meta viewport tag present) and by the CDP
call site (mobile emulation correctly requested). hvac.html is left as
shipped; both new master prompts (roofer, roofer-rich) require the tag
explicitly, and both resulting pages reflow correctly at 390px (see
Step 4).

**Authored text — the function's blind spot, read by eye.**
`authored_display_text_candidates()` only reads `h1`/`h2`/`h3`/
`button`, so an eyebrow `<div>` above a heading never reaches it.
Read directly from each page's design source (`class="eyebrow"`
spans), cross-checked against the function's own output:

| Business | Function output (h1/h2/h3/button) | Eyebrow/label divs the function never sees |
|---|---|---|
| hvac | `Milestone Electric, A/C & Plumbing`, `Plumbing`, `Electrical`, `Air conditioning`, `Zero airflow, after hours`, `Hours`, `Service area`, `Credentials`, `Same-day plumbing, electrical & AC for Plano` | `Plano's plumbing, electrical & AC crew`, `What we cover`, `A real call, start to finish`, `From the people we've helped`, `Ready when you are` |
| roofer | `Status Roofing LLC`, `What homeowners ask us`, `Service area`, `Phone`, `Roofing and insurance claims, handled` | `Roofing across four states`, `From the people we've helped`, `Ready when you are` (2 more eyebrows, `Consistent five-star reviews across all four states.` and `Straight answers about roofing, insurance claims, and the W2 difference.`, are real verbatim copy reused as eyebrows, not authored) |
| roofer-rich | `Bert Roofing`, `Three steps, one project manager`, `Hours`, `Service area`, `Schedule a roof inspection` | `Roofing for Dallas homeowners`, `Credentials`, `How it works`, `From the people we've helped`, `Ready when you are` |

All 5+3+5 eyebrow/label divs read as compliant by eye (≤8 words, no
digit, no CLAIM_RE match, names only the business/trade/town).

**A second function limitation, found the same way**: the function's
own output for roofer (`A referral partner who protects your closing
timelines.`) and roofer-rich (`No pressure, no surprises, no
high-pressure sales tactics.`) are **not actually authored** — both
are real verbatim copy (`feature_0[0]` / `feature_2[0]`) that happen
to also satisfy the function's three closed checks (≤8 words, no
digit, no CLAIM_RE match) by coincidence, sitting in an `<h2>`. The
function cannot tell "authored" from "verbatim copy that happens to be
short" apart — it only checks shape, never provenance. Not a defect in
these two pages (the text is true and sourced either way), but a
sharper edge on the function's own claim than "authored_display_text"
suggests: it is really "short claim-free h1/h2/h3/button text",
authored or not.

**The naming check, done by eye, since the function cannot do it (Step
2's specific ask): three strings actually flagged, not just hvac's
one.**
- hvac: `Same-day plumbing, electrical & AC for Plano` — "Same-day" is
  a service-speed claim, not a name. (Already reported before this
  step; repeated here for completeness.)
- roofer: `Roofing and insurance claims, handled` — "handled" implies
  a competence/capability claim ("we handle it"), not a name. Borderline,
  flagged rather than decided.
- roofer: `Roofing across four states` (eyebrow) — true and corroborated
  (`about[1]`: "...across all four states"), but "four states" is scope
  information beyond the business, its trade, or its town — the rule as
  written doesn't have a slot for "true but out-of-scope."

None of these were fixed — Step 2 said diagnose and report, not decide
the flag's own rule. Flagging for the next slice, same as Part A left
`_corroborated_numbers()`.

## Step 3 — roofer and roofer-rich

`uptime` before roofer: `1.97 2.10 2.00`. Before roofer-rich: (same
session, load unchanged, not re-checked separately — both ran back to
back with no other load on the machine). Both well under 6 throughout.

Both businesses: art direction generated and validated
(`app/design/art_direction.py`, contrast-repaired against WCAG AA
before being accepted — see `roofer.art-direction.json` /
`roofer-rich.art-direction.json`), master prompt filled with the
lessons from hvac's own critique baked in up front (viewport meta tag,
no combined/reworded sentences, only listed copy, distinct adjacent
section backgrounds, no over-claiming authored text), one first-pass
design session, gate, critique, one revision session, gate again.
Neither business's session failed, errored, or ran past 30 minutes;
no retries were needed.

Two real mistakes were caught and fixed **within** each first-pass
session, before saving `-v1.html` — not counted as extra sessions:
- roofer: two straight-quote/apostrophe mismatches against source text
  in the W2-employee FAQ answer, the same bug class hvac's own critique
  found.
- roofer-rich: the hero subhead dropped "and written estimate" from
  the real source sentence (`feature_0[0]`) — a truncation/rewording
  violation, caught before publishing rather than after.

## Step 4 — screenshots

`uptime` before capturing: `0.72 0.91 1.27`. One Chrome process per
capture (via `app.adapters.chrome_cdp`/`tools.contact_sheet.shoot`,
the project's own real-Chrome CDP path — not `--screenshot`, which
clamps under 500px). 4 captures: roofer and roofer-rich, revised pages
only, 1440 and 390 wide, full page. Window height matched to each
page's own measured content height (`footer.getBoundingClientRect()
.bottom`, ~3350–3360px for both) rather than a fixed tall window —
both heroes use `min-height: min(88vh, 640px)` / `min(84vh, 580px)`
(capped in `vh`), and an oversized window inflates that cap the same
way it would have inflated hvac's uncapped `92vh` hero (see the
craft-table note below). hvac's own two screenshots were not retaken.
No capture failed or timed out.

Both new pages reflow correctly at 390px: credential badges wrap onto
their own lines, review grids stack to one column, the ledger/index
rows stack. The viewport-meta-tag fix specified in both master prompts
worked as intended — screenshots confirm it, they did not diagnose it
(Step 2 already did, by reading code).

## Step 5 — measure

Design source measured throughout via `extract_main_dc_html`
(`tests/sitegen/test_seam_design_page.py`) — `content.files
["Main.dc.html"]` inside each `.html`'s own `<script id="appifact-doc">`,
never the ~2.5MB outer canvas export.

### Craft table

| Page | keyframes | transitions | scroll observer | transforms | gradients | `clamp()` | own photos used/available | hotlinked |
|---|---|---|---|---|---|---|---|---|
| hvac v1 → revised | 0 → 0 | 5 → 5 | yes → yes | 9 → 9 | 2 → 2 | 7 → 7 | 2/6 → 2/6 | 2 (both, unchanged) |
| roofer v1 → revised | 0 → 0 | 4 → 5 | yes → yes | 8 → 11 | 1 → 1 | 6 → 6 | 1/4 → 3/4 | 0 |
| roofer-rich v1 → revised | 0 → 0 | 5 → 5 | yes → yes | 9 → 9 | 1 → 1 | 5 → 5 | 3/4 → 4/4 | 0 |

No page uses `@keyframes` — every reveal and hover is a `transition`
plus a class toggle, not a keyframe animation; not a defect, just
worth naming since the table asks for the count. hvac's numbers are
unchanged from Part B's first pass; its own hero also still ships
uncapped `min-height: 92vh` in the committed file (the `min(92vh,
720px)` cap that made roofer/roofer-rich's captures behave was a fix
made to hvac only in an uncommitted scratch copy, discovered while
diagnosing Step 4's window-height math, and correctly **not** carried
into `hvac.html` — Step 1 said not to revise hvac again).

### Playbook

| Page | Required elements | Forbidden avoided | Section order |
|---|---|---|---|
| hvac v1 → revised | 7/7 → 7/7 | 5/5 → 5/5 | pass → pass |
| roofer v1 → revised | 5/5 (+2 n/a) → 5/5 (+2 n/a) | 4/5 → 5/5 | pass → pass |
| roofer-rich v1 → revised | 6/6 (+1 n/a) → 6/6 (+1 n/a) | 4/5 → 5/5 | pass → pass |

roofer and roofer-rich each have 1-2 "n/a" required elements (no job
story exists in their material; roofer has no hours to state) — scored
n/a, not fail, per the playbook's own "omitted when the brief has no
backing for it" rule. Both businesses' one forbidden-item miss in v1
was the same shape: real photographs embedded but unused, fixed in the
revision (see the craft table).

### Gate (findings, `allow_authored_display_text` flag off / on)

| Page | v1 off | v1 on | revised off | revised on |
|---|---|---|---|---|
| hvac | 27 | 23 | 13 | 9 |
| roofer | 8 | 5 | 8 | 5 |
| roofer-rich | 7 | 6 | 7 | 6 |

hvac's own big drop (Part B's first pass, already reported) came from
fixing real copy-rule violations. roofer and roofer-rich's revisions
made no gate-count difference at all — both revisions fixed craft
(photo use, motion, framing), not content violations, because neither
first pass shipped one worth counting. Every remaining finding on
every page, at every stage, is a documented residual: a compliant
authored div the tag-only `authored_display_text_candidates()` can't
see (see Step 2's table), or (roofer only) a `<a class="cta-btn">`
CTA styled as a button but not a literal `<button>` tag, so the same
tag-only limitation applies to CTAs built as anchors, which every
"Call ___" button on every page in this round actually is.

### Authored display text

Function output — see Step 2's table (left column) for all three
pages; unchanged between v1 and revision on every page (none of the
three revisions touched a heading/button/eyebrow's own text). Eyebrow/
label divs the function cannot see — Step 2's table (right column).
Flagged as naming more than business/trade/town — Step 2's own
three-item list (hvac's "Same-day...", roofer's "...handled", roofer's
"across four states").

### Template holes

0 on all six files (`hvac-v1.html`, `hvac.html`, `roofer-v1.html`,
`roofer.html`, `roofer-rich-v1.html`, `roofer-rich.html`) — checked by
grepping the extracted design source for `{{`, not the outer canvas
file.

### Contrast

Computed directly with `app.site.theme.contrast()` against each page's
actual rendered color pairs (`app.site.audit.check_contrast()` reads
CSS custom properties named `--bg`/`--surface`/`--raise`/`--on-*`,
render.py's own convention; none of these three design pages use it,
so the function finds nothing to check — noted as a real gap, not
routed around silently).

| Pair | Ratio | Needs | Result |
|---|---|---|---|
| hvac body ink `#211a12` / base `#f7f3ea` | 15.53 | 4.5 | pass |
| hvac accent-as-text `#866713` / base | 4.78 | 3.0 | pass |
| hvac white on accent (Call Now) | 5.30 | 4.5 | pass |
| **hvac hero ghost button** (`color`/`border: var(--ink)` = `#211a12`) **on its own near-black hero scrim** (~`#0f0b06`) | **1.14** | 4.5 | **FAIL** |
| hvac closing ghost button (cream `#f7f3ea` on ink `#211a12`, explicit override) | 15.53 | 4.5 | pass |
| roofer body / accent / white-on-accent / ledger text-on-ink | 16.02 / 5.00 / 5.38 / 9.49 | 4.5/3.0/4.5/4.5 | all pass |
| roofer-rich body / accent / white-on-accent / index text-on-ink | 15.84 / 4.88 / 5.30 / 10.04 | 4.5/3.0/4.5/4.5 | all pass |

**Confirmed, with numbers, not refuted**: hvac's hero "Schedule Online"
button is a real, severe contrast failure. `.cta-btn.ghost` is styled
`color: var(--ink); border: 2px solid var(--ink)` — dark-on-light
colors meant for use on a light background, and correctly overridden
inline where it's used on the dark `.closing` section
(`style="border-color:#d9cba6;color:#f7f3ea;"`). The hero's own
instance of the same class was never given that override, so it
renders near-black text and a near-black border directly against the
hero's own near-black bottom scrim: a measured 1.14:1 contrast ratio,
against a 4.5:1 requirement — not "nearly invisible," genuinely
invisible in the region of the photo it actually sits in. Not fixed
(hvac is not being revised again); roofer and roofer-rich do not
repeat it — neither one's hero has a second, ghost-styled button at
all.

### Section rhythm — the one gap neither hvac revision nor any measurement above catches on its own

Named here because it doesn't fit any other table row cleanly. hvac's
`.quote-signature` (light) and `.cover` (breathing) sections still
share the identical `--base` background — the gap Part A's own hvac
critique found, never touched by the revision (see Step 1). roofer and
roofer-rich do not repeat it: every adjacent section pair on both
pages uses a genuinely different background tone, checked directly
against each page's own CSS custom properties.

### Sessions and screenshots

Sessions used: **6 of 6** (hvac 2, roofer 2, roofer-rich 2). None
stopped, none retried. Screenshots used: **6 of 6** (hvac 2 from Part
B's first pass, roofer 2, roofer-rich 2, this round).

## Step 6 — checks

Seam and design tests touched this round: `tests/sitegen/
test_seam_gates.py`, `test_seam_design_page.py`,
`test_phase_2c_reopened_gaps.py`, `test_seam_planted_corpus.py`,
`test_seam_reopened_gaps.py`, `tests/test_no_contradicted_fact_ships.py`
— **543 passed, 3 skipped, 12 xfailed**, no failures.

`ruff check app tests` and `mypy app`: one real lint error found and
fixed (`zip()` without `strict=` in the new `app/design/
art_direction.py`, B905) — both clean after.

`make check` (full suite, browser-gated tests deselected — the same
8-test list Phase 2c used): **1577 passed, 3 skipped, 8 deselected, 21
xfailed, 0 failed**, in 90 seconds — well under the 15-minute budget.

## Sessions used of 6, and any stopped and why

6 of 6 used (hvac 2 from the prior pass, roofer 2, roofer-rich 2, this
round). None stopped early; none failed; none retried.

## Verdict

**Did direction close the craft gap on the measured table?** Yes, for
roofer and roofer-rich — both landed their first pass close to clean
(5 and 6 gate findings, all documented residuals, zero real content
violations) and used their one revision entirely on craft: photo use,
a signature motion moment actually tied to the signature device, and
(roofer-rich) a photograph treatment that matches what the art
direction actually named. Both fix the section-rhythm distinct-
background rule hvac's own critique found and neither one repeats.
Partial for hvac: the credential-laundering and review-count fixes
from Part A carried through, and the page is genuinely more
information-dense and structured than Milestone's Phase-2 icon grid —
but this round's own measurement surfaced a severe, unfixed contrast
failure (1.14:1 on the hero's second button) and a section-rhythm gap
neither the original critique nor the revision caught, both left
standing because hvac was explicitly out of scope for further revision
this round.

**Which of the three would I show an owner today, and which would I
not, and why.** I would show **roofer-rich** without reservation: four
real, correctly-attributed named reviewers, four real corroborated
credentials printed by their own exact label, a genuinely framed hero
matching its own stated art direction, and zero gate findings beyond
documented, harmless residuals. I would show **roofer** with one
caveat spoken out loud first: the page itself is clean and well-
proportioned, but "Roofing and insurance claims, handled" and
"Roofing across four states" are both authored strings this round's
own tighter naming check flags as riding past what the business
literally said, even though both happen to be true — I'd want that
signed off, not silently shipped. I would **not** show hvac as it
sits in the committed file today: a real button on the hero — the
first thing a visitor's thumb would look for — is measurably
unreadable against its own background, and that is exactly the kind
of defect an owner notices in the first three seconds, whatever else
the page gets right.
