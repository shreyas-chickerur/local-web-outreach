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

# Design brief: Milestone Electric Air Plumbing, Plumber — Plano, TX

You are designing a single-page, responsive marketing homepage for a
real, independently owned plumber business. Every fact and every
photograph below is real, supplied by the business or a directory
listing that corroborates it. You are not writing anything factual about
the business — see "Copy" below for the one narrow exception.

## What the visitor needs, in order

1. Can you help with my problem now? (the trades covered, stated
   plainly, above everything else)
2. Do you serve my area? (Plano, TX and the surrounding area)
3. Can I trust who shows up? (a named technician, a real credential, a
   real review with a name attached)
4. What does it cost, or how do I get a price?
5. How do I reach you in one tap?

## Section order

1. Trade + service area + call action (opening screen)
2. Trust proof: the signature review device (Jeff Willie / named techs)
3. What is covered: plumbing, electrical, A/C, by real block coverage
4. Proof of a real job: the 92F/zero-airflow furnace repair story (job_story_block_30/31/32/33 groups)
5. Reviews, with names (Mandana Shahbazi, Farrah Carlton, James Kerr...)
6. Credentials / hours / service area detail
7. Final call to action

Allowed variations: trust proof and "what is covered" may swap when
credentials are the stronger asset than a single review; the job story
may fold into "what is covered" rather than carry its own section. The
opening (trade + service area + call action) never moves from first;
the final call to action never moves from last.

## Art direction

- **Mood:** workhorse trust — Milestone's own words lead with speed and follow-through ("same-day", "fully stocked trucks", "peace of mind") and their photographs show real trucks, technicians and a completed panel job, not a styled studio set -- the material earns a page that reads as capable and immediate, not polished-generic.
- **Type pairing:** condensed and structural, a trade-shop wordmark (display: oswald,
  body: barlow)
- **Palette:** base #f7f3ea, ink #211a12, one accent #866713
  (mustard) — contrast-checked (ink/base and accent/base both
  clear WCAG AA for normal text).
- **Photograph treatment:** vignette_scrim.
- **Signature device:** quote — Milestone's strongest real asset is five named-author Google reviews (Jeff Willie, Mandana Shahbazi, Farrah Carlton, Brett Conway, James Kerr) behind a real 4.9-star, 6,203-review count -- one review set at full display size does more to earn a stranger's trust than a stat band or an icon grid ever could for someone deciding who to let into their home.
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

- `/photo/9/0` — people: A smiling bald man in a white polo shirt holding folders, standing in front of a branded yellow service van (hero candidate)
- `/photo/9/1` — product: An outdoor air conditioning condenser unit next to a brick wall and green shrubs (hero candidate)
- `/photo/9/2` — work: A hand adjusting colorful wiring inside an open furnace control panel
- `/photo/9/3` — product: Two gray gas water heaters installed side by side in a utility closet
- `/photo/9/4` — room: A tall entryway hallway with a crystal chandelier hanging from a high ceiling and a staircase to the side (hero candidate)
- `/photo/9/5` — detail: The underside of a kitchen sink showing a garbage disposal unit and connected pipes
- `/photo/9/6` — product: An outdoor standby generator and electrical panels mounted on a white brick wall next to an air conditioning unit (hero candidate)
- `/photo/9/7` — room: A white toilet and bathtub in a bathroom with patterned wallpaper and tile flooring
- `/photo/9/8` — work: A person's hands using a yellow clamp meter to test electrical wiring inside an open equipment panel. (hero candidate)
- `/photo/9/9` — detail: A close-up of a brushed nickel bathroom faucet and sink basin with water droplets.
- `https://callmilestone.com/plano/wp-content/uploads/sites/7/2022/10/9A0A9697-2-web-res-med-quality.jpg` — people: A smiling bald man in a white work shirt standing in front of a yellow and red branded service van parked outside a house. (hero candidate)

**Publicly fetchable versions** (the `/photo/9/N` paths above are this
app's own local proxy and will not resolve inside your canvas; these are
the same real photographs at their real, public CDN URLs, safe to use as
actual `<img src>` values):

