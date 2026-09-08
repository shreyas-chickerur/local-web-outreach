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

    agreement   19 of 27 cross-pairs (tuning 19 of 27, held out 0 of 0)
                ruler aece36b7, rule 95f4d93e, labels dafe510d,
                held-out e3b0c442
    census      same-trade mean 51% distance = 49% identical, 7 scored pairs
                closest pair hvac / roofer at 37%, judged SAME
    unreachable 0
    gate        0 of 55 pairs collide under its own rule
    tests       760

**Done — Slice B, axis three: page architecture.** `app/site/architecture.py` —
five arrangements (stacked, banded, ledger, column, gallery) covering rhythm,
measure, ground and separator, applied to the sections and never to the hero.
Offered only where the section count can carry it. Proven with the stripped-class
test phase 1's defect made necessary: all ten value pairs render differently once
`class="..."` is taken out of the comparison, and a standing test holds that the
arrangement never reaches into the first screen.

**Its binding claim FAILED, and the reason is the instrument.** The claim was
that the count of verdicts determined by `first_screen` alone would fall below
the total. It went 16 of 16 to 12 of 12. **The ground truth is read from the
first viewport and this axis lives below it** — measured, `ledger` is
byte-identical to `stacked` in a fold capture, and `banded` and `gallery` differ
only in the sliver of the next section reaching the bottom edge, which reads as
colour and is discounted by name.

**So the instrument can only validate first-screen axes.** That corrects what
was recorded here after axis two: the generator does not have one arrangement
dimension, the measurement only looks at one screen. Section edges and most of
the signature device are below the fold as well, so building them now would
produce axes whose claims cannot be tested. **Whether the ground truth moves off
the fold is the open question, and it is a change to the instrument's
definition rather than a tuning.**

**Done — the type-setting rule, and the blind spot closed.** `pairs.json` named
colour and subject and was silent on how the name is set; two verdicts fell into
that silence in opposite directions and produced both unreachable comparisons.
The rule was written before the verdicts were looked at and moved exactly one.
`unreachable()` is zero, and **axis two's justification is gone with it** — type
treatment was built to close a blind spot that was never evidence about axes.
The axis stays; it renders, it varies the corpus, the gate needs it. See
`.reviews/slice-b-type-rule.md`.

**Done — a defect in axis one, found by judging and repaired.** `first_screen`
declared five positions and two of them rendered the same first screen: `photo`
and `facts` differed above the fold by the class attribute and nothing else.
That is `layout_bias` again — see §3 — in the axis weighted heaviest at 2.5, so
every distance across such a pair was overstated by a quarter, and
`test_a_first_screen_axis_changes_the_first_screen` passed it because a class
name is markup. `facts` now opens on the rating at display size with the name
second, which is what §2.1 says the position is for. A strengthened test strips
the class attribute before comparing and holds all ten position pairs.

**The instrument cannot validate anything yet, and this is the reason.** All
sixteen live verdicts are exactly "do they share `first_screen`". With colour,
subject and type setting discounted by the judging rules, the generator has
**one arrangement dimension**. Judging more pairs adds verdicts already
determined by the vector, which is self-consistency rather than validity. Page
architecture is next — not by §2.1's ordering, but because it is the second
arrangement dimension and nothing can be measured until there is one.

**Done — Slice B, axis two.** Type treatment in `app/site/typetreatment.py` —
size, case, alignment, tracking; five treatments; availability constrained by
the length of the NAME rather than by the photographs. It visibly separates
three restaurants that all open on the same position. `HIGH_WEIGHT = 2.5` ships
with it: type treatment weighs 2.5, so the gate's required set is
`{first_screen, type_treatment}` — twenty-five combinations against a window of
ten, where `first_screen` alone was five and unmeetable.

**And its pre-registered claim failed.** `agreement.unreachable()` reports two,
not zero. The pairs a person calls one studio share their GEOMETRY and differ in
type treatment, colour and subject — and the judge discounts all three, so the
vector now carries a 2.5-weight term exactly where a person sees no difference.
That is the failure mode `accent` and `hero_subject` already had.

