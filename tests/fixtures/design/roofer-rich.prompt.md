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

# Design brief: Bert Roofing, Roofing Contractor — Dallas, TX

You are designing a single-page, responsive marketing homepage for a
real, independently owned roofing contractor business. Every fact and every
photograph below is real, supplied by the business or a directory
listing that corroborates it. You are not writing anything factual about
the business — see "Copy" below for the one narrow exception.

## What the visitor needs, in order

1. Can you help with my problem now? (the trades covered, stated
   plainly, above everything else)
2. Do you serve my area? (Dallas, TX and the surrounding area)
3. Can I trust who shows up? (a named technician, a real credential, a
   real review with a name attached)
4. What does it cost, or how do I get a price?
5. How do I reach you in one tap?

## Section order

1. Trade + service area + call action (opening screen)
2. Trust proof: real named 4-5 star reviews (Cristin Damon, Clint Compton, Jeff Vance, Jason Early)
3. What is covered / credentials: warranty, free estimate, service area, manufacturer badge (all corroborated)
4. The real 3-step process: inspection, decision, completion (feature_2/3/4/5)
5. Reviews, with names
6. Service area / hours / contact detail
7. Final call to action

Allowed variations: trust proof and "what is covered" may swap when
credentials are the stronger asset than a single review; the job story
may fold into "what is covered" rather than carry its own section. The
opening (trade + service area + call action) never moves from first;
the final call to action never moves from last.

## Art direction

- **Mood:** quietly thorough — Bert Roofing's own material corroborates four real credentials (warranty, free estimate, service area, manufacturer badge) and describes a plain three-step process -- inspection, decision, completion -- with a named project manager at each step. Nothing in their own words reaches for excitement; the material earns a calm, procedural page, not a louder one.
- **Type pairing:** an engineering firm's serif — designed, not decorative (display: ibm,
  body: inter)
- **Palette:** base #f2f6f8, ink #141c22, one accent #0e71aa
  (sky) — contrast-checked (ink/base and accent/base both
  clear WCAG AA for normal text).
- **Photograph treatment:** framed.
- **Signature device:** index — Bert Roofing's own site already frames the job as three numbered steps (inspection, decision, completion) with a named project manager at each -- a numbered index device makes that real structure the spine of the page instead of restating it as three more paragraphs.
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

- `hero-truck.jpg` — work/exterior: A white pickup truck with roofing company branding parked on a residential street in front of a brick house with a large tree. (hero candidate)
- `work-install.jpg` — work/exterior: Workers installing a new roof with underlayment paper visible on a brick house under a clear blue sky. (hero candidate)
- `aerial-finished.jpg` — work/exterior: An aerial view of a large house with grey shingle roofing and a metal standing-seam roof section, surrounded by trees and a street. (hero candidate)
- `detail-vents.jpg` — work/exterior: A close-up view of a shingled roof with several black turbine vents and pipe stacks, with houses and trees in the background. (hero candidate)

## Copy

Body copy comes ONLY from the numbered list below, selected by index —
you may choose which sentences to use and in what order, but you may
never write a new one, reword one, or combine parts of two into one.
Anything you print as body prose must be one of these exact sentences.

**about**
  [0] We had the best experience getting some repairs to my Mom's roof.
  [1] We originally got estimates from 3 companies, and not only was the Bert quote very reasonable, but they actually listened to us and what we wanted done.
**feature_0**
  [0] Tell us about your roof and a Bert Roofing project manager will call to schedule a no-obligation inspection and written estimate.
  [1] Insurance-related estimates and documentation are available.
  [2] First Name * Last Name Phone * Email * Property Address * Briefly describe your roof issue (optional) Get My No-Obligation Quote By submitting this form you consent to receive text messages from Bert Roofing about your inspection, quote, and project.
  [3] Message frequency may vary.
  [4] Message and data rates may apply.
  [5] Reply HELP for help, STOP to opt out.
  [6] We never sell your data.
  [7] 4.8 ★★★★★ 100+ Google reviews
**feature_1**
  [0] ★★★★★ 4.8/5 on Google · 100+ verified reviews Barbara S.
  [1] 08 December 2025 I needed some roof repair and I was very happy with Bert Roofing.
  [2] The crew was professional and they cleaned up completely after they finished their work.
  [3] They also explained what they were doing and answered every question I had.
  [4] Read full review → Jerry A.
  [5] 08 December 2025 I recommend Bert Roofing 100%.
  [6] From the first phone call to the completion of the repair work, Bert Roofing couldn't have been better.
  [7] I had a leak in my roof that dripped from the soffit onto my patio.
  [8] Bert Roofing inspected it, located the source, and repaired it cleanly.
  [9] Read full review → Carolyn G.
  [10] 08 December 2025 We had the best experience getting some repairs to my Mom's roof.
  [11] We originally got estimates from 3 companies, and not only was the Bert quote very reasonable, but they actually listened to us and what we wanted done.
  [12] Read full
**feature_2**
  [0] No pressure, no surprises, no high-pressure sales tactics.
  [1] Three steps from inspection to final cleanup, with a single project manager assigned to your home.
  [2] Step 01
**feature_3**
  [0] A local project manager evaluates your roof and walks you through what they find.
  [1] No pressure, no obligation.
  [2] Most inspections take 30 to 45 minutes.
  [3] Step 02
**feature_4**
  [0] Repair vs.
  [1] replacement options, scope, materials, and pricing, all in writing with no hidden line items.
  [2] Insurance claims documented for your adjuster.
  [3] Step 03
**feature_5**
  [0] Professional installation by our own crews.
  [1] Thorough cleanup with magnetic nail sweep.
  [2] Final walk-through and full manufacturer and workmanship warranty.
  [3] Schedule a Roof Inspection No obligation · 214-321-9341

**The one exception — headings, eyebrows, and button labels only**
(`ALLOW_AUTHORED_DISPLAY_TEXT`, this round only): you may write a short
heading, eyebrow, or button label yourself, ONLY if it is 8 words or
fewer, contains no digit, asserts nothing that would need a source to
verify (no "since", no award, no ranking, no credential word, no
"voted"/"best"/"trusted by"/"family-owned" or similar), and names
nothing except Bert Roofing, its trade, or Dallas, TX. Every such
string will be recorded and reviewed separately — write plainly, don't
reach for a claim to sound more impressive.

## Required elements

- Call action pinned/reachable at phone widths (material.phone: (214) 321-9341)
- Service area near the top (Dallas, TX -- material.address's town)
- Hero: the business's own truck/crew photo (hero-truck.jpg or work-install.jpg, both real hero candidates)
- Reviews with names: real testimonials (Cristin Damon, Clint Compton, Ken Holt, Jeff Vance, Jason Early)
- Hours: Fri 7:30am-5pm, Saturday/Sunday closed (material.hours, corroborated) -- print only what is given, do not infer weekday hours that are not stated
- Credentials: warranty, free_estimate, service_area, manufacturer_badge are all corroborated (contractorfacts.found() on this business's own about/blocks text returns exactly these four) -- use contractorfacts.py's own label text for each ("Workmanship warranty", "Free estimate", "Service area", "Manufacturer certified") so each badge is recognized as backing the fact it names, not a paraphrase of it
- The real 3-step process (inspection -> decision -> completion) is a strong asset -- give it its own section using the index signature device

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
- **A credential badge's exact label matters.** Print "Workmanship warranty" / "Free estimate" / "Service area" / "Manufacturer certified" verbatim, as their own short label, not folded into a longer authored sentence -- otherwise the fact it backs cannot be told apart from surrounding invented text.
