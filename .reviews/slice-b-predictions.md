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
