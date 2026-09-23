# Spec: `page-text`

Module 1 of 4 in `docs/specs/SPEC-crawl-is-the-source.md`. Status: draft, awaiting approval.

## Objective

The crawl already reads up to 24 pages of a business's own site and every menu
PDF it finds, then keeps only the fields it extracted and throws the text
away. Keep the text. Each document read becomes one entry in a new `pages`
list on the brief, so the checks (module 2) have the business's own words to
search, dated with the crawl they came from.

A page the crawl tried and failed to read is kept too, with the reason, so
"we never saw it" can be told apart from "it is not there".

## The shape

One entry per document the crawl attempted:

```python
{
    "url": "https://www.theheritagetable.com/dev/wine/",
    "kind": "page",          # page | pdf
    "read": True,
    "reason": "",            # when read is False: "status 404", "timed out",
                             # "certificate error", "PDF has no text layer" ...
    "text": "Cabernet Sauvignon, Caymus, Napa Valley ...",  # visible text only
}
```

- Visible text comes from `app.site.visible.visible_text_runs`, the reader that
  already exists, one run per line. Not a new parser.
- The homepage is the first entry.
- Order is the order the crawl read them in.
- No size cap in this module. Twenty-four small-business pages are around a
  hundred kilobytes. If a real site proves otherwise, cap it then and say so.

## Producers and consumers, for the wiring check

| Seam | Producer | Consumer | What can break |
|---|---|---|---|
| Text of each page | `_read_their_site` in `app/workbench/brief.py` | `Brief.pages` | a page fetched but not recorded; a failed fetch skipped silently with `continue`, as today |
| PDF text | `_read_menu_pdfs` in `brief.py` | `Brief.pages` | the text is used for menu items and dropped |
| `Brief.pages` → document | `brief_to_dict` in `app/web/serialize.py` | archive and database | **it copies only keys it names**, so a new field is dropped here unless added |
| Document → archive | `brief_archive.save`, called by `app/cli.py` and `app/web/server.py` | `briefs/<slug>/<stamp>.json` | none expected; it writes the whole document |
| Document → database | `leads.save_brief`, called by the same two | `leads.brief_json` | none expected; it stores the whole document |
| Database → with corrections | `leads.brief_with_overrides` | the checks, the generator, the screen | must pass `pages` through untouched |
| Other callers of `build_brief` | `tools/capture_census.py`, `tools/make_fixtures.py` | fixture files | fixtures grow a `pages` key; check nothing compares them byte for byte |

After this module ships, what is stale: every brief archived before it has no
`pages`. Module 2 must treat a missing `pages` as "not crawled with text yet",
not as "the site says nothing".

## Commands

```
make check                                        # the gate
.venv/bin/python -m pytest -q tests/workbench/test_brief.py tests/store
make brief Q="The Heritage Table, Frisco, TX 75033"   # the real run
```

## Project structure

No new files except tests. Changes land in `app/workbench/brief.py` (the
`Brief` dataclass and the crawl), `app/web/serialize.py`, and
`tests/workbench/test_brief.py` plus one round-trip test in `tests/store/`.

## Code style

As `app/workbench/extract.py`: comments say why and name the bug that forced
the shape. For example:

```python
        sub = fetcher.fetch(page)
        fetched += 1
        # Recorded before the failure check, not after: a page skipped on
        # failure used to vanish, and "we never saw it" read exactly like
        # "the site does not say so" to everything downstream.
        pages.append(_page_entry(page, sub))
        if not (sub.ok and sub.html):
            continue
```

## Testing strategy

Tests are sentences, and each docstring says what breaks in the real world.

1. `test_every_page_the_crawl_reads_keeps_its_text`: fake fetcher, three
   pages, all three in `pages` with their visible text.
2. `test_a_page_that_fails_is_kept_with_its_reason`: a 404 and a timeout, both
   recorded with `read: False` and a reason a person can act on.
3. `test_a_menu_pdf_keeps_its_text_not_only_its_items`.
4. **Round trip, nothing hand-made in between:** `build_brief` with a fake
   fetcher → `brief_to_dict` → `brief_archive.save` → `leads.save_brief` →
   `leads.brief_with_overrides`, and the page text comes out the far end.
5. The real system: `make brief` on The Heritage Table, then open the newest
   archived file and the database row and confirm both contain the wine
   menu's text, or the reason it was not read.

## Boundaries

- **Always:** record every attempted document, including failures; run
  `make check`; open the real archived file before calling it done.
- **Ask first:** running `make brief` against the real site, since it makes
  paid directory lookups; any size cap on stored text.
- **Never:** delete or rewrite an archived brief; read `live-site.md`; change
  what the extracted fields contain.

## Success criteria

- [ ] A fresh `make brief` on The Heritage Table writes `pages` into both the
      archived file and the database row.
- [ ] Every page the crawl attempted appears, read or not; every unread one
      has a non-empty reason.
- [ ] The round-trip test passes with nothing hand-made in between.
- [ ] `make check` passes.
- [ ] Whether "Cabernet" appears in the stored text is reported, either way.

## Open questions

None blocking. Whether the stored text needs a size cap is decided by what the
real run produces.
