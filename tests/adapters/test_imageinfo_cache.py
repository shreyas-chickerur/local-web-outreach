"""The image-size cache: two bugs that hid each other.

The key used `hash()`, which Python randomises per interpreter, so nothing
survived a process boundary — 2026 files on disk for about thirty distinct
images, and every build re-measured everything over the network.

Underneath it, a transient failure was written as a permanent unknown. Fixing
the key alone would have turned one timeout into a photograph the hero picker
could never see again, so the two belong in one change.
"""

from __future__ import annotations

import time

import httpx
import pytest

from app.adapters import imageinfo

pytestmark = pytest.mark.unit

# The autouse guard in tests/conftest.py stubs `measure` out so no test reaches
# the network by accident. This file is testing `measure` itself.
REAL = imageinfo.measure


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(imageinfo, "CACHE", tmp_path / "imagesize")
    monkeypatch.setattr(imageinfo, "measure", REAL)
    return tmp_path / "imagesize"


PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 4 + b"IHDR"
       + (1600).to_bytes(4, "big") + (900).to_bytes(4, "big"))


def transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_the_key_survives_a_process_boundary():
    """`hash()` is salted per interpreter. sha256 is not."""
    key = imageinfo._key_for("https://example.test/a.png")
    assert key == imageinfo._key_for("https://example.test/a.png")
    assert len(key) == 32 and all(c in "0123456789abcdef" for c in key)


def test_a_measured_size_is_read_back_from_disk():
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(206, content=PNG)

    url = "https://example.test/a.png"
    assert REAL(url, transport(handler)) == (1600, 900)
    assert REAL(url, transport(handler)) == (1600, 900)
    assert len(calls) == 1, "the second call should have hit the cache"


def test_bytes_that_carry_no_dimensions_are_cached_forever():
    """The server answered and we could not read it. That will not change."""
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(206, content=b"not an image at all")

    url = "https://example.test/b.png"
    assert REAL(url, transport(handler)) is None
    assert REAL(url, transport(handler)) is None
    assert len(calls) == 1


def test_a_transient_failure_is_retried_rather_than_believed(cache):
    """One timeout used to blind the hero picker to that photograph forever."""
    state = {"fail": True}

    def handler(request):
        if state["fail"]:
            raise httpx.ConnectError("refused")
        return httpx.Response(206, content=PNG)

    url = "https://example.test/c.png"
    assert REAL(url, transport(handler)) is None
    # Within the retry window it does not ask again.
    assert REAL(url, transport(handler)) is None

    # Past it, it does — and the answer is now available.
    stamp = time.time() - imageinfo.RETRY_AFTER - 1
    (cache / (imageinfo._key_for(url) + ".txt")).write_text(
        f"{imageinfo.UNREACHABLE}{stamp:.0f}")
    state["fail"] = False
    assert REAL(url, transport(handler)) == (1600, 900)


def test_a_refusing_status_is_unreachable_not_unknown(cache):
    """A 403 says nothing about the image, so it must not become a fact."""
    def handler(request):
        return httpx.Response(403, content=b"")

    url = "https://example.test/d.png"
    assert REAL(url, transport(handler)) is None
    stored = (cache / (imageinfo._key_for(url) + ".txt")).read_text()
    assert stored.startswith(imageinfo.UNREACHABLE)
