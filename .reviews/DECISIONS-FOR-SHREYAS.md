# Decisions for Shreyas

Round 6's governing rule: only work with a right answer gets built.
Everything below requires taste, product judgment, or a verdict about
how the sites look — prepared as decisions with evidence, not made.
Nothing in this file changed a single rendered page; both fingerprint
hashes and `render_snapshots.json` are byte-identical to the start of
the round (confirmed in `.reviews/round-6.md`).

Each item: the question, the evidence, the options, the cost of each,
a recommendation, and what's needed from you to proceed.

---

## 1. `roofer`/`hvac-rich` — the blind judge and the vector disagree

**The question.** One live verdict says these two pages are the same
template; the fingerprint vector says they sit 69% apart — nearly the
corpus-wide mean of 80%, further apart than several pairs judged
"different." This one pair drives all four inversions in the full
agreement score and all three "unreachable" comparisons
`quality_census.py` reports. Which reading should stand?

**The evidence.** Both pages open on the identical recipe — full-screen
photograph, a rating number at display size in the corner, two buttons
(one solid, one outlined) — and run the same section set below it in
nearly the same order: a single-colour band with three numbers, an
eight-card service grid under the same kind of heading, a review grid,
a twelve-photo "Recent jobs" gallery, a two-column closing paragraph.
The verdict's own recorded reasoning names two differences and
dismisses both: a short row of small labelled badges present on one
page and not the other, and reviews/services swapping which comes
first. Round 6's own check (below) found that BOTH of those exact
signal types — an order swap, an extra small element — were each
independently enough to call three OTHER live pairs "different"
(`dentist`/`law`, `roofer-rich`/`hvac-rich`, `law`/`law-rich`). That is
internally inconsistent, not a missing-axis finding: no property named
in any of the four verdicts' own text separates `roofer`/`hvac-rich`
from the three "different" pairs while still joining it to itself.

**Deliberately not re-judged this round**, on your own instruction: a
fresh Claude verdict would replace one Claude judgment with another and
read as "settled" rather than as what it would actually be — the same
model reconsidering itself, not independent confirmation. You are going
to look at these two pages yourself; that is the actual second opinion
this needs.

**Two readings, and what each implies:**

- **The vector is right, the verdict is the odd one out.** If a fresh,
  careful look at `roofer.html` and `hvac-rich.html` side by side says
  "no, these read as two different studios" — the order-swap and the
  badge row were more salient than the earlier blind pass gave them
  credit for, and the fix is a re-judge of this ONE pair (not a
  same-session flip; a deliberate, separately-recorded pass), which
  would very likely clear all four inversions and all three unreachable
  comparisons at once, since they all trace back here.
