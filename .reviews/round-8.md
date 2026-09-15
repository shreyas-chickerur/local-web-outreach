# Round 8 — three bounded forks, then one re-freeze

Continues Round 7 ("Thicken the brief," commits `2c1b4bd`..`c54b83d`,
which fixed the four causes: PDFs discarded, no JavaScript rendering,
a keyword-gated one-level crawl, and aggressive caps). This round's own
governing instruction was narrower and explicit: diagnose why
restaurant-rich still has zero menu items as a DIFF against two
working fixtures and stop at the first checkpoint that fails, raise
the block cap since it was binding on the majority, then re-freeze —
in that order, three commits maximum, nothing touched in the fingerprint/
quality-census/blind-judging apparatus that measures the generator
being retired.

Baseline held throughout, confirmed unchanged after every commit:
ruler `a762bcc9`, rule `254e171b`, labels `122e6ec8`, held-out
`7aa64298`, `render_snapshots.json`'s own committed hash (regenerated
for exactly the fixtures this round moved — see below).

## 1. Why restaurant-rich still has zero menu items

Diffed against barbecue and law-rich (24 menu items each) at exactly
three checkpoints, stopping at the first that failed:

- **(a) Is the PDF reached by the crawl at all?** Yes. Using the
  fixture's own real `website_url`
  (`http://www.theheritagetable.com/` — the `www.` matters, the
  homepage's own internal links are all `www`-prefixed and a
  non-`www` base would silently treat every one of them as external)
  the depth-2 crawl reaches four real pages —
  `/dev/menu-dinner-menu/`, `/dev/menu-drinks/`, `/dev/menu-wine/`,
  `/dev/chefs-tasting-menu/` — and `extract_menu_media()` correctly
  finds the same PDF on every one of them.
- **(b) If reached, does text extraction return characters or
  nothing?** Nothing — and it is not a scanned/image PDF, it is a
  dead link. `HT-Dinner-Menu-1-17-23-1.pdf` 404s directly from
  WordPress itself (`x-nginx-cache: WordPress`, plain `text/html`
  error body), confirmed with plain `curl`, multiple user agents, an
  explicit `Referer` header (ruling out hotlink protection), and the
  project's own real-Chrome fetch path. All four pages that embed it
  carry **zero blocks and zero menu items of their own** — the entire
  "menu" on this business's real, current site is this one now-dead
  PDF, embedded via a WordPress plugin, with no text fallback anywhere
  else on the site.
- **(c)** Moot — (b) already failed.

Per this round's own instruction ("nothing = scanned/image PDF, a
different problem — say so and stop, do not build OCR"): stopping
here. This is the business's own site being missing content, not a
crawl or extraction defect — no fix applies, and this round does not
attempt one. It confirms Round 7's finding (already reported as
"genuinely dead on the live site") with more certainty, not a new
result.

One unrelated, real bug found while tracing this: `content_page_urls()`
doesn't `.strip()` an href before `urljoin`, so a whitespace-padded
href (`<a href=" https://external.example/">`, seen on this exact
page) gets joined as a relative path instead of recognized as
external, letting garbage URLs onto the crawl candidate list. Did not
affect this fixture's outcome (real internal pages were still found)
and is out of this round's scope — flagged as a separate task
(`task_fbaab086`) rather than fixed here.

## 2. The block cap

`_BLOCK_LIMIT` raised from 20 to 40
([extract.py:599](../app/workbench/extract.py)). A single uncapped
measurement (no experiment series — one pass, several fixtures) found
natural block counts of 0 (blocked), 6, 14, 75, 107, 134, 227 — no
single number clears all of them without also pulling in noise.
Inspecting law-rich's own blocks past position ~35 showed individual
FAQ sub-questions from deep practice-area subpages and an unrelated
sponsored blog post (a Baylor Athletics feature), not further genuine
sections about the business. 40 doubles the old cap, clears every
fixture that was genuinely under it, and reaches well into the largest
sites' real content (awards, admissions, testimonials, in-the-news
items) before crossing into that granularity — a crawl-shape /
deduplication problem, not a cap problem, and out of scope this round.

