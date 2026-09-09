"""Two guards on `tools/make_fixtures.py --redecide`, added after a real
incident: eight untracked fixtures were destroyed by a redecide that failed
partway through on an unrelated API credit exhaustion, while the eleven
git-tracked fixtures beside them were `git checkout`-restorable instantly.
Untracked material has no such recovery path, so the tool now refuses to
touch it.

A cheap preflight call is the same shape of fix for a different failure that
happened the same session: the credit exhaustion itself surfaced eight
fixtures deep into a run, because nothing checked the key could still pay for
anything before spending on research and vision first.
"""

from __future__ import annotations

import pytest

from tools.make_fixtures import OUT, _refuse_if_untracked_fixtures

pytestmark = pytest.mark.unit


def test_an_untracked_fixture_refuses_a_redecide():
    """The exact incident, reproduced safely: a fixture that exists only on
    disk must block `--redecide` rather than being silently exposed to it."""
    scratch = OUT / "_test_untracked_guard.json"
    scratch.write_text("{}")
    try:
        assert _refuse_if_untracked_fixtures() is True
    finally:
        scratch.unlink()


def test_a_clean_tree_does_not_refuse():
    """The corpus as committed must never trip this — a guard that refuses
    the normal case is worse than no guard."""
    assert _refuse_if_untracked_fixtures() is False


def test_every_committed_fixture_really_is_tracked():
    """The premise the guard depends on: `git status` only sees what is
    outside the index, so if a fixture were ever added to `OUT` without
    `git add`, this catches it directly rather than trusting the guard to
    have been exercised."""
    import subprocess

    tracked = set(subprocess.run(
        ["git", "ls-files", str(OUT)], capture_output=True,
        text=True, check=True).stdout.splitlines())
    on_disk = {str(p) for p in OUT.glob("*.json")}
    assert on_disk <= tracked, on_disk - tracked