- `https://b2048518.assetcdn.net/2.0/2048518/wp-content/uploads/sites/7/2024/04/9A0A9697-2-web-res-med-quality.jpg` — the technician-and-van hero photo (same shot as `/photo/9/0`)
- `https://b2048518.assetcdn.net/2.0/2048518/wp-content/uploads/2026/07/HVAC-1.jpg` — HVAC equipment/work
- `https://b2048518.assetcdn.net/2.0/2048518/wp-content/uploads/sites/7/2025/01/acunitrepair-scaled-1.jpg` — AC unit repair in progress
- `https://b2048518.assetcdn.net/2.0/2048518/wp-content/uploads/sites/7/2025/01/HeaterTuneUp_Body.jpg` — heater tune-up work
- `https://b2048518.assetcdn.net/2.0/2048518/wp-content/uploads/sites/7/2021/08/Electrical_Body.jpg` — electrical work
- `https://b2048518.assetcdn.net/2.0/2048518/wp-content/uploads/sites/7/2021/07/HomeWhyChoose.jpg` — a residential exterior, "why choose us" context

Use the hero photo for the opening screen. Use two or three of the
others across the page (the job-story section is a natural place for
one), matching the vignette_scrim treatment above. Do not use every one
of them if the page starts to feel like a stock gallery rather than a
designed page.

## Copy

Body copy comes ONLY from the numbered list below, selected by index —
you may choose which sentences to use and in what order, but you may
never write a new one, reword one, or combine parts of two into one.
Anything you print as body prose must be one of these exact sentences.

**about**
  [0] What our customers say about us are very important.
  [1] From how timely we are to how trustworthy we are, we strive to give a good experience to everyone who uses our services.
**feature_0**
  [0] Since November 2022, we’ve proudly served the Plano, TX community, providing reliable plumbing services for over 13 months in the area.
  [1] Centrally located: Our office ensures that we can offer same-day repairs and respond quickly to your plumbing needs.
  [2] Fully stocked work trucks: Our plumbers come prepared and are always ready to handle everything from minor leaks to major emergencies.
  [3] 2-mile radius of many Plano neighborhoods: This means we have faster arrival times and more efficient service, so you can count on us to resolve your plumbing issues quickly and effectively.
  [4] Whether it’s a routine repair or an urgent situation, we’re here to keep your home running smoothly.
  [5] Call Now For Service Schedule Online Now Call Now For Service Schedule Online Now Same-Day Plumbing Repairs
**feature_1**
  [0] When you’re dealing with a plumbing issue, waiting isn’t an option.
  [1] That’s why we have plumbers in Plano ready to provide same-day plumbing repairs you can trust.
  [2] From leaky faucets to clogged drains or water heater problems, we’re here to ‘fix it in a flash’.
  [3] With our reliable and efficient service, you’ll have peace of mind knowing your plumbing is back to normal—today, not tomorrow!
  [4] Call Now For Service Schedule Online Now Call Now For Service Schedule Online Now Awards That Reflect Our Service!
  [5] We Fix All Plumbing Issues
**feature_2**
  [0] At Milestone, we provide a wide range of plumbing services to meet your specific needs.
  [1] Whether you need a water heater installation, help with clogged drain lines, or other plumbing solutions, our team is equipped to handle it all.
  [2] Our expert plumbers ensure reliable service for any project, big or small.
  [3] Plumbing Installation Plumbing Maintenance Plumbing Repair Safe and Trusted Plumbing Company Choosing The Right Plumber in Plano, TX Finding the right plumber in Plano can make all the difference when it comes to receiving reliable, stress-free service.
  [4] It’s important to choose experienced professionals with a proven track record of quality work and exceptional customer care.
  [5] At Milestone, we take pride in offering: Upfront Pricing : We begin work on your home only after providing you with a clear, upfront price.
  [6] Same-Day Service : Our fully stocked trucks carry the parts needed to handle most plumbing repairs on the same day.
  [7] 100% Satisfaction Guarantee : We are committed to delivering a great experience and won’t leave until you are completely satisfied.
  [8] When you choose Milestone, you’re choosing dependable service and peace of mind.
  [9] What our customers say about us are very important.
  [10] From how timely we are to how trustworthy we are, we strive to give a good experience to everyone who uses our services.
**feature_3**
  [0] September 3, 2026 via Google Milestone to the Rescue!
  [1] Once again, Milestone was available to come to our aid for air conditioner repair.
  [2] I was home alone this afternoon, and noticed that it began to feel uncomfortably warm.
  [3] I checked the thermostat and saw that it said it was cooling but I could not hear...
  [4] Read more
