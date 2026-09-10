# Start here

This is nineteen generated sites, side by side, so you can form your own
opinion about whether this is worth a thousand dollars to a small business —
not a demo of one good one.

## Open, in this order

1. **`index.html`** — every business, one card each: the model's own
   rationale in plain English, the signature device's own justification when
   it has one, and a plain list of what's actually on the page. No axis
   names anywhere.
2. **Pick two or three cards whose rationale sounds similar** (a barbecue
   place and a smokehouse, the two law firms, the two HVAC companies) and
   open both standalone pages. This is the real test: does either one look
   like it came out of the same template as the other, once you're actually
   looking at the page rather than reading about it?
3. **`../sheet/index.html`** — the whole corpus at once, half-scale, with
   every axis value printed under each thumbnail. This is the instrument's
   own view of itself — useful once you've formed your own opinion from step
   2, to see whether the axes explain what you noticed or missed something.

## The weakest point, named directly

**A licensure claim shipped unverified, on six of nineteen pages, until this
session found and fixed it.** `signature.py`'s `stamp` device printed
"Licensed & insured" / "Registered practice" / "Admitted to the bar" from
`trade_kind` alone — nothing checked it was true. The content gate
(`render.unsupported`) couldn't have caught it either: its claim pattern
had no entry for credential language at all. Both are fixed now (the
pattern widened; the device only renders when the business's own text
actually corroborates it — see `.reviews/slice-c-credential-claims.md`),
and a standing test holds the invariant across the whole corpus going
forward. Named here anyway, not just in its own handoff, because it is the
most serious thing this session found: a specific, checkable, false
professional claim on a page meant to be shown to a stranger. **The honest
residual risk:** the corroboration is deliberately strict (an exact phrase
match against the business's own published text, never inferred), which
means it is proven to REMOVE a false claim and not yet proven to CARRY a
true one — in this 19-fixture corpus, not one business's own copy happens
to use a phrasing the patterns catch, so `stamp` currently renders on
nobody. A business that says "TX-licensed contractor" rather than "licensed
and insured" would lose the mark even with a real claim to make. That is
the right failure direction (silence over a false assertion) but it is
still a gap, not a solved problem.

**Slice C (trade-specific structure) is now eight of nine facts, plus
real composition variety — but still corroborated-or-nothing, and that
discipline has a cost.** A cost-minimising pass (`.reviews/first-pass.md`)
added service area, financing, a named manufacturer certification, and
response time to the original four, each matched only against a
business's own published text, never inferred. The ninth — before-and-
after — is still not built: it needs a PAIRED photograph (a labelled
before and a labelled after of the same job), which nothing in this
corpus's photo data carries, and approximating one without that pairing
is the same "invent a licence number" failure the credential fix above
exists to prevent. `services` and `reviews` now each have a genuine
second/third composition keyed to content shape, and gallery/contact
headings vary by trade. Still true: whether a fact fires depends entirely
on whether the business happened to use a matching phrase, so a real
dentist's or law firm's page can still show nothing trade-specific beyond
a heading if their own copy never says the words. Open `dentist.html` or
`law.html` and check for yourself.

**The instrument that judges "do these look the same" has never found a
genuine collision in this corpus.** Zero same-trade or cross-trade pairs,
of eleven checked by hand this session (on top of sixteen checked the
session before, all since retired against a rendering that has since
changed twice), read as "one studio" to a blind judge. That is either the
diversity gate working exactly as intended, or a sign the corpus is still
small enough that collisions haven't caught up with it yet. Both are true;
which one matters more is a question for more fixtures, not more code. One
attempted redecide this session DID produce a genuine unresolved collision
(two HVAC/roofing pages, honestly flagged by the gate itself rather than
hidden) before a retry cleared it — the gate's failure mode is disclosure,
not silent collision, which is the property that matters most.

**The sampled design review's findings are fixed — one of them was a
tooling artifact, and chasing it down found a second, real bug of the
same shape.** `law`'s nav sitting on the attorney's face is fixed
(`.hero.first-proof` gets a solid nav ground, like every other position
that puts a photo up top). A quote-truncation bug that cut a review
mid-word ("outstanding" -> "outta") — very likely what a design review
actually saw and described as "cut off" text — is fixed with a
word-boundary truncation. The "duplicated CTA cropped at the mobile
edge" finding turned out not to be a page defect at all: Chrome's
headless `--screenshot` mode silently clamps any viewport request under
500px to exactly 500, so every "mobile" screenshot this project has
ever taken — this review's included — was captured 110px wider than
labelled and cropped on output. Fixed properly (a real sub-500px capture
path over the DevTools protocol, `tools/contact_sheet.py`), and
verifying it properly found a real version of the same defect on
`law-rich`: a CSS grid with a genuine 570px minimum, wider than any
phone, that grew the whole hero instead of wrapping — fixed with one
declaration. A standing test (`test_no_element_collides_with_another.py`)
now checks every fixture at three widths for a clipped control or text
painted over by another element.

**The contradiction gap named here previously is closed, and the same
class of bug was checked for corpus-wide.** `hvac`'s own "about" text
claimed 20,000 reviews against a corroborated count of 6,203 two
sections away — a genuine internal contradiction between two backed
facts, distinct from the credential-claims defect above (that was one
UNVERIFIED claim; this was two VERIFIED ones disagreeing). Fixed: a
sentence stating a review count that contradicts the corroborated value
is dropped before it reaches any section, never rewritten. A corpus-wide
scan before writing the fix found this was the only instance in the
19-fixture corpus.

**A second false-content bug, the same shape as the credential claim,
found acting on the content census and fixed on five fixtures.**
`law-rich` was rendering "12 dishes on the menu" at prices of $812, $55
and $49 — every one actually a line off the firm's own settlement-results
page, not a menu. The extraction that builds `menu_items` anchors on any
bare dollar amount as the one unambiguous signal of a priced item, which
is sound for a restaurant and knows nothing about what business it is
reading. The same false positive was checked for and found on four more
fixtures — a dental promo, a plumbing coupon, a financing banner, an
insurance estimate, none of them a menu. Fixed by gating menu content on
`trade_kind == "food"` at both places it could reach the page. Disclosed
here because it is the same class of defect as the licensure claim
above — invented-sounding structure that was never actually true for the
business showing it — just caught by acting on a measurement tool
rather than by reading the corpus by eye.

**The content census itself undercounted, in a way that happened to look
right.** Its own grand-total line was adding a subset row
(`own_site_photos`) into the total a second time, on top of the "photos"
row it is explicitly a subset of — a real double-count that had been
quietly inflating every "share of published material reached the page"
percentage this project has quoted, and it did not have to change the
headline number to be wrong: 556/766 and the corrected 556/762 both
round to "73%". Fixed, along with two lines that had gone stale the
moment the fixes below shipped (`menu_media`'s row still said "read by no
section builder" after one started reading it; the feature-block cap's
row still said "4" after it was raised to six) — the same "two copies
drift apart" failure this project keeps finding, this time in its own
measurement tool.

**Round 4's full design-review sweep (19 fixtures, not the 4-fixture
sample) found a mislabeled heading on four real fixtures, and a second,
independent copy of a text-truncation bug already fixed once.** A
roofer, two HVAC contractors, and a law firm's own "services" section
was headed "What we cook and serve" — the restaurant heading — because
one function (`_offer_heading`) read `if m.menu_items` alone, without
the `trade_kind == "food"` gate Round 3 already added everywhere else
after the same underlying extraction misread a law firm's settlement
figures as menu prices. Fixed at the root; a fifth affected fixture
(`dentist`) the design review never happened to flag came along free.
Separately, `signature.py`'s big pull-quote device had its own,
never-touched copy of the word-boundary truncation bug Round 3 fixed
for review cards — on `hvac`'s real testimonial it produced "...
knowledgeable. H" with a decorative quote mark glued to the cut. Fixed
the same way; a related styling issue (the decorative quote marks
themselves reading as stray letters in this typeface) fixed alongside
it. A third finding — a broken map embed on four fixtures — turned out
NOT to be a site defect: reproduced under a controlled test as a pure
artifact of `--disable-gpu`, the flag every screenshot tool in this
project passes for stability. No real visitor's browser carries that
flag. Disclosed, not fixed — there is nothing in this project's own
code responsible for it. Full account: `.reviews/round-4.md`.

