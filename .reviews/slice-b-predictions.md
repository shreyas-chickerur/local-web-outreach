# Pre-registered, before Slice B is written

Written 2026-09-07, before any Slice B code exists. The point is that a number
moving the wrong way with a story attached is the escape hatch this project has
now closed three times in the other direction — an invalid baseline, a corpus
that changed underneath a pinned number, a distance that became weighted while
the baseline stayed flat. Predicting the dip in advance is what stops "worse,
but for a good reason" from being available after the fact.

## The claim being tested

Adding **first-screen contract** and **type treatment** as axes resolves the
standing inversion.

    dentist / law — a person says these are the same page.
                    The vector says 80% apart, and is wrong.

Both are serif display over a photograph of a person indoors, laid out
identically. The vector can only see that they differ in colour and in what
they publish, so it overstates. Those two axes are what a person is actually
reading when they call them the same.

## What counts as the axes having worked

**Primary, and binding.** After first-screen contract and type treatment land,
`dentist / law` resolves — it stops being an inversion. If it does not, the
axes did not do what they were added to do, whatever happened to the mean. No
story about the mean substitutes for this.

**Expected and acceptable.** Agreement may fall before it rises. More axes
means more room to differ, and the two new ones start with few positions each,
so early on they can separate pairs a person groups together. A dip is
allowed — but only with the primary claim met, and only with every new
inversion re-judged blind and either accepted as a genuine correction to the
labels or recorded as a real miss.

**Not acceptable, whatever the mean says.**

* `dentist / law` still inverted.
* A new inversion accepted as noise without a blind re-judge of that pair.
* Agreement reported without the inversion list beside it. "Worse" has to be
  inspectable, not a single number with an explanation attached.
* The ruler or the label hash changing in the same commit as a claimed
  improvement. Re-pin, then measure — never both at once.

## What I expect to happen, recorded so it can be wrong

* Same-trade mean falls from 52% identical toward 35–40%. Low confidence: this
  number has moved for the wrong reason three times.
* Agreement dips to somewhere around 30/36 as the new axes take positions, then
  recovers past 35/36 once each has three or more.
* `contractor-bare / roofer` and `barbecue / restaurant-rich` — the two
  closest same-trade pairs — separate on first-screen contract before they
  separate on anything else.
* The proof-forward position is what separates the two attorneys from the two
  restaurants, rather than separating each pair from the other.

## Checked, after axis one (first-screen contract)

**The binding claim held.** `dentist`/`law` is no longer inverted. Agreement
went 35/36 to 36/36 on the labels as they stood, and 40/40 after the pair was
re-judged — see below.

**Wrong: the dip.** I forecast agreement falling to around 30/36 before
recovering. It rose immediately. The reasoning — a new axis with few positions
separates pairs a person groups together — did not apply, because the pair in
question was one a person had grouped WRONGLY under the old rendering.

**Wrong, and more concretely: the separation.** I predicted that
`contractor-bare`/`roofer` and `barbecue`/`restaurant-rich`, the two closest
same-trade pairs, would "separate on first-screen contract before they separate
on anything else". `contractor-bare`/`roofer` did. `barbecue`/`restaurant-rich`
did not — both chose `photo`, and they remain the worst same-trade pair at 20%.
The direction call, offered a real choice, picked the same obvious default for
two businesses that both have strong photography, and nothing yet stops it: the
diversity budget that would push the second away from the first is
`identity.py`, which does not exist. An axis being real and a collision gate
being wired are different pieces of work.

**Right: the mean did not move**, 52% to 52%, and no credit is claimed for it.
`dentist`/`law` is not a same-trade pair — a dentist and an attorney are
different trade kinds — so resolving it could not move that number by
construction, whatever axis one did.

**A category I had not predicted: the label went stale.** The verdict on
`dentist`/`law` described a rendering where both opened on a photograph with
white type. After axis one one opens on `proof` and the other on `facts`, and a
blind re-look says they are plainly different pages. Re-judged, and the labels
now record which rendering they were taken from. A label kept past the page it
judged is as stale as a baseline kept past a change of ruler, and that was not
on the list of things to watch for.

## Baseline this is measured against

    ruler   563eaa0b        (seven axes, visibility x decidedness)
    labels  747e4ef5        (fifteen pairs, re-judged blind)
    agreement  35 of 36 cross-comparisons
    same-trade mean  52% distance = 48% identical
    worst pair  contractor-bare / roofer at 27%

## Outcome so far — 2026-09-08

**Still open.** The binding claim needs both axes and only the first-screen
contract has landed.

`dentist`/`law` did resolve on that axis alone, and it was reported here as
resolved. It has come back. Re-deciding the corpus under the corrected gate
rule put both of them on `proof`, and judged blind against the current pages
they are one page in two colours again: the same band of photograph, the same
serif name on cream, the same ruled row of figures, the same single button,
the same coloured band at the foot — teal against burgundy.

That is worth more than the interim pass was. It is the clearest evidence in
the corpus for what the claim predicted: what a person reads when they call two
pages the same is the skeleton and the typeface, and the vector has an axis for
neither. Two more pairs now say the same thing — `hvac`/`roofer` and
`threadbare`/`hvac`, both judged the same site, both ranked far apart.

**One correction to the record.** The verdicts this file's claim was scored
against were read off contact-sheet thumbnails captured in a 720-pixel window,
below the breakpoint where the split hero stacks and the columns collapse. The
"35 of 36" and "40 of 40" readings were taken against pictures of a narrower
page than the product ships. Re-judged against half-scale desktop folds, the
vector scores 19 of 33. Nothing regressed to cause that.

## The claim came back — 2026-09-08, answered

`dentist`/`law` is inverted again, at 60%. Answering it against this file
rather than around it, because that is the whole point of having written it.

**Did the verdict change, or did something regress? Both, and the second one
matters.** The verdict moved from `different` (labels 449b9ddb) to `same`
(371f24fa). It moved because the pages moved: at `f3ce823` `dentist` opened on
`proof` and `law` on `facts` — exactly the difference this file predicted the
first-screen axis would create, and it did. Re-deciding the corpus under the
corrected gate rule put **both of them on `proof`.**

The corpus lost a difference it had. Why the gate allowed it:

    law vs dentist differ on: accent, action, compositions, leads_with,
                              mood, section_order
    highly weighted:          first_screen, mood
    satisfied via:            mood        <- and nothing else
    collides?                 No

`mood` alone cleared the "at least one weighted highly" requirement. What
`mood` does visibly for this pair is colour — teal against burgundy — and the
judging rule at the top of `pairs.json`, written blind and before any of this,
says a difference in colour alone is not a different site. **The rule added to
stop a pair passing on differences nobody sees let a pair pass on a difference
the judge had already ruled out.**

### Pre-registered, before the change is written

`highly_weighted()` should contain `first_screen` and nothing else — it is the
only axis in the vector whose difference cannot be expressed as colour. Under
`weight_of`, that is `HIGH_WEIGHT = 2.5`.

**Binding claim.** After that change and the re-decide it forces:

1. `dentist` and `law` do not both open on `proof`, and the pair leaves the
   inversion list.
2. Agreement on the **held-out third** does not fall. This is the first rule
   that set can honestly score — it was carved out of labels that were all
   available when the current rule was chosen, so it says nothing about that
   one, and everything about this one. It currently reads 5 of 5.
3. The scored same-trade figure is reported without `threadbare`, both before
   and after, so the exclusion cannot be what moves it.

**What would falsify it.** `dentist`/`law` still inverted, or the held-out
score falling while the tuning score rises — which is what fitting looks like
from the outside, and is the reason the set exists.

**What is expected and acceptable.** The scored same-trade figure getting
worse. Requiring `first_screen` to move on every build is a strong constraint
on a five-position axis with eleven fixtures, and there may not be room for it.
If the mean gets worse and agreement gets better, that is the trade this
project has said it wants: the number is not the target, the judgement is.

### Outcome — tried, refuted, not shipped

`HIGH_WEIGHT = 2.5` was applied, the corpus re-decided under it, and the result
checked against the three bound claims. It is reverted. All three, in order,
pass or fail:

**1. `dentist`/`law` no longer both open on `proof` — PASSED.** `dentist` moved
to `split` and `law` to `facts`. Side by side they are plainly two pages: one a
hard split, cream and serif beside a reception photograph; the other a full
photograph washed dark with white type over it. The reweighting did what it was
predicted to do for the pair it was predicted to do it for.

**2. The held-out third — NOT MEASURABLE, and the criterion was invalid.**
Every one of its six live verdicts was stale: the re-decide changed the fold of
eight of the eleven fixtures. Retiring them all leaves nothing to score.

That is not bad luck, it is the criterion being wrong, and the reason is worth
keeping. `HIGH_WEIGHT` feeds `rule_version()` and not `metric_version()` — the
distance is untouched by it, and `metric_version()` stayed `575db030` through
the whole change. **The held-out agreement score is a function of the distance.
Scored against the pages it judged, it would return exactly what it returned
before, whatever `HIGH_WEIGHT` is.** A held-out set of pair verdicts can score a
change to the ruler. It cannot score a change to the gate, because the gate
does not move the ruler — it moves which corpus gets produced.

So "does the held-out score fall" was never a test of this fix. What *would*
test a gate rule is how many pairs of the corpus it produces a stranger calls
the same site, and that needs fresh judging every time, guarded by
pre-registration rather than by holding verdicts back.

**3. The scored same-trade figure — WORSE, 38% → 47% identical.** Reported as
required. The pre-registration says a worse mean is acceptable if the held-out
score holds; it did not hold, it could not be taken.

### And the thing that decides it, which the pre-registration half-saw

"There may not be room for it" was closer to the truth than it reads.

A candidate must differ from **each** of the last ten sites on at least one
highly weighted axis. At 2.5 that set is `{first_screen}` alone, and
`first_screen` has five positions. Once the window holds all five, **no site can
satisfy the rule at all** — the gate stops being strict and starts being
unmeetable, every build past the fifth is an unresolvable collision, and the
corpus quietly fills with pages the gate would reject if anybody asked it.

Measured, not argued: the corpus re-decided under 2.5 has **eight of its
fifty-five pairs collide under its own gate**, including `dentist`/`salon`,
which the gate tried to separate, could not — every first-screen position was
already taken — and shipped anyway with the collision recorded and then
discarded, because `make_fixtures` keeps the config and not the `unresolved`
flag.

At 2.0 the required set is `{first_screen, mood}`: five positions by six moods
is thirty combinations against a window of ten, which is satisfiable. That is
why 2.0 works and 2.5 does not, and it has nothing to do with which of them
describes perception better.

`test_the_gate_is_satisfiable` now asserts that the highly weighted axes can
describe more distinct sites than the window holds. It fails on 2.5 in
milliseconds with the arithmetic in the message. The next attempt at this costs
a test run rather than a corpus re-decide, a re-render and a re-judge.

### What this does to the order of work

**The `dentist`/`law` regression stands unfixed, and it is blocked on axis two
rather than the other way round.** Tightening the required set needs more
high-visibility cardinality to tighten into. Type treatment is exactly that: it
adds a highly visible axis that is not colour, which is both what the pair needs
perceptually and what the rule needs arithmetically. The rule tightens after
axis two, not before it.

# Pre-registered — axis two, type treatment

Written 2026-09-08, before any axis-two code exists.

## The claim being tested

`agreement.unreachable()` currently reports **two** comparisons that no
reweighting of the existing axes can order correctly — both `hvac`/`roofer`,
judged one studio, against `contractor-bare`/`roofer` and
`contractor-bare`/`hvac`, judged two. The axes it moves on top of them are
`accent` and `hero_subject`: colour and subject, the two the judging rule says
cannot alone make a different site.

That is not a calibration gap. It is the vector having no way to say what the
judge is actually reading, which for those pages is *the same type set the same
way*.

## Binding claim, primary

**After type treatment lands, `agreement.unreachable()` reports zero.**

Pass or fail is that number and nothing else. Agreement rising while the blind
spot stays is NOT the claim being met — it would mean the axis moved some
distances around without giving the vector the thing it was missing.

## Binding claim, secondary

The axis has to be **real** before it counts: every treatment changes the first
820 pixels, no treatment is a pure function of another axis, and no treatment
is constant across the corpus. `tests/sitegen/test_axes_are_real.py` is what
says so, and the axis goes into its manifest in the same commit that adds it to
`AXES`.

## And the arithmetic it has to fix

`HIGH_WEIGHT = 2.5` was tried and reverted last commit because it left
`first_screen` alone in the required set — five positions against a window of
ten, so the gate became unmeetable. Type treatment is weighted 2.5, which puts
it in that set alongside `first_screen`. With five treatments that is
twenty-five combinations against a window of ten.

**So this pass ships both**: the axis, and the `HIGH_WEIGHT = 2.5` it makes
satisfiable. If `test_the_gate_is_satisfiable` still fails after the axis
lands, the axis is too small and the reweight goes back again — that is the
falsifier, and it is checkable in milliseconds before any corpus is re-decided.

## What is expected and acceptable

The scored same-trade figure may get worse. Nine axes describe more difference
than eight, so the mean rises for arithmetic reasons and means less, which is
why the mean is not the claim.

Tuning-set agreement is what I will iterate against. **The held-out seven are
not touched until the axis is finished**, and a held-out pair whose page moves
under it is retired with a reason rather than re-judged.

## Outcome — axis two landed, the claim FAILED

`agreement.unreachable()` reports **two**. The claim was zero. Pass/fail was
that number and nothing else, so this is a fail, and the reason is worth more
than the pass would have been.

    barbecue/restaurant-bare (same) contains restaurant-bare/restaurant-rich
        (different) — extra: action
    dentist/hvac             (same) contains restaurant-bare/restaurant-rich
        (different) — extra: action

**The axis is real.** It is in `AXES`, weighted 2.5, in the `FLIPS` manifest and
the first-screen list, swept by `test_no_axis_is_a_function_of_another`, and it
visibly separates three restaurants that all open on the same position:
`HUTCHINS BBQ` in heavy capitals, `The Heritage Table` in a sentence-case serif,
`I C H I K A` in capitals opened right out. The gate is satisfied by the corpus
it produced — zero of fifty-five pairs collide — and `HIGH_WEIGHT = 2.5`, which
was unmeetable last commit, ships with it: five positions by five treatments is
twenty-five against a window of ten.

**And as a term in the distance it currently makes the instrument worse.** The
pairs a person calls one studio share their GEOMETRY and differ in type
treatment, colour and subject — and the judge discounts all three:

    bare-trade / contractor-bare   "a photograph filling the screen washed
                                   dark, the name at the upper left in white,
                                   text under it, a star line beneath. The only
                                   thing that changes is whether the name is a
                                   serif or blocky capitals"
    dentist / hvac                 "same arrangement twice — one set in a serif
                                   and one in heavy capitals, teal against
                                   amber"
    barbecue / restaurant-bare     "One name is shouted and the other is spaced
                                   out, and the plates are different colours"

So the vector now carries a 2.5-weight term exactly where a person sees no
difference. That is the failure mode `accent` and `hero_subject` already had,
and the axis was added to fix a blind spot of that shape.

### The counterfactual, which is what makes this a fail rather than a shrug

Scored on the same corpus and the same labels with `type_treatment` removed from
the vector, `unreachable()` also reported zero at the point the claim was first
checked, and agreement was identical. The axis was not what moved the number
either way. It was the corpus and the labels changing underneath.

### What I am NOT doing about it

Not re-weighting. Thirteen verdicts is not enough to fit a weight against, and
that path was searched and rejected once already. The next question is what
`type_treatment` should be worth in the distance when the gate needs it at 2.5
to stay satisfiable — the two weights disagree for the first time, which is the
case `weight_of`'s `min()` was annotated as waiting for. That is a fork for
review, not something to settle by fitting.

