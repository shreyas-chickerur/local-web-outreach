"""Does the fingerprint agree with a person looking at the pictures?

The distance number on its own cannot answer whether an axis was worth adding.
Adding axes always raises the mean, because more dimensions means more room to
differ — so a vector can get louder and less accurate at the same time. That is
what the invalid baseline did in miniature: the number improved because the
corpus changed, and it looked like progress.

So the vector is scored against hand-judged pairs instead: for each pair
somebody has called "same site" or "different studios", does the distance fall
on the right side of a threshold? The test of a new axis is whether agreement
went up. If it did not, the axis is decoration on the instrument.

`unsure` pairs are excluded from the score and reported separately. They are
where a second opinion is worth most, and scoring against a coin flip would
just add noise.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

PAIRS = Path("tests/fixtures/pairs.json")


@dataclass(frozen=True)
class Agreement:
    """How well the vector's ordering matches a person's verdicts.

    Scored by RANK, not against a threshold. Every pair a person called
    "different studios" should sit further apart than every pair they called
    "same site" — so with four same and six different there are twenty-four
    cross-comparisons and the score is how many come out in the right order.

    A threshold would be a free parameter chosen on the same ten pairs it is
    scored against, which is the invalid baseline in another costume: a number
    that looks measured and is partly chosen. This has no parameter, it uses
    the magnitude rather than which side of a line something falls, it is
    comparable across versions as axes are added, and it cannot be improved by
    moving a cut.

    If the gate later needs a pass-or-fail, derive the cut from these labels
    then — and record that it was fitted, and on how many pairs.
    """

    ordered: int
    comparisons: int
    unsure: int
    unmeasured: int
    # The pairs that came out backwards: (same-pair, different-pair, distances)
    inversions: list[tuple[str, str, float, float]]
    # Which judgements this was scored against. A score is only comparable to
    # another taken against the same labels.
    labels: str = ""

    @property
    def rate(self) -> float:
        return self.ordered / self.comparisons if self.comparisons else 0.0

    def report(self) -> str:
        lines = [f"  AGREEMENT  {self.ordered}/{self.comparisons} "
                 f"({self.rate:.0%}) of cross-comparisons ordered correctly, "
                 f"{self.unsure} unsure and not scored"
                 f"  [labels {self.labels}]"]
        if self.unmeasured:
            lines.append(f"             {self.unmeasured} pair(s) had no "
                         f"measurement and were skipped")
        for same, other, near, far in self.inversions[:6]:
            lines.append(f"    {same} ({near:.0%}) should be closer than "
                         f"{other} ({far:.0%}) and is not")
        return "\n".join(lines)


def load(path: Path | None = None) -> list[dict]:
    source = path or PAIRS
    if not source.exists():
        return []
    return list(json.loads(source.read_text()).get("pairs") or [])


def labels_version(path: Path | None = None) -> str:
    """Which set of judgements a score was taken against.

    The distance got a ruler and the census refuses to compare across a change
    of it. The hand-judged pairs are equally part of that ruler: the labels
    were re-judged blind, so 34/36 is not comparable to the earlier 8/10, and
    in six weeks nobody will remember that. Derived from the verdicts, so it
    moves whenever a judgement does.
    """
    material = "|".join(
        f"{p.get('a')}~{p.get('b')}={p.get('verdict')}"
        for p in sorted(load(path),
                        key=lambda row: (str(row.get("a")), str(row.get("b")))))
    return hashlib.sha256(material.encode()).hexdigest()[:8]


def judged_against(path: Path | None = None) -> str:
    """Which rendering the verdicts were taken from.

    A verdict describes a page. When the page changes the verdict has to be
    re-taken, and one kept past the rendering it judged is as stale as a
    baseline kept past a change of ruler — `dentist`/`law` was labelled "the
    same page twice" when both opened on a photograph with white type, and
    stayed labelled that after one moved to `proof` and the other to `facts`.
    """
    source = path or PAIRS
    if not source.exists():
        return ""
    return str(json.loads(source.read_text()).get("_judged_against") or "")


def score(distances: dict[tuple[str, str], float],
          pairs: list[dict] | None = None) -> Agreement:
    """Rank the vector's distances against the hand-judged verdicts."""
    judged = pairs if pairs is not None else load()

    def measured(pair: dict) -> float | None:
        a, b = str(pair.get("a")), str(pair.get("b"))
        found = distances.get((a, b))
        return found if found is not None else distances.get((b, a))

    same: list[tuple[str, float]] = []
    apart: list[tuple[str, float]] = []
    unsure = unmeasured = 0
    for pair in judged:
        verdict = pair.get("verdict")
        if verdict == "unsure":
            unsure += 1
            continue
        distance = measured(pair)
        if distance is None:
            unmeasured += 1
            continue
        label = f"{pair.get('a')}/{pair.get('b')}"
        (same if verdict == "same" else apart).append((label, distance))

    ordered = 0
    inversions: list[tuple[str, str, float, float]] = []
    for near_name, near in same:
        for far_name, far in apart:
            if near < far:
                ordered += 1
            else:
                inversions.append((near_name, far_name, near, far))
    inversions.sort(key=lambda row: row[2] - row[3], reverse=True)
    return Agreement(ordered=ordered, comparisons=len(same) * len(apart),
                     unsure=unsure, unmeasured=unmeasured,
                     inversions=inversions,
                     labels=labels_version() if pairs is None else "ad hoc")
