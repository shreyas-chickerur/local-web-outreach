"""Fetching a candidate's existing website so the qualifier can inspect it.

The qualifier depends on the ``SiteFetcher`` protocol, not on httpx directly, so
tests inject a fake fetcher and get deterministic HTML without touching the
network.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class FetchResult:
    """Outcome of fetching a URL."""

    ok: bool
    status: int | None
    final_url: str | None
    html: str
    elapsed_ms: int
    error: str | None = None


class SiteFetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


class HttpSiteFetcher:
    """Real fetcher (httpx). Follows redirects so ``final_url`` reflects the
    landing page (important for detecting http→https upgrades or their absence)."""

    def __init__(self, client: httpx.Client | None = None, timeout: float = 10.0) -> None:
        self._client = client or httpx.Client(
            follow_redirects=True, timeout=timeout, headers={"User-Agent": "lwo-qualifier/0.1"}
        )

    def fetch(self, url: str) -> FetchResult:
        start = time.perf_counter()
        try:
            resp = self._client.get(url)
        except httpx.HTTPError as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return FetchResult(
                ok=False, status=None, final_url=None, html="", elapsed_ms=elapsed_ms,
                error=str(exc),
            )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return FetchResult(
            ok=resp.status_code < 400,
            status=resp.status_code,
            final_url=str(resp.url),
            html=resp.text,
            elapsed_ms=elapsed_ms,
        )