**The fork is decided: the gate's required set is split from the distance's
weighting.** `fingerprint.REQUIRED_HIGH` is what `collisions()` reads;
`HIGH_WEIGHT` and `highly_weighted()` are gone. The two were one number and are
not one question — the gate asks whether a site's decision set repeats a recent
one, the distance asks whether a stranger would say two pages came from one
tool, and `type_treatment` is where they came apart: the gate needs it or it
becomes unmeetable, and four blind verdicts describe a type difference and
dismiss it. An axis can be mandatory for variety and cheap in the metric, and
while they were coupled that sentence had nowhere to live.

Both hashes are unchanged by the split, which is the point: it is a structural
change that provably alters no output. **No weight was changed.** The freedom is
now available and deliberately not taken — lowering `type_treatment` moves
agreement 21/36 to 30/36 and the held-out set 0/2 to 2/2, which is a change
arriving pre-validated by the score it improves. See
`.reviews/slice-b-weight-split.md`.

**The blind spot is a label contradiction, not a missing axis.** Both remaining
unreachable comparisons trace to two verdicts of mine that cannot both be right:
`restaurant-bare`/`restaurant-rich` differs on a strict subset of what
`barbecue`/`restaurant-bare` differs on, both `why` texts rest on how the name
is set, and one is called the same site while the other is called two studios.
No axis can clear that. `pairs.json`'s judging rule covers colour and subject
and says nothing about type setting, which is the gap they fell into — stating
that rule and re-judging against it comes before axis three, and is
pre-registered in `.reviews/slice-b-predictions.md`.

**The held-out third cannot survive this work.** Emptied twice now, by both
changes since it was created: every axis re-decides the corpus, every re-decide
moves the folds, and a held-out verdict whose page is gone is retired by rule. A
held-out set of PAIR VERDICTS can score a change to the ruler and never a change
to the gate.

**Not started.** The rest of Slice B, and Slices C, D, E, G, H and the rest of
F.

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

Two to four real compositions per section, selected by content shape, page
architecture, and the identity call. Headings stop being one hardcoded string
per section and come from a per-trade table the model picks from. Trade profiles
declaring which sections matter, in what order, and which facts extraction
should hunt for — including the sections contractors need and the generator
lacks: service area, licensed and insured, before-and-after, financing,
emergency availability, warranty, manufacturer badges, response time, free
estimate. The call-to-action label gets its trade dimension here.

Verdict point. First fair moment to ask whether someone pays a thousand dollars.

### Slice D — content completeness and copy selection

`tools/content_census.py` first, before changing anything: every heading,
paragraph, list, image and fact on their site, and whether it reached the page,
and if not which rule dropped it. Fix what it exposes. Surface it in the
workspace.

Then let the model select and order their own sentences — never author one.
Replace `unsupported()` with a provenance check: every visible sentence is a
verbatim or prefix-cut span of source material, a member of a whitelisted
generic-copy library, or a value rendered from a corroborated field. Keep the
claim expression as a second layer.

### Slice E — backdrops, motion, video

Preference ladder, never skipped for effect: their own video; a sequence built
from their own stills; an abstract backdrop generated from the palette;
licensed stock last and heavily constrained — stock may not depict a place,
person, or finished job a visitor could read as theirs. Encode that in code.

`prefers-reduced-motion` cancels everything, poster frame always, muted and
inline and looping, never the largest contentful element, budgeted near two
megabytes. Hold Largest Contentful Paint under 2.5 seconds, Interaction to Next
Paint under 200 milliseconds, Cumulative Layout Shift under 0.1. Motion level is
a design-system property driving one choreography, not effects sprinkled per
element.

### Slice G — the design review

Screenshot at three widths, send with the brief for a critique: defects only,
closed categories — hierarchy, crop, spacing, colour, imagery, credibility, and
"this reads as a template". Findings join the existing defects list. Auto-repair
only the deterministic ones. A reviewer, not an author. Run it on every lead's
opening version.

### Slice H — the conversational workspace

Close to Lovable, with one difference: the photographs are already labelled and
the site is already sellable when the screen opens, so every exchange is a
preference rather than a repair.

The conversation opens with Claude's rationale, not an empty box. Every reply is
grounded in the `IterationResult` — the model sees what happened, never the
page, so it cannot invent an outcome. It asks back: a defect becomes a question
rather than a panel and no change. Later, repeated preferences accumulate across
leads and feed the opening design.

### Rest of F

Structural diff surfaced per iteration; a blast-radius guard so an instruction
that changes one facet cannot silently change others; snapshot tests over the
fixtures.

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
