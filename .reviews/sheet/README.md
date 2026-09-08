# Contact sheet — the committed copy

Half-scale first viewports, one per fixture, with each site's axis vector
printed underneath. This is the only version that goes in the repository.

The question it answers is not whether any one of these is good. It is whether
a stranger would guess they came from the same tool — and the vector under each
says which axis collided when two of them feel alike.

Regenerate, along with the full-size and mobile sheets, into the gitignored
`artifacts/` directory:

    .venv/bin/python tools/contact_sheet.py

Those pages embed every photograph as a data URI, because a screenshot taken
from a `file://` URL has no server to ask for `/photo/<lead>/<n>` and every
image would 404 — which produced eleven grey rectangles the first time, and a
conclusion nearly read off them. That inlining takes the directory to 400MB, so
it is never committed at any scale. This copy references its images as files.
