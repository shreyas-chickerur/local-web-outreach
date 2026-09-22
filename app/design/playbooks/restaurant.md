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
- A menu shown only as an image or a PDF link when the text exists.
- Hours, a price or a dish the brief does not hold.
- The look of the last site this system made. Each restaurant's page takes
  its register from the place itself: a seafood shack is not a tasting room
  with the photographs swapped.
- Centred-everything layout, identical section heights, or a grid of
  identical icon cards as the main structure.
