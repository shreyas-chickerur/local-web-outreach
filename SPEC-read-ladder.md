# Spec: `read-ladder`

Module 3 of 4 in `SPEC.md`. Depends on `page-text`, which is built.

## Objective

Every way this project has of reading a document is tried before a page is
recorded as unreadable, and when one fails the reason is the specific one.
Found by the real crawl of The Heritage Table on 22 September: its wine list
is an image the crawl never recognised as a menu, its dinner menu PDF was
recorded as "could not download" when the server said 404, and seven of its
eighteen page slots went to WordPress short links duplicating pages already
read.

## The ladder, per document

| Document | Tried in order | Recorded reason when all fail |
|---|---|---|
| Web page | Chrome render, then plain fetch (already so: `ChromeSiteFetcher`) | the fetch's own error or status |
| PDF | download, then the PDF text reader | `status 404`, `timed out`, `no text layer` |
| Menu image | download, then a model reading it, **once per image**, cached by a fingerprint of its bytes | `status …`, `no Anthropic key configured`, `the model could not read it` |

## Producers and consumers, for the wiring check

| Seam | Producer | Consumer |
|---|---|---|
| Menu images found | `extract_menu_media` (links only; now also `<img>` by `src` or `data-src`, by filename or `alt`/`title`) | `ExtractedSite.menu_media` → `_read_menu_images` |
| Bytes and why they failed | new `site_fetch.download` → `(bytes, reason)`; `fetch_bytes` keeps its shape | `_read_menu_pdfs`, `_read_menu_images` |
| Text of an image | new `app/adapters/image_text.read` → `language_model.structured`, cache `.cache/image-text/<sha256>.json` | a `kind: "image"` entry in `brief.pages` → the checks |
| Pages worth crawling | `content_page_urls` (`_JUNK_PAGE_RE` gains `xmlrpc.php` and `?p=<number>`) | `_read_their_site` |

## Cost

One model call per distinct image, ever. A re-crawl of an unchanged menu costs
nothing: the cache is keyed on the image's bytes, not its address. No other
step spends credits.

## Tasks

1. `download` returns the reason; PDFs record it.
2. Menu images are found in `<img>` tags, including lazy-loaded ones, and
   "wine", "cocktail" and "beer" count as menu words.
3. Menu images are read by a model, cached by content, and recorded as pages.
4. WordPress short links and `xmlrpc.php` are not crawled.
5. The real run: `make brief` on The Heritage Table, then the checks in memory.

## Success criteria

- [ ] A second crawl of the same menu image makes no model call.
- [ ] A 404 PDF is recorded as "status 404".
- [ ] The Heritage Table's wine list reaches `pages` as text, or its entry says why not.
- [ ] `make check` passes.
