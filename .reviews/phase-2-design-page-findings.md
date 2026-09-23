# Phase 2b, Step 4 — the real designed page, classified

`tests/fixtures/seam/hvac-designed.html`, extracted via
`content.files["Main.dc.html"]` in its own `<script id="appifact-doc">`
state block (`tests/sitegen/test_seam_design_page.py`), against the
real brief `tests/fixtures/briefs/hvac.json`. The fixed gate
(`app.site.seam_gates.gate`) raised **42** findings when this document
was first written, pinned by `test_the_gate_finding_count_is_pinned`.
Every one is classified below: the design's own sentence, the closest
real source span it traces to (quoted, with its location), and a
verdict — **verbatim**, **true reworded**, **changed specific**, or
**invented**.

**2026-09-15 (Phase 2c) update:** the count is now **48** — see
"Six more findings" below the original 42, added once
`_credential_backed_remainder` (`.reviews/NEXT-ROUND.md`) stopped
letting a real credential (`Licensed & insured`, `24/7 emergency`,
`Same-day service`) exempt the WHOLE sentence it shared with a separate,
true-but-reworded caption. All 6 are real; none is invented or changed
specific. The rows below (0-41) are unchanged from the original
classification and keep their original numbers so existing
cross-references (e.g. "finding #18") still point at the same row.

**Verdict tally (all 48): 25 verbatim, 22 true reworded, 1 changed
specific, 0 invented.** (Original 42: 25 verbatim, 16 true reworded, 1
changed specific, 0 invented.)

## The original 42 findings

