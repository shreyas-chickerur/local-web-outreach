# Ironplains Web Co. — Lead & Site Workbench

Research a local business from public sources, design a website for it, check
every claim on the page, and hand the owner a proposal. Outreach happens **in
person**: nothing here sends email.

- **Who sees what**
  - You: the command line and the workbench at `http://127.0.0.1:8099`.
  - The owner: the finished page (or a proposal file) and nothing else. A
    `?review=` link carries every doubt the checks have; never send one.
- **Where to read more**
  - [`CLAUDE.md`](CLAUDE.md) — the working context and the rules.
  - [`docs/architecture.md`](docs/architecture.md) — every module and the data flow.
  - [`docs/state-of-play.md`](docs/state-of-play.md) — where the work stands today.
  - [`docs/working-agreement.md`](docs/working-agreement.md) — how to work here.

## Set up

1. Install Python 3.11 or newer, and Google Chrome (the crawl renders pages in it).
2. Install the project:
   ```bash
   make install
   ```
3. Copy the keys file and fill it in:
   ```bash
   cp .env.example .env
   ```
   - `GOOGLE_PLACES_API_KEY` — finds a business's website, rating and photographs.
   - `YELP_API_KEY` — covers service businesses OpenStreetMap misses (free).
   - `ANTHROPIC_API_KEY` — design runs, chat edits and reading menu images.
   - OpenStreetMap needs no key.
4. Optional settings:
   - `WORKBENCH_DB` — where the database lives (default `./workbench.db`).
   - `WORKBENCH_OPERATOR` — your name on the audit trail (default `$USER`); a
     label, not authentication.
   - `ANTHROPIC_MODEL` — the model for menu images and the older generator's
     instruction reader (named in `ANTHROPIC_MODEL`). Design runs and edits
     use the model named in `DESIGN_MODEL`.

## Commands

| Command | What it does | Costs |
|---|---|---|
| `make brief Q="Name, City, ST"` | Research one business; save its brief | a few directory lookups; a model read per new menu image |
| `make ui` | Start the workbench at `http://127.0.0.1:8099` | — |
| `make design LEAD=8 PROMPT=prompts/<slug>/v1.md` | One design run: a new version of the lead's site | up to $5 |
| `make proposal LEAD=8` | The current version as one file for the owner | — |
| `make check` | Lint, type check and the whole test suite | — |

- `make brief` takes `Q`, not `NAME`. A URL works too: `make brief Q=fishshackplano.com`.
- After changing `app/web/server.py`, restart `make ui`; `index.html` is re-read on
  every request, the server is not.

## From a name to a proposal

1. **Find a business**
   - Open the workbench; the landing page lists local businesses by trade,
     ranked by how much they look like they need a website.
   - Or search by name or URL in the header.
2. **Research it** — `make brief Q="Fish Shack, Plano, TX"`.
   - Every source's claim about a field is compared; two independent sources
     agreeing makes a fact **verified**, a disagreement is a **conflict**.
   - The crawl reads up to 24 of the business's own pages, their menu PDFs and
     menu images, and keeps the text of each, with a reason for any it could
     not read.
   - It picks the business's logo by one rule (structured data, then an image
     called a logo that names the business, then a large site icon).
3. **Correct what you know** — on the lead's screen, type what the owner told
   you into a field and say how you know.
   - Your value outranks every source; the source's value is kept and shown
     as superseded.
   - A logo the crawl missed is corrected the same way, with its address.
4. **Design the site**
   - Write the design prompt at `prompts/<slug>/v1.md` from the brief and
     `app/design/playbooks/restaurant.md`.
   - Run `make design LEAD=<id> PROMPT=prompts/<slug>/v1.md`.
   - The run prints its cost and the new version's address; a missing logo is
     flagged.
5. **Refine it in the workbench chat** — open the lead's workspace.
   - Type a change ("make the menu tabs bigger"); press Enter.
   - Each change is a new version with its parent, up to $1, and the reply
     says what changed, what it cost and whether the claim checks moved.
   - Facts only come from the brief: ask for one it does not hold and the edit
     says so and changes nothing.
6. **Mark the master** — select the version you judge good and click
   "Mark vN as master"; a ★ marks it. It is the checkpoint to return to.
7. **Review every claim** — click "Review vN" in the workspace.
   - Each claim is pinned on the page with a verdict: `corroborated`,
     `unsourced`, `assembled`, `wording`, `contradicted`, `defect`, `unmeasured`.
   - Every corroborated claim links to the exact page and words that back it.
   - Only `contradicted` blocks approval. A person approves; always.
8. **Make the proposal** — `make proposal LEAD=<id>` writes
   `proposals/<slug>-v<N>.html`: every photograph and the logo inside one file,
   openable offline and sendable as an attachment.

## The rules it works by

- **A fact needs two independent sources.** One source is unverified; a
  disagreement is a conflict and names both sources.
- **What you were told outranks every source**, and never erases it.
- **The claim check is an inventory, not a veto.** Generation is free; every
  claim is listed afterwards and a person decides.
- **Nothing is guessed.** A gap becomes a question to ask in person; a missing
  logo is flagged, never drawn.
- **Money is spent only on real change.** Confirming what the sources already
  said costs nothing; each menu image is read once; every run has a ceiling.

## The website check

The address on a Google listing is not always the one that works. Each fault is
a different sentence at the door:

| Fault | What it means |
|---|---|
| `certificate` | the listing's address throws a browser security warning |
| `not-found` | the domain answers; that page is gone |
| `parked` | the domain lapsed and shows a registrar's for-sale page |
| `no-https` | the site works, but every browser marks it not secure |
| `http-link` | the listing links the old http address; the site serves https |
| `redirected` | the listing's link lands on a different domain |
| `dead` | nothing answers at all |
| *blocked* | their bot filter refused the check: **not** a fault, nothing concluded |

## Where things live

- **Database** — `workbench.db`: leads, the audit trail, versions, reviews,
  findings, the chat. Additive migrations only.
- **Briefs** — `briefs/<slug>/<timestamp>.json`, one per crawl, never
  overwritten; `current.json` is a pointer to the newest.
- **Prompts** — `prompts/<slug>/vN.md`, one per design run.
- **Generated, gitignored**
  - `runs/<slug>/<timestamp>/` — a design or edit run's workspace.
  - `proposals/` — files for owners.
  - `.cache/photos`, `.cache/logos`, `.cache/image-text` — paid for once, kept.

## Development

1. Run the gate before every commit:
   ```bash
   make check
   ```
2. Tests never reach the network, a real database or a paid agent run;
   `tests/conftest.py` refuses all three.
3. Browser tests (layout, rendering) need Chrome and are skipped without it.
4. After changing code, refresh the knowledge graph: `graphify update .`.
5. Removed code is archived by git tag first; see `CLAUDE.md`.