- **The verdict is right, the vector is missing something.** If they
  genuinely do read as one template to you, the fingerprint is
  overcounting a difference that does not matter to a stranger — most
  likely `architecture` (the axis every one of the three "different"
  comparisons' extra-differences includes) is weighted too heavily
  relative to how visible a services/reviews reorder actually is. That
  would be a real, evidence-backed argument for a weight change,
  investigated the way `slice-b-weight-split.md` already did once for a
  similar disagreement (never chosen by watching the tuning number move
  — pre-register the change, spend held-out verdicts once).

**What I'd need from you:** which reading you land on after looking, or
"still unsure" — in which case the honest move is to leave it disclosed
exactly as Round 5 left it, and let a THIRD independent pair of eyes (a
future blind judge, not this session) break the tie later rather than
force it now.

---

## 2. The weight budget

**The question.** BRIEF §5 pins every fixture to 2MB of measured page
weight. Is that the right budget for an image-heavy trade, or should
those pages be allowed to carry their own photographs?

**The evidence — measured honestly, not estimated.** The harness this
depended on had two real bugs (Round 6 Phase 2): it measured every
`/photo/` reference at the largest tier regardless of what a mobile
`srcset` would actually select, and it silently never counted a
business's own externally-hosted images at all. Fixed, and all 19
re-measured with the real DevTools Network domain (real bytes
transferred, not a disk estimate):

| fixture | weight | vs 2MB | largest contributor |
|---|---:|---|---|
| threadbare | 59KB | clear | — (no photos at all) |
| bare-trade | 570KB | clear | gallery (1 photo, ~500KB) |
| dentist | 424KB | clear | gallery ~198KB / external ~156KB |
| contractor-bare | 718KB | clear | gallery, ~651KB of 718KB |
| law | 816KB | clear | external ~518KB / gallery ~228KB |
| roofer-rich | 667KB | clear | gallery, ~597KB of 667KB |
| hvac-second | 1021KB | clear | gallery ~735KB / external ~216KB |
| dentist-rich | 1089KB | clear | gallery ~597KB / external ~420KB |
| hvac | 1276KB | clear | gallery, ~1097KB of 1276KB |
| restaurant-bare | 1345KB | clear | gallery, ~1278KB of 1345KB, no external |
| hvac-rich | 1682KB\* | clear | gallery ~1.2MB / external ~0.7MB |
| restaurant-casual | 1823KB | clear | gallery ~1046KB / external ~710KB |
| **barbecue-rich** | **2182KB** | **BREACH** | gallery is the larger share (~1.5MB of 2.2MB) |
| **salon** | **2165KB** | **BREACH** | gallery is the larger share (~1.3MB of 2.2MB) |
| **salon-rich** | **3039KB** | **BREACH** | gallery, almost entirely (~3.0MB of 3.0MB, no external) |
| **barbecue** | **4272KB** | **BREACH** | external is the larger share (~2.4MB of 4.3MB, vs ~1.7MB gallery) |
| **law-rich** | **4898KB** | **BREACH** | external is the larger share (~3.3MB of 4.9MB, vs ~1.5MB gallery) |
| **restaurant-rich** | **6544KB** | **BREACH** | external, overwhelmingly (~5.4MB of 6.5MB) |
| **roofer** | **14032KB** | **BREACH** | external, overwhelmingly (~10.0MB of 14.0MB) — the worst in the corpus |

"gallery" = this project's own `/photo/` proxy (Google Places photos,
served at the correct responsive tier). "external" = images the
business's own live site references directly (a "recent jobs" block, a
feature photo) that this product pulls in as-is rather than re-hosting
or resizing.

\* `hvac-rich`'s own weight was not perfectly reproducible run to run —
1682KB in the committed baseline, 1982KB in a separate diagnostic pass
run for this table, both comfortably clear of budget either way. Worth
a note, not a concern: every other fixture above matched the committed
baseline to the byte or within a few KB of noise, and this is the only
one that did not. The measurement's own docstring calls weight "not
timing-noise-prone" relative to LCP/INP; this one fixture is the
exception found while building this table, disclosed here rather than
smoothed over — not investigated further this round, since it doesn't
change which side of the budget it lands on.

**Two genuinely different problems are hiding under one budget number.**
Of the 7 breaches, 3 (`barbecue-rich`, `salon-rich`, `salon`) are
dominated by this project's OWN photo gallery — a choice already inside
this product's control (how many photos, at what tier, in what
composition). The other 4 (`barbecue`, `law-rich`, `restaurant-rich`,
`roofer`) are dominated by images the BUSINESS's own live site serves,
which this product currently re-displays as-is, uncompressed, at
whatever size and format the business's own site happens to use —
`roofer`'s worst single external file alone is 3MB. These have
different fixes with different costs, which is exactly why this item
is being handed to you rather than resolved here.

**Options, not taken here:**

- **A. Leave the 2MB budget as-is; compress or cap the offending
  fixtures.** Cheapest to implement, but changes what a real visitor
  sees — recompressing a gallery photo or dropping images from an
  external feature block is exactly the kind of "what does the site
  look like" call this round's rule keeps out of my hands. It would
  also need a decision on WHICH external images this product is even
  allowed to re-encode — they are not this product's own asset, pulled
  from the business's own site as-is.
- **B. Raise the budget for image-heavy trades specifically** (a
  per-trade-kind budget rather than one flat 2MB), on the reasoning
  that a barbecue joint or a salon's own selling point IS the photos,
  and a visitor on a decent connection may reasonably tolerate more
  weight for a page whose whole value is showing the work. Cost: gives
  up a single, simple, uniform performance promise BRIEF §5 currently
  makes to every fixture regardless of trade — a real product claim
  this round isn't positioned to change unilaterally.