| # | Design page text | Closest source span | Location | Verdict |
|---|---|---|---|---|
| 0 | "since 2004" | "Since 2004, Milestone is a family-owned..." | `blocks[7]` | verbatim |
| 1 | "5-star" | "Over 33,000 5 Star Reviews!" / "20,000 5 star reviews" | `blocks[10]` / `published.about` | verbatim |
| 2 | "family-owned" | "family-owned and operated home service company" | `blocks[7]` | verbatim |
| 3 | "certified" | "a team of certified technicians" | `published.about`-adjacent block text (services blocks) | verbatim |
| 4 | "Plano's trusted plumbers, electricians & AC techs" | "Trusted Plano plumbers delivering fast, reliable service" + real plumbing/electrical/AC block coverage | `blocks[1]`, `blocks[9]`, `blocks[20-29]` | true reworded |
| 5 | "Same-day repairs, upfront pricing, and a 100% satisfaction guarantee — from the neighborhood company Plano residents have called since 2004." | "same-day plumbing repairs" (`blocks[1]`) + "100% satisfaction guarantee" (`blocks[2]`, `[9]`) + "Since 2004" (`blocks[7]`, `[20]`) | composite, see cited blocks | true reworded |
| 6 | "Call (972) 913-6165 Schedule online" | verified phone fact `(972) 913-6165`; "Schedule Online Now" | `facts` (phone, verified) / `blocks[2]`, `[9]` | verbatim |
| 7 | "Why Plano trusts Milestone" | "Why Choose Milestone?" | `blocks[7]`, `[8]` (headings) | true reworded |
| 8 | "What our customers say about us matters most to us" | "What our customers say about us are very important." | `published.about` | true reworded |
| 9 | "We've earned thousands of 5-star reviews from Plano residents who've used our plumbing, electrical, and AC services." | "We've acquired over 20,000 5 star reviews from all Plano residents who have used our plumbing services." | `published.about` | true reworded — generalizes the exact (internally-inconsistent, see below) count to "thousands," compatible with the real corroborated `material.reviews = 6203`; widens "plumbing" to the business's actual three trades |
| 10 | "From how timely we are to how trustworthy we are, we strive to give a good experience to everyone who calls Milestone." | "From how timely we are to how trustworthy we are, we strive to give a good experience to everyone who uses our services." | `published.about` | verbatim (one clause swapped: "who uses our services" → "who calls Milestone") |
| 11 | "Since 2004, we've been a family-owned and operated home service company dedicated to doing business in Plano the right way — and we stand behind every job with the Milestone Guarantee." | "Since 2004, Milestone is a family-owned and operated home service company dedicated to doing business in Plano the right way... With The Milestone Guarantee..." | `blocks[7]` | verbatim |
| 12 | "Upfront pricing A clear price before we begin — no surprises on the invoice." | "Upfront Pricing: We begin work on your home only after providing you with a clear, upfront price." | `blocks[2]` | true reworded |
| 13 | "What we do" | (services-section label; no single source span — a generic navigational heading, not a claim) | — | true reworded / generic, not a claim |
| 14 | "Three trades, one trusted crew" | real coverage of plumbing + electrical + A/C across many blocks; "trusted" used throughout | `blocks[1]`, `[9]`, `[20-29]` | true reworded |
| 15 | "Leak repair, clogged drains, water heater installation, and same-day fixes for anything from a minor drip to a major emergency." | "water heater installation, help with clogged drain lines... Plumbing Repair... Same-Day Service" | `blocks[2]` | true reworded |
| 16 | "A/C & heating" | "A/C & Heat" | `published.services` | verbatim |
| 17 | "Repair, maintenance, and duct inspections from certified technicians — keeping North Texas homes comfortable through every season." | duct-inspection content (`blocks[34-37]`) + "certified technicians" + "North Texas homes" | `blocks[34-39]` | true reworded |
| 18 | "Panel upgrades, surge protection, rewiring, and generator repair — over 100,000 homes served across the Plano area." | "With over 100,000 homes served; the pride we take in our work shows through..." — **no location is attached to this number anywhere in the source** | `blocks[22]` | **changed specific** — the brief's own address fact is itself in unresolved conflict between Plano (Google) and Irving (Yelp); "across the Plano area" is invented specificity the source never claims |
| 19 | "A real call, start to finish" | "...professional... from start to finish" | `blocks[3]` (Ron Brenners testimonial block) | true reworded |
| 20 | "92°F, zero airflow, after hours — here's what we did" | "climbed to 92°F", "wasn't moving any air... at all", "The call came in after hours" | `blocks[30]` | true reworded |
| 21 | "Inside a 2,000 sq ft home, the temperature had climbed to 92°F — the furnace wasn't moving any air at all." | "Inside their 2,000 square foot single-family home, the temperature had climbed to 92°F. The... furnace wasn't moving any air through the home at all." | `blocks[30]` | verbatim (condensed; brand names Carrier/York dropped) |
| 22 | "A failed blower motor on a 30-year-old furnace." | "The culprit was a failed blower motor... equipment that is thirty years old" | `blocks[31]` | verbatim — "thirty years old" is the source's own words; **not** a computed value (see note below) |
| 23 | "Our technician worked carefully, avoiding damage to the aging, brittle components around it." | "one wrong move on a brittle component... Our technician took his time and worked deliberately to avoid creating any secondary damage." | `blocks[31]` | true reworded |
| 24 | "From zero airflow to a fully functioning system with a healthy 24°F temperature split — fixed in one after-hours visit." | "...a fully functioning system — in a single visit after hours... Temperature Split... 24°F" | `blocks[32]` | verbatim |
| 25 | "From the people we've helped" | (testimonials-section intro; no single source span) | — | true reworded / generic |
| 26 | "Here are five." | `material.quotes` genuinely holds 5 entries | `testimonials` (5 entries) | true reworded — an accurate count, not a fabricated one |
| 27 | "Cody Roberts is an ultimate professional, transparent, honest, and totally focused on the homeowner's needs. | "Cody Roberts is an ultimate professional, transparent, honest, and totally focused on the homeowner's needs." | `testimonials[0]` (Jeff Willie) | verbatim — see the apostrophe note below |
| 28 | "I had an excellent experience with this technician, Mr. | "I had an excellent experience with this technician/Mr.  Brett Conway ." | `testimonials[1]` (Mandana Shahbazi) | verbatim ("/" normalized to ",") |
| 29 | "Brett Conway. | "...Mr.  Brett Conway ." | `testimonials[1]` | verbatim — a sentence-splitter artifact: "Mr." reads as a sentence end |
| 30 | "He communicated clearly throughout the entire process, took the time to explain the issue and my options in a way that was easy to understand." | "He communicated clearly throughout the entire process, took the time to explain the issue and my options in a way that was easy to understand, and was incredibly respectful of my home." | `testimonials[2]` (Farrah Carlton) — **not** Mandana Shahbazi/Brett Conway, whose quote card this sentence follows on the design page | verbatim (prefix-cut) — real words, but drawn from a different reviewer than the one named two sentences earlier; worth a look before shipping, not a fabrication |
| 31 | "They explain the work, execute with precision, and are worth the money spent." | "They explain the work, execute with precision , and are worth the money spent." | `testimonials[4]` (James Kerr) | verbatim |
| 32 | "4.9 out of 5 across 6,203 Google reviews" | `material.rating = 4.9`, `material.reviews = 6203` | `ratings[0]` (google) | verbatim |
| 33 | "Ready when you are" | (CTA-section heading; no single source span) | — | true reworded / generic |
| 34 | "SERVING Plano, TX & the surrounding area" | "Plano" is the business's real, dominant (if disputed) location; "North Texas" used throughout | `facts` (address), `blocks[17]`, `[34]`, `[39]` | true reworded |
| 35 | "100%" | "100% Satisfaction Guarantee" | `blocks[2]`, `[7]`, `[9]`, `[24]` | verbatim |
| 36 | "2004" | "Since 2004" | `blocks[7]`, `[20]` | verbatim |
| 37 | "2004," | "Since 2004," | `blocks[7]` | verbatim |
| 38 | "100,000" | "over 100,000 homes served" | `blocks[22]` | verbatim as a bare number — the location attached to it (finding 18) is the changed-specific part, not the count itself |
| 39 | "92" | "92°F" | `blocks[30]`, `[32]` | verbatim |
| 40 | "2,000" | "2,000 square foot single-family home" | `blocks[30]` | verbatim |
| 41 | "30" | "thirty years old" | `blocks[31]` | verbatim |

