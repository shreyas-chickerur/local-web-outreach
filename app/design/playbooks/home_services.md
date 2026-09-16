# Home services playbook

Trade: HVAC, plumbing, electrical, roofing, and adjacent home-services
trades. A checklist a page is scored against (Step 5, this round's
critique pass), not prose advice. Versioned; a content hash is recorded
by `app/design/playbooks.py` at load time, so a scored page can always
say which exact revision of this checklist it was measured against.

## 1. What the visitor needs first, in order

A home-services visitor arrives with a problem, usually urgent, and
reads a page to answer five questions in this order:

1. **Can you help with my problem now?** — the trade(s) covered, stated
   plainly, above everything else.
2. **Do you serve my area?** — a named town or service radius, not a
   generic "we're local."
3. **Can I trust who shows up?** — a real technician, a real credential,
   a real review with a name attached.
4. **What does it cost, or how do I get a price?** — a path to a price
   (free estimate, upfront pricing, a call) even when no number is
   published.
5. **How do I reach you in one tap?** — a phone number or call action
   that works with a thumb, not a form buried at the bottom.

A page that answers these out of order (leads with an award, a stat
band, or a generic "about us" before naming the trade) fails item 1
regardless of how the rest reads.

## 2. Required elements

Each is tied to brief fields and OMITTED, not stubbed or invented, when
the brief has no backing for it. A slot with no real material behind it
is a gap to leave empty, never a placeholder.

- **A call action always reachable on phones** — a pinned bar or fixed
  element at narrow widths, not just a link inside a hero. Required
  whenever `material.phone` exists; there is nothing to pin otherwise.
- **Service area near the top** — `material.address`'s town, or a
  stated service radius from the business's own words. Near the top of
  the page, not only in the footer.
- **The business's own truck, crew, or job photograph as the hero** —
  when `photo_vision` labelled at least one photograph usable
  (`is_hero_candidate: true`, not a logo or screenshot). A stock-look
  illustration or an unrelated stock photo is never a substitute for a
  real one that exists.
- **A named technician, taken from reviews** — when a review in
  `material.quotes` names a specific person by name (a tech, not just
  the business). Printed with that name attached, not folded into
  generic praise.
- **A job story (problem, found, result)** — when a content block
  carries one (a before/after narrative structure already present in
  the business's own material, not invented to fill the slot).
- **Reviews with names** — `material.quotes`' own author names, never
  anonymized or replaced with "a happy customer."
- **Hours, including emergency availability** — only when corroborated
  (`material.hours` is non-empty, or a genuine `emergency` fact from
  `contractorfacts.found()`). A page must not state 24/7 availability
  it cannot back.

## 3. Section order

Follows directly from §1's ordering:

1. Trade + service area + call action (the opening screen)
2. Trust proof (named tech, or the strongest available review)
3. What is covered (services, in the visitor's own words for the
   problem, not a catalog list)
4. Proof of a real job (the job story, when one exists)
5. Reviews, with names
6. Credentials / hours / service area detail
7. Final call to action

**Allowed variations:** trust proof and "what is covered" may swap when
the business's own material makes credentials the stronger asset than a
single review (many reviews, no standout quote); the job story may be
folded into "what is covered" for a business with only one clear
narrative rather than carrying its own section. The call action and
trade/service-area opening never move from first; the final call to
action never moves from last.

## 4. Forbidden for this trade

- A generic icon-card grid as the page's main structural device (the
  Milestone/Phase-2 failure this round exists to fix) — three or four
  identical white cards with a line icon, repeated as the primary way
  services are presented.
- Stock-looking illustration standing in for a real photograph the
  brief has.
- Centred-everything layout with no directional reading order.
- Identical section heights running the length of the page — Milestone
  alternated two backgrounds at one height; a page here must vary
  section weight and height section to section.
- Any placeholder (a `{{...}}` token, a generic silhouette, a "your
  photo here" state) where a real photograph exists in the brief. A gap
  is an honest empty state, stated as such, only when no photograph
  exists at all.
