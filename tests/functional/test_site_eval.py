"""The capability-B eval must pass its bar (grounded site content, no fabrication)."""

from __future__ import annotations

import pytest

from evals.site_eval import run

pytestmark = pytest.mark.functional


def test_capability_b_eval_passes_bar():
    passed, report = run()
    assert passed, "\n".join(report)