## Six more findings (Phase 2c, 2026-09-15)

Before the credential-remainder fix, each of these 6 sentences carried a
real, corroborated credential somewhere inside it (`Licensed & insured`
→ `licensed_insured`, `24/7 emergency` / `24/7 emergency line` →
`emergency`, `Same-day service` → `response_time`), and the OLD
`_credential_backed()` exempted the entire sentence on that match alone
— so the true-reworded caption riding beside the credential was never
reached by the provenance check at all. Fixed: the credential now
exempts only its own matched span, and the rest of the sentence is
checked the same as any other. All 6 trace to real material; none is
invented.

| # | Design page text | Closest source span | Location | Verdict |
|---|---|---|---|---|
| 42 | "Licensed & insured Drug tested and background checked, so every visit gives you peace of mind." | "Licensed and Insured Drug tested, background checked, and fully licensed, giving you peace of mind." | `blocks[9]` ("Plano's Most Trusted AC Service" block) | true reworded |
| 43 | "Same-day service Fully stocked trucks ready to handle most repairs the same day you call." | "Same-Day Service : Our fully stocked trucks carry the parts needed to handle most plumbing repairs on the same day." | `blocks[2]` | true reworded |
| 44 | "24/7 emergency line A real team member answers your emergency call, any hour." | "24/7 Emergency Service We have team members available 24/7 to answer your emergency phone call." | `blocks[9]` | true reworded |
| 45 | "Call now for same-day service, or reach us online any time — a real team member answers 24/7 for emergencies." | composite of "Call Now For Service Schedule Online Now" (`blocks[2]`, `[9]`) and "team members available 24/7 to answer your emergency phone call" (`blocks[9]`) | `blocks[2]`, `[9]` | true reworded |
| 46 | "HOURS Mon–Fri, 8am–5pm 24/7 emergency line" | `material.hours = ('Mon-Tue-Wed-Thu-Fri-Sat-Sun 00:00-24:00', 'Monday-Friday 8am-5pm')` + "24/7 Emergency Service" (`blocks[9]`) | `facts` (hours), `blocks[9]` | true reworded — day names abbreviated, dash style changed |
| 47 | "© Milestone Electric, A/C & Plumbing Licensed & insured · Family-owned since 2004" | business name (`facts`) + "Licensed and Insured" (`blocks[9]`) + "Since 2004, Milestone is a family-owned and operated home service company" (`blocks[7]`) | `facts` (name), `blocks[7]`, `[9]` | true reworded — footer composite of three real facts |

## Notes on two specific rows the round asked to check independently

### The "100,000 homes ... across the Plano area" call (finding #18)

