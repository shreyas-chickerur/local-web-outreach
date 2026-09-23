# The crawl is the source — statement of intent

Confirmed with Shreyas on 22 September 2026. Replaces the hand-made
`captures/<slug>/live-site.md` as what the claim checks judge against.

- **Outcome:** every `make brief` stores the full text of every page it read
  from the business's own site, dated beside the brief. The checks read that.
  The hand-made capture is archived: kept on disk, never read again.
- **Reading:** every tool is exhausted before a page is called unreadable —
  plain fetch, then a real browser for JavaScript, then the PDF reader, then a
  model reading images, automatically. Each image is read once and remembered
  by a fingerprint of its content.
- **Verdicts:** "unsourced" means the crawl read everything and the claim is
  not there. A page that could not be read gets its own verdict naming the
  exact reason (blocked, timed out, an image the model could not read). It does
  not block approval.
- **Mapping:** each claim on the page points at the specific fact and the
  specific sentence that backs it, not a loose word match across a pile of
  text.
- **Corrections:** a person's correction for a specific fact replaces the crawl
  as that fact's source; the crawl's version is shown as superseded, exactly as
  overrides already work for the brief.
- **Success:** re-run on The Heritage Table, "Cabernet" and "Sauvignon" are
  either backed by a sentence from the live wine menu, or flagged with the
  exact reason it could not be read.
- **Constraint:** credits are spent only on images not read before, never twice
  on the same image.
- **Out of scope:** re-generating the page; any design change (that goes
  through the design tool); crawling sites other than the business's own; the
  lead-detail screen (C1–C4).
