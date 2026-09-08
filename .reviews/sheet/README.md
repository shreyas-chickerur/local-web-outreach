# Contact sheet — the committed copy

Half-scale pictures of the **desktop** first viewport, one per fixture, with
each site's axis vector printed underneath. This is the only version that goes
in the repository.

The question it answers is not whether any one of these is good. It is whether
a stranger would guess they came from the same tool — and the vector under each
says which axis collided when two of them feel alike.

Half-scale is now what it says. This row used to be captured in a 720-pixel
window rather than shrunk from the 1440-pixel one, which is below the
breakpoint where the split hero stacks, the header changes and the columns
collapse — so every blind verdict taken off this sheet was a judgement of a
narrower page than the one the owner is shown. It is now the same viewport as
`fold` at half the device scale.

Two standing tests hold this directory honest, because both faults it has had
were the same shape — something declared here and not in force:

* `test_the_committed_sheet_shows_the_corpus_that_shipped` — the vector printed
  under every thumbnail must match the corpus as it stands. The sheet was once
  committed nine minutes older than the fixtures beside it, so five of the
  eleven pictures were of pages that no longer existed and the captions said
  otherwise.
* the `WIDTHS` table in `tools/contact_sheet.py` carries the device scale
  explicitly, so the committed row cannot silently become a narrow rendering
  again.

Regenerate, along with the full-size and mobile sheets, into the gitignored
`artifacts/` directory:

    .venv/bin/python tools/contact_sheet.py

Those pages embed every photograph as a data URI, because a screenshot taken
from a `file://` URL has no server to ask for `/photo/<lead>/<n>` and every
image would 404 — which produced eleven grey rectangles the first time, and a
conclusion nearly read off them. That inlining takes the directory to 400MB, so
it is never committed at any scale. This copy references its images as files.
