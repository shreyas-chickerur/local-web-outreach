# Review — the headline number, and what it is made of

Reviewing `347edb9` and the second pass on top of it. Recorded here rather than
left in a chat window: a review that only exists in a chat window did not
happen.

Opening observation from the review, and it is the one thing worth keeping in
sight: **same-trade identical has gone 52 → 48 → 38 → 30 under a constant
distance ruler.** That is the metric §2 exists to move, and it is the first
time in this project it has actually moved. What follows is mostly about
whether the last step of that is real.

---

## 1. `threadbare` is inflating the headline — CONFIRMED, and the headline changes

The arithmetic in the review is exact. "Same trade" is the trade *bucket*, not
the trade string: food 3, desk 2, trade 4 — three, one and six pairs. That puts
`threadbare` in the four-fixture bucket and into **three of the ten pairs the
headline is made of.**

Its three pairs are the three most distant in the whole same-trade set:

     100%  contractor-bare  threadbare
      90%  roofer           threadbare
      75%  hvac             threadbare
      85%  barbecue         restaurant-rich     <- the most distant real pair
      ...
      45%  contractor-bare  roofer

An empty page is maximally unlike everything, for reasons that have nothing to
do with design. Measured both ways, and across the rule change so the exclusion
cannot be doing the work on its own:

    corpus                          all 10 pairs      without threadbare (7)
    f3ce823, before the rule fix    38% identical     42% identical
    347edb9, after --redecide       30% identical     38% identical

**The honest headline is 38% identical, improved from 42%.** The rule fix is
real either way, and roughly half the gain I reported was the empty fixture.
Re-pinned to the scored number; the all-pairs figure still prints underneath,
labelled so the exclusion is visible rather than the better number being the
one on show.

## 2. `threadbare` is excluded from every score — AGREED, and excluded not deleted

It was the "same" side of four of the six inversions. A page with nothing on it
cannot answer "same site or different studios"; there is no design to compare,
only an absence.

`agreement.UNSCORED` is one definition, imported by the census and by the
reproducibility test rather than restated in each. Its three verdicts are
RETIRED in `pairs.json` — the mechanism built for exactly this in the previous
commit, used for the first time — not re-judged and not deleted. The fixture
stays: it is the only proof the floor refuses a condemned photograph, and the
only page that opens on type alone. It is evidence about the generator; it was
never evidence about sameness.

One of the retired pairs was in the held-out third, so `HELD_OUT` is re-pinned.
That is the allowed path and it has to be said out loud, which is what the
guard's failure message demands. It was an `unsure` verdict and contributed
nothing to any score.

    agreement   19/33 -> 14/22 (64%)
    inversions  dentist/law, hvac/roofer
    blind spot  3 comparisons -> 2, both hvac/roofer

## 3. `dentist`/`law` — answered directly, and the answer is a regression

**The verdict changed in the re-judge**: `different` under 449b9ddb, `same`
under 371f24fa. But that is not the explanation, because **the pages changed
too**. At `f3ce823` `dentist` opened on `proof` and `law` on `facts` — the
difference the first-screen axis created, and the reason the inversion
resolved. After `--redecide` **both open on `proof`.**

So this is not a scoring artefact and not only an instrument failure. The
corpus lost a difference it had. The generator regressed, and here is why:

    law vs dentist differ on: accent, action, compositions, leads_with,
                              mood, section_order
    highly weighted axes:     first_screen, mood
    satisfied via:            mood
    gate collides?            No

**`mood` alone satisfied the "weighted highly" requirement** that this same
commit added. And what `mood` does visibly for this pair is colour — teal
against burgundy — which is precisely what the judging rule in `pairs.json`
says cannot alone make a different site. The rule I landed to stop a pair
passing on invisible differences let a pair pass on a difference the judge had
already ruled out.

The pre-registration did its job. A dip was allowed; a dip with `dentist`/`law`
still inverted was not, and it is inverted. Recorded in
`.reviews/slice-b-predictions.md` with the next test pre-registered rather than
fixed inline, because the fix re-decides the corpus again and the held-out
third is the thing that can score it.

## 4. The two smaller ones — both fixed

**The census fingerprint table** omitted `first_screen`, the heaviest axis at
2.5 and the one that had just landed, and still named `layout_bias`, which
stopped being an axis two commits ago. A reader could not reconcile the printed
vectors with the distances under them. It now derives the columns from
`fp.AXES`, so an axis cannot be silently missing from it again; the two long
values print on their own lines rather than being truncated.

**The agreement figure crossing a label change** now prints the same kind of
guard the distance baseline has: the census names the previous labels and the
previous reading and says the number is the first of a new series, not the old
one having fallen.

## And the one to record properly

**Reweighting cannot reach two of the twenty-two comparisons.** A pair judged
the same site that differs on a superset of a different-pair's axes is further
apart under any non-negative weighting — exact, no threshold, no search. Both
surviving cases are `hvac`/`roofer`, and the axes the vector counts where the
judge did not are `accent` and `hero_subject`: colour and subject.

It is `agreement.unreachable()`, it prints under BLIND SPOT on every census
run, a test pins it, and it is written into `BRIEF` §1. It is the argument
*for* type treatment: the axis set is too thin to express the judgement, and no
amount of tuning changes that.