## The `mood` weight — measured, and no claim registered

A round was scoped to lower `mood`'s weight below `HIGH_WEIGHT` so that it stops
satisfying "weighted highly". No pre-registration was written, because there is
nothing to predict: `mood` left `highly_weighted()` two commits ago when
`type_treatment` joined `first_screen` at 2.5, and lowering it now touches only
the distance.

Measured across four weights on the shipped corpus, agreement moves 21/36 →
30/36 and the held-out set moves 0/2 → 2/2, while **`unreachable()` stays at two
and the inversion set does not change at all**. The score is a function of the
weights; the defect is not. Recorded in `.reviews/slice-b-mood-weight.md` and
not made.

## Axis three — NOT pre-registered, and why

The round was scoped to pick the next axis against the blind spot rather than
against `BRIEF` §2.1's default order, and to pre-register it before coding.
Neither axis is registered, because the check says the blind spot is not
evidence about axes at all.

### What the two unreachable comparisons are made of

    barbecue / restaurant-bare       [SAME]
      differs on: accent, action, compositions, mood, section_order,
                  type_treatment
      why: "the same page: a food photograph edge to edge, the name over it on
            the left, a line of figures, two buttons in the same place. One
            name is shouted and the other is spaced out, and the plates are
            different colours"

    restaurant-bare / restaurant-rich  [DIFFERENT]
      differs on: accent, compositions, mood, section_order, type_treatment
      why: "both fill the screen with a food photograph, but one sets the name
            in capitals with the letters opened right out and the other in a
            large sentence-case serif — they read as a counter and a dining
            room"

The second pair's differing set is a **strict subset** of the first's — the
same five axes, and the first adds `action`. Both `why` texts describe three
food photographs filling the screen and rest the verdict on how the name is
set. One of those is called the same site and the other two different studios.

**They cannot both be right.** That is a judging inconsistency in my own
verdicts, and it is what produces both unreachable comparisons.

### So no axis can clear it

Clearing comparison one requires an axis where, simultaneously:

    axis(restaurant-bare) != axis(restaurant-rich)     the DIFFERENT pair
    axis(barbecue)        == axis(restaurant-bare)     the SAME pair
    axis(dentist)         == axis(hvac)                the other SAME pair

Nothing in the judged text names a property that separates Ichika from The
Heritage Table while joining Ichika to Hutchins — the whys describe all three
as a food photograph filling the screen with the name over it. Colour structure
would not do it, and neither would page architecture. **The requirement is
unsatisfiable because the labels contradict, not because the vector is thin.**

### And on colour structure specifically, the answer would be no anyway

Every one of the four "same" verdicts names the colour and dismisses it: "the
plates are different colours", "teal against amber", "the same rust-coloured
fill". Colour is the property the judging rule already discounts by name. An
axis built on it would be weighted into the distance and discounted by the
judge — the exact sequence that made type treatment's binding claim fail. That
is a prediction I am willing to be held to, and it is why colour structure is
not next whatever happens to the labels.

### The claim I am registering instead

Before any axis three: **state the missing judging rule and re-judge against
it.** The rule in `pairs.json` covers colour and subject and says nothing about
type setting, which is the gap these verdicts fell into.

**Binding claim.** After the rule is stated and every live verdict re-judged
against it — not just the contradictory ones — `agreement.unreachable()` is
recomputed and reported. If it reaches zero with no axis added, the axis-two
blind spot was a label artefact and the case for axis three has to be made
again from scratch. If it does not, what remains is evidence about the vector
and names the axis.

**Falsification.** Re-judging that moves the score without a rule stated in
advance. The rule goes in `pairs.json` first, then the verdicts, and the two
contradictory pairs are re-judged by applying it rather than by choosing.

**Held-out.** Untouched. No re-decide is involved, so no held-out verdict goes
stale and none may be re-judged — the rule applies to the tuning set only, and
the held-out three stay as the check on whatever comes out of it.

## Phase 1 found a defect in axis one, and it is pre-registered before the fix

Judging the remaining pairs turned up something that changes what the later
phases can be measured against. `first_screen` declares five positions. Two of
them render the same arrangement:

    above-the-fold markup differences between photo and facts: 2
       -<header class="hero first-photo type-quiet has-photo" id="top"
       +<header class="hero first-facts type-quiet has-photo" id="top"

**The class attribute is the only thing that differs.** The CSS then adds
`align-items:center`, a smaller heading clamp and wider gaps between the
figures — a setting applied to the same arrangement, which is exactly what the
type-setting rule written in Phase 0 says is not a different site.

Side by side, `barbecue` (`photo`) and `contractor-bare` (`facts`) are the same
page: a photograph filling the screen, the name in white at the left, text under
it, a line of figures. So is `bare-trade`, also `facts`.

This is `layout_bias` again — `BRIEF` §3 already records that one as "declares
itself structural and renders nothing above the fold" — in the axis the vector
weights heaviest at 2.5. Every distance involving a photo-versus-facts pair is
overstated by a quarter.

`test_a_first_screen_axis_changes_the_first_screen` passes it, because the
markup does change: the class name is markup.

### Binding claim

**A strengthened axes-are-real test, with the class attribute stripped from the
comparison, passes for every pair of first-screen positions.** Ten pairs, five
positions. It must fail on `photo`/`facts` before the fix and pass after it.

`facts` gets above-the-fold consequence rather than having its weight dropped,
because `BRIEF` §2.1 already says what the position is for — "the numbers first,
at a size that reads as the point of the screen" — and the renderer does not do
that. It leads with the name and puts the figures underneath, which is `photo`.

### Falsification

The strengthened test still failing for any pair after the fix; or the fix
changing the fold of a page whose position is not `facts`.

### What it costs, stated in advance

Rendering changes the pictures for `bare-trade` and `contractor-bare` without
changing any fingerprint, so no re-decide and no hash moves. But verdicts about
those two pages go stale, and **`bare-trade`/`contractor-bare` is the held-out
set's only "same" verdict.** Retiring it by rule takes the held-out set to zero
scorable comparisons. That is the cost of the repair and it is not a reason to
skip it.

### Phase 1 outcome — the repair held, the corpus did not grow usefully

The strengthened test failed on `('photo', 'facts')` before the repair and
passes on all ten position pairs after it. No fingerprint moved, so no
re-decide and no ruler or rule change; `bare-trade`/`contractor-bare` was
retired by rule as the pre-registration said it would be.

Held-out reached three scorable comparisons, short of the four to five the
phase asked for. The shortfall does not matter next to what judging showed:
**sixteen of sixteen live verdicts are exactly "do they share `first_screen`"**
— thirteen of thirteen before the repair, and the repair restored the relation
rather than breaking it. The generator has one arrangement dimension. Judging
more pairs adds determined verdicts, which makes agreement look better
supported while measuring the same single axis.

## Phase 2 — page architecture, and the claim registered before it is built

The evidence check has one answer and it is not `BRIEF` §2.1's ordering.
Colour structure remains predicted to fail — every "same" verdict that mentions
colour dismisses it — but that is not why page architecture is next. It is next
because **the instrument cannot validate anything until a second arrangement
dimension exists**, and page architecture is that dimension.

**Binding claim.** After page architecture lands and the corpus is re-decided:
the count of live verdicts determined by `first_screen` alone falls below the
total. One verdict that is not a restatement of the opening position is enough
to have broken the degeneracy; the number to report is how many.

**Falsification.** All verdicts still determined by `first_screen`, which would
mean the new axis changes nothing a stranger reads and is a fourth instance of
declared-but-not-in-force; or the strengthened position test failing for the
new axis's own values, which is the same defect caught earlier.

**Not claimed.** That `unreachable()` stays at zero — it is zero now and a
wider vector can only make superset relations rarer. And not that agreement
rises: a ninth axis raises the mean arithmetically, and `BRIEF` §3 says an axis
earns no credit for that.

### Phase 2 outcome — FAILED, as registered

    verdicts determined by first_screen alone, before   16 of 16
    verdicts determined by first_screen alone, after    12 of 12

Held to the claim as written. The axis is real — ten value pairs distinct with
the class attribute stripped, the hero provably untouched, availability
constrained by section count, 0 of 55 pairs colliding under the gate — and none
of that could have moved the number.

**The ground truth is read from the first viewport and this axis lives below
it.** Measured: `ledger` is byte-identical to `stacked` in a 1440x820 fold
capture, and `banded` and `gallery` differ only in the sliver of the next
section reaching the bottom edge, which reads as colour and is discounted by
name.

This corrects Phase 1's conclusion. The generator does not have one arrangement
dimension; **the instrument only looks at one screen**, so it can only validate
first-screen axes. Section edges and most of the signature device are below the
fold too, so phases 3 through 8 would build axes whose claims cannot be tested.
The run stops here.

# Phase A — the ground truth moves off the fold

Registered before the capture code is written.

## What is changing, and why it is not a tuning

Every blind verdict this project has taken was read from a first-viewport
screenshot. Axis three proved what that costs: page architecture is real —
ten value pairs render differently with the class attribute stripped, the hero
provably untouched, 0 of 55 pairs colliding under the gate — and its binding
claim could not have passed, because `ledger` is byte-identical to `stacked`
above the fold. Section edges and most of the signature device sit below the
fold too. The instrument can only validate first-screen axes.

So the definition of the ground truth changes: **what a stranger sees scrolling
the whole page**, not what the owner sees with the laptop turned around.

That invalidates every existing verdict — not because they were judged badly but
because the thing being judged is different. All of them are RETIRED with that
reason and fresh verdicts are taken. None is re-judged: a verdict taken under
one definition cannot be carried into another, which is the same rule that
retires a verdict whose page has moved.

## Binding claim

**The count of verdicts determined by a single axis alone falls below the
total.** Under fold judging it was 12 of 12, all `first_screen`. Report the
actual number, and report it for any single axis rather than only
`first_screen` — a ground truth that merely swaps which one axis decides
everything has bought nothing.

## Falsification

Still determined by one axis alone. That would mean the whole page carries no
more distinguishing information than the fold did, which would be a finding
about the generator rather than about the instrument, and the run stops on it.

## Also to report, either direction

* `agreement.unreachable()` recomputed cold — not assumed to match the fold
  reading.
* Whether the judging rules carry over. Colour discounted above the fold is not
  obviously discounted across a whole page: one accent in a hero is paint, and
  two-tone bands down a page are structure. Checked rather than assumed.
* Held-out at four to five scorable comparisons after the hash split. It has
  been emptied four times on too few judged pairs and that shortfall is not
  carried into the new definition.

### Phase A outcome — PASSED, and it carries Phase B

    fold judging        12 of 12 verdicts decided by first_screen alone
    whole-page judging  15 of 20, and no axis decides all twenty

Reported for every axis: `architecture` 18/20, `first_screen` 15/20,
`type_treatment` 8/20. No single axis decides everything, which is the check
that the change bought something rather than swapping which one term the labels
restate.

**Phase B settles with it.** Page architecture's binding claim — the count
decided by `first_screen` alone falls below the total — passes at 15 of 20. The
axis was already built and correct; the instrument was blind to it.

`unreachable()` recomputed cold against the new verdicts: zero.

One rule moved on re-check: a ground that ALTERNATES down the page is
arrangement, not colour. Colour is discounted where it is paint and counted
where it is structure.

# Phase C — the evidence names the signature device, not colour structure

`agreement.unreachable()` is zero, so no comparison is out of reach and no axis
is forced by a superset relation. The evidence is in the four "same" verdicts,
and it is unanimous:

    bare-trade / contractor-bare   shares: action, architecture, first_screen
    dentist / law                  shares: architecture, first_screen,
                                           hero_subject
    barbecue / restaurant-bare     shares: architecture, first_screen,
                                           hero_subject, leads_with
    restaurant-rich / salon        shares: architecture, first_screen

**Every pair a stranger calls one studio shares exactly `first_screen` and
`architecture`.** What they differ on — accent, mood, type treatment, action,
section order, compositions — is either discounted by the judging rules or is
what the business happens to publish.

So the judge's model is: same opening, same arrangement, same site. The vector
already holds both of those terms.

## Which rules out the next two items in §2.1's order

**Colour structure is contraindicated, and the whole-page re-check strengthens
that rather than weakening it.** Every one of the four pairs differs on `accent`
AND on `mood` and the judge called them one studio anyway. The one thing the
re-check did move — that an alternating ground is arrangement rather than paint
— is already carried by `architecture`'s `banded` value. A colour-structure axis
would add a term the judge discounts, which is exactly how type treatment's
claim failed.

**Section edges is contraindicated for a different reason: `architecture`
already decides it.** `ledger` separates bands with rules, `banded` with a change
of ground, `gallery` with whitespace alone. A separate axis for the separator
would be a second decision on one thing, which is how `layout_bias` came to be a
function of `mood`.

## What the evidence does name

Four pages that share an opening and an arrangement and have **nothing else
designed on them**. Every other difference is paint, lettering, or what the
business published. The signature device — §2.3, exactly one per site, justified
against the business — is the only remaining lever that is designed, is not
colour, is not lettering, and is not the arrangement.

## Binding claim

**After the device lands, at least one pair that shares `first_screen` AND
`architecture` is judged DIFFERENT.**

That is the rule the whole-page verdicts currently follow without exception, and
the device exists to break it. Reported as the count: how many of the pairs
sharing both terms are judged different, out of how many such pairs.

## Falsification

Every pair sharing those two terms still judged the same site. That would mean a
single designed mark does not change what a stranger reads, which is a real
finding about §2.3's premise and the run stops on it.

## Also to report, either direction

`weight_of()`'s `min()` was annotated with the prediction that this is the axis
where visibility and decidedness disagree in the OTHER direction — a strong,
decided choice that often sits below the fold. Whole-page judging is what makes
that testable for the first time. Report whether it held.

### Phase D outcome — PASSED, and narrower than it looks

Two pairs shared `first_screen` and `architecture` after the re-decide and both
are judged different: `barbecue`/`restaurant-bare` and
`bare-trade`/`contractor-bare`. **Both turn on `quote`**, the one device that
takes a whole screen. The others are bands of ordinary height. So the claim
passes on the strength of one device rather than of devices in general, and the
rule written into `pairs.json` says so.

The `min()` prediction held. `signature` is `VISIBILITY` 1.0 against
`DECIDEDNESS` 3.0 — the first entry to extend that scale past `first_screen` —
and `min()` suppresses it to 1.0, which is the disagreement the comment
predicted, in the direction it predicted.

**And the corpus ran out.** Zero "same" verdicts across twenty pairs; agreement
is 0 of 0. §2's requirement is met on these eleven fixtures and the instrument
cannot validate a further axis on them. Phase E is not built for that reason.

# Phase 1 — widening the corpus, and the binding claim before any judging

Registered 2026-09-08, before any new-fixture screenshot has been looked at.

Eight real businesses added via `tools/make_fixtures.py` (no `--redecide`):
`barbecue-rich` (Hard Eight BBQ), `restaurant-casual` (Whisk Crepes Cafe),
`roofer-rich` (Bert Roofing), `hvac-rich` (Baker Brothers Plumbing, Air
Conditioning & Electric), `hvac-second` (One Hour Air Conditioning & Heating),
`salon-rich` (Drybar), `dentist-rich` (Plano Dental Loft), `law-rich` (Kraft &
Associates). All resolved through the live Google Places / Yelp / OSM
directories with real ratings, review counts and photographs — no invented
material. Weighted toward the buckets that were already crowded: `trade` +3,
`food` +2, `desk` +1, `groom` +1, `care` +1.