- **C. Treat the two failure modes differently: keep 2MB for
  `/photo/`-proxy weight (this product's own choice, so its own
  budget), and measure/budget external images SEPARATELY** — since
  they are not a design choice this product made at all, but a
  side-effect of quoting a business's own material as-is. This would
  immediately clear `barbecue-rich`/`salon-rich`/`salon` under the
  existing 2MB gallery budget while leaving `barbecue`/`law-rich`/
  `restaurant-rich`/`roofer` as a genuinely different, disclosed
  problem (should this product re-host and compress a business's own
  external images, or drop them, or accept the weight since it's their
  own site's material being shown as-is) — worth deciding on its own
  terms rather than folding two different costs into one number.
- **D. Do nothing — accept 7 of 19 fixtures as documented,
  intentional `xfail`s**, exactly as this round leaves them, on the
  reasoning that a performance budget with a small number of disclosed,
  understood exceptions is more honest than a budget quietly loosened
  to make every fixture pass.

**Recommendation:** (C) is the most defensible next step if you want to
act on this at all — it is the only option that does not conflate "this
product's own design choice" with "a business's own material passed
through as-is," which this table shows are actually two different
problems with two different owners. But (D) is a legitimate, honest
position too: the budget as a single flat number was always somewhat
arbitrary, and 7 disclosed exceptions with a clear reason each is not
obviously worse than a more complicated two-tier budget.

**What I'd need from you:** which of A/B/C/D (or none), and if B or C,
what the actual numbers should be — that is a product promise, not a
measurement.

---

## 3. Deterministic headings — the table BRIEF §5 asked for already exists

**The question, as given to me this round:** "BRIEF §5 wants a
per-trade table; they are model-chosen today. Propose the table using
the EXISTING headings as its values."

**The evidence says the premise is out of date, not that the work is
undone.** `app/site/tradeprofile.py` already carries exactly this: a
pure, deterministic, per-`trade_kind` lookup with no model call
anywhere in it —

    HEADING = {
        "food":    ("On offer",       "What we cook and serve"),
        "care":    ("Treatments",     "Ways we can help"),
        "groom":   ("Services",       "What we offer"),
        "body":    ("Classes",        "What we teach"),
        "desk":    ("Practice areas", "How we can help"),
        "trade":   ("Services",       "What we handle"),
        "retail":  ("The shop",       "What we carry"),
        "default": ("What we do",     "How we can help"),
    }

plus a parallel table for the gallery heading (`GALLERY_HEADING` —
"Recent jobs" for a contractor, "Where we work" for a practice, "Have a
look around" otherwise) and the contact section
(`CONTACT_HEADING` — "Reach us" for a contractor, "Schedule a
consultation" for a practice, "Come and see us" otherwise), and one
content-shape override (`PRODUCTS_ONLY_HEADING`, "What we make", for a
business selling goods with no services list). BRIEF §5's own Slice C
entry already names this precisely: "Headings are deterministic per
trade rather than something the identity call picks from a table — a
disclosed scope reduction." This was done, and disclosed, in an earlier
round; this round's instruction appears to have been written from an
older reading of the brief.

**What's actually still open** is narrower than "build the table": each
`trade_kind` gets exactly ONE heading, always — there is no per-business
CHOICE among options the way the identity call chooses a mood or an
accent. If "the model picks from" was always meant literally (a menu of
2-3 headings per trade, model-selected per business rather than one
fixed string every business in that trade shares), that is a real,
separate, NOT-YET-BUILT feature — and building it honestly needs
additional heading wording per trade to choose AMONG, which is new
prose, which is exactly the kind of taste call this round's rule keeps
out of my hands.

**Options:**
- **A. Call the existing table the answer.** It already replaces "the
  model picks headings" with something deterministic and disclosed; the
  residual gap (no per-business variety within a trade) may not be
  worth solving at all — plenty of the corpus's own variety already
  comes from `first_screen`/`architecture`/`compositions`, not headings.
- **B. Build the "pick from a menu" version**, once you (not me) supply
  2-3 real alternate headings per trade — I can wire the selection
  logic and the model-facing prompt the moment the wording exists; I
  should not originate the wording myself under this round's rule.

**What I'd need from you:** which of A/B, and if B, the actual
alternate phrases per trade (or tell me to draft candidates for you to
edit next round, under a rule that allows drafting copy).

---

## 4. The remaining single-composition sections: gallery, about, hours

**The question.** BRIEF §5 asks for two to four compositions per
section, keyed to content shape, the way `services` (3) and `reviews`
(2) already have. `gallery`, `about`, and `hours` still render exactly
one layout each regardless of what the business's own material looks
like. Worth a second composition for any of them, and what would it
cost?

**The evidence, section by section:**

- **`gallery`** (`render._gallery`) always renders one "mosaic" grid,
  sized `wanted, wide, narrow = gallery_shape(len(candidates))` — the
  GRID's own column count already varies by photo count, but the
  ARRANGEMENT is always a mosaic grid. A plausible second composition:
  the `scroll_gallery`/`.scrollstrip` treatment `salon-rich`'s
  SIGNATURE DEVICE already uses (a horizontally-scrolling strip) is
  currently gated to the signature-device system, not offered as a
  second GALLERY composition in its own right. Making it one would mean
  deciding whether it is offered by photo count, by trade, or by
  whatever already decides the signature device — a real design
  question, not a mechanical one.
- **`about`** (`render._about`) always renders one text-block layout.
  A plausible second: the two-column "story beside a named person's
  card" layout `dentist.html`'s about section already happens to use
  informally (from a `block:story` structure) versus a single flowing
  paragraph — whether that is a genuine SECOND COMPOSITION or just what
  the content shape happens to produce today needs a closer look before
  proposing it as an axis-worthy choice.
- **`hours`** (`render._hours`) always renders one open/closed flag plus
  a seven-line list. A plausible second: a compact "open now" badge
  alone for a business with unremarkable, regular hours, versus the
  full weekly table for one with real variation (extended weekend
  hours, a mid-week closure) — this is the cheapest of the three to
  reason about, since "hours vary a lot" vs. "hours are the same every
  weekday" is a fact already in the material, not a taste call about
  photographs.

**Cost, roughly, of building any one of these:** a new template
function plus a decision rule for when it applies (by content shape,
matching how `services`'/`reviews`' compositions are already keyed);
a `compositions` fingerprint-axis value added for that section (already
structured to carry per-section values); a redecide, since compositions
is a corpus-moving axis — the same one-redecide-per-phase batching
already used for the last several composition additions.

**Recommendation:** `hours` is the cheapest, most mechanically-argued
place to start if any of the three get built — it needs no new
photographic or copy judgment, just a threshold on how much the
business's own hours already vary. `gallery` and `about` both carry
more of a real design decision (would the scroll-strip suit every
trade, or only ones already showing off a room) that reads as exactly
the kind of call this round keeps out of my hands.

**What I'd need from you:** which section (if any) to build next, and
for `gallery` specifically, whether the scroll-strip treatment should
be its own composition or stay exclusive to the signature device.

---

## 5. The ninth contractor fact (before-and-after) — recommend closing it

**The question.** Should this stay an open item in BRIEF §5, or be
marked closed-blocked?

**The evidence.** Checked three times now, independently, across three
different rounds (Round 4, Round 5, and again this round): no
fixture's `photo_vision` data carries a before/after pairing (a
labelled "before" and a labelled "after" of the same job). This is not
an effort gap — building it without that pairing is the exact
"invent a licence number" failure this project's own credential-claims
fix exists to prevent (a fabricated pairing on a real business's page).
The corpus would need photographs that do not exist in it today, which
is a data-acquisition question, not a code one.

**Recommendation:** mark it closed-blocked in BRIEF §5 rather than
leaving it open to be re-checked a fourth time. "Closed-blocked" should
read as "not abandoned, but not actionable without new material" —
re-open it the day a fixture (or a real lead) actually carries a
labelled before/after pair, not before.

**What I'd need from you:** agreement to phrase it that way in BRIEF,
or a different phrasing you'd prefer.

---

## 6. Growing the corpus past nineteen fixtures

**The question.** What would a larger corpus buy, and what would it
cost?

**What it would buy.** Every same-trade distance, the agreement score,
and the "closest pair" reading are all statements about NINETEEN
businesses — the same-trade mean specifically is computed over just 30
scored pairs (36 including `threadbare`, which is excluded from every
score). A number computed from 30 pairs moves a lot for each new
business added; the agreement score's own held-out third currently
holds 12 comparisons total, which is enough to CLEAR the "4-5 scorable
comparisons" floor this round's predecessor was bound to, but is still
a small enough sample that one contested verdict (see item 1) drives
100% of the current inversions. More fixtures, especially more within
an already-crowded trade, would make any single verdict's disagreement
matter proportionally less, and would give the diversity gate more
real collisions to actually be tested against (it has never yet found
a genuine same-trade collision it could not resolve).

**What it would cost.** Each new fixture is a real business's data,
researched and verified the same way the current nineteen were (BRIEF
§1's own account of widening 11→19 describes the actual cost: real
API-credit spend for vision + design-direction calls per fixture, plus
the same amount of manual verification this round's own investigations
required — checking a photo's provenance, confirming a fact is
corroborated, and so on). It also FORCES at least one redecide (a new
fixture's own design-direction call is itself a corpus-moving event)
and very likely invalidates the current held-out verdict set's
composition (new same-trade pairs become possible that were not
judgeable before), meaning a real judging round has to follow, not just
a fixture-count bump.

**Recommendation:** worth doing when the goal is specifically to
stress-test the diversity gate or to grow the same-trade sample past
what a single contested verdict can dominate — not worth doing casually,
since the true cost is a full redecide-plus-rejudge cycle, not a
data-entry task.

**What I'd need from you:** how many new fixtures, which trades to
weight them toward (the historical pattern has been "toward trades
already crowded" since sameness is a same-trade question), and whether
you want to supply the businesses or have them found the way the
existing nineteen were.

---

## 7. What 85% agreement actually is evidence of

**Stated plainly, because the number is easy to over-read.** The 85%
full / 82% held-out agreement figure is Claude judging, blind, from
screenshots — whether Claude's OWN fingerprint distance calculation
ranks two pages the way Claude's OWN visual read of them does. Both
halves of that comparison were produced by this same model, in
different roles, at different points in the project.

**What that number IS evidence of:** whether the STRUCTURED axis
system (first_screen, architecture, type_treatment, and so on) captures
the same notion of "same design" that a single, careful visual pass
already captures — a real, useful internal-consistency check, and one
this project has repeatedly found real problems through (the
first-screen/type-treatment axes were added BECAUSE an earlier version
of this same check inverted on `dentist`/`law`; the current
`roofer`/`hvac-rich` disagreement, item 1 above, is the same kind of
finding, not yet resolved).

**What it is NOT evidence of:** whether a human visitor, or you, would
agree with either the vector OR the blind judgment. Every "same" or
"different" verdict in `tests/fixtures/pairs.json` was written by
Claude looking at Claude-generated pages, using resolving rules ALSO
written by Claude (with your review at each round's close-out, not
independent human judging of the underlying pairs themselves). A
number built entirely from one model's own two ways of looking at its
own output can be internally consistent and still be systematically
wrong about what a stranger — the actual audience for these pages —
would say. The real test of that remains what BRIEF's own
`READ-ME-FIRST.md` already asks a human reviewer to do first: open two
pages whose rationale sounds similar and decide for yourself whether
they read as the same studio.

**Recommendation:** keep using the agreement figure as an internal
regression check (did a new axis or a weight change move the vector
CLOSER to or FURTHER from a documented set of blind readings) — and
do not cite it, alone, as evidence the product is diverse enough to
sell. That claim needs your own eyes on the pages, which is exactly
what this round's close-out points you toward first.

**What I'd need from you:** nothing to proceed — this is a statement of
what the number means, not a decision with an implementation cost. Flagged
here so it is read once, plainly, rather than assumed.
