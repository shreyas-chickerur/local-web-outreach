# Restaurant playbook

DRAFT, 22 September 2026, awaiting Shreyas's judgement. Not yet used by any
generated page.

Trade: independent restaurants, from a counter-service seafood shack to a
tasting-menu dining room. A checklist a finished page is scored against, not
a rule the design session is held to while it builds: generation is free,
and every factual claim is listed and checked afterwards. Versioned; a content
hash is recorded by `app/design/playbooks.py` at load time.

## 1. What the visitor needs first, in order

A restaurant visitor is deciding where to eat, often today, often on a phone,
often with someone else. They read a page to answer:

1. **What kind of place is this, and would I like it?** The food and the
   feeling, at once: a photograph of the actual food or room, and a plain
   line saying what they serve. Before any story.
2. **Is it open when I want to go, and where is it?** Today's hours and the
   neighbourhood, near the top, not only in the footer.
3. **What would I eat, and what would it cost?** The menu, with prices when
   the business publishes them. A price is the fastest trust signal a
   restaurant has.
4. **Do people like it?** The strongest real proof it has: a rating with its
   count, a named review, a press mention, an award.
5. **How do I go?** One tap to the right action for this place: call,
   reserve, order to go, or directions.

## 2. Required elements

Each is tied to what the brief actually holds, and left out, never stubbed,
when there is nothing behind it.

- **The primary action, always reachable on phones.** Which action is
  primary follows the place: reservations for a dining room that takes them,
  ordering for a place with a to-go or online-ordering page, a call
  otherwise. Pinned at narrow widths.
- **Real food or room as the opening photograph**, from the business's own
  site or its labelled place photographs. Never stock.
- **The menu, readable on the page**, from the stored page text, with prices
  when published. A link to a PDF is not a substitute when the text exists.
- **Hours and address together**, with directions one tap away.
- **Rating with its count** when a directory publishes one ("4.5 from 3,351
  Google reviews"), never a rating without its count.
- **Prices in one format.** A business's own site often mixes "$3.00" with
  "6.50"; the page picks one and prints every price that way.
- **The business's own voice where it has one**: a story, a chef, a history,
  a farm list. Absent is fine; invented is not.

## 3. Section order

1. The place: photograph, what they serve, the primary action
2. Hours and location
3. The menu (or its best section, with the rest one tap away)
4. Proof: rating, reviews, press
5. The story, when the business has one
6. Final action, with hours and address repeated

**Allowed variations:** a dining room whose story is the reason to go (a
chef, a history, a farm list) may move the story to second. A place with a
long menu may show its signature section first and fold the rest.

## 4. Forbidden for this trade

- A stock photograph of food, or of any room that is not theirs.
- Anything carried over from the business's existing site except its facts.
  That site is usually the old one being replaced: take its menu, prices,
  hours and words, never its decorations, symbols or formatting. Fish Shack's
  version 5 turned the owner's hand-typed "======>" into a neon ornament.
- A menu shown only as an image or a PDF link when the text exists.
- Hours, a price or a dish the brief does not hold.
- The look of the last site this system made. Each restaurant's page takes
  its register from the place itself: a seafood shack is not a tasting room
  with the photographs swapped.
- Centred-everything layout, identical section heights, or a grid of
  identical icon cards as the main structure.

## 5. Never repeat what an earlier site used

Each finished site takes its practical information (hours, address, phone,
how to get there) in a form that belongs to that place. Shreyas, 22 September
2026: Fish Shack's first build repeated The Heritage Table's shapes closely
enough that the two read as one template. Every device below has been used and
is forbidden on the next site; add each new site's to this list when it is
built.

| Site | Device used, never to repeat |
|---|---|
| The Heritage Table | a dark full-width strip of hours · address · phone, four items in a row |
| The Heritage Table | a "visit" block: a one-line headline over labelled columns of hours, address, contact and social links, with one button |
| Fish Shack, rejected | a dark "visit" block led by the address as a giant headline, an hours list and two buttons, which read as The Heritage Table's |
| The Heritage Table | cream and deep green, editorial serif |
| Fish Shack, version 4 (not chosen) | a drawing of the business's own roadside sign, its marquee reading the hours |
| Fish Shack, version 4 (not chosen) | a not-to-scale street sketch built from the business's own directions |
| Fish Shack, version 4 (not chosen) | the footer as a call-ahead order ticket with a torn edge |
| Fish Shack, version 4 (not chosen) | a letterboard of weekday specials with today's row lit |
| Fish Shack, version 4 (not chosen) | harbor navy, sign red and kraft; a sign-painter slab with a typewriter face for prices |
| Fish Shack, chosen (versions 5 to 9) | butter yellow and charcoal, with a red-orange accent and a condensed grotesque headline |
| Fish Shack, chosen | a neon "OPEN" sign that reads the clock and says CLOSED after hours |
| Fish Shack, chosen | ordering ahead as three numbered steps: call, head for the address, the register |
| Fish Shack, chosen | the menu in tabs, one per section |
| Fish Shack, chosen | a family-pack price ticket |
| Fish Shack, chosen | a polaroid of a signature dish overlapping the opening photograph |
