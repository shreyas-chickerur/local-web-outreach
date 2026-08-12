# Design brief — the generated business website

**For:** Claude design
**Deliverable:** one self-contained, responsive HTML page (inline CSS + JS, no external requests) that our Python renderer will turn into a template.
**Status of what exists:** a working but weak first pass at `app/render/site_html.py`. Treat it as a reference for *data shape only* — the design is to be replaced, not refined.

---

## 1. What this page is

A local business (restaurant, lawn care, plumber, roofer) has a bad, dated, or broken website. We research the business, build a **better site for them as a private proposal**, and email them a link. They open it cold, on a phone, having never heard of us.

The page has to do one job: **make the owner think "this is better than what I have — I want it."**

Two audiences, in this order:

1. **The owner** (buyer). Skeptical, busy, non-technical. Wants to see their business look good and correct.
2. **Their customers** (the demo). The page must work as a real site for someone hungry / needing a plumber — because that's what the owner is judging.

It is **not** a pitch page. No pricing, no "we build websites", no agency branding. It reads as *their* finished site.

---

## 2. Hard constraints (non-negotiable)

| Rule | Why |
|---|---|
| **Self-contained.** One HTML file. Inline `<style>` and `<script>`. No CDNs, no web fonts, no analytics, no external JS. | Served from a tokenized private URL; must render with zero third-party requests. |
| **Never invent content.** Every word/number comes from the data model. If a field is missing, the section is omitted — no lorem ipsum, no "Serving the community since 1985". | Legal + trust. The whole system is built on not fabricating. |
| **No fabricated social proof.** No testimonials, no review quotes, no award badges, no "Voted best in Frisco" — unless present in the data as a verified field. | Same. Awards/press are explicitly filtered out upstream. |
| **Never link back to the business's current website.** | The page replaces that site; linking to it makes this a brochure for the thing we're replacing. |
| **`noindex, nofollow`** meta tag. | Private proposal until purchased. |
| **All values escaped.** Assume every string is hostile third-party input. | It is scraped from arbitrary sites. |
| **WCAG AA.** 4.5:1 text contrast, visible focus rings, full keyboard operation, `prefers-reduced-motion` honored. | Non-negotiable baseline. |

---

## 3. The data contract

The renderer passes one JSON object. **Design to this exact shape.** Every field is optional except `business_name` and `industry` — the layout must be excellent when fields are missing and when they're all present.

```jsonc
{
  "business_name": "Craftway Kitchen",
  "industry": "restaurant",            // "restaurant" | "service" | "generic"
  "tagline": "Scratch kitchen in Frisco",     // may be null
  "hero_image": "https://…/dining-room.jpg",  // may be null — design a strong no-photo hero
  "noindex": true,

  "actions": [                          // 0–3. Buttons. NEVER their old site.
    { "kind": "Menu",          "label": "See the menu", "url": "#menu" },
    { "kind": "Book / Reserve","label": "Book a table", "url": "https://opentable.com/r/x" },
    { "kind": "Order Online",  "label": "Order",        "url": "https://doordash.com/x" }
  ],
  // kind ∈ Menu | Book / Reserve | Order Online | Get a Quote | Shop | Gallery | Careers
  // url is either an in-page anchor (#menu) or a real third-party service.

  "socials": [ { "name": "Instagram", "url": "https://…" } ],

  "sections": [
    { "type": "hero", "heading": "Craftway Kitchen", "subheading": "Frisco, TX" },

    { "type": "bill_of_fare", "heading": "Menu", "provenance": "self_attested",
      "items": [
        { "name": "Short Rib", "price": "$32", "description": "braised eight hours" }
      ],
      "media": [ { "url": "https://…/menu.pdf", "kind": "pdf", "label": "Dinner Menu" } ]
      // items MAY be empty while media is present (menus are often PDFs/photos)
    },

    { "type": "offerings", "heading": "What we offer", "provenance": "self_attested",
      "items": ["Catering", "Private dining", "Weekend brunch"] },

    { "type": "story", "heading": "About us", "provenance": "self_attested",
      "body": "Our philosophy is simple. Start with high-quality ingredients…" },

    { "type": "opening_hours", "heading": "Hours", "provenance": "self_attested",
      "items": ["Sunday – Wednesday: 5pm – 9pm", "Thursday – Saturday: 5pm – 10pm"] },

    { "type": "gallery", "heading": "Gallery", "provenance": "self_attested",
      "images": ["https://…/1.jpg", "https://…/2.jpg"] },

    // fact-bearing sections. Each fact is independently verified; render as truth.
    { "type": "standing", "heading": "Rated by customers",
      "facts": [ { "label": "Rating", "field": "rating", "value": "4.6" } ] },
    { "type": "contact", "heading": "Contact",
      "facts": [
        { "label": "Address", "field": "address", "value": "7110 Main St, Frisco, TX 75033" },
        { "label": "Phone",   "field": "phone",   "value": "(469) 664-0100" }
      ] },

    { "type": "cta", "heading": "Get in touch", "body": "Reach out to Craftway Kitchen." }
  ],

  "needs_confirmation": ["hours", "owner_name"]   // fields we could NOT verify — do not render as fact
}
```