Confirmed before anything else: the existing eleven fixtures' fingerprints are
byte-identical to their pre-widening values (checked field by field against
what was printed and pinned before this round). No `--redecide` ran; the
frozen `design_direction` replayed for all eleven.

## Binding claim

**At least one pair in the widened nineteen-fixture corpus is judged "same"
from a whole-page screenshot, so `agreement.score()` has a nonzero
denominator again.** Judged blind, applying the rules already stated in
`pairs.json`'s `_why` — colour and subject discounted unless structural
(an alternating ground), type setting discounted unless it moves the type or
changes what shares the screen with it, a signature device discounted unless
it changes the page's proportions.

## Falsification

Every pair — new against new, and new against the original eleven — still
judged "different". That would mean §2's requirement holds more robustly than
expected on a corpus of nineteen real small businesses across five trades, and
§2.2 still could not be validated. If that happens: report the actual count
(zero), restore nothing, re-pin nothing that depends on judging, and stop
before Phase 2.

## Also to report, either direction

Whether `test_the_corpus_no_longer_has_a_pair_the_gate_would_reject` — a
pinned all-pairs static check — still holds now that the corpus (19) exceeds
the gate's rolling comparison window (`WINDOW = 10`). Investigated before
judging, separately from the binding claim above: five same-trade pairs
collide statically. Every one has fewer than four axes moved, or moves four
without a structural axis or a required-high axis among them — the rule
working correctly on pairs it was never asked to compare live, because they
are more than ten builds apart and the gate only ever compares a new site
against the last ten. This is a limit of the window, not a bug in the
collision rule, and not something a threshold change fixes. Reported and the
test's assertion corrected to state what the gate actually guarantees, rather
than either loosened to hide the finding or left red as an unexplained
failure.

### Phase 1 outcome — PASSED

Five same-trade pairs judged "same" out of thirty-two live verdicts:
`barbecue`/`barbecue-rich`, `dentist`/`dentist-rich`, `hvac-rich`/`roofer`,
`hvac-rich`/`roofer-rich`, `roofer`/`roofer-rich`. Agreement is computable
again at 133/135 (tuning 84/84, held out 6/6), `unreachable()` is 0. Ruler and
rule unchanged (`d2f37ed7` / `95f4d93e`) — no `--redecide` ran, and the
eleven original fixtures' fingerprints were confirmed byte-identical before
and after. See `.reviews/slice-b-phase-1-widen.md` for the full record,
including a real claims-gate-observability bug found and fixed along the
way (two initial business picks had unverifiable tenure claims in their own
site copy; the gate correctly rejected them and `make_fixtures.py` was
silently freezing the ungated direction anyway — fixed at the source, and
the two businesses replaced with different real ones).

The single-axis degeneracy check is restored
(`test_no_single_axis_decides_every_verdict`): no axis decides all
thirty-two verdicts.

