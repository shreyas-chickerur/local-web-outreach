"""Hours only corroborate if the three ways of writing a week reduce to one."""

from __future__ import annotations

import pytest

from app.workbench.hours import canonical, describe, from_canonical, parse_week

pytestmark = pytest.mark.unit

GOOGLE = ["Monday: 8:00 AM – 5:00 PM", "Tuesday: 8:00 AM – 5:00 PM",
          "Wednesday: 8:00 AM – 5:00 PM", "Thursday: 8:00 AM – 5:00 PM",
          "Friday: 8:00 AM – 5:00 PM", "Saturday: Closed", "Sunday: Closed"]
FOOTER = ["Mon-Fri 8:00am - 5:00pm", "Sat-Sun Closed"]
SCHEMA = ["Mo-Fr 08:00-17:00", "Sa,Su Closed"]


@pytest.mark.parametrize("lines", [GOOGLE, FOOTER, SCHEMA])
def test_every_format_reduces_to_the_same_week(lines):
    assert canonical(lines) == canonical(GOOGLE)


def test_a_comma_list_is_not_a_range():
    """"Mon, Wed, Fri" is three days; "Mon-Fri" is five."""
    assert set(parse_week(["Mon, Wed, Fri 9am-5pm"])) == {"mon", "wed", "fri"}
    assert len(parse_week(["Mon-Fri 9am-5pm"])) == 5


def test_a_week_that_wraps_the_weekend():
    assert set(parse_week(["Sat-Mon 10am-4pm"])) == {"sat", "sun", "mon"}


def test_a_stray_day_is_not_a_schedule():
    """One line is not enough to compare against another source."""
    assert canonical(["Monday: 9am-5pm"]) is None


def test_round_trip_is_readable_not_machine_shaped():
    """The canonical form exists for comparing; nobody should have to read it."""
    assert describe(from_canonical(canonical(GOOGLE))) == (
        "Mon-Fri 8am-5pm · Sat-Sun closed")
    assert describe(from_canonical(canonical(["Mon-Sun 11am-9:30pm"]))) == (
        "Mon-Sun 11am-9:30pm")
