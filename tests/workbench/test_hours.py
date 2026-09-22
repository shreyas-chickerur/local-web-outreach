"""Hours only corroborate if the three ways of writing a week reduce to one."""

from __future__ import annotations

import pytest

from app.workbench import hours
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


# Google writes an evening as "5:00 – 9:00 PM", marking only the closing time.
# Read literally that is five in the morning, which is what The Heritage Table's
# brief stored — and because their own site said 1700, the two sources
# "disagreed" and the hours were dropped as a conflict for a restaurant whose
# hours both sources state identically.
@pytest.mark.parametrize(("line", "expected"), [
    ("Monday: 5:00 – 9:00 PM", "1700-2100"),      # dinner only
    ("Monday: 6:00 – 11:00 PM", "1800-2300"),     # late
    ("Monday: 12:00 – 9:00 PM", "1200-2100"),     # opens at noon
    # Borrowing the meridiem here would run the day backwards, so it must not
    # happen: eight in the morning to five in the evening is the ordinary case.
    ("Monday: 8:00 – 5:00 PM", "0800-1700"),
    ("Monday: 11:00 – 2:00 PM", "1100-1400"),     # lunch service
    ("Monday: 9:00 – 5:00 PM", "0900-1700"),
    # Nothing to borrow, or nothing to borrow from.
    ("Monday: 8:00 AM – 5:00 PM", "0800-1700"),
    ("Monday: 09:00-17:00", "0900-1700"),
])
def test_an_unmarked_opening_time_borrows_the_closing_meridiem(line, expected):
    assert parse_week([line]) == {"mon": expected}


def test_the_heritage_tables_week_as_google_publishes_it():
    """The exact lines that produced the conflict, start to finish."""
    google = [f"{day}: 5:00 – {close} PM" for day, close in (
        ("Monday", "9:00"), ("Tuesday", "9:00"), ("Wednesday", "9:00"),
        ("Thursday", "10:00"), ("Friday", "10:00"), ("Saturday", "10:00"),
        ("Sunday", "9:00"))]
    their_site = ["Sunday – Wednesday: 5pm – 9pm", "Thursday – Saturday: 5pm – 10pm"]
    assert canonical(google) == canonical(their_site), (
        "both sources say the same week; storing them differently is what "
        "turned agreement into a conflict and dropped the hours entirely")


# ---------------------------------------- however the operator chooses to type it


@pytest.mark.parametrize("written,expected", [
    # The commonest shorthand a small business writes. Read literally this is
    # nine in the morning to five in the MORNING — a twenty-hour overnight.
    ("Mon-Fri 9-5", "Mon-Fri 9am-5pm"),
    ("Mon-Fri 9 to 5", "Mon-Fri 9am-5pm"),
    ("Tuesday through Saturday, 11am to 9pm", "Tue-Sat 11am-9pm"),
    ("Monday: 8:00 AM - 5:00 PM", "Mon 8am-5pm"),
    ("Mo-Fr 08:00-17:00", "Mon-Fri 8am-5pm"),
    ("Sat closed", "Sat closed"),
    # A whole week on one line, which is how a footer writes it. The first
    # range used to be applied to every day named anywhere on the line.
    ("Sun – Wed 5pm – 9pm, Thu – Sat 5pm – 10pm",
     "Mon-Wed 5pm-9pm · Thu-Sat 5pm-10pm · Sun 5pm-9pm"),
    ("Mon-Thu 11-10, Fri-Sat 11-11, Sun 12-9",
     "Mon-Thu 11am-10pm · Fri-Sat 11am-11pm · Sun 12pm-9pm"),
])
def test_any_way_a_person_writes_a_week_reads_the_same(written, expected):
    assert hours.readable([written]) == expected


def test_something_that_is_not_a_schedule_reads_as_nothing():
    """It is kept verbatim rather than refused — the screen says so."""
    assert hours.readable(["by appointment, call ahead"]) == ""


def test_an_eight_to_five_evening_is_still_morning_to_evening():
    """"8:00 - 5:00 PM" cannot be eight in the evening: the range runs backwards."""
    assert hours.readable(["Mon 8:00 - 5:00 PM"]) == "Mon 8am-5pm"


def test_a_comma_between_days_and_times_is_not_a_second_entry():
    """Splitting "Tue-Sat, 11am to 9pm" would throw both halves away."""
    assert hours.parse_week(["Tue-Sat, 11am to 9pm"])["tue"] == "1100-2100"