Proceeding to Phase 2 (§2.2, palette from the business's own photographs).

# Phase 2 — palette from the business's own photographs (§2.2)

Registered before `app/site/palette.py` is written.

## What "sampled from their own photographs" actually means here

`§2.2` asks to sample dominant colours from the hero and gallery photographs.
That data already exists and is already corroborated: the vision pass records
`dominant_colours` — up to four real hex values per photograph, strongest
first, validated (`_is_hex`) — on every photo of every fixture, right now.
Building a second colour-extraction pipeline (a pixel sampler over cached
JPEG bytes) would duplicate work the vision call already paid for and
verified, and would need a new image-decoding dependency this project has
deliberately kept at two runtime deps for its whole life. Reading the field
that is already there is the smaller, more honest change, and it is `#2.2`'s
own instruction read literally — "sample dominant colours" is a description
of the vision schema's own docstring, not a hint to reimplement it.

"Prefer a declared brand colour over a sampled one": there is no declared
brand-colour field anywhere in this system's data model. The nearest
corroborated equivalent is a photograph the vision pass flagged
`is_logo_or_badge` — a business's own logo or signage, which is the one
photograph in the set that IS the brand rather than a picture of the
premises. When one exists, its `dominant_colours` are treated as the
strongest candidates; otherwise the hero and the best two or three gallery
shots are used, exactly as `§2.2` says.

Each sampled hex is mapped to the nearest named entry in
`theme.ACCENT_TUNING` by hue distance, with a saturation floor to skip
near-neutral colours (shadow and highlight greys that a photograph's
`dominant_colours` list is often padded with, which are not an accent
anybody would call a decision). This keeps `accent` a closed enum exactly as
it is today — every value still runs through `Theme.recoloured()`, which
already derives saturation/lightness from the theme and chooses a
contrast-safe ink by trying every candidate and keeping the one that passes.
No new contrast machinery; the existing repair is total.

## Binding claim

**The same-trade mean distance improves** — same-trade pairs currently
share an accent because the mood table maps their trade to one colour by
default, not because their photographs actually look alike. A palette drawn
from what each business's own photographs actually show should pull
same-trade businesses apart on this axis for a reason grounded in their
material rather than in a shared fallback.

## Falsification

The mean gets worse, or is unchanged within measurement noise. Either is a
real result to report, not a bar to clear before shipping — `BRIEF` §3
already says an axis earns no credit for raising the mean, and the reverse
holds too: worse is not disqualifying on its own if agreement holds, but it
would mean this specific mechanism did not do what it was built to do, and
that has to be said plainly rather than routed around.

## Also to report, either direction

The count of fixtures matching a forbidden default from `§2.4`. Two currently
match `warm cream + serif display + terracotta` (`barbecue`, `barbecue-rich`).
Not the primary claim, because barbecue's own photographs are genuinely
brown/rust-toned (firewood, smoked meat) — a palette faithful to the real
photographs could sample terracotta again for exactly the right reason, and
treating that as a failure would be asking the feature to override real
material rather than represent it.

## What this costs

A re-decide. Offering a new signal in the prompt changes what the model can
answer even where the frozen answer would otherwise replay unchanged for a
business whose sampled accent matches what it already chose — the whole
corpus has to be re-decided to find out which, so every fold moves,
verdicts about moved pages are RETIRED (not re-judged), and the held-out set
is retired-not-re-judged the same way. Restated because it bears repeating
before it happens: this is exactly the cost stated as the reason this phase
was not built before the corpus was widened.

### Phase 2 outcome — PASSED, harder than asked

Same-trade mean improved 49% identical to 45%. The count of same-trade pairs
a stranger calls one studio went from five to ZERO among the ten checked —
every prior "same" verdict broke apart, including the trade trio that used to
render one page in three colours. Not credited to palette sampling alone: the
whole identity call was re-asked and the diversity gate ran fresh regardless
of the prompt; no control redecide was run to isolate the two.

Secondary metric, forbidden-defaults count: held at two, membership moved
(`barbecue` escaped, `restaurant-rich` matched) — both for the same honest
reason, real material.

Agreement is 0 of 0 again, for the same reason as before Phase 1. Full record
in `.reviews/slice-b-palette.md`, including a real API-credit exhaustion hit
mid-redecide, its recovery, and a second `make_fixtures.py` claims-gate bug
found and fixed along the way.

# Phase 1 (this project's Slice B close-out) — the batched redecide

Registered before `make_fixtures.py --redecide` is run.

## What's bundled

1a. `WINDOW` widened 10 -> 60 (`app/store/fingerprints.py`), so the live gate
compares each new site against the last 60 built rather than 10 — wide enough
to cover all nineteen fixtures with 3x margin, still comfortably satisfiable
(room=125 combinations of the three axes it already required, now vastly
larger with 1d's addition). `restaurant-bare`/`salon-rich` — a restaurant and
a salon differing on only mood, accent and hero_subject, an unambiguous
collision — is the confirmed defect this fixes; the redecide is what makes
the fix take effect on the shipped corpus rather than only on future builds.

1d. The typeface pair, `app/site/theme.TYPEFACE_PAIRS` (20 named entries),
chosen by the identity call and validated against that closed set exactly
like every other axis. Added to `fingerprint.AXES`, weighted
`VISIBILITY=3.0` (renders on the first screen — the name is set in the
display face) and `DECIDEDNESS=3.0` (chosen outright, no material
constraint at all), and to `REQUIRED_HIGH` on the strength of evidence
already collected rather than awaited: multiple blind verdicts, taken before
this was ever an axis, named the typeface directly as the reason two pages
read as one ("the same serif", "one set in a serif and one in heavy
capitals"). Proven in force by `test_no_axis_is_a_function_of_another`
(caught it as a function of `mood` on the first attempt — the sweep never
varied it independently until fixed) and
`test_a_first_screen_axis_changes_the_first_screen`.

1e. `signature_why` — already generated by the identity call, previously
reaching nowhere — now persisted in the opening version's notes and surfaced
in the workspace panel, never in the rendered page. Proven by two tests: it
round-trips through a rebuild without re-asking, and the exact justification
text is absent from the rendered HTML.

## Binding claims

**Primary (1a).** `test_no_collision_survives_anywhere_in_the_corpus` passes
after the redecide — no pair anywhere in the corpus, any trade, collides
under the gate's own rule. This is the one the whole redecide exists to
satisfy; if it does not, 1a's fix did not work and the run stops before 1b/1c.

**Secondary, reported either direction, not a bar to clear.** The same-trade
mean will move (a tenth axis, `typeface`, describes more difference — `BRIEF`
§3 gives an axis no credit for raising it, and by the same logic no blame for
it moving at all as a side effect of a bugfix). Whether `dentist`/`dentist-rich`
and the roofer/HVAC trio — the closest same-trade pairs on record, previously
judged "same" — still read as one studio once they also carry an independent
typeface choice is worth checking directly against the new screenshots rather
than assumed either way.

## Falsification

`test_no_collision_survives_anywhere_in_the_corpus` still failing after the
redecide — meaning 60 is not enough, or `identity.decide()`'s retry/perturb
sequence cannot find a free combination in practice even though one exists
arithmetically (a `MAX_RETRIES` or `perturb()` problem, not a `WINDOW`
problem). If that happens: stop, report which, and do not widen `WINDOW`
again without checking why the arithmetic isn't converting into practice.

## Outcome — 2026-09-08

**Primary claim PASSED.** `test_no_collision_survives_anywhere_in_the_corpus`
passes after the redecide. No pair anywhere in the 19-fixture corpus, any
trade, collides under the gate's own rule.

**Secondary claim, reported as bound.** Same-trade mean moved from 55%
distance (pre-redecide, `d2f37ed7`) to 56% distance / 44% identical
(`a762bcc9`) — essentially flat, one point of movement on an added axis,
consistent with `BRIEF` §3's stance that an axis is judged by whether it
raises agreement, not by whether it moves this number.

The direct check went further than the secondary claim asked. Sixteen pairs
were judged blind against the redecided rendering — not just the two named
candidates (`dentist`/`dentist-rich` and the roofer/HVAC trio), but the
closest pair the corpus has ever produced under any ruler. **All sixteen
came back DIFFERENT**, including `dentist`/`dentist-rich` and every pair
built on `hvac-rich`, `hvac-second` and `roofer-rich`. Zero same-trade or
cross-trade collisions found among the pairs checked. Agreement stays 0 of 0
— not because too few pairs were checked, but because the pairs most likely
to collide, checked carefully, do not.

One pair (`bare-trade`/`dentist`) was briefly misjudged "same" from the
shrunk contact-sheet thumbnail and corrected before being written to
`pairs.json`, once the actual rendered markup showed a hairline rule above
every section and a narrower text measure on one page and not the other. See
`.reviews/slice-b-phase-1.md` for the full account.

# Round 3, Phase 1 — the review-count contradiction bug

`hvac` (Milestone Electric Air Plumbing) ships a page asserting both "over
20,000 5 star reviews" (verbatim from its own published `about` text — real,
so `render.unsupported()` correctly lets it through) and "6203" (the
corroborated Google review count, `Material.reviews`, printed eight times).
Confirmed directly against the built page before writing any fix: `page.count
("6203") == 8`, `page.count("20,000") == 1`, and the surrounding text is
exactly the "about" sentence named in the design review. `BRIEF §4`'s "no
unverified fact ships" invariant has nothing to say about two VERIFIED facts
disagreeing — `unsupported()` checks provenance (did they say this), never
consistency (do their own numbers agree with each other) — so this is a real
gap, not a mis-classified instance of an existing check.

**Corpus-wide scan before deciding anything**, per instruction: every
fixture's `about` text, block text, and services list, searched for a number
immediately followed by "review(s)" (optionally "5-star review(s)") and
compared against that fixture's `Material.reviews`. `hvac` is the only hit —
20,000 claimed against 6,203 corroborated, roughly 3.2x over. A second,
broader scan for "years"/"customers"/"clients"/"jobs completed" numeric
claims found two more mentions (`dentist`: "10 years"; `law-rich`: "100+
years"), but this system has no structured founding-date, customer-count, or
jobs-count field anywhere to reconcile either against — so there is nothing
to check them against, and nothing to fix; disclosed rather than silently
ignored. Also noted, out of scope for this fix: `hvac`'s own block text says
"Since November 2022... for over 13 months", which was consistent at
scrape time but reads as stale relative to today — a staleness issue
already disclosed in `.reviews/review/READ-ME-FIRST.md`'s "Numbers not to
trust" section, not a same-page contradiction between two facts this system
corroborates.

## The resolution rule

**Suppress the contradicting sentence, never rewrite it.** When a sentence
in free text (`about`, or a block's `text`) states a review count differing
from `Material.reviews` by more than `max(10, 15% of reviews)`, the whole
sentence is dropped before it reaches any section builder — applied once, in
`material_from_brief()`, so every section that reads `about`/`blocks` sees
already-reconciled text rather than needing its own check. The corroborated
number itself is never touched. Chosen over the other two options BRIEF
offered: rewriting the sentence would mean the system authoring prose, which
every invariant in §4 already forbids; refusing the whole block would drop a
real, true opening sentence ("What our customers say about us are very
important") along with the one false one, which is a worse page for a
smaller reason.

## Binding claims

**Primary.** A new standing test
(`tests/test_no_contradicted_fact_ships.py`), corpus-wide, holding the
invariant rather than the one string: no fixture's rendered page states a
review count that contradicts `Material.reviews` by more than the tolerance
above. Confirmed to FAIL against the current `hvac` page before the fix
(reproduced by calling the old, unreconciled `material_from_brief` path) and
PASS after `app/site/contradiction.py` is wired into `material_from_brief()`.

**Secondary.** No redecide required — this changes what free text a page
prints, not a design-system decision or an axis value, so no fingerprint
value moves and `test_no_axis_is_a_function_of_another` and the fingerprint
tests are unaffected.

## Falsification

If the standing test cannot be made to fail against the unfixed code (i.e.
the "before" run already passes), the reproduction is wrong and the claim
that this is a live defect needs re-checking before anything is fixed. If
fixing it requires touching more than `material_from_brief()`'s construction
of `about`/`blocks` (e.g. if a section builder reads raw block text from
somewhere `material_from_brief` does not control), that is a sign the single
point of reconciliation was the wrong design and each section would need its
own guard — report that rather than patching around it.

## Outcome — 2026-09-09

**Primary claim PASSED, exactly as predicted.** With the fix reverted (a
scratch checkout of the unfixed `render.py`), both new tests fail: the
corpus-wide sweep names `hvac` printing "20,000" against a corroborated
6203, and the direct fixture test shows "20,000" still on the page. With
`app/site/contradiction.py` wired into `material_from_brief()`, both pass —
"6203" still prints unchanged, "20,000" does not. One point of
reconciliation in `material_from_brief()` was sufficient; no section
builder needed its own guard, confirming the design held.

**One false positive caught and fixed before this was reported passing.**
The standing test's own tag-stripped page scan first failed against `law`,
matching "2026" (the end of an unrelated offer-card heading, "North
Texas's Choice for 2026") glued across a real newline to "Reviews" (the
next section's heading) — an artifact of stripping HTML tags to a single
space while the source's own line breaks between block-level elements
survive as literal newlines. Fixed by requiring the number and
"review(s)" sit on one line (no-newline whitespace, in both
`contradiction.py` and the test) rather than loosening the check. This
confirms the corpus-wide scan done before writing the fix was still
correct: `hvac` was the only genuine review-count contradiction; `law`'s
"2026" was never a real hit, only a test artifact.

**Secondary claim held.** No redecide needed — `make check` (840 passed)
is green with only `hvac`'s render snapshot moving (content-only,
regenerated and reviewed by hand: the sentence claiming 20,000 reviews is
gone, the surrounding sentences and every other fixture's bytes are
untouched). No fingerprint value, axis, or gate collision count changed.

# Round 3, Phase 2 — the rendering defects Slice G found, and whether they were real

Three findings from the sampled design review, named in the round's own
instructions: `law`'s nav overlapping the attorney's photograph, a
paragraph overlapping/hidden behind a stats banner, and a duplicated CTA
button cropped at the mobile viewport edge on `hvac`/`restaurant-rich`.
The instructions were explicit to confirm each before changing anything —
this record is unusually exploratory because two of the three did not
hold up as stated, and one review artifact was a defect in the review's
own tooling, not the site.

## What was actually true, checked one at a time

**Nav-over-photo: real, confirmed directly.** `law`'s desktop screenshot
shows "What we do / Reviews / About / Hours / Visit" printed across the
attorney's face with no scrim — legible in places, illegible in others.
Root cause: `.hero.first-proof` deliberately turns its `.veil` scrim off
(`app/site/styles.py`, "the type never sits over the photograph at all")
because its own type sits below a narrow photo band, on the theme's own
ground — a real, sound design choice for the TYPE. Nobody carried the same
reasoning to the NAV BAR, which is `position:fixed` and floats over
whatever is at the top of the page regardless of what the hero does below
it — for `first-proof`, that is exactly the photo band. Every other
first-screen position either has no photo up top (`first-type`) or darkens
the whole photo it sits on (`first-facts`, the default `.veil`) or gives
the bar its own ground explicitly (`first-split`). `first-proof` alone had
neither.

**"Hidden behind a stats banner": did not reproduce at the stated
location, but a real bug was one screen-height away.** Grepped the exact
quoted sentence ("If you or a loved one has been...") — it belongs to
`law`'s "Our Mission" feature block, nowhere near the stats band or
"Practice Areas". No CSS collision exists there; screenshotted and
inspected directly, twice, at different scales. But `_review_card`/
`_review_feature` both truncate a quote with `text[:340]` — no word
boundary, no ellipsis — and `law`'s second testimonial is 1074 characters,
cut mid-word: "Snelling Law Firm was outta[nding]" becomes "...was outta".
That is very likely what a vision model described as "cut off" text,
mis-located relative to which section it was reading. Verified: the
character count analysis confirms the exact cut point; the fix (a
word-boundary truncation with an ellipsis) is applied regardless of
whether it was the literal thing described, because it is a real,
separately-confirmed defect either way.

**"Duplicated CTA cropped at the mobile edge": the SPECIFIC finding was a
tooling artifact, not a site defect — but chasing it down surfaced a
different, genuine CSS bug in the same family.** Reproduced the crop with
`tools.contact_sheet.shoot()` at width 390 exactly as the design review
would have captured it. Then reproduced the SAME markup at a genuinely
emulated 390px viewport (Chrome DevTools Protocol,
`Emulation.setDeviceMetricsOverride`) and the crop was GONE — "Book a
table" wrapped cleanly, "Get directions" sat fully on screen. Instrumented
the page to print `window.innerWidth` from inside the actual headless
capture: it read **500**, not 390, regardless of `--window-size=390,844`.
Binary-searched the boundary (390, 450, 500 all clamp to 500; 550 measures
550 correctly) — Chrome's headless `--screenshot` CLI mode has an
undocumented floor of 500 CSS pixels that nothing in the available flags
changes. Every "mobile" screenshot this project has ever taken — the
contact sheet, and by extension every Slice G design review, since
`design_review.py` reuses `shoot()` — was laid out for a viewport 110px
wider than labelled, then the output image was cropped to 390px,
producing exactly the visual signature of a cropped button whether or not
one existed.

Having built a genuine sub-500px capture path (`_cdp_session`,
`evaluate_in_page`, `CDP_MIN_WIDTH` in `tools/contact_sheet.py`) to check
this properly, ran a DOM-level collision probe across the whole corpus at
the three review widths rather than trusting a second round of screenshots
read by eye. It found a real instance of the SAME defect CLASS the design
review named, just not on the fixtures or in the shape originally
reported: `law-rich`'s hero actions row (`Call ... / Get directions`)
generated the identical "second button clipped" signature at a REAL
390px viewport, for a reason unrelated to any screenshot tool.
`.hero.first-proof .proof` sets `grid-template-columns:repeat(auto-fit,
minmax(190px,1fr))` — a genuine 570px minimum at three items — and
nothing constrained the hero's own grid track to less than its content's
minimum, so the whole hero (and everything in its `.wrap`, including the
actions row) grew to 570px on a 390px viewport instead of wrapping the
proof row. Fixed with one declaration, `.hero .wrap{min-width:0}` —
overriding the grid-item default that let a child's minimum content width
dictate the parent's own size.

## Binding claims

**Primary.** A new standing test
(`tests/test_no_element_collides_with_another.py`), corpus-wide at the
three review widths, using the CDP path so "mobile" is a genuine 390px
rather than the CLI flag's silent 500px: no interactive control is
clipped by the viewport edge, and no text-bearing element is painted over
by another (excluding `position:fixed` chrome, which legitimately floats
above scrolled content by design). Confirmed to catch the `law-rich`
defect before the `min-width:0` fix and pass after, across all 19
fixtures at all 3 widths.

**Secondary.** No redecide required for either fix — both are CSS-only;
no `compositions`/`section_order`/any axis value changes as a result.

## Falsification

If the "hidden behind stats banner" claim could not be located anywhere
on the page after a direct text search, and no other genuine defect
turned up nearby, that would mean the design review hallucinated a defect
with no basis at all — worth flagging as evidence the sampled review's
signal-to-noise is worse than the earlier pass estimated. That did not
happen: the truncation bug is real, confirmed independently of the
vision model's read, and plausibly what was actually seen.

If the "duplicated CTA cropped" finding turned out to be real at a
genuinely emulated mobile width, the tooling-artifact explanation would
be wrong and the right fix would have been a CSS change on `hvac`/
`restaurant-rich` directly, not a capture-tool fix. It did not reproduce
at a true 390px viewport on either named fixture — the crop was fully
explained by the 500px floor, confirmed by measuring `window.innerWidth`
directly inside the same headless process.

## Outcome — 2026-09-09

All three claims resolved as described above before any speculative fix
was applied. Two genuine CSS defects fixed (`first-proof`'s missing nav
scrim; the quote-truncation mid-word cut); one genuine tooling defect
fixed (`shoot()`'s silent 500px floor, now routed through a real DevTools
Protocol path below `CDP_MIN_WIDTH`); one reported finding did not
reproduce as stated but led to finding a second, real instance of the
same underlying defect class on a different fixture. `make check` green
after the fix (841 passed) — see `.reviews/<phase>.md` for the literal
tail.

**2c, re-run against the fixed tooling: confirmed.** Re-ran
`tools/design_review.py` on the same four sampled fixtures (12 model
calls). `law`'s nav-over-face finding is gone from both the desktop and
mobile read this time — nothing in either mentions the navigation
overlapping the photograph. The quote-truncation artifact ("outta") does
not appear anywhere in the new pass. `restaurant-rich`'s mobile read
still names the duplicated `Book a table`/`Get directions` buttons but
now purely as a hierarchy/spacing observation about the sticky bar
existing at all — no mention of either button being cropped or
partially visible, which is the tooling-artifact explanation confirmed
independently a second way. Two NEW mentions appeared this round —
`hvac` and `law` mobile both note the sticky "Call us" bar overlapping
the stats band's numbers near the bottom of the initial viewport.
Checked directly: this is the same, expected property of any
`position:fixed` bottom bar covering whatever document content happens
to be scrolled into its footprint at a given moment — present on
essentially every site with a persistent mobile CTA bar, not a layout
defect, and excluded from the standing collision test on that basis (see
`test_no_element_collides_with_another.py`'s own filter for `.callbar`).
Noted here rather than silently dropped, since it is a real thing the
review saw, just not one this pass treats as a defect.

One unrelated finding surfaced in passing and flagged separately rather
than fixed here (out of scope for this phase): `law-rich`'s stats band
prints "Dishes on the menu" as its third stat label — a restaurant-trade
label applied to a law firm.

**Correction, written during Phase 3**: this turned out not to be a
cosmetic label bug at all — see Round 3, Phase 3 below. Fixed there,
along with the same defect on four other non-food fixtures.

# Round 3, Phase 3 — acting on the content census

BRIEF §5, Slice D item 2: "fix what it exposes." Four items, named in the
round's own instructions (3a-3d), each decided on its own evidence before
any code was written, per fixture where the numbers disagreed with intuition.

## 3a — a business's own photography, never once selected

`own_site_photos` measured 0 of 4 ever used, corpus-wide, before this.
`Material.images` put Google's photos first — "nearly always better than
what the business put on its own site" — and every section beyond the
hero spends from the pool in plain first-N order, so Google's larger
pool never ran dry before reaching the business's own.

**Decision: prefer AND reserve, not one or the other.** `Material.images`
reversed to own-first, Google-second — this is what "reserve" actually
means for a first-N consumer, since order is the only lever those
sections have. Hero additionally got a real, small `own_photo` scoring
term (`HERO_WEIGHTS["own_photo"] = 0.2`) — real weight, not just a
position — but calibrated to only break a close tie, never override a
resolution/aspect/quality gap Google's photo actually wins. Checked
directly against all 19 fixtures with own photos: zero fingerprint values
changed anywhere (`hero_subject` included) — Google's photos were simply,
verifiably, better on the terms this scores, everywhere they were tried;
this pass earns its "prefer" credit at the gallery/offer-card level, not
by moving what leads the page. One test fixture (`test_proxied_
photographs_are_offered_at_several_widths`) had accidentally been relying
on Google-first order to test something unrelated (proxied-photo srcset
widths) — fixed by clearing its own-site photos, not by weakening the
new preference.

Content-only: `make check` (post-fix, pre-redecide) showed zero
fingerprint moves, only render-snapshot drift on the fixtures that
actually had own photos. Regenerated.

## 3b — `menu_media`, extracted since Slice A, read by nothing

`Material` never had a `menu_media` field at all — `material_from_brief`
dropped it on the floor before any section builder could have read it
even if one tried. Added the field; `_menu()` now uses the first entry
(never more — one document, not several) as a direct link (PDF) or an
embedded image, appended after parsed `menu_items` when there are any,
or as the section's only content when there are not.

Also gated behind `trade_kind == "food"` — see 3c below for why that
guard exists and what it was already protecting `_stats()` from.

**Moves the corpus.** `restaurant-rich` has `menu_media` but no parsed
`menu_items` — `_menu()` returning content for the first time added a
`menu` section to its `section_order`/`compositions` that was not there
before. Batched into the round's one redecide (see close-out below).

## 3c — the real bug 3a's investigation surfaced: `menu_items` on a law firm

Not one of the four named items, but found while confirming 3b touched
nothing it shouldn't: `law-rich` was rendering "12 dishes on the menu" in
its stats band, at prices of $812, $55, $49 — each one actually a line
off the firm's own "Notable Results" settlement-amounts page.
`extract_menu_items` (BRIEF era, `app/workbench/extract.py`) anchors on
ANY bare dollar-amount pattern as the one unambiguous signal of a priced
item — sound for a restaurant, and it does not know what business it is
reading. Scanned the whole corpus for the same shape: **5 of 19
fixtures** had it — `law-rich` (settlement amounts), `dentist` (a
promotional "Special $500"), `hvac-rich` (a coupon, "10% Off... $109"),
`hvac-second` (a financing banner, "$0 DOWN"), `roofer-rich` (an
insurance estimate line, "$20,783.75") — every one a false positive, none
a real menu.

**Fix: gate on `trade_kind == "food"`, at both places `menu_items`
reaches the page** (`_stats()`'s tile, `_menu()`'s whole section) —
`plan_for`'s own architecture (a section's presence is read from whether
its builder actually produced HTML, never re-derived) means gating the
builders was sufficient; no separate plan-vs-page reconciliation needed.
Confirmed the standing test fails against the reverted guard and passes
restored (`test_a_non_food_trades_stray_menu_items_never_render`); a
sibling test confirms real food-trade menus are untouched.

This closes the exact defect a previous phase's design review sample
would have flagged as "mislabeled stat" and had already spawned a
follow-up task for — dismissed as superseded once this landed (see
above).

## 3c (as asked) — the `block:feature` 4-block cap

The single biggest drop in the census (40 blocks on one fixture alone).
Checked what items 5+ actually were before touching the number, fixture
by fixture: `law-rich` (14 total) is a clean 14-question FAQ, substantive
writing cut off arbitrarily; `barbecue`, `hvac-second`, `roofer-rich`
(12-14 each) are real catering/service/FAQ detail. Some IS noise —
`dentist-rich`'s items 7-9 are customer names ("Melody H.") that belong
in reviews, not features — but that noise starts around item 7 on every
fixture checked, not item 5.

**Decision: raise 4 -> 6** (`FEATURE_CAP` in `app/site/render.py`).
Recovers most of the genuine loss (two more rows everywhere it applies)
while staying short of where the miscategorised content starts on the
fixtures this was checked against — disclosed as a fixture-checked
finding, not a guarantee for content this has not seen; the actual
defect (a scraper filing testimonials as "feature") belongs to Slice D's
provenance work, not to this number.

Effect on page length: +1-2KB on the affected fixtures (verified
directly, e.g. `law-rich` 73037 -> 74205 bytes). Effect on
`test_the_corpus_matches_only_the_forbidden_defaults_we_know_about`:
none — re-ran it immediately after the cap change alone, before the
redecide, and it still passed unchanged. Content-only by itself; no
fingerprint value moved from the cap in isolation.

## 3d — `fact:address`/`fact:phone`, dropped as "no source verified"

Read the actual `facts` array for every dropped instance (19 total,
corpus-wide) rather than guessing at the shape of the problem:

    7  single, uncontested Google Business Profile claim (never Yelp
       alone, never their own site alone)
    12 genuine CONFLICT — two sources actually disagree (a law firm's
       Google phone number and its own site's number were different
       numbers entirely)

The 12 conflicts are the majority and are correctly dropped —
`app/workbench/corroborate.py`'s own stated rule is "never presented as
fact" when sources disagree, and recovering those would mean guessing
which source is right, which is exactly what the module exists to
refuse. The 7 single-Google cases are different in kind: a GBP listing
is verified against the business by Google itself (mail, phone, or video
verification) before it goes live, which is a real corroboration, just
not an "independent second source" in the sense the rule was written
for.

**Decision: a lone Google Business Profile claim now verifies address
and phone on its own** (`_GBP_ALONE_IS_ENOUGH`, scoped to exactly these
two fields — not extended to every field on the strength of two
examples). Standing tests added and confirmed against the reverted code
(`test_a_lone_google_claim_verifies_address_and_phone`); the two
existing tests that encoded the OLD blanket rule
(`test_one_source_is_only_unverified`,
`test_the_same_source_twice_does_not_corroborate_itself`) were updated
to test it against a non-Google source instead, preserving their actual
point (a lone source, or a duplicated one, still is not independent
corroboration) rather than being weakened or deleted.

Applied to the frozen fixture corpus by patching the 7 existing `facts`
entries directly (confidence + score, matching what `corroborate()` would
now produce from the same stored candidates/sources) — no re-research,
no new network call, since the raw claims that motivated "unverified"
haven't changed, only how they are scored.

**Moves the corpus.** Four fixtures (`bare-trade`, `contractor-bare`,
`dentist-rich`, `threadbare`) gained a `contact` section they did not
have before, now that an address or phone exists to show. Batched into
the round's one redecide.

## A bug in the census tool itself, found verifying 3a's "no fingerprint
## moved" claim

`content_census.py`'s grand-total aggregator stripped the
"(subset of photos, informational)" annotation off `own_site_photos`
before summing it — which meant it was being added to the OVERALL total
a second time, on top of the "photos" row it is explicitly a subset of.
Every corpus-wide percentage this project has quoted from this tool
carried a small, consistent overcount (766 total instead of the true
762) that happened to still round to the same headline "73%" both ways,
which is exactly how a double-count hides — it does not have to change
the answer to be wrong. Fixed by excluding any row marked
"informational" from the grand-total sums entirely, keeping it in the
per-fixture diagnostic output where it is still useful.

`content_census.py`'s own hardcoded strings — "no section builder reads
this field at all" for `menu_media`, a literal "4" for the feature cap —
also went stale the moment 3b/3c shipped, the exact "two copies drift
apart" failure this project keeps finding, this time in its own
measurement tool. Fixed: `menu_media`'s line now checks the real built
page; the feature-cap line imports `FEATURE_CAP` instead of restating it.

## Binding claims

**Primary.** Content census overall percentage improves and every
individual metric named in 3a-3d moves in the right direction, with the
new percentage attributable to specific, explained fixes rather than a
tooling artifact (checked directly: the census-tool bug above was found
and fixed BEFORE trusting any of these numbers).

**Secondary.** `make check` green after the one redecide the round's
corpus-moving items (3b, 3d) require; zero collisions across all 171
pairs; no judging round.

## Falsification

If raising `FEATURE_CAP` had pushed any fixture over a forbidden-default
threshold, or lengthened a page enough to look templated, that would be
grounds to prefer a smaller number or a different mechanism — checked
directly (byte counts, the forbidden-defaults test) and neither
happened.

If the Google-alone corroboration change had recovered a fact that
turned out to be WRONG on inspection (a real address/phone mismatch
Google itself had wrong), that would be reason to reconsider a blanket
"Google alone is enough" rule — inspected all 7 promoted facts by hand;
none contradicts what the business's own site or a second directory
would say, only the CONFLICTING cases (correctly excluded) show that
kind of disagreement.

## Outcome — 2026-09-09

All four items landed. Content census overall: **73% -> 77%** (556/766
double-counted -> 559/762 corrected pre-redecide -> 588/762 with all four
fixes applied), the first count using the corrected, non-double-counting
denominator throughout so the improvement is comparable start to finish:

    own_site_photos   0% -> fully absorbed into `photos`, no longer its
                      own dropped category — every fixture with own
                      photos now uses at least one
    menu_media        0% -> 38% (3 of 8)
    block:feature      36% -> 52% (53/148 -> 77/148)
    fact:address       42% -> 68% (8/19 -> 13/19)
    fact:phone         56% -> 67% (10/18 -> 12/18)
    OVERALL            73% -> 77% (corrected denominator both readings)

One redecide, covering 3b (the menu fallback) and 3d (newly-verified
contact facts) — 3a and 3c, verified content-only, needed none. Zero
collisions on the first attempt across all 171 pairs. Same-trade mean
moved 56.10% -> 61.52%; the corpus's closest-ever pair is now
`barbecue`/`barbecue-rich` at 17% (eight of twelve axes shared) —
reported, not judged, per the round's no-judging-round rule. Agreement
stays 0 of 0, deliberately, for the same reason as Phase 1/2: nothing
live to retire, nothing added. `make check` green (848 passed) — see
`.reviews/<phase>.md` for the literal tail.

A fifth, unplanned fix landed alongside 3c: the mislabeled "Dishes on the
menu" stat flagged in passing during Phase 2 turned out to be the exact
`extract_menu_items` false-positive this section describes, affecting 5
fixtures, not 1 — fixed by the same `trade_kind == "food"` guard, not a
separate patch. A `spawn_task` suggestion made for the narrower version
of this bug was superseded and is stale.

# Round 3, Phase 4 — surfacing the census in the workspace

BRIEF §5, Slice D item 3: "the operator should be able to see, per lead,
what of the business's own material did not reach the page and why."
Instruction was explicit: "Reuse the census; do not write a second
implementation of it."

## The refactor this actually required

`tools/content_census.py`'s `measure()` already took `(conn, slug,
lead_id)` and never touched the fixture corpus directly — reusable in
principle. But it lived in `tools/`, which `app/web/server.py` (the live
workspace server) has no business depending on: `tools/` is one-off
scripts, `app/` is the product. Importing a tools script into the server
would have inverted that, and the FIRST time this project's own
"two copies drift" defect showed up in this very file (the
double-counting bug from Phase 3) was exactly because measurement logic
sat somewhere it was awkward to import correctly.

Moved `measure()`, `FixtureCensus`, and their helpers into
`app/site/census.py` — a real library module — and left
`tools/content_census.py` as a thin CLI: loop the fixture corpus, call
the shared `measure()`, total the results. Verified byte-for-byte
identical output from the CLI before and after the move (588/762, 77%,
same per-fixture rows) — a pure relocation, no logic changed.

## Wiring

`workspace()` (`app/web/server.py`) now calls `census.measure()` against
the SAME frozen opening direction `plan`/`outline` already describe (not
the currently-active iteration, if the operator has since iterated —
that is a real limitation, disclosed rather than silently assumed away;
tracking the active version instead is a bigger design question this
phase's scope did not ask to resolve). Returns `dropped()` as
`{field, reached, of, why}` rows, degrading the same way every other
`workspace()` field does — a failure appends to `trouble`, never blanks
the screen.

The workspace UI (`app/web/index.html`) gets a new panel, "What didn't
reach the page", placed beside "The plan" (the other read-only,
opening-version diagnostic) rather than inside the per-iteration
`diagnostics` panel, since census does not change per iteration the way
`understood`/`blast_radius` do. Each dropped field is shown with its own
reason inline — not a hover tooltip, which would have hidden content an
operator needs to actually read.

## Verified live, not just by the standing test

Started the real dev server (`.claude/launch.json`'s `workbench` config)
against `workbench.db` — the actual persistent database this project's
own interactive use has been building up, not a fixture — and opened the
workspace for lead 1 (`The Heritage Table`, 46 real versions). The panel
rendered correctly against real data: `fact:hours`, `services+products`,
`menu_media`, `about_text`, `photos`, each with its own reason, matching
what `tools/content_census.py` would say about the same lead. Confirmed
no new console errors, and that switching between historical versions
(`pickVersion`) leaves the panel untouched, as it should — it is not a
per-iteration diagnostic.

## Binding claims

**Primary.** `workspace()` returns a `census` list, computed by the
identical `measure()` a corpus-wide report calls — not a reimplementation
— for any real lead with a frozen opening direction, degrading to
`trouble` rather than raising. Confirmed against the reverted code
(`KeyError: 'census'`) and restored
(`test_workspace_surfaces_what_did_not_reach_the_page`).

**Secondary.** The CLI tool's own output is unaffected by moving its
measurement logic out from under it — checked directly, byte-for-byte,
before trusting the refactor.

## Falsification

If moving `measure()` into `app/site/census.py` had changed any number
`tools/content_census.py` reports, that would mean the "reuse, don't
reimplement" refactor introduced a behavior change alongside the
relocation — it did not; the CLI's full output was diffed before and
after and is identical.

## Outcome — 2026-09-09

Landed as described. `make check` green (849 passed, one new standing
test). Verified live against the real workbench database in addition to
the standing test — screenshot taken, no console errors introduced,
panel legible and correctly reasoned for a real lead outside the
fixture corpus.

# Round 4, Phase 1 — copy selection and provenance (Slice D's last item)

BRIEF §5: the model selects and orders the business's own sentences and
never authors one. Two deliverables: (1a/1b) a provenance layer checking
every visible sentence is verbatim-or-prefix-cut source, whitelisted
generic copy, or a corroborated-field value — kept SEPARATE from
`app.core.claims`'s CLAIM_RE check, which catches a different shape of
problem (an assertion nothing backs, vs. text that isn't traceably
theirs at all); (1c) an actual model call that selects and orders
sentences within those constraints, replacing the deterministic
first-sentence-as-standfirst / trim-to-460-chars logic `_about()`/
`_features()` use today.

## Where free prose actually reaches the page today

Audited every section builder for text that is the business's own
multi-sentence prose (not a heading, a button, a stat tile, or a single
name/price — those are template chrome or single-field values, never
"selected sentences"): `_about()` (`.standfirst`/`.prose`, from
`material.about` or a story block), `_features()` (same two classes, per
block, from `block["text"]`), `_review_card`/`_review_feature` (the
quote itself, from `quote["text"]`), menu item descriptions (`.d`, from
`item["description"]`), and `_recognition()`'s `.accolade-note` (from an
award block's text). Five spots, all deterministic today — none
currently asks a model anything.

## The provenance check (1a/1b)

`app/site/provenance.py`, `unexplained_sentences(page, material)`:
extracts sentences from exactly those five prose containers (identified
by their own CSS class, `html.unescape`d, tags stripped) and checks each
against a widened "own words" corpus (the same fields `unsupported()`
already used, PLUS menu item descriptions, which the old check never
needed since `CLAIM_RE` rarely appears there but a full-sentence check
now does) via substring match after normalising whitespace/case —
same technique `unsupported()` already uses, applied to every prose
sentence rather than only ones matching a claim pattern. A small
`GENERIC_COPY` whitelist exists for future hardcoded boilerplate; empty
today, honestly, since nothing in this codebase currently authors a
prose sentence outside these five sourced spots.

`unsupported()` is UNTOUCHED — still the CLAIM_RE layer, still wired into
the pipeline's gate exactly where it was. The new check is additive, a
second call in the same gate function, not a replacement.

## Copy selection (1c)

A new adapter call, `app.site.copyselect.select(candidates, client=None)`:
given named groups of source sentences (one group per prose spot — the
about text's sentences, each feature block's sentences), returns which
INDICES to keep and their display order, per group. Returning indices
rather than re-typed text makes verbatim provenance true by
construction — the rendered sentence is always `sentences[i]` from the
original list, never a model's retyping of it, so there is nothing for
the provenance check above to catch here by design, not by luck.

Frozen once per lead, like every other model answer BRIEF §4 already
names in this list ("design system, compositions, copy selection,
vision, signature device") — computed during the same freeze pass that
already handles vision and the design direction
(`tools/make_fixtures.py freeze_vision`), stored in the brief as
`copy_selection`, read by `_about()`/`_features()` at build time instead
of the deterministic trim. Falls back to the existing deterministic
method with no key — everything degrades, and the degraded path is the
method already shipping today, not a new one.

**No axis moves.** Copy selection is not a fingerprint input;
`compositions`/`section_order` do not read sentence content. No
redecide. Screenshots are invalidated (the words on the page change) —
recaptured with `--widths page,fold` per instruction.

## Binding claims

**Primary.** The provenance check fails on synthetic text NOT sourced
from `material` (a fabricated sentence injected into a test page) and
passes on the real corpus once wired in, for all 19 fixtures.

**Secondary.** `test_no_unverified_credential_ships` and
`test_no_contradicted_fact_ships` both still pass, unchanged, proving
the new layer is additive rather than a replacement that lost coverage.

**Tertiary.** Copy selection, once frozen, reproduces byte-identically
on a second `build_from_spec()` call with no client available — the
determinism BRIEF §4 requires.

## Falsification

If the provenance check ever flags real, currently-shipping prose as
unexplained, that means the "own words" corpus is missing a field the
old `unsupported()` never needed (menu descriptions were exactly this
case, found before writing the check rather than after). If copy
selection ever renders a sentence NOT equal to `sentences[i]` for some
`i` in the original candidate list, the by-construction guarantee above
is false and the feature is unsafe to ship.

## Outcome — 2026-09-10

**Primary claim PASSED.** The provenance check catches a synthetic
fabricated sentence in a test page and passes the real, current 19-fixture
corpus with zero unexplained sentences — confirmed before any freezing,
using the deterministic fallback path (no `copy_selection` present yet).

**One correction, made before trusting the design further:** the group
naming in this file's own pre-registration (`feature:0`) does not survive
contact with the API — Claude's tool-use schema rejects property keys
containing a colon (`HTTP 400: ... Property keys should match pattern
'^[a-zA-Z0-9_.-]{1,64}$'`), found on the very first live call against
`barbecue`'s real groups. Renamed to `feature_0` throughout
(`app/site/copyselect.py`, `app/site/render.py`'s matching lookup key).
Caught before any fixture was frozen under the broken name, so no
re-freeze was needed on top of the rename.

**Secondary claim PASSED.** `test_no_unverified_credential_ships` and
`test_no_contradicted_fact_ships` both pass unchanged, run alongside the
new provenance layer in `pipeline._gate` rather than folded into
`unsupported()`.

**Tertiary claim PASSED by construction, not just tested.** Copy
selection is read from a frozen dict at render time
(`_apply_copy_selection`); nothing in `_about()`/`_features()` calls the
model. `make check` (865 passed) confirms nothing broke; determinism
follows from there being no live call in the render path at all, the same
guarantee every other frozen decision in this system already has.

**Real freeze, all 19 fixtures, 19 model calls** (`tools/make_fixtures.py
--vision-only`, which already re-runs `direction`/`page` under the
EXISTING frozen `design_direction` — confirmed by
`test_the_instrument_reproduces.py` staying green afterward: zero
fingerprint values moved). `render_snapshots.json` regenerated (every
fixture's bytes changed — expected, this changes what ships); screenshots
recaptured (`--widths page,fold`, then `page,fold,thumb` for the
committed sheet, per house practice).

**1d — the numbers asked for.**

Content census: still 77% overall, unchanged — expected and disclosed
rather than a null result. The census counts whether a FIELD (an about
text, a feature block) reached the page at all; copy selection decides
WHICH SENTENCES within an already-counted field are kept, a finer grain
than the census currently measures. Nothing here regressed; the census
simply answers a different question than 1d's own ratio does.

Sentence-provenance ratio, computed directly (not from the census):
**687 of 687 rendered prose sentences (100%) are verbatim-or-prefix-cut**
source material; 0% generic-library (the whitelist is empty — nothing in
this codebase currently authors a boilerplate sentence); 0% rendered
corroborated-field values (no current prose spot is built that way). This
is not a coincidence of the check being lenient — it is what "select and
order, never invent" guarantees when every group's answer is applied by
INDEX into the exact list offered, never by re-reading model-generated
text.

Selection ratio (how much of what was available got kept, per fixture —
the more informative number, since 100% verbatim was true before this
phase too, by the old deterministic method):

    barbecue-rich   19/22   86%        hvac             17/21   81%
    barbecue        25/34   74%        law-rich         33/37   89%
    bare-trade      32/33   97%        law              25/28   89%
    dentist-rich    26/29   90%        restaurant-rich  11/12   92%
    dentist         30/37   81%        roofer-rich      27/38   71%
    hvac-rich       27/27  100%        roofer           31/34   91%
    hvac-second     51/59   86%        salon            27/40   68%
    TOTAL                              389/459  85%

(`contractor-bare`, `restaurant-bare`, `salon-rich`, `threadbare` have no
qualifying prose group at all — 0 candidates, nothing to select from,
correctly absent above rather than shown as a false 100%.)

`make check` green (865 passed) after the freeze and the snapshot
regeneration. No redecide — every fingerprint test still passes
unchanged.

# Round 4, Phase 2 — Slice E, with its own way of being seen

BRIEF §5: motion as a design-system property, but only after it can be
measured — the instruction was explicit that building the feature first
"repeats the page-architecture failure exactly" (Slice B's own history:
an axis shipped before anything checked it changed what it claimed to).

## 2a — the performance harness, before any feature

`tools/perf_census.py`, real numbers from a headless-Chrome
`PerformanceObserver` (LCP via `largest-contentful-paint`, `buffered:
true`; CLS via `layout-shift`, excluding `hadRecentInput`; an INP proxy
via the Event Timing API's `type: 'event'` plus a synthetic click),
never estimated from CSS or counted statically. Page weight computed
from disk — HTML bytes plus every distinct local image the page
actually references — not from `file://` resource timing, which does
not reliably report a transfer size for a protocol that never
transferred anything.

Budgets pinned from BRIEF §5: LCP < 2500ms, INP < 200ms, CLS < 0.1,
weight < 2MB. `tests/fixtures/performance_baseline.json` is the
committed, periodically-regenerated snapshot (the same pattern as
`render_snapshots.json` and the committed contact sheet) —
`tests/test_performance_budgets.py` asserts against it, not against a
live browser, so `make check` stays fast and deterministic.

## 2b — the capture problem

Every existing screenshot tool (`contact_sheet.py`, `design_review.py`)
passes `--force-prefers-reduced-motion`, so a static capture of a moving
page is indistinguishable from a still one — Slice E's own capture
problem, stated in the instruction. Decision: a **separate tool**,
`tools/motion_preview.py`, used by nothing else in this project — a
filmstrip of real screenshots (motion left on) at fixed intervals over
one CSS crossfade cycle, written as a small reviewable HTML page per
fixture. Not a recording: the point is showing a person the
choreography exists and looks right, not archiving it, and nothing in
this codebase's test/census/verdict pipeline reads its output.

**The determinism property survives untouched** — it was never at risk.
A pre-existing, universal `prefers-reduced-motion` CSS rule in
`app/site/styles.py` (`*,*::before,*::after{animation:none!important}`)
means every animation added anywhere, including this one, automatically
disables under the flag every other capture tool already passes. No
change to `contact_sheet.py`, `design_review.py`, or the collision/
verdict pipeline was needed for this to hold.

## 2c — the preference ladder

`app/site/backdrop.py`, `select_backdrop(m) -> Backdrop`: their own
video (dormant — no extraction path in this codebase gathers one yet,
disclosed rather than built against untested code) → a sequence of 2+
of their own uncondemned photos (`looked_at_and_rejected`, the same
vision floor `pick_hero` already enforces, reused so a backdrop can
never show what the hero itself refused to lead with) → an abstract
backdrop generated from the palette (always available, CSS gradient
only) → licensed stock, never reached — no source integrated, refuses
rather than fabricates a credential or a URL, consistent with this
project's standing rule against inventing evidence. Of the 19 fixtures,
only the stills and generated rungs are exercised by the real corpus;
said plainly rather than claiming video coverage that does not exist.

## 2d — reduced motion, and never the largest element

Poster frame is the first still (`:first-child{opacity:1}`), always
present with motion disabled. Muted, inline, looping by construction —
this is a CSS background-image crossfade, not a `<video>` element, so
there is nothing to unmute or a browser autoplay policy to fight. Never
the largest contentful element: the stills sit at `z-index:-2` behind
the hero's own text, which is what LCP already measures on every other
`first_screen` position.

## 2e — axis thirteen: decided against, this pass

The only live rendering change is the backdrop's presence at
`first_screen == "type"` — which is already a function of the existing
`first_screen` axis, not an independently-settable property. BRIEF §3's
own axis test ("changing it alone must change the rendered page") fails
today: motion cannot be varied while `first_screen` holds still. Written
up in `app/site/fingerprint.py` beside the `layout_bias` precedent this
follows. **No redecide** — nothing was added to `AXES`.

## Binding claims

**Primary.** Every one of the 19 fixtures holds all four budgets, OR
each breach is a real, disclosed, currently-pinned exception
(`pytest.mark.xfail`, never a silently widened budget or a deleted
assertion) — reported honestly rather than tuned to pass.

**Secondary.** The motion feature is visible in the capture path 2b
establishes — confirmed directly: `salon-rich` (the one fixture in the
current corpus with `first_screen == "type"` and 2+ uncondemned photos)
shows a different background photograph between filmstrip frames at
t=0s and t=5s, a real, human-visible crossfade, not merely present in
markup.

## Outcome — 2026-09-10

**Primary claim PASSED, honestly rather than by tuning.** Final clean
run of `tools/perf_census.py` (after every Slice E render/CSS change
had landed — a first run launched mid-edit was discarded rather than
kept as the pinned baseline):

    fixture             LCP    CLS     INP    weight    breach
    barbecue-rich       244ms  0.000   160ms   7361KB    weight
    barbecue            296ms  0.000    64ms   6683KB    weight
    bare-trade          312ms  0.000    24ms     71KB
    contractor-bare     152ms  0.000    16ms   2001KB
    dentist-rich        216ms  0.000    24ms   1895KB
    dentist             200ms  0.000    32ms     69KB
    hvac-rich           216ms  0.000    24ms   2633KB    weight
    hvac-second         188ms  0.000    24ms   3917KB    weight
    hvac                268ms  0.000     0ms   3176KB    weight
    law-rich             304ms  0.000    32ms   8249KB    weight
    law                 184ms  0.000    24ms     69KB
    restaurant-bare     252ms  0.000    24ms   4514KB    weight
    restaurant-casual   168ms  0.000    16ms   4791KB    weight
    restaurant-rich     252ms  0.000    24ms   3010KB    weight
    roofer-rich         260ms  0.000    24ms     69KB
    roofer              276ms  0.000    24ms   7788KB    weight
    salon-rich          320ms  0.000    32ms   4181KB    weight
    salon               172ms  0.000     0ms   2992KB    weight
    threadbare          108ms  0.000     0ms     59KB

Every LCP is under 320ms (budget 2500ms) and every CLS is 0.000 (budget
0.1) — neither has ever come close to breaching on this corpus. INP,
which DID show real breaches in an earlier mid-edit run (up to 1064ms
on a single noisy sample), is clean on every fixture in this final run
once measured as min-of-5 — the noise-filtering approach held up.
Twelve of nineteen fixtures breach the 2MB weight budget, all for
photo-gallery weight predating Slice E entirely (confirmed: the stills
backdrop reuses images already counted in `m.images`, adding no bytes
of its own). Pinned in `tests/test_performance_budgets.py` as twelve
`xfail(strict=True)` cases — visible in test output, and a future fix
would show as a hard XPASS failure rather than a silent pass, catching
drift either direction. The other 66 (fixture, metric) combinations are
a real, currently-green regression gate.

**Secondary claim PASSED.** `tools/motion_preview.py` built as a
separate, human-review-only tool; run against the full corpus, only
`salon-rich` currently exercises the stills rung (the one fixture with
`first_screen == "type"` and 2+ uncondemned photos — said plainly
rather than claiming broader coverage). Its filmstrip shows a real,
visible crossfade: frame 0 (t=0s) and frame 2 (t=5s) are genuinely
different photographs of the business, confirmed by direct inspection,
not merely by the presence of `hero-stills` markup — a first version of
this check matched the CSS rule text (present on every page regardless
of use) rather than the actual wrapping div, caught and fixed before
being trusted. Determinism was never touched: the pre-existing global
`prefers-reduced-motion` rule in `styles.py` already disables every
animation everywhere, so `contact_sheet.py`/`design_review.py` and the
whole verdict/collision pipeline need no change and make none.

**Axis thirteen: decided against**, written up in
`app/site/fingerprint.py` beside `layout_bias`'s precedent — the
backdrop's only live effect is a function of the existing `first_screen`
axis, failing BRIEF §3's own independence test. No redecide.

`make check`: ruff clean, mypy clean (63 source files), **938 passed,
12 xfailed** (0:04:02). The twelve are exactly the disclosed weight
breaches above, nothing else.

**Slice C's ninth contractor fact (before-and-after), re-checked this
round per the "if room" instruction:** no fixture's `photo_vision`
carries any before/after pairing field — confirmed by direct inspection
of all 19 fixtures' vision data, not assumed. Still correctly unbuilt;
nothing changed here.

# Round 4, Phase 3 — Slice G in full, and rebuild the ground truth

## 3a — the full sweep, and two classes of defect fixed

`tools/design_review.py --full`: extended from the 4-fixture sample to
all 19, still 3 widths, 57 model calls (up from 12), findings written
to `artifacts/design-review-full.json` for a proper diff rather than
read off stdout. 295 findings total (credibility=64, spacing=59,
hierarchy=46, crop=38, template=37, imagery=36, colour=15).

The overwhelming majority are photographic/design judgment calls tied
to a specific source photo or a specific business's own copy — a
cropped face, a low review count, generic-feeling boilerplate — which
are real observations but not code defects: the generator has no lever
to un-crop a bad source photograph, and BRIEF's own standing rule
(`quality_census.py`'s comment on `layout_bias`) is to prefer a
standing test over chasing individual findings by eye. Scanned for
recurring, corpus-wide PHRASE patterns instead, which is how a code
defect actually announces itself in a per-screenshot review — a bug
gets caught independently by four different fixtures' calls, an opinion
does not.

Two real, deterministic bugs surfaced this way, both fixed by class:

**"What we cook and serve" on a roofer, two HVAC contractors, and a law
firm.** `_offer_heading()` (`app/site/render.py`) read `kind = "food"
if m.menu_items else m.trade_kind` — `m.menu_items` alone, ignoring
`trade_kind`, the exact over-trusting `extract_menu_items` anchor Round
3 already gated everywhere else (`_stats()`, `_menu()`) after it misread
a law firm's settlement figures as "12 dishes on the menu". This one
call site never got the gate. Fixed to read `trade_kind` directly,
matching the other two call sites; a fifth instance (`dentist`) the
57-call sample never happened to flag came along for free, since the
fix is at the root cause rather than a patch per finding. Five
fixtures' rendered bytes moved; `render_snapshots.json` regenerated.
Standing regression test added (`test_a_stray_menu_item_does_not_
borrow_the_food_heading`), confirmed to fail against the reverted code.

**The signature device's own copy of a truncation bug already fixed
once.** `signature.py`'s `quote` device sliced testimonial text with a
bare `text[:220]`, no word boundary — the same defect `_truncate_quote`
was built to fix for `_review_card`/`_review_feature`, in a second
implementation the fix never reached. On `hvac`'s real testimonial it
landed on "...knowledgeable. H", a lone capital letter with the
decorative closing curly quote glued directly onto it. Fixed by reusing
`_truncate_quote` rather than patching the slice in place. A second,
independent issue surfaced verifying the fix visually: the decorative
`::before`/`::after` curly quote marks render at full body size and
weight with no distinguishing style, legible as punctuation on close
reading but misread as a doubled first letter ("CCody Roberts") and a
stray trailing letter by both the design review and a first glance at
the same screenshot. Toned down (accent colour, 0.6 opacity, 0.6em) so
they read as ornamental rather than more of the word — verified against
a real capture both before and after, not just the CSS. Four fixtures
carry the `quote` device; all four fixtures' bytes moved for the
truncation fix, all 19 for the CSS-only quote-mark fix (inlined
stylesheet). Standing regression test added directly against the
device, confirmed to fail against the reverted code.

**Run to ground, not "fixed":** the WebGL "your browser does not
support WebGL" map error four findings raised independently
(`contractor-bare`, `restaurant-bare`, `salon-rich`, `threadbare`). A
controlled before/after capture of the same OpenStreetMap embed URL —
identical Chrome, identical page, only `--disable-gpu` toggled —
reproduces the exact error with the flag and shows a normal map without
it. Every screenshot tool in this project (`contact_sheet.py`,
`design_review.py`, `perf_census.py`) passes `--disable-gpu` for
headless-rendering stability; no real visitor's browser carries that
flag. Disclosed as a capture-tooling artifact, the same finding shape
as Round 3's CDP width-clamping discovery, not a defect in the
generated site — and not fixed, since there is nothing in this
project's own code to fix.

Also confirmed and left alone: `threadbare`'s "page content repeats
twice" finding (a hallucination reading blank canvas below a short page
as duplicated content — the `page` capture is a fixed 6000px window and
`threadbare` does not fill it) and `law-rich`'s "Boad Certified"
misspelling (verbatim in the fixture's own scraped `published.services`
data alongside genuine navigation-link contamination — a source data
quality issue, not a rendering bug).

`make check`: ruff clean, mypy clean, 940 passed, 12 xfailed (the same
twelve disclosed weight breaches, untouched by this phase).

## 3b — rebuilding the ground truth

The verdict set had sat at 0 live for two full rounds (131 retired, all
of Round 3 and Round 4 Phase 1-2 with nothing to score against).
Fifteen fresh verdicts, judged the same way the file's own header
already specifies — whole page, scrolled top to bottom, blind, no axis
values in view, `artifacts/contact-sheet/<slug>-page.png` — recaptured
this same session, after every Phase 3a fix had landed, never reused
from an earlier run.

Pairs were chosen before judging, never after: some because the
census's own "closest pairs" list called them close by the vector's own
measure (the exact test of whether the instrument's sense of
"similar" matches a stranger's), some for same-trade coverage.
`is_held_out()` — a fixed hash of the two slugs — was computed on that
already-decided list, not used to choose which pairs to include.
Twelve of fifteen landed in the held-out third; eleven of those twelve
came back "different", one — `roofer`/`hvac-rich` — came back "same":
both pages open on an identical recipe (full-screen photograph, a
rating number at display size in the corner, two buttons) and run an
identical section set below it (a band of three numbers, an eight-card
service grid under the same heading, a review grid, a twelve-photo
"Recent jobs" gallery, a two-column closing paragraph), only two of
those sections swapping order plus one small extra badge row.

**Binding claim: enough pairs that the held-out third holds 4-5
scorable comparisons.** One same against eleven different in the
held-out set is eleven cross-comparisons — cleared, not engineered to
just clear it.

**Agreement, reported plainly.** Full (every live pair): **22/26
(85%)**. Held-out only, the number that actually says something about
generalising: **9/11 (82%)**. Both real, not tuned toward — every
inversion (four in the full set, two held-out) traces to the one
disputed pair: `roofer`/`hvac-rich` sits at 69% by the vector's own
measure, nearly the corpus-wide 80% mean, further apart than several
pairs judged "different". This is a genuine, disclosed mismatch between
the instrument and a stranger's eye on one specific pair — reported as
found, not argued away, and not re-judged to make the number move.
`barbecue-rich`/`barbecue`, the closest same-trade pair the fingerprint
has ever produced (17%, eight of twelve axes shared), was also judged
and also came back "same" — landed in the tuning third by the same
fixed hash, so it does not count toward the held-out score either way.

`tests/test_the_instrument_reproduces.py`'s five tests that pinned the
"0 live verdicts" state are rewritten, not weakened — each replaced
with an equally exact pin against the new state (the labels hash, the
held-out hash, the agreement tuple, the exact inversion pair, the exact
live "same" set), confirmed to fail if any of those move again without
a reason. `tools/quality_census.py`'s baseline constants re-pinned to
match. `BASELINE_IS_FRESH` deliberately left `False`: the flag also
gates the same-trade mean's own freshness message, and that number did
not move this phase — only the agreement labels did — so `True` would
have silently claimed "nothing to compare" on a real, still-valid "no
better than baseline" reading.

`.reviews/sheet/` recaptured at all five widths (`tools/contact_sheet.py`
with no `--widths` filter). An earlier `--widths page`-only run
regenerated the committed sheet without `thumb` screenshots, silently
emptying its figures — caught by `test_the_committed_sheet_shows_the_
corpus_that_shipped` before it was committed, not after.

`make check`: ruff clean, mypy clean, 940 passed, 12 xfailed.

# Round 5, Phase 1 — the stale review bundle

**Binding claim, pre-registered:** a freshness guard on `.reviews/review/`
must fail against the currently-committed bundle before anything is
regenerated, and pass after — checked in both directions, not assumed.

## What was found

Confirmed the reported defect (`dentist.html` reading "What we cook and
serve") and then found the actual scope was larger than reported: the
committed review bundle (`.reviews/review/*.html`) was last touched at
`d2bfbfa`, Round 3's own close-out — BEFORE Round 4's first commit. Every
one of the nineteen committed pages predates the entire round: Phase 1's
copy-selection changes, Phase 2's Slice E CSS, and Phase 3a's two render
fixes are all missing from the committed bundle, not just the five
fixtures the heading bug touched. `dentist`, `hvac-rich`, `hvac-second`,
`law-rich`, and `roofer-rich` were the only ones with a VISIBLY wrong
heading; all nineteen were byte-stale.

## The freshness guard

`tests/tools/test_build_review.py::test_the_committed_review_bundle_
shows_the_corpus_that_shipped`: rebuilds every fixture through the
identical path `tools/build_review.py`'s own `main()` uses (frozen
direction replay, the same `_copy_photographs` URL rewrite) and diffs the
fresh bytes against the committed file, byte for byte — not a hash
comparison against a separate pinned file (there is no equivalent of
`render_snapshots.json` for this bundle), since the committed file IS the
thing being checked for freshness. Mirrors
`test_the_committed_sheet_shows_the_corpus_that_shipped`'s reasoning,
applied to full page content rather than printed axis captions.

**Confirmed failing against the stale bundle, before regenerating
anything:** all nineteen slugs reported stale, `AssertionError` naming
each one.

**Regenerated** via `tools/build_review.py` (all nineteen, relative photo
paths — confirmed zero `base64` occurrences across the bundle).

**Confirmed passing after regeneration:** the same test, unchanged, now
green.

## 1c — known-open items named in READ-ME-FIRST.md

Added two disclosures that were previously absent: the three
"BLIND SPOT" comparisons `quality_census.py` reports (all tracing to
`roofer`/`hvac-rich` — a genuine axis-superset limit no reweighting can
reach, not a bug), and the twelve pre-existing weight-budget `xfail`s
(all photo-gallery weight predating Slice E, LCP/CLS/INP clean on all
nineteen).

`make check`: ruff clean, mypy clean, 941 passed (the new freshness
guard), 12 xfailed.

# Round 5, Phase 2 — Slice H, the conversational workspace

**Binding claim, pre-registered:** the reply builder cannot see the
rendered page (structurally, proven by test), and an unmet instruction
produces a question rather than a silent no-op. **Both PASSED** — see
below.

## What already existed, read before writing anything

Per instruction, nothing already built was rebuilt. `app/store/
messages.py` (the thread, its prose boundary, the AST test) was
untouched. Reading `app/site/pipeline.py`'s `_build_opening()` before
starting found item 2a already fully working — `if rationale and not
messages.opened(conn, lead_id): messages.add(conn, lead_id, "assistant",
rationale, version=version)` has been there since Slice F. Confirmed by
actually running it (`pipeline.open_site` against a real fixture): the
workspace opens with the model's own rationale as message one. It had no
standing test; added one
(`test_the_workspace_opens_on_the_rationale_not_an_empty_box`) rather
than building a feature that already existed.

## 2b/2c — the reply builder

`app/site/reply.py`, `reply_for(result: IterationResult) -> str`. The
structural proof of "never given the page": the function's own
signature takes exactly one parameter, typed `IterationResult` — there
is no second parameter for a page to ride in on, `IterationResult` itself
carries no `html`/`page`/`rendered` field, and the module imports nothing
from `app.site.render`. Three tests hold this directly
(`tests/sitegen/test_reply.py`): the signature check, the
`IterationResult` field check, and an AST scan mirroring
`test_messages.py`'s own technique for the opposite boundary.

Deterministic and template-based, a considered choice rather than a live
model call: every field `reply_for` reads is already closed-vocabulary,
plain-English material a PRIOR step produced (the model's own
`understood` strings, or a rule-derived `"mood: 'quiet' -> 'warm'"` line)
— turning that into a sentence is the same job `tools/build_review.py`'s
`_plain_outline()` already does, not a second free-text pass that could
drift from what the `IterationResult` actually says. It also means a
reply is never blocked on the model being reachable, which matters most
exactly when `reader_error` is set — the one case BRIEF's own instruction
named explicitly ("the operator must be TOLD that, not left guessing").

A DEFECT BECOMES A QUESTION: `unmet`, `contradictions`, and
`ignored_tokens` all turn into "I ... What did you mean?" rather than a
passive list. A gate rejection reports its findings plainly, without a
question (nothing to ask — the instruction did not pass, full stop). A
non-style instruction (a bug report or a request this cannot build) gets
its own reply shape — never "Done —", which is the exact misread
`_offer_heading` and its siblings already exist to avoid one level up
the stack (answering a defect by pretending an edit happened).

Wired into `pipeline.iterate()`: the existing function renamed to
`_iterate` (unchanged internals, every branch untouched), wrapped by a
new `iterate()` that calls `_iterate`, writes `reply_for(result)` to
`messages`, and records style preferences (2d) — one exit point for the
new behaviour rather than four early returns each needing the same two
lines added.

## 2d — repeated preferences, scoped to real leads by construction

`app/store/preferences.py`: `record()` ties each understood phrase to
the lead it was said on; `repeated(min_leads=3)` returns phrases said on
at least three DISTINCT leads, most-repeated first. Deliberately exact
string matching, not fuzzy — the same closed-vocabulary discipline as
everywhere else in this project; conflating two different phrasings of
"the same" preference would be inventing a similarity nothing measured.

Threaded into `opening.opening_spec()`'s new `preferences` parameter,
appended to `_prompt()` as one more consideration beside the sampled-
palette line, worded as a lean rather than a rule ("worth leaning toward
... never worth overriding what \[the business's own material\] says").
`identity.decide()` computes `preferences.repeated(conn)` once and
threads it through both of its own calls to `opening_spec()`.

**Does this apply to the fixture corpus? No — not by a scope decision
written here, but because the existing replay invariant makes it
structurally unreachable.** `opening_spec()` returns `{**frozen,
read_by:"frozen"}` for any brief carrying a `design_direction` — every
fixture — before it ever calls `_prompt()` or looks at `preferences` at
all. `test_a_frozen_brief_ignores_preferences_entirely`
(`tests/sitegen/test_opening.py`) proves this directly: a Claude call
that raises if reached at all, and identical output with an empty versus
a four-item preferences list. No redecide follows from this phase — the
full suite, `render_snapshots.json` and `test_the_instrument_reproduces.py`
included, passed unchanged.

## 2e — the prose boundary, re-confirmed rather than assumed

`tests/store/test_messages.py::test_the_generator_cannot_reach_the_
conversation` still passes with `reply.py` added — it does not import
`app.store.messages` at all (the message write happens in
`pipeline.iterate()`, already whitelisted), so the AST scan's allowed
set (`{"pipeline.py"}`) needed no change. `identity.py`'s new import of
`app.store.preferences` is not `messages` and does not trip the same
check — a different table, closed-vocabulary phrases already validated
as understood instructions, not free model prose.

## Tests added

`tests/sitegen/test_reply.py` (12), `tests/store/test_preferences.py`
(5), three new cases in `tests/sitegen/test_opening.py`, four new cases
in `tests/sitegen/test_pipeline.py` (the opening-rationale standing test
plus three Slice H integration tests) — 24 new tests total.

`make check`: ruff clean, mypy clean, 965 passed, 12 xfailed. No
fixture's fingerprint or rendered bytes moved.

# Round 5, "if room" — the three items, investigated in order

## 3a — the three unreachable comparisons: labels, not axes

Pulled all four verdicts' own `why` text (`roofer`/`hvac-rich` [same],
`dentist`/`law`, `roofer-rich`/`hvac-rich`, `law`/`law-rich` [different])
and applied the exact test the last time this happened
(`.reviews/slice-b-predictions.md`, the axis-two blind spot): do the
"different" verdicts rest on a standard the "same" verdict's own why
text also describes as present?

They do. `roofer`/`hvac-rich`'s own "same" reasoning names two things
and dismisses both: "reviews and services swapping which comes first"
(an order swap) and "a short row of small labelled badges tucked into
one of them" (an extra element the other page lacks). But an order swap
is the FIRST reason given for `dentist`/`law` being called different,
and for `roofer-rich`/`hvac-rich` being called different (credentials-
before-stats vs. stats-immediately-after); and an extra element the
other page lacks is the SOLE reason given for `law`/`law-rich` being
called different (a nine-photo gallery there). The same two signals
that were each independently sufficient to call three other pairs
"different" were both present in `roofer`/`hvac-rich` and did not move
its verdict.

**That is a self-contradiction in these four verdicts, not evidence the
vector is missing an axis.** No property named in any of the four `why`
texts separates `roofer`/`hvac-rich` (same) from the three "different"
pairs while also joining it to itself — the requirement `unreachable()`'s
own docstring poses ("clearing it requires an axis where the different
pair still differs and the same pair still matches") is unsatisfiable
here for the same reason it was unsatisfiable last time: the labels
disagree with each other before any axis gets a vote.

**Not fixed this pass.** The precedent's own resolution to an identical
finding was a full re-judging round, done carefully after a missing rule
was named first — not a same-session flip of one contested verdict. This
is disclosed, with the specific contradiction shown, rather than left
implicit or quietly patched: `roofer`/`hvac-rich` is the one live verdict
most worth a fresh, careful look in a future judging round, and the
size-of-an-extra-element question ("a small badge row" vs. "a nine-photo
gallery" — are these really the same class of difference?) deserves
more than a same-session mechanical reversal. **No axis was built on the
strength of this**, per instruction.

## 3b — the twelve weight-budget xfails: partly measurement, partly real

Sampled three of the twelve with real data rather than arguing from the
architecture alone. `app/web/server.py`'s `/photo/` route already honours
`?w=`, resizing via Google's own Places Photo API
(`photos_api.nearest_width`/`fetch`) — the responsive path `srcset()`
already emits (800/1600/2400) has never actually been exercised,
though: zero of law-rich's ten photos had an 800px variant cached
anywhere on disk before this check, because every local measurement and
capture tool (`_link_photographs()`, reused by `perf_census.py`) links
every `/photo/` reference to the SAME cached `MAX_WIDTH` file regardless
of its own `?w=` — a real, disclosed tooling gap, not new information.

Fetched the real 800px tier for three fixtures via the live Google API to
see how much of the twelve that gap actually explains:

    fixture           2400w (measured)   800w (real, smallest tier)
    barbecue-rich     7188KB             1590KB   — clears the budget
    law-rich          8249KB             2741KB   — still over
    roofer            7788KB             4695KB   — still well over

**Not a single answer.** For `barbecue-rich`, the measurement gap is the
whole story — a real mobile visitor using the responsive path this
project already built would load under budget today, and the xfail is
purely an artifact of the local harness never honouring its own `?w=`
parameter. For `law-rich` and `roofer`, it is not: even the smallest
tier currently offered falls short, by a wide margin for `roofer`. Three
fixtures is not twelve, but it is enough to say the true split is
somewhere between "all measurement artifact" and "all genuine weight" —
not either extreme, and not knowable without doing the same check on
the other nine.

**Decided, not left hanging:** this needs its own scoped pass, not a
same-session patch of either kind — measuring the real path properly
(teaching `perf_census.py` to serve photos width-aware rather than
collapsed to one file, the same class of fix Round 3 already made once
for the mobile-viewport capture width) would settle which fixtures clear
on measurement alone; for the ones that do not, the real choice is
between a narrower `srcset` tier for thumbnail-sized slots (a gallery
tile renders far narrower than 800px), a stricter photo cap, or
accepting that a photo-driven trade genuinely costs more to show
properly. Recommended as the first item of a future round rather than
guessed at here with two-thirds of the evidence missing.

## 3c — before-and-after: re-confirmed, still unsupported

Re-checked directly (not assumed from Round 4's finding): no fixture's
`photo_vision` carries a before/after pairing field, scanned fresh
across all nineteen. Nothing in this round added or could add one — no
new fixtures, no new vision extraction. Still correctly unbuilt.

# Round 6, Phase 1 — correctness bugs in the artifact he opens

Governing rule this round: only work with a right answer. No redecide,
no new verdicts, no visual change to any page — the corpus must be
byte-identical when the round ends. Baseline captured before touching
anything: ruler `a762bcc9`, rule `254e171b`, labels `122e6ec8`, held-out
`7aa64298`, `render_snapshots.json` sha256
`554cdf5df2aeb45c1ec0684d103979191899e519ef1df5a7206f4a9ff0233765`.

## 1a — the og:image bug, confirmed before fixing

Confirmed the exact diagnosis: `app.site.render.absolute()` correctly
builds `http://127.0.0.1:8099/photo/1/6`; `build_review.
_copy_photographs`'s regex (`/photo/{lead_id}/(\d+)...`) matches
anywhere in the page text, including the seven characters after the
port number in that absolute URL, and rewrites the match to
`photos/<hash>.jpg` with no leading slash — `...8099photos/<hash>.jpg`.
17 of 19 committed pages carried this. `absolute()` is used in exactly
one place (the og:image meta tag); no `<img>` uses it, so this was
always metadata-only.

Traced every legitimate context `/photo/<lead>/<n>` appears in a
rendered page (an `<img src="...">`, a `srcset` list's later entries,
a CSS `url(&quot;...&quot;)` background) and found each is preceded by
a quote, `&quot;`, or `, ` — never by an alphanumeric character. The one
occurrence that IS preceded by an alphanumeric character (the port
number's own last digit) is the one inside `absolute()`'s output. Fixed
with a negative lookbehind, `(?<![0-9A-Za-z])`, rather than enumerating
every legitimate preceding character — excludes exactly the one case
that was ever wrong.

Two tests added: one constructs the exact og:image shape and asserts
the URL survives byte-for-byte and `"8099photos/"` never appears; one
constructs a full three-entry `srcset` list and asserts all three
entries still rewrite (checking the fix does not over-correct and
leave a legitimate later entry, preceded by `, ` rather than a fresh
quote, unmatched). Both pass.

## 1b — the freshness guard's false alarm

Confirmed the failure mode directly: with `.cache/photos/` emptied,
`_copy_photographs` cannot resolve any `/photo/` URL (every
`_cache_path(...).exists()` check fails), so every URL comes back
unchanged — which will never match a committed page that WAS built
against a populated cache, regardless of whether the bundle actually
moved. Added a guard: the freshness test now `pytest.skip()`s with a
message naming the exact command to run first
(`tools/build_review.py`) when `.cache/photos/` holds no `.jpg` files.
Verified in both directions: moved the real cache aside, confirmed the
test skips with the intended message rather than failing; restored it,
confirmed the test runs and passes again.

## 1c — every page verified to open offline with its photographs visible

Not a code-change item — a verification, done with the project's own
established headless-Chrome technique (`tools/contact_sheet.py`'s CDP
plumbing) rather than trusted from file existence alone. First attempt
via the interactive Browser pane tool was a false negative: it renders
a `file://` URL as a static snapshot with no real network activity, so
no image ever "loads" there regardless of whether the bundle works —
abandoned in favour of a real headless Chrome instance, matching what
this project already trusts for every other capture.

A first CDP pass (no scrolling) found EVERY `<img>` on every page
unloaded (`naturalWidth: 0`). Traced to `loading="lazy"` — used by
default in `render.py` — combined with a headless viewport that never
scrolls; this is normal browser behaviour; a real reader scrolling the
page would trigger every one. Re-ran scrolling the full page height
first: 12 of 14 on a sample page loaded; the remaining two were
investigated individually rather than written off as noise:

- An `<img src="">` inside a lightbox modal template (`role="dialog"
  aria-label="Photo"`) — an intentionally empty slot a JS lightbox
  fills in when opened, not a content defect. Browsers resolve an empty
  relative `src` to the current document URL, which is why it showed
  up in a naive scan.
- An external `https://...netlify.app/.../*.svg` partner-logo image —
  not a `/photo/` proxy URL at all, and never meant to be cached
  locally by this bundle's own asset-copying (`_copy_photographs` only
  ever touches `/photo/{lead_id}/(\d+)`). Out of scope for "their own
  photographs" the same way a business's own external badge images
  always have been.

Swept all nineteen fixtures with the same technique (page-height
scroll, then check every local `photos/*.jpg` `<img>`'s
`naturalWidth`): one genuine hold-out, `salon-rich`, where one image
stayed unloaded even after a full-page scroll. Investigated rather than
dismissed: that fixture's gallery is a `.scrollstrip`
(`overflow-x:auto`, the `scroll_gallery` composition) — a HORIZONTAL
scroll container my first pass never scrolled. Scrolling it
horizontally (`el.scrollLeft = el.scrollWidth`) loaded it immediately
(`naturalWidth: 768`, `complete: true`). Not a bug; a gap in the check.

Thirteen cached files were also found with a `.jpg` extension but real
PNG content (`file` command confirms: 1080×1080 and 810×1080 RGB PNGs).
Four of the thirteen are actually referenced (`roofer.html`,
`law-rich.html`); the other nine are orphaned copies from an earlier
`place_photos` list `_copy_photographs`'s `if not dest.exists()` never
cleans up — harmless disk clutter, not investigated further, since
nothing currently references them. Confirmed the four referenced ones
render correctly regardless of the extension mismatch (browsers sniff
real image content for `<img>`, not the URL's extension) — verified
directly, not assumed.

Added a permanent, browser-free standing test
(`test_every_referenced_photograph_is_a_real_non_empty_image`): every
`photos/*.{jpg,png,webp,gif}` reference in every committed page must
exist on disk, be non-empty, and sniff as a recognised image format
from its own first bytes — catches a missing, zero-byte, or garbage
file on every `make check` without needing a browser at all. It would
NOT have caught the og:image bug (that was a URL string malformed
inside a `<meta>` tag with no file reference at all) or the two
non-issues above (both real, valid files) — it catches a different,
narrower class: a page pointing at something that plainly is not a
photograph.

## Binding claims, pass or fail

| Claim | Result |
|---|---|
| The og:image rewrite bug reproduces exactly as diagnosed | **CONFIRMED** |
| Fix leaves every legitimate rewrite (img, full srcset, CSS url) intact | **PASSED** |
| Freshness guard skips (not fails) on an empty photo cache | **PASSED**, checked both directions |
| Every page's own photographs are genuinely visible offline | **PASSED** — two apparent failures were investigated and explained, not dismissed; one genuine gap (`salon-rich`'s horizontal strip) was found in the CHECK, not the bundle |
| Both hashes unchanged (ruler/rule/labels/held-out, render_snapshots.json) | **PASSED** — identical to the values captured before Phase 1 began |

`make check`: ruff clean, mypy clean, 968 passed, 12 xfailed.

# Round 6, Phase 2 — the weight-budget harness re-measured honestly

Same governing rule as Phase 1: measure, do not decide. No compression,
no gallery caps, no budget change — genuine breaches go to
`.reviews/DECISIONS-FOR-SHREYAS.md` item 2, not fixed here.

## 2a — two real bugs in the harness, not one

The diagnosed bug (the one this phase was scoped around): every
`/photo/<lead>/<n>` reference in a rendered page was measured on disk at
`photos_api.MAX_WIDTH` (2400px) regardless of which `srcset`/
`image-set` candidate a real mobile browser would actually select for a
390px-wide viewport — every fixture's weight was the cost of its
LARGEST tier, never the one a phone downloads. Fixed with
`_link_photographs_width_aware`: resolves each reference's own `?w=`
(defaulting to `MAX_WIDTH` exactly as `app.web.server`'s real `/photo/`
route does for a request with none) to `photos_api.nearest_width()`,
fetching whichever (photo, width) pair is not already cached.

A second bug, not diagnosed going in, found while building the
replacement: the old measurement was disk-based and only ever walked
`/photo/` references — every externally-hosted image a business's own
page links directly (a "recent jobs" block, a feature photo pulled
straight from their live site rather than through this project's own
proxy) was silently absent from the total. `roofer` alone carries 10+MB
of these, counted as zero before. Fixed with `_link_external_images` +
a new `.cache/external/` (content-hash-of-URL keyed, real bytes, `None`
returned rather than a placeholder on a genuine fetch failure — a
business's asset having moved is a real, disclosed fact, not something
to paper over).

Both fixes reproduced the exact og:image regex-corruption bug Phase 1a
fixed in `build_review.py` — in NEW code, not old: the first draft of
`_link_photographs_width_aware` had no lookbehind and glued a relative
path onto the port number in `render.absolute()`'s output the same way.
Fixed identically, `(?<![0-9A-Za-z])`. A dedicated test
(`test_the_og_image_absolute_url_survives_width_aware_linking`) asserts
this specific shape can never regress again in this file either.

Weight measurement itself moved from a disk-based sum to the real
DevTools Network domain: `Network.loadingFinished`'s `encodedDataLength`
per request, summed after a full-page scroll (to trigger every
`loading="lazy"` image) and, discovered checking `salon-rich`, a
horizontal scroll of any `.scrollstrip` gallery too — a plain vertical
scroll never reaches a horizontally-scrolling gallery's later images,
which would have UNDER-counted exactly the fixtures using that
composition.

A third, unrelated, previously-unknown bug was found blocking this very
re-measurement: `bare-trade` hung indefinitely on every attempt. Root
cause, found by comparing an isolated CDP reproduction against the real
measurement path: the synthetic `Input.dispatchMouseEvent` click
dispatched to sample INP was landing on a plain `<a href="https://www.
google.com/maps/...">` CTA with no JS handler — both of `bare-trade`'s
own CTAs are exactly this — and actually navigating the whole headless
tab to Google Maps mid-measurement, replacing the fixture's own document
before the weight-measuring scroll step ran against it. Fixed with a
capture-phase click guard installed via
`Page.addScriptToEvaluateOnNewDocument` (so it runs before the page's
own scripts): `preventDefault()` on any `<a href>` click, letting the
real click event still fire (INP is sampled from the event itself, not
the navigation) while the tab never actually leaves. Verified in both
directions: `git stash push -- tools/perf_census.py` reproduces the
real-browser test's failure
(`test_the_synthetic_inp_click_never_actually_navigates_the_tab`,
`AssertionError: the synthetic click navigated the tab away: https://
www.google.com/maps/search/?q=x`); `git stash pop` restores the passing
fix. Confirmed the fix resolves the actual hang: three consecutive
`bare-trade` runs, ~9.7s each, weight=584074 bytes every time.

A secondary, defensive measurement change made alongside these: OSM's
map-embed iframe (rendered for any fixture with lat/lon) made a real,
potentially slow external request during measurement — blocked at DNS
resolution (`--host-resolver-rules=MAP openstreetmap.org 127.0.0.1,...`)
so a third party's uptime can never hang or skew a measurement run,
matching the existing font-blocking rationale. Its own resource weight
is deliberately excluded from the total (already broken under
`--disable-gpu` per an earlier round's own finding, a WebGL-unsupported
error, unrelated to this round).

## 2b — all 19 re-measured

    barbecue-rich      LCP=   180ms  CLS=0.000  INP=    0ms  weight=  2182KB  BREACH: weight
    barbecue           LCP=   168ms  CLS=0.000  INP=    0ms  weight=  4272KB  BREACH: weight
    bare-trade         LCP=   180ms  CLS=0.000  INP=   24ms  weight=   570KB
    contractor-bare    LCP=   128ms  CLS=0.000  INP=    0ms  weight=   718KB
    dentist-rich       LCP=   164ms  CLS=0.000  INP=    0ms  weight=  1089KB
    dentist            LCP=   156ms  CLS=0.000  INP=    0ms  weight=   424KB
    hvac-rich          LCP=   160ms  CLS=0.000  INP=    0ms  weight=  1682KB
    hvac-second        LCP=   140ms  CLS=0.000  INP=    0ms  weight=  1021KB
    hvac               LCP=   200ms  CLS=0.000  INP=  128ms  weight=  1276KB
    law-rich           LCP=   188ms  CLS=0.000  INP=    0ms  weight=  4898KB  BREACH: weight
    law                LCP=   156ms  CLS=0.000  INP=    0ms  weight=   816KB
    restaurant-bare    LCP=   180ms  CLS=0.000  INP=   24ms  weight=  1345KB
    restaurant-casual  LCP=   136ms  CLS=0.000  INP=    0ms  weight=  1823KB
    restaurant-rich    LCP=   192ms  CLS=0.000  INP=   16ms  weight=  6544KB  BREACH: weight
    roofer-rich        LCP=   228ms  CLS=0.000  INP=  152ms  weight=   667KB
    roofer             LCP=   256ms  CLS=0.000  INP=    0ms  weight= 14032KB  BREACH: weight
    salon-rich         LCP=   216ms  CLS=0.000  INP=   24ms  weight=  3039KB  BREACH: weight
    salon              LCP=   172ms  CLS=0.000  INP=    0ms  weight=  2165KB  BREACH: weight
    threadbare         LCP=   116ms  CLS=0.000  INP=    0ms  weight=    59KB

    budgets: LCP<2500ms  INP<200ms  CLS<0.1  weight<2MB

Net effect of measuring honestly: 5 fixtures that used to breach under
the old (wrong-tier) method now clear (`hvac`, `hvac-rich`,
`hvac-second`, `restaurant-bare`, `restaurant-casual` — their old
"breach" was mostly the over-measured `/photo/` tier, not real gallery
weight), and 2 (`roofer`, `restaurant-rich`) are far WORSE than the old
number ever showed (their true weight is mostly external images the old
method never counted). Twelve of nineteen clear; seven are real. Full
per-fixture largest-contributor breakdown, and the actual decision
this table feeds, is in `.reviews/DECISIONS-FOR-SHREYAS.md` item 2.

## 2c — `KNOWN_BREACHES` updated to match

Mechanical once 2b's numbers were in. Old 12-entry list replaced with
the 7 fixtures genuinely over budget above.

Building item 2's per-fixture table for the decisions file needed more
than the aggregate weight number — "what the largest contributor is"
required a real photos-vs-external breakdown per resource, not a guess
from the total alone. A one-off diagnostic script (not committed —
reuses `perf_census.py`'s own page-building and CDP plumbing, adds
`Network.requestWillBeSent` tracking to map bytes back to URLs) found
that two of the seven KNOWN_BREACHES reasons, written before this
breakdown existed, were wrong about which contributor actually
dominates: `barbecue` (labelled "large photo gallery") is in fact 58%
external / 39% gallery (~2.4MB external vs ~1.7MB gallery of 4.3MB),
and `law-rich` (same label) is 67% external / 31% gallery (~3.3MB vs
~1.5MB of 4.9MB). Both corrected to name the actual dominant
contributor rather than repeat the assumption. This is the same class
of "measure honestly" fix Phase 2a made to the harness itself, applied
to a descriptive string rather than a number — a wrong claim about
which contributor is bigger is still a wrong claim, not a taste call.
`restaurant-rich`, `roofer`, `salon-rich`, `salon`, `barbecue-rich`'s
existing labels were checked against the same breakdown and confirmed
accurate as written. Verified after the correction:

    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[barbecue-rich-weight] - large photo gallery, genuine — gallery photos are the larger share (~1.5MB of 2.2MB)
    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[barbecue-weight] - external feature-block images from the business's own live site are the larger share (~2.4MB of 4.3MB, vs ~1.7MB gallery) — corrected from an earlier, less precise 'photo gallery' label once the actual per-resource split was measured
    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[law-rich-weight] - external feature-block images from the business's own live site are the larger share (~3.3MB of 4.9MB, vs ~1.5MB gallery) — corrected from an earlier, less precise 'photo gallery' label once the actual per-resource split was measured
    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[restaurant-rich-weight] - external feature-block images from the business's own live site, genuine — the largest single contributor once measured honestly (~5.4MB of 6.5MB)
    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[roofer-weight] - external feature-block images from the business's own live site, genuine — 14MB, the worst in the corpus, almost none of it the /photo/ proxy (~10MB external of 14MB)
    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[salon-rich-weight] - large photo gallery, genuine — almost entirely gallery photos (~3.0MB of 3.0MB, no external images)
    XFAIL tests/test_performance_budgets.py::test_fixture_holds_its_budget[salon-weight] - large photo gallery, genuine — gallery photos are the larger share (~1.3MB of 2.2MB)
    ======================== 71 passed, 7 xfailed ==========================

One measurement inconsistency surfaced building this same breakdown,
disclosed rather than hidden: `hvac-rich` (well under budget either
way) measured 1682KB in the committed baseline and 1982KB in the
separate diagnostic pass — every other fixture matched the baseline
within a few KB. Not investigated further since it does not change
which side of the 2MB line anything falls on; noted in
`.reviews/DECISIONS-FOR-SHREYAS.md` item 2 as a caveat on that one row.

## 2d — genuine breaches: laid out as a decision, not fixed

Per this round's own rule: no photo compression, no gallery cap, no
budget change attempted here regardless of how clearly any of the seven
breaches. All seven, their cost, and the options for each are in
`.reviews/DECISIONS-FOR-SHREYAS.md` item 2.

## Binding claims, pass or fail

| Claim | Result |
|---|---|
| The diagnosed wrong-tier `/photo/` measurement bug reproduces and is fixed | **CONFIRMED / PASSED** |
| External images are now counted; verified via a fixture (`roofer`) known to carry them | **PASSED** |
| The og:image absolute-URL corruption cannot recur in this file's own linking code | **PASSED**, dedicated test |
| `bare-trade`'s hang is a real, previously-unknown click-navigation bug, not environment flakiness | **CONFIRMED** — reproduced identically 3x before the fix, resolved deterministically 3x after |
| The click-navigation fix is proven by a real-browser test that fails without it | **PASSED** — confirmed via `git stash` in both directions |
| `KNOWN_BREACHES` matches the newly measured reality exactly, no stale or missing entries | **PASSED**, `test_no_stale_known_breach` + 71 passed / 7 xfailed |
| No page, composition, budget, or copy changed | **PASSED** — this phase touched only `tools/perf_census.py`, its tests, and the breach list |
| Both hashes unchanged (ruler/rule/labels/held-out, render_snapshots.json) | **PASSED** — identical to Phase 1's captured values |

`make check`: ruff clean, mypy clean, (pending final combined run before commit).
