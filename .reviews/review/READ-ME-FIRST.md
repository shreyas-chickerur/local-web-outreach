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
genuine collision in this corpus.** Zero same-trade or cross-trade pairs, of
sixteen checked by hand this session, read as "one studio" to a blind judge
— including the closest pair the corpus has ever produced (two personal-
injury firms sharing eight of eleven axes). That is either the diversity
gate working exactly as intended, or a sign the corpus is still small enough
that collisions haven't caught up with it yet. Both are true; which one
matters more is a question for more fixtures, not more code.

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

- **"55.52% same-trade distance = 44% identical"** is a real, current
  measurement, but it is the ONLY reading this ruler has ever taken — there
  is no prior number under the current axis set to compare it against.
  "Slice C should move this" is the standing claim; nothing has tested that
  yet.
- **Agreement is 0 of 0.** This is not "untested" — sixteen pairs were
  checked by hand, including the five closest theoretical collision
  candidates in the whole corpus — it means no "same" verdict has ever been
  found to rank against. A rank-based score needs at least one on each side.
  Take "the vector agrees with a human" as unproven, not as disproven and
  not as confirmed.
- **Ratings, review counts and "dishes on the menu" tallies** on each page
  are read from Google's own data at the time each business was researched —
  they will have drifted since. Nothing here is refreshed automatically.
- **The `.captured.json` manifest and `artifacts/` directory are not
  committed** — regenerate the full contact sheet and this review bundle
  with `tools/contact_sheet.py` and `tools/build_review.py` if either looks
  stale; both are meant to be cheap to re-run (no model calls against
  frozen fixtures).

## If you find something that looks wrong

It might be. This session found and fixed a real one this way: the
workbench's "plan" panel and its "site preview" disagreed about section
order for seventeen of nineteen fixtures, silently, because two different
functions implemented the same reordering rule slightly differently. See
`.reviews/plan-page-disagreement.md`. Trust what you see over what a panel
claims about it, and say so if they don't match.
