# Architecture

Every module, what it is for, and which way the data flows. Read alongside
`CLAUDE.md`. Current as of 23 September 2026.

## The flow, end to end

```
a name / a URL / "Name, City, ST"                    make brief Q="…"
        |
        v
app/workbench/resolve.py      name, town, website URL, and an assumption list
app/workbench/discover.py     which directories to ask
app/adapters/places.py, yelp.py, osm.py     one listing per source
app/adapters/site_fetch.py    their own site: Chrome render, then plain fetch
app/adapters/pdf_read.py      a menu PDF's text
app/adapters/image_text.py    a menu image's text, read by a model once per image
        |
        v
app/workbench/extract.py      one page -> ExtractedSite (+ evidence, logo candidates)
app/workbench/brief.py        every source -> RawClaims -> Brief (+ pages, logo)
app/workbench/corroborate.py  RawClaims -> Facts with a confidence and a score
        |
        v
app/store/brief_archive.py    briefs/<slug>/<timestamp>.json   (permanent)
app/store/leads.py            leads.brief_json, and corrections applied on read
        |
        v
prompts/<slug>/vN.md          the design prompt, written from the brief and the playbook
app/design/bridge.py          one design run (make design), or one chat edit
app/store/sites.py            one row per version, each with a parent
        |
        v
app/web/server.py             the workbench: chat, versions, master, /site/, /photo/, /logo/
app/review/run.py, checks.py  every claim on the page against the crawl's own text
app/store/reviews.py          reviews and findings, decided by a person
app/web/annotate.js           the findings pinned onto the page itself
        |
        v
app/design/proposal.py        one self-contained file for the owner (make proposal)
```

The workbench can still build a first version with the older generator in
`app/site/` (the "Build the first version" button). Pages from the design tool and
from the design bridge are the current path; see `app/site/` below.

## By package

### `app/workbench/` — research and corroboration

- `resolve.py` — free text into a company. Anything ambiguous is read as a name,
  never a URL. Splits a trailing "City, ST 75033" off the name.
- `discover.py`, `categories.py`, `prospect.py` — finding candidate businesses
  near a point, and ranking them by how much they need a website.
- `brief.py` — the crawl and the brief. Reads up to 24 pages of the business's
  own site, keeps every page's text (`pages`, with a reason for each one it
  could not read), reads menu PDFs and menu images, and ranks the logo
  candidates (`_pick_logo`).
- `extract.py` — one page of markup into services, hours, prose blocks,
  photographs, menu items, socials, phone, address, the **evidence** (the
  source's own sentence and where it was found) and logo candidates. Every
  reader is conservative; each guard names the false positive that forced it.
- `corroborate.py` — RawClaims to Facts. Two independent sources agreeing is
  verified; a tie is a conflict and ships nothing.
- `hours.py`, `match.py`, `weburl.py`, `types.py` — hours in comparable form,
  name matching, the website address check (`FAULTS`), and the `RawClaim`
  vocabulary.

### `app/adapters/` — the outside world

One module per source. `site_fetch.py` renders a page in Chrome and falls back to
a plain fetch, recording each attempt's reason when both fail; `download()`
returns bytes or the reason there are none. `image_text.py` reads a menu image
with a model once and caches the text by the image's bytes. `photos.py` and
`logos.py` fetch a lead's photographs and logo once and cache them. `language_model.py`
is the one place a structured model call is made.

### `app/store/` — everything that persists

- `db.py` — schema and connection. Additive migrations only.
- `leads.py` — the lead, its brief and its audit trail. `brief_with_overrides()`
  is what almost everything should call: the stored brief with the operator's
  corrections applied on read, into both `facts` and `published`. The master
  version (`mark_master`, `master_version`) is an event in the same trail.
- `brief_archive.py` — every crawl kept; `current.json` is a **pointer**.
- `sites.py` — versions, each with a parent, its notes (model, cost, prompt) and
  the instruction that made it.
- `reviews.py` — reviews and findings; a decided finding survives a re-run.
- `photos.py`, `messages.py`, `preferences.py`, `fingerprints.py` — photograph
  labels, the workbench conversation, style preferences, and the old
  generator's sameness records.

### `app/design/` — pages from the design model

- `bridge.py` — the design bridge. `design()` runs one design from a prompt;
  `edit()` makes one change a person asked for in the chat. Both run the Agent
  Software Development Kit with the model named in `DESIGN_MODEL`, in a folder of
  their own, with four file tools approved by path, a spending ceiling ($5 a design, $1 an
  edit), and the photographs and logo as files. The page is saved as a new
  version with its cost.
- `proposal.py` — the current version as one file with every photograph and the
  logo inside it, for an owner to open before anything is hosted.
- `playbooks/restaurant.md` — what a restaurant page is scored against, and the
  list of devices each earlier site used and the next may not repeat.

### `app/review/` — the final gate

- `run.py` — assembles what a review judges: the brief with corrections, the
  text the crawl stored for every page it read (`page_text`), and the values
  corrections replaced, removed so they cannot support a claim.
- `checks.py` — `inventory()`, `contradictions()`, `mechanics()`,
  `structured_data()`. Pure functions over text. Every corroborated claim links
  to the page and the words that back it, or the directory fact.

### `app/site/` — the older generator, and two readers the current path uses

`visible.py` (a page's visible text) is used by the crawl. Everything else here
is the older generator the workbench's build button still uses: `pipeline.py`
(`run_stage`, `iterate`), `render.py`, `theme.py`, `styles.py` and the rest. Do
not extend it; it is archived when the workbench no longer calls it. Modules
nothing reached were removed on 23 September 2026 and are recoverable from the
tag `archive/before-cleanup-2026-09-23`.

### `app/web/` — the workbench

- `server.py` — a standard-library HTTP server. `iteration()` sends a chat
  sentence to an edit run on a designed page, or to the old generator on one
  it built; `rebuild_after()` does the same for a correction.
- `index.html` — one file: the dashboard, the lead detail, the workspace (chat
  on the left, the page in the middle, versions and history on the right), the
  labeller and the review panel.
- `annotate.js` — injected at serve time only for `?review=<id>`.
- `serialize.py` — a brief as JSON.

## The data shapes

**RawClaim** — `field, value, source_url, source_type, quote, found_in`.

**Fact** — `field, label, value, confidence, score, corroborations, sources,
candidates, dissent`. `confidence` is `verified`, `unverified`, `conflict` or
`operator_verified`; a corrected fact keeps the value it replaced as
`superseded`.

**Brief** — `name, location, website_url, url_check, facts, published, pages,
ratings, testimonials, place_photos, assumptions, open_questions`.

`published` is what the business says about itself: `tagline, about, services,
hours, menu_items, menu_media, photos, socials, emails, logo, blocks,
evidence`. **This is where a page's words come from.** An override that does
not reach here changes nothing a visitor sees.

`pages` is every document the crawl attempted: `url, kind (page, pdf or image),
read, reason, text`. The claim checks search it.

**Finding** — `stage, verdict, title, detail, locator, anchor, quote, evidence,
resources`. Only `contradicted` blocks approval.
