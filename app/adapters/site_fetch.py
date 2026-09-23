"""Fetching a candidate's existing website so the qualifier can inspect it.

The qualifier depends on the ``SiteFetcher`` protocol, not on httpx directly, so
tests inject a fake fetcher and get deterministic HTML without touching the
network.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Protocol

import httpx

from app.adapters import chrome_cdp


@dataclass(frozen=True)
class FetchResult:
    """Outcome of fetching a URL."""

    ok: bool
    status: int | None
    final_url: str | None
    html: str
    elapsed_ms: int
    error: str | None = None
    # The certificate does not match the hostname, or is expired or untrusted.
    # Worth its own flag: it is not the site being down, it is every visitor
    # who types that address getting a full-page security warning.
    tls_error: bool = False


_TLS_MARKERS = ("certificate_verify_failed", "ssl:", "sslcertverification",
                "hostname mismatch", "certificate has expired",
                "self signed certificate")


def _is_tls_failure(exc: Exception) -> bool:
    """Tell a broken certificate apart from a dead server."""
    text = str(exc).lower()
    return any(marker in text for marker in _TLS_MARKERS)


class SiteFetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


# A page's HTML is what a server sent; a page's DOM is what a browser drew.
# Where a site builds its own content client-side — a JavaScript menu, a
# React storefront — `HttpSiteFetcher`'s raw response is a near-empty shell:
# the platform reads source, the world renders. `render_document()` renders
# it too, then reads back the DOM a real visitor would see.
_MAIN_DOC_TIMEOUT = 20.0
# A page's own scripts can keep running past `document.readyState ==
# "complete"` (a menu widget that fetches its items, a slow analytics tag) —
# a fixed settle window catches most of that without waiting on a network
# that may never go fully idle. `tools/perf_census.py` settles 1.5s after
# load for the same reason before trusting what it measures.
_SETTLE_SECONDS = 1.5
_CERT_ERROR_MARKERS = ("cert", "ssl", "erroraborted")


def render_document(binary: str, url: str, timeout: float = _MAIN_DOC_TIMEOUT
                    ) -> FetchResult:
    """Fetch `url` the way a visitor's browser would: run its JavaScript,
    then read back the DOM it produced.

    Reuses `app.adapters.chrome_cdp.cdp_session` for every piece that is
    hard to get right twice (the Chrome launch, the WebSocket handshake,
    the JSON-RPC framing) rather than a fourth copy of it. The session
    itself is opened on `about:blank` and the real navigation happens
    inside this function instead, because the main document's HTTP status
    can only be read from a `Network.responseReceived` event, and that
    event has to be listened for BEFORE the navigation that produces it —
    `cdp_session`'s own initial navigation (via `/json/new?<target>`)
    starts before a caller has any chance to enable the Network domain.
    """
    start = time.perf_counter()
    status: int | None = None
    failed_error: str | None = None

    def on_event(message: dict) -> None:
        nonlocal status, failed_error
        method = message.get("method")
        params = message.get("params") or {}
        if method == "Network.responseReceived" and params.get("type") == "Document":
            if status is None:
                status = params.get("response", {}).get("status")
        elif method == "Network.loadingFailed" and params.get("type") == "Document":
            failed_error = failed_error or params.get("errorText")

    try:
        with chrome_cdp.cdp_session(
                binary, "about:blank", 1440, 900, 1.0, timeout=timeout,
                on_event=on_event) as call:
            call("Network.enable")
            call("Runtime.enable")
            call("Page.navigate", {"url": url})
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                state = call("Runtime.evaluate", {
                    "expression": "document.readyState", "returnByValue": True})
                if (state.get("result", {}).get("result", {}).get("value")
                        == "complete"):
                    break
                time.sleep(0.05)
            time.sleep(_SETTLE_SECONDS)
            location = call("Runtime.evaluate", {
                "expression": "location.href", "returnByValue": True})
            final_url = location.get("result", {}).get("result", {}).get("value")
            dom = call("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True})
            html = dom.get("result", {}).get("result", {}).get("value") or ""
    except (TimeoutError, OSError) as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return FetchResult(ok=False, status=None, final_url=None, html="",
                           elapsed_ms=elapsed_ms, error=str(exc))

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    tls_error = bool(failed_error and any(
        marker in failed_error.lower() for marker in _CERT_ERROR_MARKERS))
    if failed_error and status is None:
        return FetchResult(ok=False, status=None, final_url=final_url, html="",
                           elapsed_ms=elapsed_ms, error=failed_error,
                           tls_error=tls_error)
    return FetchResult(
        ok=(status is None or status < 400) and bool(html),
        status=status, final_url=final_url, html=html,
        elapsed_ms=elapsed_ms, tls_error=tls_error)


class ChromeSiteFetcher:
    """Fetch through a real, headless Chrome rather than a raw HTTP GET —
    render, then extract, so a page that draws itself with JavaScript is
    read the way a visitor's browser sees it rather than the empty shell
    the server actually sent.

    Falls back to a plain HTTP GET, per URL, when Chrome is not installed
    or a render attempt errors — the same "a real answer is better, but a
    degraded one is not nothing" shape `app.site.opening`'s Claude-then-
    trade-table fallback already uses. A page that genuinely needs no
    JavaScript loses nothing by falling back; a JS-built page that fails
    to render still gets *a* result rather than none.
    """

    def __init__(self, fallback: SiteFetcher | None = None,
                timeout: float = _MAIN_DOC_TIMEOUT) -> None:
        self._fallback = fallback or HttpSiteFetcher()
        self._timeout = timeout
        self._binary = chrome_cdp.chrome()

    def fetch(self, url: str) -> FetchResult:
        if self._binary is None:
            return self._fallback.fetch(url)
        try:
            rendered = render_document(self._binary, url, self._timeout)
        except Exception:  # noqa: BLE001 — a render bug must not lose the fetch
            return self._fallback.fetch(url)
        if rendered.ok and rendered.html:
            return rendered
        # A render that fails comes back as a result, not an error, so the plain
        # fetch was never tried: The Heritage Table's history page timed out in
        # Chrome and was recorded unreadable. Try it, and if it fails too, say
        # what each attempt ran into.
        plain = self._fallback.fetch(url)
        if plain.ok and plain.html:
            return plain
        def why(result: FetchResult) -> str:
            return result.error or (f"status {result.status}" if result.status
                                    else "empty response")
        return replace(rendered, error=f"browser: {why(rendered)}; plain fetch: {why(plain)}")


def default_fetcher() -> SiteFetcher:
    """The best fetcher this machine can actually run.

    Mirrors `app.adapters.claude.available()`'s own pattern: prefer the
    real capability, degrade to the simpler one rather than failing, and
    let the caller stay ignorant of which it got.
    """
    return ChromeSiteFetcher() if chrome_cdp.chrome() else HttpSiteFetcher()


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
                error=str(exc), tls_error=_is_tls_failure(exc),
            )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return FetchResult(
            ok=resp.status_code < 400,
            status=resp.status_code,
            final_url=str(resp.url),
            html=resp.text,
            elapsed_ms=elapsed_ms,
        )


def download(url: str, timeout: float = 15.0) -> tuple[bytes | None, str]:
    """The raw bytes behind a URL — a menu PDF or image — or why there are none.

    The reason is the specific one. The Heritage Table's dinner menu PDF was
    recorded as "could not download" when the server had plainly said 404,
    which reads the same as a timeout or a refusal.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout,
                          headers={"User-Agent": "lwo-qualifier/0.1"}) as client:
            resp = client.get(url)
    except httpx.TimeoutException:
        return None, "timed out"
    except httpx.HTTPError as exc:
        return None, f"could not download ({type(exc).__name__})"
    if resp.status_code >= 400:
        return None, f"status {resp.status_code}"
    if not resp.content:
        return None, "empty response"
    return resp.content, ""


def fetch_bytes(url: str, timeout: float = 15.0) -> bytes | None:
    """The bytes from `download`, without the reason, for callers that only
    need to know whether there were any."""
    return download(url, timeout)[0]
