"""Command-line entry point for running the built stages.

    python -m app.cli demo                     # no API key: live-fetches real Frisco sites
    python -m app.cli discover "Frisco, TX"    # live: needs GOOGLE_PLACES_API_KEY in .env
        [--category restaurant]

`demo` runs against a throwaway SQLite DB so it is always repeatable and never
touches your real database.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from app.adapters.places import BusinessCandidate, StubPlacesSource, get_places_source
from app.adapters.site_fetch import HttpSiteFetcher
from app.ai.research_runner import PassthroughExtractor
from app.core.audit import latest_transition_reason
from app.core.config import database_url
from app.core.db import Base, make_engine, make_session_factory
from app.demo_data import demo_businesses
from app.models import (  # noqa: F401  (register metadata)
    AuditEvent,
    Business,
    ResearchClaim,
    SiteWeakness,
)
from app.stages.discover import discover
from app.stages.generate import generate_website
from app.stages.qualify import SiteProber, qualify
from app.stages.research import build_dossier

# A few real Frisco, TX businesses for the no-key demo (websites are their
# real/claimed URLs; the demo fetches them live to classify).
FRISCO_DEMO = [
    BusinessCandidate("demo-depot", "The Depot Cafe", "Frisco, TX", "restaurant",
                      website="https://depotcafefrisco.com"),
    BusinessCandidate("demo-friscodiner", "Frisco Diner", "Frisco, TX", "restaurant",
                      website="https://friscodiner.com"),
    BusinessCandidate("demo-jslawn", "JS Lawn Care Service", "Frisco, TX", "lawn",
                      website=None),
    BusinessCandidate("demo-mcd", "McDonald's Frisco", "Frisco, TX", "restaurant",
                      website="https://www.mcdonalds.com"),
]


def _report(session, businesses: list[Business]) -> None:
    print(f"\n{'BUSINESS':30} {'STATUS':13} {'SCORE':>5}  WHY")
    print("-" * 92)
    for biz in sorted(businesses, key=lambda b: -(b.opportunity_score or 0)):
        why = latest_transition_reason(session, biz.id)
        print(f"{biz.name[:30]:30} {biz.status.value:13} {biz.opportunity_score or 0:>5}  {why}")
    print()


def _run(session, source, location, category) -> list[Business]:
    created = discover(session, source, location, category)
    prober = SiteProber(HttpSiteFetcher())
    for biz in created:
        qualify(session, biz, prober)
    session.commit()
    return created


def cmd_demo(_args: argparse.Namespace) -> int:
    tmp = Path(tempfile.mkdtemp()) / "demo.db"
    engine = make_engine(f"sqlite+pysqlite:///{tmp}")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    print("Running discovery+qualification on a live Frisco, TX demo set (no API key)...")
    created = _run(session, StubPlacesSource(FRISCO_DEMO), "Frisco, TX", None)
    _report(session, created)
    session.close()
    engine.dispose()
    return 0


def cmd_research_demo(_args: argparse.Namespace) -> int:
    """Run the research pipeline on the bundled real Frisco data (no API key)."""
    from app.core.enums import BusinessStatus

    tmp = Path(tempfile.mkdtemp()) / "research.db"
    engine = make_engine(f"sqlite+pysqlite:///{tmp}")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    print("Building research dossiers from bundled, hand-verified Frisco data (no key)...\n")
    for entry in demo_businesses():
        sources = entry.pop("sources")
        biz = Business(status=BusinessStatus.RESEARCHED, **entry)
        session.add(biz)
        session.flush()
        dossier = build_dossier(session, biz, sources, extractor, model_version="demo/manual")
        session.commit()

        print(f"=== {biz.name} ({biz.location}) ===")
        print(f"{'FIELD':14} {'STATUS':11} {'CONF':>4}  VALUE")
        print("-" * 78)
        for c in sorted(dossier.claims, key=lambda c: c.field):
            print(f"{c.field:14} {c.status.value:11} {c.confidence:>4.2f}  {(c.value or '')[:44]}")
        if dossier.questions:
            print("\nOpen questions for the owner (gaps — not fabricated):")
            for q in dossier.questions:
                print(f"  • {q}")
        if dossier.rejected_sources:
            names = ", ".join(sorted({s.entity_name for s in dossier.rejected_sources}))
            print(f"\nSources NOT merged (entity resolution): {names}")
        print()

    session.close()
    engine.dispose()
    return 0


def cmd_site_demo(_args: argparse.Namespace) -> int:
    """Research the bundled Frisco data, then generate a grounded site draft."""
    from app.core.enums import BusinessStatus

    tmp = Path(tempfile.mkdtemp()) / "site.db"
    engine = make_engine(f"sqlite+pysqlite:///{tmp}")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    print("Generating grounded site drafts from bundled Frisco research (no key)...\n")
    for entry in demo_businesses():
        sources = entry.pop("sources")
        biz = Business(status=BusinessStatus.RESEARCHED, **entry)
        session.add(biz)
        session.flush()
        build_dossier(session, biz, sources, extractor, model_version="demo/manual")
        site = generate_website(session, biz)
        session.commit()

        content = site.content_json
        print(f"=== {content['business_name']}  [{content['industry']} template] ===")
        print(f"preview: {site.preview_url}  (state={site.state.value}, "
              f"noindex={content['noindex']})")
        for s in content["sections"]:
            if s.get("facts"):
                print(f"  [{s['type']}] {s['heading']}")
                for f in s["facts"]:
                    print(f"      - {f['label']}: {f['value']}   ← claim {f['claim_id'][:8]}")
            else:
                print(f"  [{s['type']}] {s.get('heading', '')}")
        if content["needs_confirmation"]:
            print(f"  needs owner confirmation: {', '.join(content['needs_confirmation'])}")
        print()

    session.close()
    engine.dispose()
    return 0


def cmd_email_demo(_args: argparse.Namespace) -> int:
    """Research → generate → approve site → compose the outreach email (no key)."""
    from app.ai.email_composer import TemplateEmailComposer
    from app.core.approvals import create_approval
    from app.core.enums import Actor, BusinessStatus, Decision, SubjectType
    from app.core.state_machine import advance
    from app.stages.outreach import compose_email

    tmp = Path(tempfile.mkdtemp()) / "email.db"
    engine = make_engine(f"sqlite+pysqlite:///{tmp}")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    composer = TemplateEmailComposer()
    print("Research → generate → approve site → compose outreach (bundled Frisco, no key)...\n")
    for entry in demo_businesses():
        sources = entry.pop("sources")
        biz = Business(status=BusinessStatus.RESEARCHED, **entry)
        session.add(biz)
        session.flush()
        build_dossier(session, biz, sources, extractor, model_version="demo/manual")
        site = generate_website(session, biz)
        approval = create_approval(session, subject_type=SubjectType.SITE, subject_id=biz.id,
                                   decision=Decision.APPROVE, approver="operator",
                                   content=site.content_json)
        advance(session, biz, BusinessStatus.SITE_APPROVED,
                actor=Actor.HUMAN.value, approval=approval)
        email = compose_email(session, biz, composer)
        session.commit()

        print(f"=== {biz.name}  →  {email.recipient} ===")
        print(f"Subject: {email.subject}\n")
        print(email.body)
        print(f"\n[status={email.status.value}, suppression_checked={email.suppression_checked}, "
              f"hash={email.content_hash[:8]}]")
        print("-" * 72 + "\n")

    session.close()
    engine.dispose()
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Populate the CONFIGURED database (the one `make api` serves) with the
    bundled Frisco pipeline so the Operator Console has real data to show:
    a mix of SITE_DRAFTED (Gate 1) and EMAIL_DRAFTED (Gate 2) businesses."""
    from app.ai.email_composer import TemplateEmailComposer
    from app.core.approvals import create_approval
    from app.core.enums import Actor, BusinessStatus, Decision, SubjectType
    from app.core.state_machine import advance
    from app.stages.outreach import compose_email

    engine = make_engine(database_url())
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()

    existing = session.query(Business).count()
    if existing and not args.reset:
        print(f"DB already has {existing} businesses. Re-run with --reset to wipe and reseed.")
        session.close()
        engine.dispose()
        return 0
    if args.reset and existing:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

    extractor = PassthroughExtractor()
    composer = TemplateEmailComposer()
    n_site = n_email = 0
    for i, entry in enumerate(demo_businesses()):
        sources = entry.pop("sources")
        biz = Business(status=BusinessStatus.RESEARCHED, **entry)
        session.add(biz)
        session.flush()
        build_dossier(session, biz, sources, extractor, model_version="demo/manual")
        site = generate_website(session, biz)  # -> SITE_DRAFTED
        # Advance every other business through Gate 1 so both gates have items.
        if i % 2 == 0:
            approval = create_approval(session, subject_type=SubjectType.SITE, subject_id=biz.id,
                                       decision=Decision.APPROVE, approver="operator",
                                       content=site.content_json)
            advance(session, biz, BusinessStatus.SITE_APPROVED,
                    actor=Actor.HUMAN.value, approval=approval)
            compose_email(session, biz, composer)  # -> EMAIL_DRAFTED
            n_email += 1
        else:
            n_site += 1
        session.commit()

    session.close()
    engine.dispose()
    print(f"Seeded {n_site + n_email} businesses into {database_url()}")
    print(f"  {n_site} awaiting SITE approval (Gate 1), {n_email} awaiting EMAIL approval (Gate 2)")
    print("Now run `make api` and open http://127.0.0.1:8090")
    return 0


