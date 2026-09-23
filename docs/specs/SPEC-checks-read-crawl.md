# Spec: `checks-read-crawl`

Module 2 of 4 in `docs/specs/SPEC-crawl-is-the-source.md`. Depends on `page-text`, which is built.

## Objective

The claim checks stop reading the hand-made `captures/<slug>/live-site.md` and
search the text the crawl stored in the brief's `pages`. A page the crawl could
not read becomes an `unmeasured` finding naming the page and the reason. A fact
Shreyas corrected outranks every source: its corrected value is checked for
contradiction, and the value it replaced cannot make a claim look supported.

## Producers and consumers, for the wiring check

| Seam | Producer | Consumer | Change |
|---|---|---|---|
| Text the checks search | `review/run.material` (read `live-site.md`) | `checks.inventory` via `run.findings` | built from `brief["pages"]`; `live-site.md` never read |
| Brief the checks judge against | `server._review_brief` → `leads.brief_with_overrides` | `run.findings` | page text taken from that same brief, so both sides share one crawl |
| Unread pages | `brief["pages"]` entries with `read: false` | `run.findings` | one `unmeasured` finding per page, with its reason |
| Old briefs with no `pages` | archive, database | `run.findings` | one `unmeasured` finding: crawled before page text was kept, re-crawl |
| Corrected facts | `leads.brief_with_overrides` (`operator_verified`) | `checks.contradictions` via `_verified_fields` | counted as verified; the superseded value removed from what can support a claim |
| Review provenance | `run.material` → `reviews.open_review(capture_hash)` | review screen ("capture …") | hash of the page text; the screen says "page text" |

Stale afterwards: every open review was judged against `live-site.md`. Review 2
(Heritage version 14) is re-run, not edited; Fish Shack gets its first review.

## Tasks

1. `material` builds the checked text from `pages`; no `pages` → one
   `unmeasured` finding. Tests in `tests/test_review.py`.
2. Each unread page → an `unmeasured` finding with its address and reason.
3. Corrections win: an `operator_verified` fact is checked for contradiction,
   and its superseded value does not corroborate a sentence.
4. The real run: checks on Fish Shack version 4 and Heritage version 14 in
   memory, compared with the stored review 2, reported before anything is
   written.

## Boundaries

- **Never:** read or delete `live-site.md`; change a finding someone decided.
- **Ask first:** opening or refreshing a review on a real lead (it writes rows
  Shreyas will read).

## Success criteria

- [ ] No code path reads `live-site.md`.
- [ ] A page that prints a corrected fact's old value is `contradicted`.
- [ ] Each unread page appears once as `unmeasured`, with its reason.
- [ ] `make check` passes; the real in-memory run is reported.
