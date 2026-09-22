# Architecture

Every module, what it is for, and which way the data flows. Read alongside
`CLAUDE.md`.

## The flow, end to end

```
a name / a URL / "Name, City, ST"
        |
        v
app/workbench/resolve.py      name, town, website URL — and an assumption list
        |
        v
app/workbench/discover.py     which directories to ask
app/adapters/gplaces.py
app/adapters/yelp.py          one Place per source
app/adapters/osm.py
app/adapters/site_fetch.py    the business's own site, crawled to depth 2
app/adapters/pdf_read.py      a menu or price list that is a PDF
        |
        v
app/workbench/extract.py      one page -> ExtractedSite (+ evidence quotes)
app/workbench/brief.py        every source -> RawClaim list -> Brief
app/workbench/corroborate.py  RawClaims -> Facts with a confidence and a score
app/workbench/hours.py        three ways of writing a week -> one comparable form
        |
        v
app/store/brief_archive.py    briefs/<slug>/<timestamp>.json   (permanent)
app/store/leads.py            leads.brief_json                 (what screens read)
        |
        v
app/site/pipeline.py          photographs -> direction -> page
app/design/master_prompt.py   the prompt the model is given
        |
        v
app/store/sites.py            one row per version, each with a parent
app/web/server.py             the workbench, and /site/<lead>/<version>
        |
        v
app/review/run.py             assemble the material a review judges
app/review/checks.py          every claim on the page, with a verdict
app/store/reviews.py          reviews + findings, decided once, kept forever
app/web/annotate.js           the findings pinned onto the page itself
```

## By package

### `app/workbench/` — research and corroboration

- `resolve.py` — free text into a company. Deliberately biased: anything
  ambiguous is read as a name, never a URL, because reading a name as a URL
  loses the name and everything downstream builds a site for "S". Splits a
  trailing "City, ST 75033" off the name, postcode included.
- `discover.py`, `categories.py`, `prospect.py` — finding candidate businesses
  and deciding which directories can answer for a trade.
- `extract.py` — the largest and most bug-prone file. One page of markup into
  services, products, hours, blocks of prose, photographs, menu items, socials,
  emails, phone, address. Also records the **evidence**: the source's own
  sentence and where it was found. Every reader here is conservative on
  purpose; each guard names the false positive that forced it (a WordPress
  timestamp read as a phone number; a directory listing read as this business's
  address).
- `corroborate.py` — RawClaims to Facts. Two independent sources agreeing is
  VERIFIED; a solo Google Business Profile is enough for address and phone
  (`_GBP_ALONE_IS_ENOUGH`); a tie is a CONFLICT and ships nothing. Normalises
  per field, so "7110 Main St. Frisco, TX 75033" and "7110 Main St, Frisco, TX
  75033, USA" are one answer, not two.
- `hours.py` — a week, comparable. Handles "Mon-Fri 9-5" (which is not five in
  the morning), a whole week on one line, and both meridiem conventions.
- `match.py`, `weburl.py`, `types.py` — name matching, URL checking, and the
  `RawClaim` / `SourceType` vocabulary everything else speaks.

### `app/adapters/` — the outside world

One module per source, each returning the same shape. `site_fetch.py` is an
ordinary HTTP client and runs no JavaScript, which is why a site whose menu is
drawn by a script reads as having no menu. `chrome_cdp.py` drives a real
browser and is the way out of that, when a Chrome is available.

### `app/store/` — everything that persists

- `db.py` — schema and connection. Additive migrations only.
- `leads.py` — the lead, its brief, and its audit trail. `brief_with_overrides()`
  is the function almost everything should call: the stored brief with the
  operator's corrections applied on read, into both `facts` and `published`.
  `VERIFIABLE` is what may be corrected; `PUBLISHED_FIELDS` maps a field to
  where it lives and how typed text is read back into it.
- `brief_archive.py` — the permanent trail. `save()` writes a new timestamped
  file every crawl and rewrites `current.json` as a **pointer** to it.
- `sites.py` — versions, each with a parent and the instruction that made it.
- `reviews.py` — reviews and findings. A finding that has been decided survives
  a re-run of the checks.
- `photos.py`, `messages.py`, `preferences.py`, `fingerprints.py` — photograph
  labels and descriptions, the workbench conversation, style preferences learned
  from instructions, and the archived sameness instrument.

### `app/site/` — generation

`pipeline.py` is the live path: `run_stage()` for one stage, `open_site()` for
the first version, `iterate()` for an instruction. Each stage is idempotent and
stores its answer, so a retry costs only the stage that failed.

Everything else in this package is the **older deterministic renderer** —
`render.py`, `plan.py`, `theme.py`, `palette.py`, `fingerprint.py`,
`agreement.py` and the rest. It is live code that little calls, kept until it is
archived by tag. Do not extend it; do not delete it either.

### `app/review/` — the final gate

- `run.py` — assembles what a review judges: the brief (with corrections), the
  capture of the business's own site, and their hashes.
- `checks.py` — `inventory()`, `contradictions()`, `mechanics()`,
  `structured_data()`. Pure functions over text, no database, so they can be
  tested directly. Produces `Finding` rows carrying a verdict, a quote, an
  anchor and the resources a person needs to check it.

### `app/web/` — the workbench

- `server.py` — a plain standard-library HTTP server. Routes are a chain of
  `elif`s on the path; `POST /api/verify` is the one that records a correction,
  rebuilds the page and reports how the hours were read.
- `index.html` — one file, around 1,900 lines: the dashboard, the lead detail,
  the workspace, the labeller and the review panel.
- `annotate.js` — injected at serve time only for `?review=<id>`. Pins each
  finding onto the thing it is about, outlines it, and talks to the workbench by
  `postMessage`, because the preview frame is sandboxed.
- `serialize.py` — the brief as the front end receives it.

## The data shapes

**RawClaim** — one source saying one thing about one field:
`field, value, source_url, source_type, quote, found_in`. The last two are the
evidence, and everything the approval screen does depends on them existing.

**Fact** — a corroborated claim: `field, label, value, confidence, score,
corroborations, sources, candidates, dissent`. `confidence` is one of
`verified`, `unverified`, `conflict`, `operator_verified`.

**Brief** — `name, location, website_url, site_reachable, url_check, facts,
published, assumptions, open_questions, sources_consulted`, and after
`brief_with_overrides()` also `events`, `confirmable`, `published_superseded`,
`photo_labels`, `photo_vision`, `photo_notes`.

`published` is what the business says about itself with nothing corroborating
it: `tagline, about, services, products, hours, menu_items, menu_media, photos,
socials, emails, has_locations_page, blocks, evidence`. **This is where a
generated page's words come from.** An override that does not reach here changes
nothing a visitor sees.

**Finding** — `stage, verdict, title, detail, locator, anchor, quote, evidence,
resources`. `anchor` is `css:<selector>`, `text:<needle>` or `page`.
