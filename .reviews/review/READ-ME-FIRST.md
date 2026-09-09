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

**Slice C (trade-specific structure) is barely started.** Four of nine
contractor facts exist (`app/site/contractorfacts.py`) — licensed/insured,
emergency availability, warranty, free estimate — and only three of nineteen
fixtures (`hvac-rich`, `hvac-second`, `roofer-rich`) actually surface one,
because that's how many had the phrase in their own published text. A
dentist's page and a law firm's page do not yet get anything trade-specific
beyond a heading. If you want to see where this whole approach is thinnest,
open `dentist.html` or `law.html` and compare the "How we can help" card
grid to what a real practice's site would actually need to say (insurance
accepted, which procedures, financing) — none of that exists yet.

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

## What's deliberately not built

- **Five of nine contractor facts** (service area, before-and-after,
  financing, manufacturer badges, response time) — each needs a kind of
  evidence (a service radius, a paired photo, a named lender, a badge image,
  a stated callback window) the current material doesn't carry, and
  approximating one without it is the "invent a licence number" failure this
  project explicitly refuses to do.
- **Compositions beyond `services` and `credentials`** — every other section
  (`reviews`, `gallery`, `about`, `hours`) has exactly one layout regardless
  of content shape. BRIEF §5 asks for two to four per section; this ships
  two, for two sections.
- **The model choosing a heading from a table** — headings are deterministic
  per trade (`app/site/tradeprofile.py`), not a decision the identity call
  makes. Consistent with how the call-to-action wording already worked
  before this session touched it, but a disclosed reduction from what was
  asked.
- **Content completeness, copy selection, backdrops, motion, video, the
  conversational workspace** — Slices D, E, G, H, and the rest of F. Not
  started at all.

## Numbers not to trust, and why

- **"53.33% same-trade distance = 47% identical"** is a real, current
  measurement, but it is the ONLY reading this ruler has ever taken under
  the current corpus — there is no prior number under this exact axis set
  to compare it against. "Slice C should move this" is the standing claim;
  nothing has tested that yet.
- **Agreement is 0 of 0.** This is not "untested" — eleven pairs were
  checked by hand this round (the closest pairs by distance), on top of
  sixteen the round before — it means no "same" verdict has ever been found
  to rank against. A rank-based score needs at least one on each side. Take
  "the vector agrees with a human" as unproven, not as disproven and not as
  confirmed.
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