**Provenance matters visually? No.** `self_attested` vs verified is an internal distinction — do **not** surface badges like "verified" to the prospect. It's their site; it should read as theirs.

---

## 4. How it's served (connections)

- `GET /preview/{token}` → this HTML. Token is 22 chars, unguessable.
- Response sets `X-Robots-Tag: noindex, nofollow`; page also carries the meta tag.
- A `draft` boolean controls one thing: a small fixed **"Draft proposal · private"** pill, bottom-center. Present while unapproved, gone once approved. It must not obstruct content or the CTA on mobile.
- The page is opened from an email link, **majority on mobile**. Design mobile-first.
- Images are **hot-linked from the business's own domain**. Assume some will 404, some will be huge, some will be tiny logos. See §7.

---

## 5. Page structure

Order is fixed. Any section whose data is absent is **omitted entirely** — no empty headings.

1. **Nav** — business name left; anchors right (Menu / About / Hours / Contact, only for sections that exist); primary action button. Transparent over hero → solid/frosted on scroll. Mobile: name + one button, no hamburger (the page is short).
2. **Hero** — see §6.1
3. **Menu** (`bill_of_fare`) — see §6.2
4. **What we offer** (`offerings`) — see §6.3
5. **About** (`story`) + **Rating** (`standing`)
6. **Hours** (`opening_hours`)
7. **Gallery** — see §6.4
8. **Contact / closing** — dark band, address + phone (click-to-call) + actions
9. **Footer** — name, socials, © year

---

## 6. Component specs

### 6.1 Hero
- **With `hero_image`:** full-bleed, `min-height: 88vh` (cap ~820px). Image `object-fit: cover`, center. **Gradient scrim** top and bottom so text always clears 4.5:1. Business name as display type. Subheading = `sections.hero.subheading` or `tagline`.
- **Without `hero_image`:** do NOT fake a photo. Design an equally strong typographic hero — oversized name, accent rule, generous space, subtle gradient or pattern from the industry palette. **This must look intentional, not degraded.** Roughly half of real businesses have no usable photo.
- Buttons: one **primary** (solid accent, e.g. "Reserve a table" / "Request a quote") + up to two from `actions`. On photography, secondary buttons must be **solid light fills, never outlines** — outlines vanish over unpredictable images.
- Scroll cue at the bottom.

### 6.2 Menu — **the most important section for restaurants**
Two modes:
- **`items` present:** a real menu. Dish name, price right-aligned with tabular numerals, description under. Group visually; dot leaders or a hairline rule. Should feel like a printed menu, not a table.
- **`items` empty, `media` present:** their menu is a PDF or photo.
  - **PDF:** `<embed>` is unreliable — do NOT rely on it. Render a **menu viewer card**: a framed preview with a clear "View full menu" that opens it in an **in-page overlay** (iframe/object with a fallback download link). It must never navigate away.
  - **Image:** render inline, full width, click to open in the lightbox (§6.4).
  - Include one small caption: *"Menu as currently published — a new site sets this in searchable text."* This is the only line on the page that hints at improvement; keep it quiet and factual.
- If both empty, omit the section **and** drop the Menu nav link and Menu action button.

