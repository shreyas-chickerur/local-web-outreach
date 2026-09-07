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

import json
from dataclasses import dataclass
from pathlib import Path

PAIRS = Path("tests/fixtures/pairs.json")

# Below this, the vector is calling two sites the same. Chosen so that the
# pairs a person called "same" and the pairs they called "different" separate
# as cleanly as the current vector allows; it moves as the vector widens, and
# moving it is a decision to record rather than a knob to tune quietly.
SAME_BELOW = 0.50


@dataclass(frozen=True)
class Agreement:
    """How often the vector and a person reach the same verdict."""

    agreed: int
    judged: int
    unsure: int
    misses: list[tuple[str, str, str, float]]   # a, b, verdict, distance

    @property
    def rate(self) -> float:
        return self.agreed / self.judged if self.judged else 0.0

    def report(self) -> str:
        lines = [f"  AGREEMENT  {self.agreed}/{self.judged} "
                 f"({self.rate:.0%}) of hand-judged pairs, "
                 f"{self.unsure} unsure and not scored"]
        for a, b, verdict, distance in self.misses:
            said = "same" if distance < SAME_BELOW else "different"
            lines.append(f"    {a} vs {b}: a person says {verdict}, "
                         f"the vector says {said} ({distance:.0%})")
        return "\n".join(lines)


def load(path: Path | None = None) -> list[dict]:
    source = path or PAIRS
    if not source.exists():
        return []
    return list(json.loads(source.read_text()).get("pairs") or [])


def score(distances: dict[tuple[str, str], float],
          pairs: list[dict] | None = None) -> Agreement:
    """Compare the vector's verdicts against the hand-judged ones."""
    judged = pairs if pairs is not None else load()
    agreed = unsure = 0
    total = 0
    misses: list[tuple[str, str, str, float]] = []
    for pair in judged:
        a, b, verdict = pair.get("a"), pair.get("b"), pair.get("verdict")
        if verdict == "unsure":
            unsure += 1
            continue
        key = (str(a), str(b))
        distance = distances.get(key)
        if distance is None:
            distance = distances.get((str(b), str(a)))
        if distance is None:
            continue
        total += 1
        says_same = distance < SAME_BELOW
        if says_same == (verdict == "same"):
            agreed += 1
        else:
            misses.append((str(a), str(b), str(verdict), distance))
    return Agreement(agreed=agreed, judged=total, unsure=unsure, misses=misses)