Confirmed independently, not just taken on faith: `blocks[22]`'s real
text is "With over 100,000 homes served; the pride we take in our work
shows through our unmatched service" — no location is attached to that
number anywhere in the source material. The design page adds "across
the Plano area." That specificity is invented, and it lands on
ground that is genuinely unsettled: `facts` (address) carries an
active, unresolved **conflict** between Google's address (2801 N
Central Expy, Plano, TX 75075) and Yelp's (4651 W John Carpenter Fwy,
Ste 170, Irving, TX 75063) — `confidence: "conflict"` in the frozen
brief. **Changed specific**, confirmed.

### The Jeff Willie testimonial — a genuine multi-review join, but not where the round expected

The round asked me to report where in `app/workbench/extract.py` the
join happens, without fixing it. I looked, and the honest answer is
more specific than "it's in extract.py" — the same symptom (several
separate customer reviews collapsed under one name) shows up **twice**
in this fixture, through two different paths, and only one of them is
actually `extract.py`.

**Where it really is** — `published.blocks[18]` (heading "Jeff
Willie") and, even more dramatically, `published.blocks[2]` (heading
"Different Plumbing Services We Offer," whose body swallows an entire
separate "Over 33,000 5 Star Reviews!" section, including the "20,000
5 star reviews" paragraph quoted above): both trace directly to
`app/workbench/extract.py:622-700`, `read_blocks()`. Its
`_HEADED_BLOCK_RE.findall(html)` (line 638) captures each recognized
heading's body as "everything up to the next recognized heading." When
the source page marks some section boundaries with a heading tag the
regex matches and others (a second and third customer review in a
carousel, an unrelated pricing/credentials section) without one,
the unheaded content is silently absorbed into the *previous* block's
`text` string as one undifferentiated blob. That is a real, reportable
gap in `read_blocks()` — not a dedicated "join reviews" function, but
its general heading-to-heading capture doing this whenever a page's
markup is heading-inconsistent. Confirmed by evidence, not assumed:
`blocks[2]`'s text runs from a plumbing-services intro all the way
through a "5 Star Reviews" sub-heading and its own paragraph, none of
which belongs under "Different Plumbing Services We Offer."

**Where it is NOT** — `testimonials[0]` (author "Jeff Willie," the
entry the design page's quote actually renders from) does not come
from `extract.py` at all. `brief.testimonials` is set once, in
`app/workbench/brief.py:397-398` (`brief.testimonials = [dict(r) for r
in place.reviews[:5]]`), from whichever directory adapter populates
`DirectoryPlace.reviews` first. Only `app/adapters/gplaces.py` ever
sets that field (`app/adapters/yelp.py` never touches `.reviews`), and
`gplaces.py:38-72`'s `_to_place()` builds it as a dict comprehension —
**one output dict per raw Google Places API review object**, `text`
taken verbatim as `(r.get("text") or {}).get("text", "")`. I read this
code end to end and found no point where two raw reviews' text fields
are concatenated. The literal `\n\n6/29/26\n` / `\n\n7/30/26\n`
structure inside `testimonials[0]["text"]` — three separately dated
reviews (Cody Roberts, Arturo Moreno, Dayton Gallagher) run together
under Jeff Willie's name — is either something Google's own Places API
returned verbatim for this one review (a real, documented Places API
quirk for edited/threaded reviews), or this fixture's `testimonials`
field predates the `gplaces.py` code currently in the tree (the
fixture was frozen in commit `9478fb1`, six months before this round).
Either way: **the round's claim that this specific join happens in
`app/workbench/extract.py` does not hold up against the code as it
exists today.** I'm reporting that discrepancy rather than writing
down a location I could not verify — the nearby, real `read_blocks()`
gap above is a true positive; the testimonials one is not the same
bug wearing a different hat.

### The apostrophe mismatch (finding #27)

`testimonials[0]`'s real text uses a curly apostrophe: "homeowner's
needs" (U+2019). The design page's rendered quote uses a straight
apostrophe: "homeowner's needs" ('). This is not the design tool
inventing anything — it traces to how the review was retyped into the
prompt given to the design skill when this fixture was built. `_bare()`'s
punctuation-stripping still resolves the substring match correctly;
noted here because the round asked for exactly this kind of
independent check, not because it changes any verdict.
