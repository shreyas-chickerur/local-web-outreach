# Tasks: `page-text`

Plan: `tasks/plan.md`. Specification: `SPEC-page-text.md`.

## Task 1: Web pages the crawl attempts reach the stored brief

**Description:** Add `pages` to `Brief`, a `_page_entry` helper, record the
homepage and every sub-page in `_read_their_site` (before the failure check),
return them to both call sites in `build_brief`, and add the key to
`brief_to_dict`.

**Acceptance criteria:**
- [x] With a fake fetcher serving three pages, `brief_to_dict(build_brief(...))["pages"]`
      holds three entries in crawl order, homepage first, each with visible text.
- [x] A 404 and a raised error are both recorded with `read: False` and a reason
      naming the status or the error.
- [x] A site whose homepage fails still has one entry, with the reason.

**Verification:**
- [x] `.venv/bin/python -m pytest -q tests/workbench/test_brief.py`
- [x] Tests: `test_every_page_the_crawl_reads_keeps_its_text`,
      `test_a_page_that_fails_is_kept_with_its_reason`,
      `test_a_site_that_cannot_be_reached_still_says_why`

**Dependencies:** none

**Files:** `app/workbench/brief.py`, `app/web/serialize.py`, `tests/workbench/test_brief.py`

**Scope:** medium

## Task 2: Menu PDFs keep their text

**Description:** `_read_menu_pdfs` appends a `kind: "pdf"` entry for every PDF
it tries: its text when read, "could not download" or "no text layer" when not.

**Acceptance criteria:**
- [x] A readable PDF's text appears in `pages`, as well as its menu items.
- [x] An unreadable PDF appears with `read: False` and which of the two reasons.

**Verification:**
- [x] `.venv/bin/python -m pytest -q tests/workbench/test_brief.py`
- [x] Test: `test_a_menu_pdf_keeps_its_text_not_only_its_items`

**Dependencies:** Task 1

**Files:** `app/workbench/brief.py`, `tests/workbench/test_brief.py`

**Scope:** small

## Task 3: Round trip through archive, database and corrections

**Description:** One test: `build_brief` with a fake fetcher → `brief_to_dict`
→ `brief_archive.save` (temporary root) → `leads.save_brief` (temporary
database) → `leads.brief_with_overrides`, with nothing hand-made in between.

**Acceptance criteria:**
- [x] The page text read at the start is present, unchanged, at the far end.
- [x] It is also present in the archived file on disk.

**Verification:**
- [x] Test: `test_the_crawls_page_text_survives_to_the_corrected_brief`
- [x] `make check`

**Dependencies:** Tasks 1 and 2

**Files:** `tests/store/test_page_text_round_trip.py`

**Scope:** small

## Checkpoint: the gate

- [x] `make check` passes
- [x] `/ponytail-review` on the diff
- [x] Commit

## Task 4: The real run on The Heritage Table

**Description:** Run the real command and open what it wrote.

**Acceptance criteria:**
- [x] `make brief Q="The Heritage Table, Frisco, TX 75033"` completes.
- [x] The newest file in `briefs/the-heritage-table/` and the lead 1 row in
      `workbench.db` both hold `pages`.
- [x] Reported: how many pages were attempted, which failed and why, the
      stored size, and whether "Cabernet" and "Sauvignon" appear.

**Verification:**
- [x] Manual: read the archived file and the database row directly

**Dependencies:** checkpoint above

**Files:** `docs/state-of-play.md` (what is now true, and what is stale)

**Scope:** no code

**Result, 22 September:** 18 documents attempted, 60,844 bytes of text, the
same in the archive (`2026-09-22T21-44-35`) and in lead 1's database row.
Three failed with reasons: `xmlrpc.php` status 405, `?p=2703` timed out, the
dinner menu PDF could not download (the server returns 404). "Cabernet",
"Sauvignon", "Non-alcoholic" and "forty-eight" appear in none of it: the wine
list is an image. See `SPEC.md` for what this hands to `read-ladder`.

## Checkpoint: review with Shreyas

- [ ] Findings from task 4 presented
- [ ] Decide whether to move on to `checks-read-crawl`