## 3. Re-freeze

7 of 16 fixtures with live sites were successfully re-crawled and
re-frozen (commit `6b2209f`) — only `published` replaced, every other
key (`design_direction`, `photo_vision`, facts, ratings, etc.)
untouched, and each fixture's own `photos` list deliberately held at
its pre-freeze value so it keeps matching the already-frozen
`photo_vision` labels (a fresh crawl can surface different images;
re-labelling them needs a real vision pass this round does not call
for).

| fixture | blocks | block chars | menu items | capture % |
|---|---|---|---|---|
| barbecue | 20→40 | 5,022→12,367 | 24→24 | 35%→59% |
| bare-trade | 20→40 | 14,214→30,251 | 1→1 | 34%→54% |
| dentist-rich | 20→40 | 5,400→16,028 | 4→4 | 20%→45% |
| dentist | 20→40 | 11,068→19,668 | 4→4 | 24%→37% |
| hvac-rich | 20→40 | 10,028→23,323 | 3→3 | 13%→25% |
| hvac-second | 20→40 | 16,770→38,265 | 1→1 | 18%→23% |
| hvac | 20→40 | 9,855→21,498 | 3→4 | 21%→40% |

The other 9 fixtures with live sites were **not** re-frozen this
round. `barbecue-rich` (hardeightbbq.com) is a confirmed, repeat 403 —
the same block already on record from Round 7. The remaining 8
(`law-rich`, `law`, `restaurant-casual`, `restaurant-rich`,
`roofer-rich`, `roofer`, `salon-rich`, `salon`) came back "site
unreachable" partway through the run, immediately after a very long
real-world gap in this session (the host's own uptime/date crossed a
day boundary mid-run) — almost certainly an environmental artifact,
not the sites actually going down. A single bounded (200s) re-check of
`restaurant-rich` afterward — chosen because it is this round's own
headline case and was confirmed working earlier in the session — also
failed to complete in time. Per the explicit instruction to do only
high-confidence work rather than chase an uncertain, possibly-transient
failure, those 8 were left on their prior crawl instead of retried
again. This does not weaken item 1's diagnosis: restaurant-rich's dead
PDF was independently confirmed by direct fetch, not by this re-freeze.

**New mean capture, all 15 measurable fixtures (7 refreshed this
round, 8 carried forward at their Round 7 value): 29% → 36%.**

`render_snapshots.json` and `.reviews/review/*.html` were regenerated
— both purely local, deterministic re-renders of each fixture's
already-frozen `design_direction`, no network, no re-judging — for
exactly the 7 fixtures that moved. Two tests are left failing on
purpose, per this round's own instruction not to touch what measures
the generator being retired:
`tests/sitegen/test_axes_are_real.py::test_no_axis_is_a_function_of_another`
and
`tests/test_the_instrument_reproduces.py::test_the_committed_sheet_shows_the_corpus_that_shipped`
— both want `tools/contact_sheet.py`'s committed sheet and the
fingerprint axis vector re-pinned against the moved fixtures, which is
exactly the RULER/RULE/LABELS/HELD_OUT re-pinning this round is told
not to do.

`make check`: 1,025 passed, 7 xfailed, 2 failed (both named above,
both expected and left alone).

## Largest remaining cause of lost content

The **services cap** (`_SERVICE_LIMIT`, still 20 — unchanged this
round, out of its stated scope). The same uncapped measurement that
picked the block cap already showed natural service counts running far
past it on the richer sites: hvac-rich 313, law-rich 338, roofer-rich
307, dentist-rich 126 — an order of magnitude past the cap, a much
bigger gap than blocks ever had. Not investigated further this round.

## Also this session, out of round scope

Added an optional `on_progress` callback to `build_brief()` /
`_read_their_site()`, wired to the CLI's `brief` command
(commit `5a3b5ef`) — a real crawl was silent for minutes with no way
to tell it apart from a hang. Purely additive; no existing caller is
affected.
