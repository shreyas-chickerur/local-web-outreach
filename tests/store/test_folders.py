"""A business's folder is filled by the same calls that fill the database."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.store import db, folders, leads, sites

pytestmark = pytest.mark.unit


def _lead(tmp_path: Path):
    conn = db.connect(tmp_path / "t.db")
    lead_id = leads.save_brief(conn, {
        "name": "Fish Shack", "location": "Plano, TX", "facts": [], "published": {},
        "assumptions": [], "open_questions": [], "sources_consulted": []})
    return conn, lead_id


def test_every_saved_version_and_the_master_reach_the_business_folder(tmp_path):
    """Versions lived only in the database, which is gitignored and can only be
    read through the workbench: The Heritage Table's fifteen pages existed
    nowhere a person could open, copy or back up."""
    conn, lead_id = _lead(tmp_path)
    sites.save(conn, lead_id, "<p>one</p>", spec="")
    sites.save(conn, lead_id, "<p>two</p>", spec="", parent_version=1)
    leads.mark_master(conn, lead_id, 1)
    folder = folders.of("Fish Shack")
    assert (folder / "versions" / "v2.html").read_text() == "<p>two</p>"
    assert (folder / "master.txt").read_text() == "v1\n"


def test_filling_writes_what_was_saved_before_the_folders_existed(tmp_path):
    """Versions made before this existed reach the folder too, and filling
    again changes nothing."""
    conn, lead_id = _lead(tmp_path)
    sites.save(conn, lead_id, "<p>old</p>", spec="")
    (folders.of("Fish Shack") / "versions" / "v1.html").unlink()
    assert len(folders.fill(conn)) == len(folders.fill(conn)) == 1
    assert (folders.of("Fish Shack") / "versions" / "v1.html").read_text() == "<p>old</p>"
