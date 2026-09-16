<!-- filled from master_prompt.md (044c4ea4f0c2) and playbooks/home_services.md (046d04f828fd) -->
<!--
Phase 3, Step 3. Versioned; hashed by app/design/master_prompt.py
alongside the filled copy committed at tests/fixtures/design/<slug>.prompt.md.
Mostly identical across businesses -- only the double-brace placeholders
below change per business. Filled from: the brief, the home-services playbook,
the art direction (art_direction.py), the business's own photographs, and
a numbered copy list (copyselect.py's own candidate groups). No prose in
this file describes the gates; the design session is not told about them,
per the round's own instruction (NEXT-ROUND.md, Part B, Step 4).
-->

# Design brief: Status Roofing LLC, Roofing Contractor — Frisco, TX

You are designing a single-page, responsive marketing homepage for a
real, independently owned roofing contractor business. Every fact and every
photograph below is real, supplied by the business or a directory
listing that corroborates it. You are not writing anything factual about
the business — see "Copy" below for the one narrow exception.

## What the visitor needs, in order

1. Can you help with my problem now? (the trades covered, stated
   plainly, above everything else)
2. Do you serve my area? (Frisco, TX, Oklahoma City, and four states)
3. Can I trust who shows up? (a named technician, a real credential, a
   real review with a name attached)
4. What does it cost, or how do I get a price?
5. How do I reach you in one tap?

## Section order

1. Trade + service area + call action (opening screen)
2. Trust proof: real named 5-star reviews (Cynthia Del Rio, Ana Idelsy, Kathy D, Sandy de Vries, adan rodriguez)
3. What is covered: two hubs / four states reach, W2 employee crews (real, from about + feature_0)
4. Proof of process: the real insurance-claim / W2-employee FAQ content (feature_2)
5. Reviews, with names
6. Service area / contact detail
7. Final call to action

Allowed variations: trust proof and "what is covered" may swap when
credentials are the stronger asset than a single review; the job story
may fold into "what is covered" rather than carry its own section. The
opening (trade + service area + call action) never moves from first;
the final call to action never moves from last.

## Art direction

- **Mood:** regional scale — Status Roofing's own words lead with reach and process, not a single local crew -- "Two Hubs. Four States. One Standard," W2 employee crews, insurance-claim handling, and market expansion into Austin -- the material earns a page that reads as a bigger, more procedural operation, not a warm neighborhood shop.
- **Type pairing:** geometric and confident, a studio rather than a shop (display: league,
  body: sans)
- **Palette:** base #faf6ef, ink #201a10, one accent #8e620b
  (amber) — contrast-checked (ink/base and accent/base both
  clear WCAG AA for normal text).
- **Photograph treatment:** full_bleed.
- **Signature device:** ledger — Status Roofing's real material is unusually document-shaped for this trade -- W2 employee documentation, insurance-claim paperwork, a real FAQ about the insurance process -- a ruled, tabular ledger device reads as the professional, paper-trail credibility their own words already lead with, more than a single review could.
- **Section rhythm:** heavy -> light -> breathing -> heavy -> light -> breathing -> heavy. No two adjacent sections share
  a weight — vary density and height section to section; do not
  alternate two backgrounds at one identical height down the page.

## Motion spec

- Reveal each section on scroll (a real intersection-observer-driven
  reveal, not a CSS-only page-load animation).
- Hover and focus states on every interactive control (links, buttons,
  the call action).
- One signature motion moment tied to the signature device above —
  something that happens once, deliberately, not a decorative loop.
- All motion cancelled under `prefers-reduced-motion: reduce`.
- Never animate the largest image on the page (the hero).

## Photographs

Use ONLY the business's own files, by the path or URL given. Never a
stock photo, a placeholder, or a generic illustration. Mark a gap with
an explicit, honestly-labelled empty state only when no real photograph
exists for that slot — do not invent one.

- `hero-team-trucks.jpg` — work/exterior: A group of people standing in front of a building, flanked by five white company trucks parked in a row. (hero candidate)
- `work-shingles.jpg` — work/exterior: Two workers installing grey shingles on a steep roof with exposed underlayment and a red tree in the background.
- `exterior-finished.jpg` — work/exterior: Side view of a brick house with a new dark roof and chimney under a clear blue sky. (hero candidate)
- `aerial-install.jpg` — work/exterior: Aerial view of a house roof mid-installation with workers and exposed underlayment paper among grey shingles. (hero candidate)

## Copy

Body copy comes ONLY from the numbered list below, selected by index —
you may choose which sentences to use and in what order, but you may
never write a new one, reword one, or combine parts of two into one.
Anything you print as body prose must be one of these exact sentences.

**about**
  [0] Yes.
  [1] We operate from our Frisco, TX headquarters and our Oklahoma City office, with crews dispatched statewide across all four states.
  [2] We're actively expanding market-specific Project Managers — including a new Austin, TX presence — to bring local expertise to every market we serve.
**feature_0**
  [0] A referral partner who protects your closing timelines.
  [1] Pre-sale inspections, transparent reporting, fast turnaround.
  [2] Two Hubs.
  [3] Four States.
  [4] One Standard.
**feature_1**
  [0] Consistent five-star reviews across all four states.
  [1] The proof is in the work.
  [2] Excellent ★★★★★ Based on 200+ reviews Audrey Gossett 1 month ago ★★★★★ "I can't say enough good things about Status Roofing.
  [3] From start to finish, the entire team was professional and communicated every step.
  [4] Our roof looks incredible." Read more Christian Hurtado 2 months ago ★★★★★ "We met with Sergio Lara for an inspection and we were satisfied with his service.
  [5] He took the time to walk us through everything and was incredibly professional." Read more Kathy D.
  [6] 2 months ago ★★★★★ "We recently had our roof and gutters replaced by Status Roofing and the entire process was seamless.
  [7] Their team is responsive, honest, and the workmanship is top-tier." Read more Fitzpatrick Real Estate 3 months ago ★★★★★ "I cannot explain enough how great the communication has been between Jeremy and his company Status Roofing and
**feature_2**
  [0] Straight answers about roofing, insurance claims, and the W2 difference.
  [1] How long does a full roof replacement take?
  [2] Most residential roof replacements are completed in a single day.
  [3] Larger homes or complex roof systems may take two days.
  [4] Our W2 crews are full-time employees — they show up on schedule and don't disappear mid-job like subcontractors sometimes do.
  [5] Will you work directly with my insurance adjuster?
  [6] Yes — this is one of our specialties.
  [7] We handle the entire insurance process: damage documentation, adjuster meetings, supplement negotiations, and final sign-off.
  [8] Most homeowners end up getting significantly more covered than their initial estimate once we're involved.
  [9] What does "W2 employees" actually mean for me as a homeowner?
  [10] It means every Project Manager running your job is a direct employee of Status Roofing — background-checked, trained, and covered by our workers' compe
**feature_3**
  [0] Status Roofing delivers dependable roofing services, ensuring quality installations and repairs across all of Texas, all of Oklahoma, all of Kansas, and all of Missouri.
  [1] Our skilled team provides the right solutions for your home or business with durable and reliable roofing craftsmanship — every job managed by a W2 Project Manager from estimate to final invoice.
  [2] All Services
**feature_4**
  [0] Status Roofing LLC offers a wide range of construction and roofing services for residential and commercial properties.
  [1] Every Project Manager on every job is a W2 employee of Status Roofing — directly accountable, fully insured, and on payroll from the first inspection through the final invoice.
**feature_5**
  [0] ✓ Transparency — no hidden costs or surprises ✓ Reliability — count on us to fulfill our promises ✓ Quality — we only use the best materials Introducing our team — meet the W2 Project Managers who run every job.
  [1] Meet Our Team

**The one exception — headings, eyebrows, and button labels only**
(`ALLOW_AUTHORED_DISPLAY_TEXT`, this round only): you may write a short
heading, eyebrow, or button label yourself, ONLY if it is 8 words or
fewer, contains no digit, asserts nothing that would need a source to
verify (no "since", no award, no ranking, no credential word, no
"voted"/"best"/"trusted by"/"family-owned" or similar), and names
nothing except Status Roofing LLC, its trade, or Frisco, TX. Every such
string will be recorded and reviewed separately — write plainly, don't
reach for a claim to sound more impressive.

## Required elements

- Call action pinned/reachable at phone widths (material.phone: (469) 424-4623)
- Service area: Frisco, TX headquarters + Oklahoma City office + expansion states (from about[1], about[2])
- Hero: the business's own crew/truck photo (hero-team-trucks.jpg, a real hero candidate)
- Reviews with names: 5 real testimonials, all named (Cynthia Del Rio, adan rodriguez, Ana Idelsy, Kathy D, Sandy de Vries)
- No hours are corroborated for this business -- do not state any hours or a 24/7 claim; leave that slot out entirely rather than inventing one
- No contractorfacts credential is corroborated for this business (checked directly: found() returns none) -- do not print a Licensed-and-insured or similar credential badge; there is nothing to back it

## Forbidden for this trade

- A generic icon-card grid as the page's main structural device.
- Stock-looking illustration standing in for a real photograph you have.
- Centred-everything layout with no directional reading order.
- Identical section heights running the length of the page.
- Any placeholder where a real photograph exists.

## Output

One standalone, responsive HTML file. Every value in this prompt
resolved — no unresolved template token, no lorem ipsum, no TODO left
anywhere in the file. Mobile-first, tested down to a narrow phone width;
the call action must stay reachable with a thumb at every width.


## Lessons from hvac's own critique this round -- follow these exactly

- **Include a real viewport meta tag**: `<meta name="viewport" content="width=device-width, initial-scale=1">` in `<head>`, always. hvac's first build shipped without one and the whole page rendered as a squeezed-down desktop layout on a real phone.
- **Never combine or reword two source sentences into one**, even when both are on the approved list and even when it would read better. Print each selected sentence exactly as given, as its own sentence. If you want two facts adjacent, print them as two consecutive sentences, not one sentence you wrote by splicing them.
- **Never use a fact, sentence, or phrase that is not in the numbered copy list below**, even if it is true and even if it appears elsewhere in this prompt's own prose (the "required elements" notes above may mention facts by way of explanation -- that is not permission to quote them verbatim unless the exact sentence also appears in the numbered list).
- **Authored headings/eyebrows/buttons must not smuggle in a claim.** "Same-day plumbing for Plano" is NOT a safe authored heading even though it has no digit and matches no CLAIM_RE pattern by coincidence -- "same-day" is itself a service-speed claim. An authored string may name the business, its trade, or its town, and nothing else asserted about them -- no adjective claiming quality, speed, size, or reputation.
- **Give visually distinct backgrounds to adjacent section-rhythm weights**, not just different content density. hvac's "light" and "breathing" sections used the identical background color and were indistinguishable as different weights. Use an actually different background tone (not necessarily a different hue -- a tint, a shade, a texture) for every adjacent pair.
- **Every visible fact still needs a place.** If you cut something the copy rules forbid, replace it with a compliant sentence from the list rather than leaving a bare heading with no body copy -- an empty card reads as unfinished, not disciplined.
