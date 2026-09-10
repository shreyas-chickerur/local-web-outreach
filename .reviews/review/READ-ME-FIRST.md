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

## What's deliberately not built

- **Before-and-after, the last of nine contractor facts** — it needs a
  paired photo (a labelled before, a labelled after, of the same job)
  nothing in the current material carries, and approximating one without
  that pairing is the same invented-evidence failure the credential fix
  refuses to do.
- **Compositions beyond `services` and `reviews`** — `gallery`, `about`,
  and `hours` still have exactly one layout regardless of content shape.
  BRIEF §5 asks for two to four per section; this ships two or three, for
  two sections.
- **The model choosing a heading from a table** — headings are deterministic
  per trade (`app/site/tradeprofile.py`), not a decision the identity call
  makes. Consistent with how the call-to-action wording already worked
  before this session touched it, but a disclosed reduction from what was
  asked.
- **A judging round.** Agreement is still 0 of 0, deliberately skipped
  two passes running now — every verdict checked so far has come back
  DIFFERENT, so judging again would spend real money to reconfirm what
  is already known rather than test anything new. See
  `tests/test_the_instrument_reproduces.py`. Recommended, not attempted:
  a full round is overdue now that this round moved the corpus twice.
- **A full (not sampled) design review, and auto-repair of what it
  finds.** The four-fixture sample's genuine findings are fixed; running
  it across all nineteen (57 model calls) and building auto-repair for
  the deterministic findings — both explicitly proposed for a later pass,
  neither attempted here.
- **Content selection and provenance** (Slice D's remaining items:
  letting the model select and order its own sentences, a provenance
  check replacing `unsupported()`), **backdrops, motion, video, and the
  conversational workspace** — Slices D (partly), E, H. Not started.
- **Growing the corpus past nineteen fixtures.**

## Numbers not to trust, and why

- **"61.52% same-trade distance"** is a real, current measurement under
  this round's redecide (up from 56.10% before this round's photo
  preference, menu fallback, and newly-verified contact facts moved the
  corpus), but it is still the ONLY reading this exact axis set has ever
  taken — there is no prior number under it to compare against. The
  closest pair this corpus has ever produced is `barbecue`/`barbecue-rich`
  at 17% apart (eight of twelve axes shared) — named because BRIEF's own
  convention is to report the closest pair, not because it was judged.
- **Agreement is 0 of 0, and no judging round has run for two passes
  now, on purpose.** Every verdict checked across both passes came back
  DIFFERENT — judging again would spend real money to confirm what a
  redecide already implies rather than test anything new, so both
  redecides retired every live verdict and replaced none of them. A
  rank-based score needs at least one "same" verdict to rank against
  something. Take "the vector agrees with a human" as unproven, not as
  disproven and not as confirmed — and overdue for a real check now that
  the corpus has moved twice with nothing re-judged.
- **The held-out third is currently empty**, not stale — every held-out
  verdict was retired across two redecides and none has been repopulated.
  This is disclosed in `tests/test_the_instrument_reproduces.py`, not
  hidden.
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
showing it; and a corpus-wide measurement tool double-counting one of
its own rows into a headline percentage (`.reviews/slice-b-
predictions.md`, "Round 3"). None of these were caught by any test
before someone looked — or, this round, before a measurement tool's own
output was checked against a second, independent read of it. Trust what
you see on the page over what any panel, test, or number claims about
it, and say so if they don't match.
