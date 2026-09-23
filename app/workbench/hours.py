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


def _read_time(text: str) -> tuple[str, str] | None:
    """'5:00 PM' -> ('1700', 'pm'). The meridiem is returned as well as applied.

    Which one was written matters later: a range where only the closing time
    says PM is the normal way to write an evening, and the opening time has to
    borrow it.
    """
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
    return f"{hour:02d}{minute:02d}", meridiem


_TIME_TOKEN = re.compile(r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?", re.IGNORECASE)


def _segments(line: str) -> list[str]:
    """One line can hold a whole week: "Sun-Wed 5-9pm, Thu-Sat 5-10pm".

    That is how a footer writes it, and reading the line as one entry applied
    the FIRST range to every day named anywhere on it — a restaurant open an
    hour later at the weekend had that hour quietly deleted.

    Only split where the pieces stand alone. "Tuesday through Saturday, 11am to
    9pm" is one entry whose comma separates the days from the times, and
    splitting it would throw both halves away.
    """
    parts = [p for p in re.split(r"[,;|]", line) if p.strip()]
    whole = [p for p in parts
             if _DAY_WORD.search(p) and len(_TIME_TOKEN.findall(p)) >= 2]
    return whole if len(whole) >= 2 else [line]


def _close_after_open(opens: str, opens_said: str,
                      closes: str, closes_said: str) -> str:
    """"9-5" is nine in the morning to five in the evening, not to five a.m.

    When neither end says which half of the day it is, the only thing that
    settles it is that a closing time comes after an opening one. Without this
    the commonest shorthand a small business writes — "Mon-Fri 9-5" — was read
    as a twenty-hour overnight shift, and the screen said so with a straight
    face.
    """
    if opens_said or closes_said or closes > opens:
        return closes
    shifted = f"{(int(closes[:2]) + 12) % 24:02d}{closes[2:]}"
    return shifted if shifted > opens else closes


def _borrow_meridiem(opens: str, opens_said: str,
                     closes: str, closes_said: str) -> str:
    """Google writes an evening as "5:00 – 9:00 PM", marking only the close.

    Read literally that is five in the morning to nine at night, which is what
    was being stored for a restaurant that opens at five in the afternoon — and
    because their own site said 1700, the two sources "disagreed" and the hours
    were dropped as a conflict. For a business whose hours both sources state
    identically.

    The rule is the one a person applies without thinking: an unmarked opening
    time takes the closing time's meridiem when doing so still leaves the range
    running forwards. "8:00 – 5:00 PM" does not — eight in the evening to five
    in the evening is backwards — so that one stays as morning.
    """
    if opens_said or not closes_said:
        return opens
    shifted = f"{(int(opens[:2]) + 12) % 24:02d}{opens[2:]}"
    if closes_said == "pm" and int(opens[:2]) < 12 and shifted < closes:
        return shifted
    return opens


def parse_week(lines: list[str]) -> dict[str, str]:
    """A {day: '0800-1700' | 'closed'} map, as far as the lines allow.

    Only days the source actually mentions appear, so a partial listing stays
    partial rather than inventing a closed day.
    """
    week: dict[str, str] = {}
    for whole in lines:
        for line in _segments(whole):
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
                read = [_read_time(t) for t in re.findall(
                    r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?", line, re.IGNORECASE)]
                times = [r for r in read if r]
                if len(times) < 2:
                    continue
                (opens, opens_said), (closes, closes_said) = times[0], times[1]
                opens = _borrow_meridiem(opens, opens_said, closes, closes_said)
                closes = _close_after_open(opens, opens_said, closes, closes_said)
                value = f"{opens}-{closes}"
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
