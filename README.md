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

Slice 2 is the lead store and tracking; then site generation, chat iteration,
and one screen that ties them together.
