# local-web-outreach — working context

Read this first. It is the whole picture: what the product is, how the code is
arranged, the rules that are not negotiable, and how to work here without
wasting the owner's money or trust. `docs/architecture.md` has the module map,
`docs/state-of-play.md` has where the work actually stands today, and
`docs/working-agreement.md` has the conventions.

## What this is

Ironplains Web Co.: an automated local-business website platform. It finds a
small business, researches it from public sources, builds a modern website for
it, and produces something the owner can be shown. The market is Dallas–Fort
Worth contractors — roofing, heating and cooling, lawn care. One real lead
exists today (The Heritage Table, a restaurant in Frisco), which is the wrong
trade and is known to be.

There are two audiences, and only one of them ever sees a screen in this
repository:

- **The operator** (Shreyas). The command line, the workbench at
  `127.0.0.1:8099`, the claim inventory, the annotations, the audit trail. All
  of it internal.
- **The prospect**, a business owner. They see exactly two things: the
  generated website, and the outreach message pointing at it.

Nothing internal should ever leak outward. The annotation layer is injected at
serve time only for `/site/<lead>/<version>?review=<id>`; the plain URL must
stay plain, because a review link pasted into an email would show a prospect
every doubt the system has about their business.

## The seven stages

1. **Resolve** — a name, a URL, or a name with a town becomes a company.
   `app/workbench/resolve.py`.
2. **Research** — Google Places, Yelp, OpenStreetMap, then a crawl of the
   business's own site. `app/workbench/brief.py`, `app/adapters/`.
3. **Corroborate** — every source's claim about a field is compared; two
   independent sources agree makes a fact VERIFIED. `app/workbench/corroborate.py`.
4. **Brief** — the result, archived permanently and stored on the lead.
   `app/store/brief_archive.py`, `app/store/leads.py`.
5. **Build** — one design run from a prompt written from the brief and the
   playbook, through the Claude Agent Software Development Kit.
   `app/design/bridge.py` (`make design`). The workbench's build button still
   uses the older generator in `app/site/pipeline.py`.
6. **Workbench** — change the page in conversation; every sentence becomes an
   edit run and a new version with a parent. A person marks the master version,
   the last one judged good. `app/web/`, `bridge.edit()`.
7. **Claim inventory and approval** — the final gate, after iteration, not
   before. Every claim on the page is enumerated with a verdict, annotated in
   place on the page itself, and decided by a person. `app/review/`.

## Rules that are not negotiable

**The claim gate is an inventory, not a veto.** Generation is unconstrained.
Validation happens afterwards and enumerates every claim with a verdict:
`corroborated`, `contradicted`, `unsourced`, `assembled`, `wording`, `defect`,
`unmeasured`. Only `contradicted` blocks approval (`app/store/reviews.py`,
`BLOCKING`). Refusing to write a sentence at generation time was tried and
produced worse pages than writing it and listing it.

**A person approves. Always.** Stage seven is deliberately not automatable.
Anything that is a judgement call — what a confidence score should mean, which
fields deserve a reviewer's attention, whether a sentence sounds right in a
business's voice — is prepared for Shreyas and left to him. Ask; do not decide.

**What the operator was told outranks every source, and never overwrites it.**
A correction is an event row. The source's own claim stays in the stored brief
and is shown as `superseded`. Overrides are applied on read by
`leads.brief_with_overrides()`; they survive a re-crawl.

**Never delete code without a tag. Archive it.** Code is removed only after the
commit holding it is tagged `archive/<what>-<date>`, so every file stays
recoverable (`git show <tag>:<path>`). On 23 September 2026 everything nothing
live reached was archived under `archive/before-cleanup-2026-09-23`. The older
generator in `app/site/` stays while the workbench's build button, photo
labelling and correction path for its pages still call it.

**Minimise credits.** A rebuild costs a generation run. Confirming a value that
did not change must cost nothing. Never run the model twice to learn the same
thing. When a cheaper path exists — reading a stored artifact instead of
re-crawling, one command on the device instead of staging files — take it.

**No acronyms in anything written for the owner.** Write "Agent Software
Development Kit", not the initials. This applies to comments, documents and
chat. Never use the word "utilize".

## The wiring check — apply before saying anything is done

Every bug that has reached the running system here was a wiring bug: two
modules that each worked, joined by an assumption nobody tested. A passing test
suite does not catch them, because the test and the code share the wrong
assumption. Three that shipped:

