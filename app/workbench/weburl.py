"""Is the address a directory publishes for a business the address that works?

Often it is not, and the ways it fails are worth telling apart, because each
one is a different sentence at the door:

* **certificate** — the URL is right but TLS fails on that exact hostname, so
  every visitor who follows the listing gets a full-page security warning.
* **not-found** — the domain answers but that page is gone.
* **no-https** — the site has no working https at all.
* **http-link** — the listing links http, but https works; the link is stale.
* **parked** — the domain lapsed and now shows a registrar's for-sale page.
* **dead** — nothing answers anywhere.
* **blocked** — a bot filter refused us (403, 429). This is not a fault of
  theirs and not a finding: it means we do not know, and the page must say so
  rather than inventing a verdict from an error page.
* **redirected** — it works, but lands somewhere else; worth knowing when the
  destination is a different domain (a Facebook page, an aggregator).

Finding the working spelling is the correction. Keeping the published one
alongside it is the point: the fault is the reason to walk in, so it must not
be silently repaired out of the brief.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse

from app.adapters.site_fetch import FetchResult, SiteFetcher

# Registrar holding pages, which mean the business let the domain lapse.
_PARKED_RE = re.compile(
    r"(this domain (name )?is for sale|buy this domain|domain( name)? parking|"
    r"parked (free )?(at|by|courtesy)|godaddy\.com/domainsearch|"
    r"sedoparking|hugedomains|afternic|dan\.com/buy-domain|"
    r"the domain .{0,40} may be for sale)", re.IGNORECASE)

FAULTS = ("certificate", "not-found", "no-https", "http-link", "parked", "dead",
          "redirected")


@dataclass
class UrlCheck:
    """What the published address does, and what to use instead."""

    published: str
    working: str | None = None
    fault: str | None = None
    note: str = ""
    tried: list[str] = field(default_factory=list)
    # Their bot protection refused us. Nothing about the site can be concluded,
    # least of all from the body of the 403 page.
    blocked: bool = False
    result: FetchResult | None = None      # the fetch we ended up using

    @property
    def needs_correction(self) -> bool:
        return self.fault is not None and self.working is not None

    @property
    def is_broken(self) -> bool:
        return self.fault in ("dead", "parked", "not-found")


def _swap_www(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc
    other = host[4:] if host.lower().startswith("www.") else f"www.{host}"
    return urlunparse(parsed._replace(netloc=other))


def _as_http(url: str) -> str:
    return urlunparse(urlparse(url)._replace(scheme="http"))


def _as_https(url: str) -> str:
    return urlunparse(urlparse(url)._replace(scheme="https"))


def _root(url: str) -> str:
    return urlunparse(urlparse(url)._replace(path="/", params="", query="", fragment=""))


def candidates(url: str) -> list[str]:
    """Spellings to try, secure ones first.

    Order matters for the verdict, not just for speed: if an https spelling
    works, the site is not insecure — its listing is simply out of date, which
    is a different thing to say and a much smaller thing to fix.
    """
    first = url if "//" in url else f"https://{url}"
    secure = _as_https(first)
    out = [first, secure, _swap_www(secure), _root(secure), _swap_www(_root(secure)),
           _as_http(first), _as_http(_swap_www(first))]
    seen: set[str] = set()
    ordered = []
    for candidate in out:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def _same_site(a: str, b: str) -> bool:
    """www.x.com and x.com are the same site; x.com and facebook.com are not."""
    def host(u: str) -> str:
        h = urlparse(u).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    return host(a) == host(b)


def validate(published: str, fetcher: SiteFetcher, *,
             max_attempts: int = 5) -> UrlCheck:
    """Probe the published address and, if it fails, the spellings that might
    work. Never raises: an unreachable site is an answer, not an error."""
    check = UrlCheck(published=published)
    if not published.strip():
        check.fault, check.note = "dead", "no website address to check"
        return check

    first_fault: str | None = None
    fallback: tuple[FetchResult, str] | None = None
    for attempt, candidate in enumerate(candidates(published)):
        if attempt >= max_attempts:
            break
        check.tried.append(candidate)
        try:
            result = fetcher.fetch(candidate)
        except Exception:                      # a broken site is data, not a crash
            first_fault = first_fault or "dead"
            continue

        fault = _classify(result, candidate)
        if fault == "blocked":
            # Try the other spellings — but if they all refuse us, the honest
            # answer is that we could not look, not that anything is wrong.
            first_fault = first_fault or "blocked"
            continue
        if fault == "no-https":
            # It answered, but only over http. Keep looking for a secure
            # spelling before concluding the site has no TLS.
            first_fault = first_fault or "no-https"
            fallback = fallback or (result, candidate)
            continue
        if fault is None:
            check.result = result
            landed = result.final_url or candidate
            if _PARKED_RE.search(result.html or ""):
                # A registrar's page answers 200; it is still not their site.
                first_fault = first_fault or "parked"
                continue
            check.working = landed
            # A working https spelling means the site is fine and the listing
            # is stale, which is "http-link", not "no-https".
            carried = "http-link" if first_fault == "no-https" else first_fault
            # Judge where it landed, not which spelling got us there: the
            # published address itself can redirect to a different domain.
            check.fault = carried or (
                None if _spelling_only(published, landed) else "redirected")
            check.note = _explain(check)
            return check
        first_fault = first_fault or fault

    if fallback is not None:
        # Nothing secure answered, so http is genuinely all they have.
        result, landed = fallback
        check.result, check.working = result, result.final_url or landed
        check.fault = "no-https"
        check.note = _explain(check)
        return check

    if first_fault == "blocked":
        check.blocked = True
        check.fault = None
        check.working = published
        check.note = ("their site refused our reader, so nothing here is a "
                      "judgement about it — open it yourself")
        return check

    check.fault = first_fault or "dead"
    check.note = _explain(check)
    return check


def _spelling_only(published: str, landed: str) -> bool:
    """A www/http difference is a spelling, not a redirect worth reporting."""
    return _same_site(published, landed)


def _classify(result: FetchResult, url: str) -> str | None:
    if getattr(result, "tls_error", False):
        return "certificate"
    if result.status == 404:
        return "not-found"
    if result.status in (401, 403, 405, 406, 429):
        return "blocked"
    if result.ok and result.html:
        return None if url.lower().startswith("https") else "no-https"
    if result.status is None:
        return "dead"
    return "not-found" if 400 <= (result.status or 0) < 500 else "dead"


def _explain(check: UrlCheck) -> str:
    """The finding, in the words you would use at the door."""
    where = check.working or ""
    return {
        "certificate": (
            "the address on their listing throws a browser security warning — "
            "its certificate is not valid for that hostname"
            + (f"; the site itself works at {where}" if where else "")),
        "not-found": (
            "the address on their listing is a dead page"
            + (f"; the site is at {where}" if where else "")),
        "no-https": (
            "their site has no https at all, so every browser marks it "
            "“not secure”"),
        "http-link": (
            f"the link on their listing is the old http one; the site itself "
            f"serves https at {where}"),
        "parked": "their domain has lapsed and now shows a registrar's for-sale page",
        "dead": "nothing answers at the address on their listing",
        "redirected": f"their listing points somewhere else — it lands on {where}",
        None: "",
    }[check.fault]
