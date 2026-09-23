# Spec: logos, proposal files, and editing in conversation

Decided with Shreyas on 23 September 2026. Three parts, built in this order.

## 1. Logos, the same way for every site

- **Found by the crawl, by one ranked rule.** Candidates are collected from every
  page read. The rule: (a) a logo named in the site's structured data;
  (b) an `<img>` whose address, class or text says "logo", preferring one that
  names the business, then the earliest; (c) the site's own touch or tab icon
  of 180 pixels or more. Award seals and badges never count (The Heritage
  Table's og:image is a James Beard seal).
- **Stored on the brief** as `logo: {url, source}`; correctable on the workbench
  like any other field; served by the workbench at `/logo/<lead>`, downloaded
  once and cached.
- **Used by every design run and edit:** top-left in the header and as the tab
  icon. **No logo found: the run is flagged and the page leaves the spot empty;
  nothing is invented.** Shreyas supplies one by correcting the field.

## 2. Proposal files, before any hosting is paid for

`make proposal LEAD=<id>` writes `proposals/<slug>-v<N>.html` from the current
version: one file with every photograph, the logo and the tab icon inside it,
openable offline and sendable as an attachment. No review markup, ever.

## 3. Editing in conversation

The workbench's chat box, on a page built by the design bridge or by hand,
sends the instruction to an edit run: the model named in `DESIGN_MODEL`, a $1 ceiling, the same
four file tools confined to their own folder, given the current page, the
photographs, the logo and the brief. It changes only what was asked, saves a
new version with its parent, and replies with what it changed, what it cost
and any new claim findings. The page pane shows the new version. Facts are
changed through corrections, not edits.

## Producers and consumers, for the wiring check

| Seam | Producer | Consumer |
|---|---|---|
| Logo candidates | `extract_from_html` → `ExtractedSite.logo_candidates` | `build_brief` ranks → `Brief.logo` |
| `logo` | `brief_to_dict`; a correction (`leads.verify`, field `logo`) | `brief_with_overrides` → `/logo/<lead>`, the bridge, the proposal |
| Logo bytes | `/logo/<lead>` (cached download) | pages, the proposal file |
| An edit | workbench chat → `/api/iterate` → `bridge.edit` | `sites.save`, `messages`, the page pane |
