# Capability map: the crawl is the source

Approved by Shreyas on 22 September 2026. Intent: `docs/intent/crawl-is-the-source.md`.

## Why

The next goal is a site for another restaurant lead: top tier, appealing to the
people who would go there, different enough from every other site this system
has made, and something the owner would pay a thousand dollars for. A page
like that can only be shown to an owner if every claim on it can be traced to
something the business actually published. Today the checks judge claims
against a hand-made copy of one site, dated 16 September, that nothing in the
code writes. That has to be replaced before a second restaurant is built.

The second restaurant is **Fish Shack**, Plano (`http://fishshackplano.com/`),
drawn at random on 22 September from the eighteen independent restaurants in
the workbench's discovery cache, national chains and The Heritage Table
excluded. It is not yet a lead.

## Modules

| Module id | Responsibility | Depends on | Spec |
|---|---|---|---|
| `page-text` | The crawl keeps the visible text of every page and menu PDF it read, with its address and, when it failed, the reason. Stored inside the brief. | — | `SPEC-page-text.md` |
| `checks-read-crawl` | The checks search that stored text instead of `live-site.md`. An unreadable page becomes an `unmeasured` finding naming the reason. A correction wins for its fact. | `page-text` | not yet written |
| `read-ladder` | Every tool is tried before a page is called unreadable: plain fetch, browser, PDF reader, then a model reading images, each image read once and remembered by a fingerprint of its content. | `page-text` | not yet written |
| `claim-mapping` | Each claim points at its fact, the page address and the exact sentence, with a "show me where" link. | `checks-read-crawl` | not yet written |

Build order: `page-text` → `checks-read-crawl` → `read-ladder` → `claim-mapping`.

The first two cost no credits. The Heritage Table's wine menu is live text now,
so they may be enough on their own to turn "Cabernet" from unsourced into
corroborated. The image reader comes after that has been measured.

## Decisions made with this map

1. Page text lives inside the brief document under a `pages` key, so the
   archive, its pointer and the database copy all carry it through paths that
   already exist.
2. "Could not read" reuses the existing `unmeasured` verdict, with the reason in
   its detail. The screen already shows it and it already does not block.
3. Image reading reuses `app/adapters/claude.py`, cached under `.cache/` by a
   fingerprint of the image's content.
4. `live-site.md` stays on disk and is no longer read. The design prompt for
   version 1 keeps its citation of it as history.
5. Old reviews keep their stored capture hash. New reviews store a hash of the
   page text in that column; no new column.
