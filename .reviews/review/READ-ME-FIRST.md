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

**A sampled design review (Slice G, four fixtures, not the full nineteen)
surfaced real defects this project has no other way of catching.** Two
kinds, and they are different problems. First, layout collisions the
generator itself causes: on `law`, the nav links sit directly on top of
the attorney's face in the hero photo, and body text is hidden behind a
stats banner further down the page; on mobile, `hvac` and
`restaurant-rich` both show a CTA button duplicated and cropped at the
viewport edge. These are rendering bugs, not content problems, and
nothing in this repository's test suite would have caught them — they
only show up in a screenshot. Second, and more interesting: `hvac`'s own
published "about" text claims "over 20,000 5 star reviews", while the
structured review count sitting one section away says 6,203 — both are
real numbers from the same business's own Google listing, not anything
this project invented, and nothing here cross-checks one published fact
against another for internal consistency. That is a materially different
failure mode than the credential-claims defect above (that was an
UNVERIFIED claim; this is two VERIFIED claims that contradict each
other), and this pass found it only because a vision model was asked to
read the whole page rather than because a rule looked for it. Neither
class of finding has been fixed this pass — Slice G was sampled
specifically to answer whether running it in full is worth the cost, not
to act on what it found. See `.reviews/first-pass.md` for the full
finding list and the recommendation.

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
  this pass — every verdict checked so far has come back DIFFERENT, so
  judging again would spend real money to reconfirm what is already known
  rather than test anything new. See `tests/test_the_instrument_reproduces.py`.
- **Content completeness, copy selection, backdrops, motion, video, the
  conversational workspace, and a full (not sampled) design review** —
  Slices D (mostly), E, G (beyond the four-fixture sample), H, and
  growing the corpus past nineteen fixtures. Not started at all.

## Numbers not to trust, and why

- **"56.10% same-trade distance"** is a real, current measurement under
  this pass's redecide (up from 53.33% before Batch B's new facts and
  compositions moved the corpus), but it is still the ONLY reading this
  exact axis set has ever taken — there is no prior number under it to
  compare against, so "Slice C moved this in the right direction" is a
  plausible read, not a proven one.
- **Agreement is 0 of 0, and no judging round ran this pass, on purpose.**
  Eleven pairs were checked by hand two rounds ago (on top of sixteen the
  round before that) and every single one came back DIFFERENT — judging
  again would spend real money to confirm what a redecide already implies
  rather than test anything new, so this pass's redecide retired all
  eleven live verdicts and replaced none of them. A rank-based score needs
  at least one "same" verdict to rank against something. Take "the vector
  agrees with a human" as unproven, not as disproven and not as confirmed.
- **The held-out third is currently empty**, not stale — every held-out
  verdict from the prior round was retired (the rendering changed under it
  twice this session) and none has been repopulated yet. This is disclosed
  in `tests/test_the_instrument_reproduces.py`, not hidden.
- **Ratings, review counts and "dishes on the menu" tallies** on each page
  are read from Google's own data at the time each business was researched —
  they will have drifted since. Nothing here is refreshed automatically.
- **The `.captured.json` manifest and `artifacts/` directory are not
  committed** — regenerate the full contact sheet and this review bundle
  with `tools/contact_sheet.py` and `tools/build_review.py` if either looks
  stale; both are meant to be cheap to re-run (no model calls against
  frozen fixtures).

## If you find something that looks wrong

It might be. Two real ones were found and fixed already: the workbench's
"plan" panel disagreeing with the rendered page on section order for
seventeen of nineteen fixtures, found verifying this bundle
(`.reviews/plan-page-disagreement.md`); and a licensure claim printed with
no corroboration on six pages, found by a reader of the corpus itself
rather than by any test in this repository
(`.reviews/slice-c-credential-claims.md`). Trust what you see on the page
over what any panel, test, or number claims about it, and say so if they
don't match.
