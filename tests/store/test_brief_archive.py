"""Every crawled brief, kept — never overwritten.

The DB's own `leads.save_brief` overwrites its cached row on every
re-crawl by design; this archive is the permanent trail beside it, so
these tests pin the one thing that mechanism cannot: that an EARLIER
crawl's file is never touched by a later one.
"""

from __future__ import annotations

import json

import pytest

from app.store import brief_archive

pytestmark = pytest.mark.unit


def test_a_fresh_crawl_writes_a_new_file_every_time(tmp_path):
    brief = {"name": "Craftway Kitchen", "published": {"about": "v1"}}
    first = brief_archive.save(brief, root=tmp_path)
    second = brief_archive.save({**brief, "published": {"about": "v2"}}, root=tmp_path)
    assert first["path"] != second["path"]
    # The first file is untouched — still says what it said the first time.
    assert json.loads(open(first["path"]).read())["published"]["about"] == "v1"
    assert json.loads(open(second["path"]).read())["published"]["about"] == "v2"


def test_two_crawls_in_the_same_wall_clock_second_still_do_not_collide(tmp_path):
    """A retried request, or two fast test runs, can land in the same
    second — "never overwrite" has to hold then too, not just when a
    human would notice the crawls were separate."""
    brief = {"name": "Craftway Kitchen"}
    paths = {brief_archive.save(brief, root=tmp_path)["path"] for _ in range(20)}
    assert len(paths) == 20


def test_the_content_hash_changes_when_the_content_does(tmp_path):
    brief = {"name": "Craftway Kitchen", "published": {"about": "v1"}}
    first = brief_archive.save(brief, root=tmp_path)
    second = brief_archive.save({**brief, "published": {"about": "v2"}}, root=tmp_path)
    assert first["hash"] != second["hash"]


def test_the_current_pointer_always_names_the_latest_file(tmp_path):
    brief = {"name": "Craftway Kitchen", "published": {}}
    brief_archive.save(brief, root=tmp_path)
    latest = brief_archive.save(brief, root=tmp_path)
    assert brief_archive.current("Craftway Kitchen", root=tmp_path) == latest


def test_a_business_never_crawled_before_has_no_current_pointer(tmp_path):
    assert brief_archive.current("Nobody Yet", root=tmp_path) is None


def test_different_businesses_get_different_directories(tmp_path):
    brief_archive.save({"name": "Craftway Kitchen"}, root=tmp_path)
    brief_archive.save({"name": "Hutchins BBQ"}, root=tmp_path)
    assert (tmp_path / "craftway-kitchen").is_dir()
    assert (tmp_path / "hutchins-bbq").is_dir()


@pytest.mark.parametrize("name,slug", [
    ("Craftway Kitchen", "craftway-kitchen"),
    ("O'Malley's Pub!!", "o-malley-s-pub"),
    ("", "unnamed"),
])
def test_the_slug_is_filesystem_safe(name, slug):
    assert brief_archive._slug(name) == slug