### 6.3 What we offer (`offerings`)
- Simple items, **no descriptions, no icons, no prices**.
- **They are not links.** Therefore: **no hover lift, no cursor change, no card affordance that implies clickability.** Style them as a typographic list or bordered tags — static, confident, informational. (The current build has hover states on non-interactive cards; that's the bug being fixed.)
- Data quality warning: this list is scraped and sometimes contains navigation junk ("GIFT CARDS", "Skip to content"). Design must look fine with 1 item and with 12, and must not collapse if an item is one word.

### 6.4 Gallery + lightbox
- Responsive grid; first tile may span 2 columns for rhythm.
- Every tile is a real `<button>`; click opens a **lightbox**: prev/next, `←`/`→` keys, `Esc` to close, click-outside to close, body scroll lock, focus moved to close and **trapped** while open, focus returned on close.
- Lazy-load; graceful failure on broken images (see §7).

### 6.5 Rating (`standing`)
- Present as a confident stat: large number, star glyphs, short caption ("Average customer rating").
- Never invent review counts or quotes.

### 6.6 Contact / closing
- Dark band. Address, phone as `tel:` link, plus any remaining actions.
- Big, obvious primary CTA. This is the page's conversion point.

---

## 7. Data-quality hazards (the design must survive these)

Real inputs are messy. Handle each gracefully:

| Hazard | Required behavior |
|---|---|
| `hero_image` is a **logo** or tiny graphic | Design a rule: if the image renders below a sane size or has transparency, fall back to the typographic hero. Provide CSS that doesn't stretch small images — e.g. `object-fit: contain` on a dark branded panel rather than a blurry `cover`. |
| Image 404s | `onerror` hides the tile / falls back to the no-photo hero. Never a broken-image icon. |
| Offering items are nav junk | Layout must not draw attention to any single item; no numbering that implies ranking is fine, but keep it low-key. |
| `about` text is short or oddly cropped | Cap to a readable block; don't let a 40-char paragraph sit in a giant empty section. |
| Hours strings are freeform | Never assume `Day: time` — split on the first colon if present, otherwise render the whole line. |
| Long business names (40+ chars) | Display type must clamp and stay on ≤3 lines. |

---

## 8. Design system

### Type
- System stack only (no web fonts): `ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif`.
- Display: `clamp(2.6rem, 7.5vw, 5.4rem)`, weight 800, tracking `-0.035em`, line-height ~0.98.
- Section title: `clamp(1.9rem, 4vw, 3rem)`, weight 800, tracking `-0.028em`.
- Body: 17px base, line-height 1.65, max measure ~70ch.
- Eyebrow: 0.76rem, weight 800, tracking 0.16em, uppercase, with a short leading rule.

### Color — one palette per `industry`
Each needs: `ink` (near-black), `accent` (saturated, AA on white **and** usable as a solid button), `accent-dark` (hover), `tint`/`sand` (section banding), `muted` text, `line` (hairlines).

- `restaurant` — warm, appetite-forward: charcoal + ember/rust.
- `service` — trades; high-trust: slate + confident blue.
- `generic` — neutral: near-black + indigo.

Feel free to improve on these; keep three distinct, deliberate palettes.

### Space & layout
- Container `min(1160px, 100% - 48px)`.
- Section padding `clamp(64px, 9vw, 120px)`.
- Alternate white / tint bands so sections read as distinct.
- Radius ~14px; two shadow tiers (resting, lifted).

### Breakpoints
`< 640` mobile · `640–899` tablet · `≥ 900` desktop. Mobile-first. Test at 375px.

---

## 9. Motion spec

Current build's motion is too timid — this is a named complaint. Make it deliberate, never gratuitous.

| Element | Animation |
|---|---|
| Hero image | Slow scale 1.06 → 1.0 over ~20s, ease-out. |
| Hero text | Staggered entrance on load: eyebrow → headline → sub → buttons, 60–80ms apart, 500ms, `cubic-bezier(.2,.8,.2,1)`, translateY 16px + fade. |
| Sections | Reveal on scroll via `IntersectionObserver` at ~12% visibility: translateY 22px + fade, 700ms. **Stagger children** (menu rows, gallery tiles, offering items) by ~50ms. |
| Nav | Background/blur crossfade 300ms on scroll past 60px. |
| Buttons | translateY(-2px) + shadow bloom, 180ms. |
| Gallery tiles | Image scale 1.06 on hover, 500ms; zoom-in cursor. |
| Lightbox | Backdrop fade 200ms; image scale 0.96 → 1 fade-in 260ms. |
| Numbers/rating | Optional count-up on first reveal (~800ms). |
| **`prefers-reduced-motion: reduce`** | **All** transforms/animations off; content visible immediately. Non-negotiable. |

---

## 10. Accessibility & performance

- Semantic landmarks: `header`/`nav`/`main`/`section`/`footer`; one `h1`; heading order unbroken.
- Every interactive element keyboard-reachable with a visible `:focus-visible` ring (3px accent, 3px offset).
- Lightbox: `role="dialog"`, `aria-modal="true"`, labeled controls, focus trap + restore.
- Decorative images `alt=""`; meaningful ones get real alt text.
- Click-to-call on phone numbers.
- `loading="lazy"` below the fold; explicit `width`/`height` or `aspect-ratio` to prevent layout shift.
- Total inline CSS+JS should stay well under ~40KB. No frameworks.

---

## 11. What to deliver

1. **One HTML file** rendering a **fully populated** restaurant example (use the §3 data verbatim).
2. **A second HTML file** for the **sparse case**: `business_name`, `industry: "service"`, phone + address facts, **no** hero image, **no** menu, **no** gallery, one-line about. This proves the design degrades well — arguably more important than the rich case.
3. Keep **CSS and JS inline**, and structure the markup so each section is a clean, repeatable block we can template.
4. Use obvious placeholder markers where data is injected (e.g. `<!-- {{HERO_IMAGE}} -->`), or simply keep sections cleanly delimited — we'll do the templating.

**Do not** add: pricing, agency branding, testimonials, stock photography, icon fonts, or any external request.

---

## 12. One-line summary to lead with

> A private, single-page website proposal for a local business, generated from verified public data and their own published content — mobile-first, self-contained, WCAG AA, that reads as *their* finished site and makes the owner want to buy it.
