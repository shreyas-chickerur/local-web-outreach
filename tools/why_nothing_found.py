"""Why did a lookup come back empty?

`make brief` reports what it established. When it establishes nothing, the
interesting part is which source was asked and what it answered — and that is
exactly what the brief cannot tell you, because a source that errors and a
source that genuinely has no record both end up as silence.

Run it the same way as a brief:

    .venv/bin/python -m tools.why_nothing_found "The Heritage Table, Frisco, TX 75033"

It prints, per source: whether it is configured, what it returned, and the
exact exception if it raised. It never prints a key — only whether one is set
and how long it is, which is enough to tell an empty variable from a wrong one.
"""

from __future__ import annotations

import sys
import traceback

from app.cli import available_directories
from app.core.config import google_places_api_key, yelp_api_key
from app.workbench.resolve import resolve_input


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    query = argv[1]

    print("CREDENTIALS")
    for label, value in (("GOOGLE_PLACES_API_KEY", google_places_api_key()),
                         ("YELP_API_KEY", yelp_api_key())):
        state = f"set, {len(value)} characters" if value else "NOT SET"
        print(f"  {label}: {state}")

    print("\nHOW THE QUERY WAS READ")
    try:
        resolved = resolve_input(query, location=None)
        name = getattr(resolved, "name", None) or getattr(resolved, "query", query)
        where = getattr(resolved, "location", None)
        print(f"  name:     {name!r}")
        print(f"  location: {where!r}")
        print(f"  looked like a web address: "
              f"{getattr(resolved, 'input_was_url', False)}")
    except Exception:
        print("  resolve() raised:")
        traceback.print_exc()
        name, where = query, None

    print("\nWHAT EACH SOURCE ANSWERED")
    for directory in available_directories():
        label = getattr(directory, "name", type(directory).__name__)
        try:
            place = directory.lookup(str(name), str(where or ""))
        except Exception as exc:
            print(f"  {label}: RAISED {type(exc).__name__}: {exc}")
            continue
        if place is None:
            print(f"  {label}: no match")
            continue
        print(f"  {label}: matched {place.name!r}")
        print(f"      address  {place.address!r}")
        print(f"      phone    {place.phone!r}")
        print(f"      website  {place.website!r}")
        print(f"      hours    {len(place.hours)} line(s)")
        print(f"      status   {getattr(place, 'business_status', None)!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
