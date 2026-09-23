# State of play — 22 September 2026

Where the work actually stands, what is stale, and what is next. Update this
file when any of it changes; a stale status document is worse than none.

## The one real lead

`lead 1`, The Heritage Table, a restaurant at 7110 Main Street, Frisco, Texas.
Fourteen versions, each parented. Its page is **finished as a design** — the
owner has judged the colour, structure and experience good and does not want
them reopened. What remains for it is factual validation.

Its site is WordPress at `https://www.theheritagetable.com/dev/`. On 22
September its menu pages held **no menu text at all**, not even hidden in the
markup: the wine list is an image (`Wine-List-Web-5-pdf.jpg`, lazy-loaded
through `data-src`), and the dinner menu PDF it links returns 404. This
contradicts version 14's own note, which says a browser saw both menu pages
as live text on 16 September. Unresolved: the site may have changed, or that
session read a different page. The site's firewall refuses plain command-line requests
(406); only the crawl's Chrome gets through. The footer
writes the address as `7110 Main St. Frisco, TX 75033` with no comma before the
town — which is what broke the address reader until it was fixed.

## Done

**The evidence trail.** `RawClaim` carries `quote` (the source's verbatim
words) and `found_in` (where in the source). It survives through corroboration
into a fact's `sources`, `candidates` and `dissent`, through the serializer,
and into the archived brief. The approval screen and the annotations are built
on it.

**Extraction fixes, all found on real data.** A WordPress timestamp inside an
image filename was being published as the business's phone number. Google
writes an evening as "5:00 – 9:00 PM", marking only the close, which was read
as five in the morning and made the hours a conflict. `Mon-Fri 9-5` was read as
a twenty-hour overnight. A whole week on one line ("Sun–Wed 5–9pm, Thu–Sat
5–10pm") had the first range applied to every day named on it. The address
reader required a comma before the town and so never read the business's own
footer, leaving the address on one source forever.

**The approval stage**, with on-page annotations rather than a separate review
screen, an audit log, and findings that survive a re-run once decided.

**Wider corrections.** Twelve fields instead of four: address, phone, hours,
website, plus business name, tagline, their story, what they sell, email,
photographs, menu items and social profiles. Overrides now reach `published`,
which is where a page's words come from. A correction rebuilds the page; a
re-confirmation of a value you already corrected costs nothing.

**The broken seams, all three.** `make brief` now writes to the database as
well as the archive. `review/run.py` follows the pointer in `current.json`
instead of reading it as a brief. The review judges the page against the brief
with corrections rather than the archived crawl.

**Workbench fixes.** Hours accept any format and the screen says back how it
was read. The listing warning resolves once the website is confirmed. Ratings
are a plain card with one open-in-new-tab control. Service chips no longer look
clickable. The first build shows a stage-by-stage progress panel with elapsed
time. Every piece of evidence has a "show me where" link that opens the source
page scrolled to the exact sentence, using a text fragment.

## Stale, and known to be

- **`captures/<slug>/live-site.md` is no longer read by anything** (22
  September, `checks-read-crawl`). The checks search the page text the crawl
  stores in the brief. Judged that way, Heritage version 14 goes from 7
  unsourced claims to 127: almost all drinks and wines, which the hand-made
  copy held as text and today's crawl cannot read (the wine list is an image).
  Its 160 "corroborated" in review 2 rested on that copy. `read-ladder` is the
  fix.
- Version 14 has its review (review 2, opened 22 September, against crawl
  `72fe0c4a`). Re-running the checks in memory on 22 September gave the
  identical 187 findings, and nothing is decided on it yet. Review 1, against
  version 13, is still open and holds the only decisions made so far.
- A second lead exists, Oishii Sushi & Pan-Asian in Plano (lead 7), created 21
  September with no site built. It is not in the trade either.
- **Fish Shack, Plano (lead 8)**, drawn at random from the discovery cache on 22
  September: versions 1 to 4, built on the Claude Design canvas from
  `prompts/fish-shack/`. Checked in memory against its crawl: nothing
  unsourced or contradicted; 4 assembled sentences and 1 wording note for
  Shreyas. No review opened yet.
- The Heritage Table's versions were written by hand, not by `pipeline.py`. A
  correction now triggers `iterate()`, which may not cope with a hand-authored
  page. The failure path is handled and the correction is never lost, but the
  path has not been exercised.

## Next

From the backlog (the live copy is an artifact; this is the summary):

- **C1–C4** — build the lead-detail screen properly: grouped by what a thing
  is, each row showing the value, the confidence, the sentence, the source link
  and an inline correction; show the gaps, because a field with no source
  currently renders as nothing; show disagreement plainly, which exists in code
  and has never been seen on a real lead. C4 is Shreyas's judgement.
- **D1–D4** — re-crawl from the screen and say what changed; tests; drive the
  screen in a browser; run `make check`.
- Then the blocking items: the Agent Software Development Kit bridge, so stage
  four stops being a person writing markup; somewhere to put a finished site; a
  crawl that can see JavaScript; and a second business, in the real trade.

## Known test failures

None on the owner's machine: 1662 passed, 3 skipped, 21 expected failures.

Three tests fail in a cloud copy that resolves a different pypdf and lacks a
`tools/` package — `tests/adapters/test_pdf_read.py`,
`tests/workbench/test_brief.py::test_a_menu_pdf_is_read_not_just_linked`, and
`tests/test_the_instrument_reproduces.py`. They are environment artifacts, not
real, and were proven so by building a Python 3.11 environment with `uv` and
running the suite against the owner's own files.

The expected failures are genuine and documented in place: known gaps in the
currently wired seam gate, and performance budgets where the weight is the
business's own photographs.
