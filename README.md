# Lead & Site Workbench

Research a local business, build a website for it, track where the lead stands.
Outreach happens **in person** — nothing here sends email.

See [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for the full spec and the
slice order.

## Slice 1 — the brief (built)

Give it a company name or a website URL, plus anything you already know:

```bash
make install
.venv/bin/python -m app.cli brief "Craftway Kitchen, Frisco, TX" --notes "owner is Allison"
.venv/bin/python -m app.cli brief craftwaykitchen.com
```

You get back what could be established about the business, with a confidence and
its sources on every line:

```
Ryno Lawn Care
  Frisco, TX
  https://www.rynolawncare.com/  (reachable)

WHAT WE ESTABLISHED
  [conflict  ] rating     30%  sources disagree:
                        google: 4.8
                          yelp: 2.4
  [verified  ] phone      90%  (469) 496-2778
                              <- google: https://www.google.com/maps/place/?q=...
                              <- yelp:   https://www.yelp.com/biz/ryno-lawn-care-frisco

WHAT THEIR SITE PUBLISHES
  services: Sustainable Lawn Care, Premium Sod Installation, Weed Control ...
  hours:    Mon-Fri 8:00am - 5:00pm | Sat-Sun Closed
```

### The rules it works by

- **A fact needs two independent sources.** One source is `unverified`;
  disagreement is a `conflict` and is never presented as fact.
- **A conflict names its sources.** Knowing Google says 4.8 while Yelp says 2.4
  is the useful part; two values joined by a pipe tells you nothing.
- **Nothing is guessed.** Gaps become questions to ask in person.
- **Assumptions are stated**, so you can correct them.

## The landing page — prospects near you

The first screen is a list of local businesses grouped by trade, ranked by how
much they look like they need a website. Location comes from the browser, or
you can type a town. Search stays in the header for when you already know who
you are looking at.

**The prospect score** is a heuristic, not a measurement, so every point of it
is shown with its reason attached — if you disagree with a reason, ignore the
number. It answers "who should I walk into today?", which is a *different*
question from confidence (how sure we are the data is right). They pull in
opposite directions: a business with no website is a prime prospect and has
almost nothing we can confirm.

Cost: one Google Places request per category (eight per town), cached for 24
hours, plus one page fetch per business.

## The UI

```bash
make ui        # http://127.0.0.1:8099
```

One page: type a company name or a URL and read the brief. It calls the same
`build_brief()` the CLI does, so the screen cannot drift from the terminal.
The example chips across the top are the stress cases — a chain, a business
with no website, one whose sources disagree, and one that does not exist.

## Slice 2 — the lead store (built)

Every lookup is saved to `workbench.db` (SQLite, gitignored). Re-running the
research refreshes what the sources say and leaves your history alone.

**Confirming a field.** After you talk to a business, type what they actually
told you into the field's card, with a line on how you know. That value
replaces the corroborated one, is marked `operator verified`, and carries your
name, the timestamp, and your note. What the sources said is kept and shown
underneath as `sources said …` — you outrank a directory, but the directory's
disagreement is not erased.

**The trail** at the bottom of a lead is append-only: nothing is ever updated
or deleted, so a correction to a correction is another row and the history
reads backwards intact.

Attribution comes from `WORKBENCH_OPERATOR`, falling back to `$USER`. This
labels changes so you can read the trail later — it is **not** authentication,
and anyone with access to this machine can write under that name.

```bash
WORKBENCH_DB=/path/to/workbench.db   # optional, defaults to ./workbench.db
WORKBENCH_OPERATOR="Shreyas"         # optional, defaults to $USER
```

## Keys

Copy `.env.example` to `.env`. OpenStreetMap needs no key but finds little on its
own; `GOOGLE_PLACES_API_KEY` is what finds their website, and a free
`YELP_API_KEY` covers service businesses.

## Development

```bash
make check     # lint + typecheck + tests
```

86 tests, no network, no database.

## Next

Slices 3-5: generating a site from a brief, chat iteration with versioning, and
the single screen that ties the lead list to a live preview.

## Notes

Slice 2 is the lead store and tracking; then site generation, chat iteration,
and one screen that ties them together.
