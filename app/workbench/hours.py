"""Opening hours, reduced to a weekly schedule that can be compared.

Google publishes seven lines ("Monday: 8:00 AM - 5:00 PM"), a website's
schema.org block publishes "Mo-Fr 08:00-17:00", and a footer publishes
"Mon-Fri 8:00am - 5:00pm". Those are the same week. Compared as text they look
like three different answers, which is why hours could never be corroborated
and every brief asked for hours the sources had already published.
"""

from __future__ import annotations

import re

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_INDEX = {d: i for i, d in enumerate(DAYS)}
_ALIASES = {"mo": "mon", "tu": "tue", "tues": "tue", "we": "wed", "weds": "wed",
            "th": "thu", "thur": "thu", "thurs": "thu", "fr": "fri",
            "sa": "sat", "su": "sun"}

_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)
_CLOSED = re.compile(r"closed", re.IGNORECASE)
_DAY_WORD = re.compile(r"\b(mon|tues?|tue|wed(?:nes)?|thur?s?|thu|fri|sat|sun|"
                       r"mo|tu|we|th|fr|sa|su)(?:day|nesday|rsday|urday)?\b",
                       re.IGNORECASE)


def _day(word: str) -> str | None:
    key = word.lower()[:4]
    for candidate in (key, key[:3], key[:2]):
        if candidate in _INDEX:
            return candidate
        if candidate in _ALIASES:
            return _ALIASES[candidate]
    return None


def _minutes(text: str) -> str | None:
    """'5:00 PM' -> '1700'. Twelve-hour and 24-hour clocks both appear."""
    match = _TIME.match(text.strip())
    if match is None:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 24 and 0 <= minute < 60):
        return None
    return f"{hour:02d}{minute:02d}"


def parse_week(lines: list[str]) -> dict[str, str]:
    """A {day: '0800-1700' | 'closed'} map, as far as the lines allow.

    Only days the source actually mentions appear, so a partial listing stays
    partial rather than inventing a closed day.
    """
    week: dict[str, str] = {}
    for line in lines:
        matches = [(m, _day(m.group(0))) for m in _DAY_WORD.finditer(line)]
        found = [(m, d) for m, d in matches if d]
        days = [d for _, d in found]
        if not days:
            continue
        # "Mon-Fri" is a range; "Mon, Wed" is a list. What separates the two day
        # words decides which — read the text between them rather than guessing
        # from the names, since sources abbreviate to two, three or four letters.
        joined = (line[found[0][0].end():found[1][0].start()]
                  if len(found) == 2 else "")
        if len(days) == 2 and re.fullmatch(r"\s*(to|[-–—])\s*", joined, re.IGNORECASE):
            start, end = _INDEX[days[0]], _INDEX[days[1]]
            span = (list(range(start, end + 1)) if start <= end
                    else list(range(start, 7)) + list(range(0, end + 1)))
            days = [DAYS[i] for i in span]

        # Day names carry no digits, so times can be read straight off the line.
        if _CLOSED.search(line):
            value = "closed"
        else:
            times = [_minutes(t) for t in re.findall(
                r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?", line, re.IGNORECASE)]
            times = [t for t in times if t]
            if len(times) < 2:
                continue
            value = f"{times[0]}-{times[1]}"
        for day in days:
            week.setdefault(day, value)
    return week


def canonical(lines: list[str]) -> str | None:
    """One comparable string for a week, or None if nothing parsed."""
    week = parse_week(lines)
    if len(week) < 3:          # a day or two is not a schedule worth comparing
        return None
    return " ".join(f"{d}:{week[d]}" for d in DAYS if d in week)


def describe(week: dict[str, str]) -> str:
    """A parsed week as the shortest honest phrasing: 'Mon-Fri 8:00am-5:00pm'."""
    runs: list[tuple[list[str], str]] = []
    for day in DAYS:
        value = week.get(day)
        if value is None:
            continue
        if runs and runs[-1][1] == value:
            runs[-1][0].append(day)
        else:
            runs.append(([day], value))
    parts: list[str] = []
    for days, value in runs:
        label = (days[0].title() if len(days) == 1
                 else f"{days[0].title()}-{days[-1].title()}")
        parts.append(f"{label} closed" if value == "closed"
                     else f"{label} {_clock(value.split('-')[0])}"
                          f"-{_clock(value.split('-')[1])}")
    return " · ".join(parts)


def _clock(hhmm: str) -> str:
    """'1700' -> '5pm'. Reading a brief should not require a 24-hour clock."""
    hour, minute = int(hhmm[:2]), int(hhmm[2:])
    suffix = "am" if hour < 12 else "pm"
    display = hour % 12 or 12
    return f"{display}:{minute:02d}{suffix}" if minute else f"{display}{suffix}"


def from_canonical(canon: str) -> dict[str, str]:
    """Read back what canonical() produced."""
    week: dict[str, str] = {}
    for token in canon.split():
        day, _, value = token.partition(":")
        if day in _INDEX and value:
            week[day] = value
    return week


def readable(lines: list[str]) -> str:
    """Raw source lines, phrased for a human. Empty when nothing parsed."""
    return describe(parse_week(lines))