**feature_4**
  [0] August 6, 2026 via Google We've had good experiences with Milestone throughout the years.
  [1] The most recent plumbing repair went exceptionally well, thanks to Daniel Tucker's expertise.
  [2] He was polite and he explained things clearly.
  [3] He didn't try to upsell/overcharge; in fact, I was thrilled with the price.
**feature_5**
  [0] July 21, 2026 via Google I had a great experience with Milestone Electric.
  [1] The service technician Luis Percy was professional, courteous, and knowledgeable from start to finish.
  [2] Despite the extreme heat, he took the time to thoroughly diagnose the issue, climbed onto the roof to access my HVAC unit...
  [3] Read more
**job_story_block_30_'The Problem'**
  [0] The call came in after hours.
  [1] Inside their 2,000 square foot single-family home, the temperature had climbed to 92°F.
  [2] The Carrier condenser outside was running, but the York furnace wasn’t moving any air through the home at all.
  [3] The system was completely down: no airflow, no cooling, and no relief from the brutal Texas summer heat.
  [4] As Texans, we know how to handle heat.
  [5] But no one should have to live like that, even for a single night.
  [6] At Milestone Electric, A/C, & Plumbing, we run after-hours calls — that part in and of itself wasn’t the challenge.
  [7] But after-hours repairs often come with real obstacles: parts suppliers are closed, which limits what you can source on the spot, and working outside in the dark adds time and complexity to every step of the job.
  [8] Our technician showed up anyway, did excellent work, and didn’t leave until the system was back up and running.
**job_story_block_31_'What We Found'**
  [0] The culprit was a failed blower motor.
  [1] Without it, the indoor air handler had no way to pull air across the coil and push it through the vents, regardless of what the outdoor unit was doing.
  [2] The added challenge: the furnace is from 1996.
  [3] Working on equipment that is thirty years old requires a different level of care — one wrong move on a brittle component and you’ve turned one repair into three.
  [4] Our technician took his time and worked deliberately to avoid creating any secondary damage.
  [5] We were honest with the homeowner: a system this age is a candidate for replacement, and that conversation is always worth having.
  [6] But replacement isn’t always the right answer for every family’s situation right now.
  [7] When a repair is what works best for the customer – even if it’s not the textbook recommendation – that’s what we’ll do, and we’ll do it right.
**job_story_block_32_'The Results'**
  [0] The home went from 92°F with zero airflow to a fully functioning system — in a single visit after hours.
  [1] Before Calling Milestone After Calling Milestone Indoor Temperature 92°F Cooling normally Airflow None Fully Restored Temperature Split None 24°F Time to Resolution – Same-Day Solution Note: A 24-degree temperature split confirms the system is doing its job.
  [2] For context, anything in the 18–22°F+ range indicates healthy, effective cooling.
**job_story_block_33_'What She Had to Say'**
  [0] Brandon was an angel sent to our family.
  [1] He was so kind to us: A++ service!
  [2] I’m currently going through treatment and thought I would need to stay in a hotel with my children that night.
  [3] But Brandon was so determined to fix the unit before leaving.
  [4] He was such a gentleman and so professional, a wonderful representation of Milestone’s values.
  [5] I truly can’t express how grateful I am for his work!
  [6] – Happy Rockwall Customer

**The one exception — headings, eyebrows, and button labels only**
(`ALLOW_AUTHORED_DISPLAY_TEXT`, this round only): you may write a short
heading, eyebrow, or button label yourself, ONLY if it is 8 words or
fewer, contains no digit, asserts nothing that would need a source to
verify (no "since", no award, no ranking, no credential word, no
"voted"/"best"/"trusted by"/"family-owned" or similar), and names
nothing except Milestone Electric Air Plumbing, its trade, or Plano, TX. Every such
string will be recorded and reviewed separately — write plainly, don't
reach for a claim to sound more impressive.

## Required elements

- Call action pinned/reachable at phone widths (material.phone: (972) 913-6165)
- Service area near the top (Plano, TX -- material.address's town)
- Hero: the business's own truck/technician photo (/photo/9/0 or the
  external CDN hero, both real hero candidates)
- Named technician from reviews (Daniel Tucker, Luis Percy both named
  in real reviews)
- Job story: the 92F/zero-airflow furnace repair -- use the
  job_story_block_30/31/32/33 groups below, real block content, not
  the capped feature_0..5 groups a rendered page would normally show
- Reviews with names: 5 real testimonials, all named
- Hours + 24/7 emergency line: both corroborated (material.hours,
  contractorfacts emergency fact)

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
