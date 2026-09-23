# Implementation plan: `page-text`

Module 1 of 4 in `docs/specs/SPEC-crawl-is-the-source.md`; specification in `docs/specs/SPEC-page-text.md`. Task list in
`tasks/todo.md`.

## Overview

The crawl keeps the visible text of every page and menu PDF it attempts, as a
`pages` list on the brief, with a reason for every one it could not read. It
reaches the archive, the database and the corrected brief through the paths
that already exist.

## Architecture decisions

- **`_read_their_site` returns the pages it attempted** as a fifth value. Both
  call sites in `build_brief` (lines 363 and 462) take it and set
  `brief.pages`. A mutable list passed in was the alternative; a return value
  is harder to forget at the second call site.
- **One helper, `_page_entry(url, result)`, turns a `FetchResult` into an
  entry.** The reason comes from what the fetch already reports, in this
  order: certificate error, the fetch's own error text, a non-success status
  ("status 404"), an empty response. Nothing new is measured.
- **The homepage is recorded even when the whole site fails**, since that is
  exactly the case where the reason matters most.
- **`_read_menu_pdfs` appends its own entries** (`kind: "pdf"`), with "could not
  download" or "no text layer" as reasons. It already knows both.
- **`brief_to_dict` gains one key.** `leads.brief_with_overrides` loads the
  stored document whole and adds keys to it, so `pages` passes through with no
  change there. The round-trip test proves that rather than trusting it.
- Fixture files written by `tools/make_fixtures.py` only gain `pages` when that
  tool is re-run. Not re-running it is deliberate: it would rewrite every
  fixture for a key nothing in generation reads.

## Dependency graph

```
_page_entry ─► _read_their_site ─► build_brief sets Brief.pages ─► brief_to_dict
                    │                                                  │
_read_menu_pdfs ────┘                                archive.save + leads.save_brief
                                                                       │
                                                         leads.brief_with_overrides
```

## Tasks

1. Web pages the crawl attempts reach the stored brief (medium).
2. Menu PDFs keep their text (small).
3. Round trip through archive, database and corrections (small).
4. The real run on The Heritage Table (no code).

Checkpoints after task 3 (the gate) and after task 4 (your review).

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `brief_to_dict` drops the new key | High: everything downstream silently empty | Task 3's round trip with nothing hand-made in between |
| A test compares serialized briefs to stored fixtures byte for byte | Medium: `make check` fails | Task 3 runs the full gate; fix by comparing named keys, not by regenerating fixtures |
| Stored text is much larger than expected | Low | Task 4 measures it on a real site before any cap is chosen |
| The Heritage Table's wine menu is not among the 24 pages the crawl reaches | Medium: "Cabernet" stays unsourced | Task 4 reports which pages were read; a reach problem becomes input to `read-ladder` |

## Open questions

None.