- `review/run.py` read `briefs/<slug>/current.json` as a brief. The writer had
  been changed to put a three-key *pointer* there. Every claim check ran against
  an empty dictionary and reported "unsourced" while the screen said a brief had
  loaded.
- `make brief` wrote only to the archive. The database — which the workbench,
  the generator and the checks all read — still held the crawl from the day the
  lead was created.
- An override stopped at `facts` and never reached `published`, which is where a
  page's words actually come from. Corrections changed a screen and nothing a
  visitor would see.

So: name the producer and the consumer for every file, table and key the change
touches. Grep for the other consumers. Write one round-trip test per seam, with
nothing hand-made in between. Open the real stored artifact for a real lead.
Run the real command. Ask what regenerates the artifact. Name what is now
downstream and stale. `docs/wiring-check.md` and the `wiring-check` skill in
`.claude/skills/` carry the full version.

Never report a fix as done on the strength of a passing test. Report it on the
strength of having watched the real system produce the right value.

## Commands

```
make check                 # ruff + mypy + the full suite. The gate.
make brief Q="Name, City, ST 75033"   # research one company (note: Q, not NAME)
make design LEAD=8 PROMPT=prompts/fish-shack/v2.md   # one design run: $5 ceiling
make proposal LEAD=8       # the current version as one file an owner can open
make ui                    # the workbench on http://127.0.0.1:8099
make install               # python3.11 -m venv .venv && pip install -e ".[dev]"
```

A design run and a chat edit spend money on the project's Anthropic key, which
the agent's own process reads from the environment. No test may reach one:
`tests/conftest.py` makes any unpatched `bridge.query` fail.

`make ui` imports `server.py` once at start, while `index.html` is read per
request. After changing `server.py`, restart it or the new routes will not
exist and the screen will report an error that looks like a bug in the page.

## Environment

- Python 3.11 or newer is required (`datetime.UTC`). The virtual environment is
  `.venv`, macOS binaries.
- Ruff: line length 100, rules `E,F,I,UP,B`, target `py311`. Mypy runs over
  `app` only.
- Keys live in `.env`, gitignored, blocked by a pre-commit hook:
  `GOOGLE_PLACES_API_KEY`, `YELP_API_KEY`, `ANTHROPIC_API_KEY`. OpenStreetMap
  needs none. Without an Anthropic key the deterministic phrase parser handles
  instructions and reports what it ignored.
- The browser tests (layout, rendering, the no-dialog check) need a real Chrome and
  are skipped without one.
- The workbench serves previews from `PREVIEW_BASE_URL`, defaulting to the port
  it listens on (`app/core/config.py`, `DEFAULT_PORT = 8099`).

## Storage

SQLite at `workbench.db` (`app/store/db.py`). Tables: `leads`, `events`,
`sites`, `fingerprints`, `messages`, `build_state`, `photo_labels`,
`discovery_cache`, `preferences`, `reviews`, `findings`. Migrations are additive
only, through `_SCHEMA` plus `_LATER_COLUMNS`.

On disk: `briefs/<slug>/<ISO-timestamp>.json` is one crawl, never overwritten;
`briefs/<slug>/current.json` is a **pointer** to the newest one, not a brief.
The text of every page the crawl read is inside the brief (`pages`); the claim
checks search that. `captures/<slug>/live-site.md` was a hand-made copy the
checks used to read; nothing reads it now.

Generated and cached, all gitignored: `runs/<slug>/<timestamp>/` (a design or
edit run's workspace), `proposals/` (files for owners), `.cache/photos`,
`.cache/logos`, `.cache/image-text` (a menu image's text, keyed by its bytes).
A site's hand-written source, when it has one, is kept under `sites/<slug>/`.

## Style

Comments explain *why*, in full sentences, and usually name the bug that forced
the code to look the way it does. This is the house style and it is deliberate —
read `app/workbench/extract.py` or `app/store/leads.py` before writing any. A
comment that restates the code is worse than none. Docstrings open with one
line a person could read aloud.

Test names are sentences: `test_a_re_crawl_does_not_erase_a_correction`. A test
docstring says what breaks in the real world when it fails.

One responsive page. Never a separate mobile and desktop design.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community
structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when
  graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for
  relationships and `graphify explain "<concept>"` for focused concepts. These
  return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw
  grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of
  raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when
  query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current
  (AST-only, no API cost).
