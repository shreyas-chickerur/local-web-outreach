"""Command line for the workbench.

    python -m app.cli brief "Craftway Kitchen, Frisco, TX"
    python -m app.cli brief craftwaykitchen.com --notes "owner is Allison"

One command, because there is currently one thing to do. Later slices add the
lead store, site generation, and chat iteration.
"""

from __future__ import annotations

import argparse
import sys

from app.adapters.osm import NominatimSource
from app.adapters.places import GooglePlacesDirectory
from app.adapters.yelp import YelpSource
from app.core.config import google_places_api_key, yelp_api_key
from app.store import brief_archive, db, leads
from app.web.serialize import brief_to_dict
from app.workbench.brief import build_brief, format_brief


def available_directories() -> list:
    """Every lookup source we have credentials for.

    OpenStreetMap needs no key and is always available, but covers storefronts
    rather than service businesses — on its own it finds very little. Google is
    what finds the website; Yelp is what covers the trades.
    """
    directories: list = []
    if google_places_api_key():
        directories.append(GooglePlacesDirectory())
    if yelp_api_key():
        directories.append(YelpSource())
    directories.append(NominatimSource())
    return directories


def cmd_brief(args: argparse.Namespace) -> int:
    """Research one company and save the brief to the archive and the database."""
    directories = available_directories()
    if len(directories) == 1:
        print("note: only OpenStreetMap is configured. Set GOOGLE_PLACES_API_KEY "
              "to find websites and YELP_API_KEY to cover service businesses.\n",
              file=sys.stderr)
    def _progress(message: str) -> None:
        print(f"... {message}", file=sys.stderr, flush=True)

    try:
        brief = build_brief(args.input, location=args.location, notes=args.notes,
                            directories=directories, on_progress=_progress)
    except ValueError as exc:
        # A bad input is a user mistake, not a crash. Say what to do instead.
        print(f"error: {exc}", file=sys.stderr)
        return 2
    # A permanent, never-overwritten copy of this crawl — a re-run of this
    # same command writes a NEW file, never touches an old one.
    payload = brief_to_dict(brief)
    brief_archive.save(payload)
    # And into the database the workbench reads. Without this the two copies
    # diverge silently: a re-crawl improved the archived file while the screen,
    # the generator and the checks all went on showing the crawl from whenever
    # the lead was first created. `save_brief` refreshes what the sources say
    # and leaves status, history and every operator correction alone.
    with db.session() as conn:
        lead_id = leads.save_brief(conn, payload)
        leads.record(conn, lead_id, "researched", note="re-crawled from the command line")
    print()
    print(format_brief(brief))
    print(f"saved as lead {lead_id} — open the workbench to see it")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    """The command line: `python -m app.cli brief "Name, City, ST"`."""
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_brief = sub.add_parser("brief", help="research one company (name or URL)")
    p_brief.add_argument(
        "input", help='e.g. "Craftway Kitchen, Frisco, TX" or craftwaykitchen.com')
    p_brief.add_argument("--location", default=None, help="city, ST — helps the lookup")
    p_brief.add_argument("--notes", default=None, help="anything you already know")

    args = parser.parse_args(argv)
    if args.command == "brief":
        return cmd_brief(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