def cmd_reset(_args: argparse.Namespace) -> int:
    """Wipe the configured database WITHOUT seeding demo rows.

    `seed --reset` reloads the bundled demo businesses (The Depot Cafe, JS Lawn
    Care) whose hand-curated sources include third-party directories — useful for
    exercising the console, confusing when mixed into live leads. Use this before
    a real discovery run.
    """
    engine = make_engine(database_url())
    # Drop and recreate rather than DELETE FROM: a dev database created by an
    # older build is missing newly added columns, and create_all never alters an
    # existing table. Production schema changes go through Alembic.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()
    print(f"Wiped {database_url()} (no demo data). Run `discover` next.")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    """Counts by status in the configured DB, plus what's waiting on you."""
    from collections import Counter

    engine = make_engine(database_url())
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    rows = session.query(Business).all()
    counts = Counter(b.status.value for b in rows)
    print(f"\n{len(rows)} businesses in {database_url()}\n")
    for status, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {status:16} {n:>4}")
    waiting = counts.get("SITE_DRAFTED", 0) + counts.get("EMAIL_DRAFTED", 0)
    print(f"\nAwaiting your approval: {waiting}"
          + ("   → run `make api` and open http://127.0.0.1:8090\n" if waiting else "\n"))
    session.close()
    engine.dispose()
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    """Walk QUALIFIED businesses → research → site draft → (if we can find an
    email) outreach draft, so they land at the approval gates."""
    from app.adapters.directory import DirectorySource
    from app.adapters.osm import NominatimSource
    from app.adapters.yelp import YelpSource
    from app.core.config import yelp_api_key
    from app.core.enums import Actor, BusinessStatus
    from app.core.state_machine import advance
    from app.stages.collect import collect_sources

    engine = make_engine(database_url())
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    extractor = PassthroughExtractor()
    fetcher = HttpSiteFetcher()
    # Independent directories make corroboration possible. OSM is free but
    # covers storefronts, not service-area businesses; Yelp covers those but
    # needs a free YELP_API_KEY.
    directories: list[DirectorySource] = ([] if args.no_directories
                                          else [NominatimSource()])
    if not args.no_directories and yelp_api_key():
        directories.append(YelpSource())
    if not args.no_directories and not yelp_api_key():
        print("note: YELP_API_KEY not set — OpenStreetMap only. OSM has poor coverage\n"
              "      of service businesses, so most facts will stay UNVERIFIED.\n")

    pending = (session.query(Business)
               .filter(Business.status == BusinessStatus.QUALIFIED)
               .limit(args.limit).all())
    if not pending:
        print("No QUALIFIED businesses waiting. Run `discover` first, or check `status`.")
        session.close()
        engine.dispose()
        return 0

    print(f"Advancing {len(pending)} qualified lead(s): research → site draft → outreach\n")
    n_site = n_email = 0
    for biz in pending:
        collected = collect_sources(biz, fetcher, directories)
        if collected.contact_email and not biz.contact_email:
            biz.contact_email = collected.contact_email
        dossier = build_dossier(session, biz, collected.sources, extractor,
                                model_version="collect/v1")
        verified = sum(1 for c in dossier.claims if c.status.value == "verified")
        advance(session, biz, BusinessStatus.RESEARCHED, actor=Actor.SYSTEM.value,
                reason=f"dossier built: {len(dossier.claims)} claims, {verified} verified")
        generate_website(session, biz)  # RESEARCHED -> SITE_DRAFTED
        n_site += 1
        session.commit()
        email_note = collected.contact_email or "no public email found — site gate only"
        print(f"  {biz.name[:34]:34} → SITE_DRAFTED   ({email_note})")

    session.close()
    engine.dispose()
    print(f"\n{n_site} site draft(s) awaiting approval"
          + (f", {n_email} email draft(s)" if n_email else "")
          + "\nRun `make api` and open http://127.0.0.1:8090 to review.\n")
    print("Note: the outreach email is drafted automatically when you approve the "
          "site (Gate 1) — approve one in the console and it appears at Gate 2.")
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    try:
        source = get_places_source()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    engine = make_engine(database_url())
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    created = _run(session, source, args.location, args.category)
    _report(session, created)
    session.close()
    engine.dispose()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="run discovery+qualification on a live Frisco set (no key)")
    sub.add_parser("research-demo", help="run research on bundled Frisco dossiers (no key)")
    sub.add_parser("site-demo", help="generate grounded site drafts from bundled data (no key)")
    sub.add_parser("email-demo", help="compose outreach emails from bundled data (no key)")

    p_seed = sub.add_parser("seed", help="populate the API database with bundled data (no key)")
    p_seed.add_argument("--reset", action="store_true", help="wipe existing rows first")

    sub.add_parser("status", help="counts by status in the configured database")
    sub.add_parser("reset", help="wipe the database WITHOUT seeding demo rows")

    p_adv = sub.add_parser("advance", help="research + draft sites for QUALIFIED leads")
    p_adv.add_argument("--limit", type=int, default=5, help="how many to advance")
    p_adv.add_argument("--no-directories", action="store_true",
                       help="skip third-party directory lookups (offline/testing)")

    p_disc = sub.add_parser("discover", help="discover+qualify a real location (needs API key)")
    p_disc.add_argument("location", help='e.g. "Frisco, TX"')
    p_disc.add_argument("--category", default=None, help="optional category filter")

    args = parser.parse_args(argv)
    if args.command == "demo":
        return cmd_demo(args)
    if args.command == "seed":
        return cmd_seed(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "reset":
        return cmd_reset(args)
    if args.command == "advance":
        return cmd_advance(args)
    if args.command == "research-demo":
        return cmd_research_demo(args)
    if args.command == "site-demo":
        return cmd_site_demo(args)
    if args.command == "email-demo":
        return cmd_email_demo(args)
    return cmd_discover(args)


if __name__ == "__main__":
    raise SystemExit(main())
