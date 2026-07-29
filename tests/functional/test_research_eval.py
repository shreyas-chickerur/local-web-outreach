"""The capability-A eval must pass its bar (no hallucination; verified facts correct)."""

from __future__ import annotations

import pytest

from evals.research_eval import run

pytestmark = pytest.mark.functional


def test_capability_a_eval_passes_bar():
    passed, report = run()
    assert passed, "\n".join(report)
