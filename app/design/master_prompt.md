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

# Design brief: {{business_name}}, {{trade}} — {{town}}

You are designing a single-page, responsive marketing homepage for a
real, independently owned {{trade_lower}} business. Every fact and every
photograph below is real, supplied by the business or a directory
listing that corroborates it. You are not writing anything factual about
the business — see "Copy" below for the one narrow exception.

## What the visitor needs, in order

1. Can you help with my problem now? (the trades covered, stated
   plainly, above everything else)
2. Do you serve my area? ({{service_area}})
3. Can I trust who shows up? (a named technician, a real credential, a
   real review with a name attached)
4. What does it cost, or how do I get a price?
5. How do I reach you in one tap?

## Section order

{{section_order}}

Allowed variations: trust proof and "what is covered" may swap when
credentials are the stronger asset than a single review; the job story
may fold into "what is covered" rather than carry its own section. The
opening (trade + service area + call action) never moves from first;
the final call to action never moves from last.

## Art direction

- **Mood:** {{mood}} — {{mood_why}}
- **Type pairing:** {{type_pair_voice}} (display: {{type_pair_display}},
  body: {{type_pair_body}})
- **Palette:** base {{base}}, ink {{ink}}, one accent {{accent}}
  ({{accent_name}}) — contrast-checked (ink/base and accent/base both
  clear WCAG AA for normal text).
- **Photograph treatment:** {{photo_treatment}}.
- **Signature device:** {{signature_device}} — {{signature_why}}
- **Section rhythm:** {{section_rhythm}}. No two adjacent sections share
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

{{photo_list}}

## Copy

Body copy comes ONLY from the numbered list below, selected by index —
you may choose which sentences to use and in what order, but you may
never write a new one, reword one, or combine parts of two into one.
Anything you print as body prose must be one of these exact sentences.

{{copy_list}}

**The one exception — headings, eyebrows, and button labels only**
(`ALLOW_AUTHORED_DISPLAY_TEXT`, this round only): you may write a short
heading, eyebrow, or button label yourself, ONLY if it is 8 words or
fewer, contains no digit, asserts nothing that would need a source to
verify (no "since", no award, no ranking, no credential word, no
"voted"/"best"/"trusted by"/"family-owned" or similar), and names
nothing except {{business_name}}, its trade, or {{town}}. Every such
string will be recorded and reviewed separately — write plainly, don't
reach for a claim to sound more impressive.

## Required elements

{{required_elements}}

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