**This review bundle itself was stale for the whole of Round 4, not
just the five fixtures with a visibly wrong heading.** Every one of the
nineteen committed pages here predated Phase 1's copy-selection changes,
Phase 2's Slice E CSS, and Phase 3a's two render fixes — `dentist.html`
still read "What we cook and serve" being the only one anyone had
actually noticed by eye. A freshness guard now exists
(`tests/tools/test_build_review.py`) that fails whenever a fresh render
of a fixture no longer matches the committed page, confirmed to fail
against the stale bundle before it was regenerated. If you are reading
this, the guard passed on the commit that shipped it.

**The three "unreachable" comparisons Round 4 left at zero — corrected,
this file having been wrong about that — trace to one contradiction in
the verdict set, not a missing axis.** `roofer`/`hvac-rich`'s own "same"
reasoning names an order-swap between two sections and a small extra
element, and dismisses both; the same two signals were each
independently sufficient to call three OTHER pairs "different"
(`dentist`/`law`, `roofer-rich`/`hvac-rich`, `law`/`law-rich`). No axis
was built on the strength of this. `roofer`/`hvac-rich` is the one live
verdict most worth a fresh, careful look in a future judging round
rather than a same-session flip.

- **Before-and-after, the last of nine contractor facts** — it needs a
  paired photo (a labelled before, a labelled after, of the same job)
  nothing in the current material carries, and approximating one without
  that pairing is the same invented-evidence failure the credential fix
  refuses to do. Re-checked as of Round 4: still no fixture's vision data
  carries the pairing.
