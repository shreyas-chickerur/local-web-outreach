"""The capability-C eval must pass its bar (compliant, grounded outreach emails)."""

from __future__ import annotations

import pytest

from evals.email_eval import run

pytestmark = pytest.mark.functional


def test_capability_c_eval_passes_bar():
    passed, report = run()
    assert passed, "\n".join(report)
