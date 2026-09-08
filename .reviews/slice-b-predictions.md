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