- **Compositions beyond `services` and `reviews`** — `gallery`, `about`,
  and `hours` still have exactly one layout regardless of content shape.
  BRIEF §5 asks for two to four per section; this ships two or three, for
  two sections.
- **The model choosing a heading from a table** — headings are deterministic
  per trade (`app/site/tradeprofile.py`), not a decision the identity call
  makes. Consistent with how the call-to-action wording already worked
  before this session touched it, but a disclosed reduction from what was
  asked.
- **Growing the corpus past nineteen fixtures.**

**Built this round (Round 4), previously listed here as not built:**
copy selection and a real provenance layer (Slice D's remaining items —
the model now picks and orders a business's own sentences by index,
never retyping, so verbatim provenance holds by construction); the
backdrop preference ladder, motion, and a separate human-review capture
tool (Slice E — video is still dormant, no extraction path gathers one
yet, disclosed rather than faked); the full 19-fixture design review
sweep and auto-repair of what it found, by class (Slice G — two real
render bugs fixed, one finding run to ground as a capture-tooling
artifact and disclosed rather than "fixed"); a real judging round,
rebuilding the ground truth from zero live verdicts. Full account in
`.reviews/round-4.md`.

**Built this round (Round 5), the last item BRIEF §5 named — the
conversational workspace (Slice H).** The opening rationale
(`_build_opening()`) turned out to already be working since Slice F,
just untested; a standing test was added rather than a feature that
already existed. New this round: `app/site/reply.py` grounds every
reply in the `IterationResult` alone — structurally proven never to see
the rendered page, since the function's own signature has no place for
one — and turns an unmet, contradicted, or unrecognised instruction into
a question rather than a silent no-op or a passive list. `app/store/
preferences.py` accumulates a style preference across leads (an exact
phrase said on three or more) and offers it to the next lead's opening
call as a consideration, never a constraint — proven, not assumed, to
leave this fixture corpus untouched (the frozen-replay check every
fixture already hits returns before the preference is ever looked at).
Full account in `.reviews/round-5.md`.

**Round 6 — a hand-review pass, deliberately scoped to work with a
right answer only.** Two real bugs fixed in this bundle itself, neither
a rendering change: the og:image meta tag's absolute URL was corrupted
on 17 of 19 pages (metadata only, invisible on the page — see below);
the freshness guard that regenerates this bundle failed on any machine
with an empty photo cache, an environment artifact, now a clear skip
instead. Every page's own photographs were verified to genuinely load
offline, not just exist on disk. The performance harness had two real
bugs of its own (see the weight-budget bullet below, corrected). No
composition, heading, photo, or budget changed — every question that
needed a human's own judgment (the one contested pair, the weight
budget, remaining single-composition sections, the ninth contractor
fact, growing the corpus, what the agreement figure is and isn't
evidence of) was written up with evidence rather than decided:
`.reviews/DECISIONS-FOR-SHREYAS.md`. Full account in
`.reviews/round-6.md`.

## Numbers not to trust, and why

- **"61.52% same-trade distance"** is unchanged since the round before
  this one — Round 4 touched content selection, performance, and the
  ground truth, not any axis or decision, so there was no redecide and
  nothing here to move. The closest pair this corpus has ever produced,
  `barbecue`/`barbecue-rich` at 17% apart (eight of twelve axes shared),
  was JUDGED this round, not just reported — a stranger scrolling both
  whole pages called it "same," which is the one case in the corpus
  where the vector's sense of "close" and a stranger's agree.
- **Agreement is no longer 0 of 0 — Round 4 rebuilt it from zero live
  verdicts.** Fifteen fresh pairs, judged blind from whole-page renderings:
  22/26 (85%) scored against every live verdict, 9/11 (82%) scored against
  the held-out third alone (the number that actually says something about
  generalising). Not a clean pass: every inversion traces to one disclosed
  pair, `roofer`/`hvac-rich`, judged "same" by a stranger's eye but placed
  69% apart by the vector — nearly the corpus-wide 80% mean. Reported as
  found, not tuned toward or argued away. See `.reviews/round-4.md` and
  `tests/fixtures/pairs.json`.
- **The held-out third is no longer empty** — twelve of the fifteen new
  verdicts landed there by a fixed hash of the two slugs, computed before
  any verdict was recorded. `tests/test_the_instrument_reproduces.py`
  pins the exact set.
- **Three comparisons no reweighting of the current axes can ever get
  right, all tracing to `roofer`/`hvac-rich` — investigated this round,
  and the answer is labels, not axes.** `roofer`/`hvac-rich`'s own "same"
  reasoning names an order-swap between two sections and an extra small
  element, and dismisses both as not enough to call it different — but
  the same two signals were each independently sufficient to call three
  OTHER pairs "different" (`dentist`/`law`, `roofer-rich`/`hvac-rich`,
  `law`/`law-rich`). That is a self-contradiction in the verdict set, not
  evidence the axis set is missing something — no axis was built on the
  strength of this. `roofer`/`hvac-rich` is the one live verdict most
  worth a fresh, careful look in a future judging round.
- **Seven of nineteen fixtures breach the 2MB page-weight budget —
  corrected in Round 6 from a wrongly-measured twelve.** The harness
  itself had two real bugs: it measured every `/photo/` reference at
  the largest tier regardless of what a mobile `srcset` would actually
  select, and it silently never counted a business's own
  externally-hosted images (a "recent jobs" block pulled straight from
  their live site) at all. Fixed with the real DevTools Network domain
  rather than a disk estimate, and the honest number moved in BOTH
  directions: five of the old twelve clear now (`hvac`, `hvac-rich`,
  `hvac-second`, `restaurant-bare`, `restaurant-casual` — their old
  "breach" was mostly the over-measured proxy tier), and `roofer`/
  `restaurant-rich` are far WORSE than the old number ever showed
  (their true weight is mostly external images the old measurement
  never counted). The seven that remain split into two different
  problems — three dominated by this project's own photo gallery,
  four by a business's own externally-hosted images — with different
  costs to fix either. See `.reviews/DECISIONS-FOR-SHREYAS.md` item 2
  for the full per-fixture table and the options, none taken. Pinned as
  disclosed, `strict` `xfail` in `tests/test_performance_budgets.py`
  either way — an actual fix would show as a hard failure (XPASS), so
  drift in either direction is caught. LCP, INP, and CLS are clean on
  all nineteen fixtures.
- **The content census's "77% of published material reaches the page"**
  is corrected for a double-count this round found in the census tool
  itself (a subset row was being summed into the total twice — see
  above) — the PRIOR reading of "73%" was against an inflated denominator
  the whole time, so this is not quite an apples-to-apples "+4 points",
  though the true corrected baseline (73%, recomputed) to this round's
  77% is a real improvement from four specific, disclosed fixes.
- **Ratings and review counts** on each page are read from Google's own
  data at the time each business was researched — they will have drifted
  since. Nothing here is refreshed automatically.
- **The `.captured.json` manifest and `artifacts/` directory are not
  committed** — regenerate the full contact sheet and this review bundle
  with `tools/contact_sheet.py` and `tools/build_review.py` if either looks
  stale; both are meant to be cheap to re-run (no model calls against
  frozen fixtures).

## If you find something that looks wrong

It might be. Real ones found and fixed so far: the workbench's "plan"
panel disagreeing with the rendered page on section order for seventeen
of nineteen fixtures (`.reviews/plan-page-disagreement.md`); a licensure
claim printed with no corroboration on six pages
(`.reviews/slice-c-credential-claims.md`); two verified facts
contradicting each other on one page, and a scraper's menu-item
extraction mistaking a law firm's settlement amounts for dinner prices
on five pages; a nav floating over a photograph with no way to guarantee
it stayed legible, and a CSS grid with a wider minimum than the phone
showing it; a corpus-wide measurement tool double-counting one of its
own rows into a headline percentage (`.reviews/slice-b-predictions.md`,
"Round 3"); and, this round, the same menu-price extraction bug
resurfacing in a heading function that never got the earlier fix, plus
an independent copy of a review-quote truncation bug already fixed once
elsewhere (`.reviews/round-4.md`). In Round 6: this bundle's own
og:image URL corrupted on 17 of 19 pages (metadata only); the
performance harness measuring the wrong `/photo/` tier and silently
skipping externally-hosted images entirely; a synthetic click used to
measure page performance actually navigating a fixture's tab away to
Google Maps mid-measurement, on any page whose call-to-action is a
plain external link; and, in the live workbench (not this bundle), an
operator-facing diagnostic string cut off mid-sentence with no word
boundary — the THIRD independent occurrence of that exact defect shape
in this codebase (`.reviews/round-6.md`). None of these were caught by
any test before someone looked — or, this round, before dry-running the
review checklist itself, exactly as you are about to. Trust what you
see on the page over what any panel, test, or number claims about it,
and say so if they don't match.
