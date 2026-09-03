"""FastAPI app for the Operator Console.

The console (built with Claude design) talks to these endpoints by swapping its
mock `lib/api.js`; field names match its contract. Read endpoints assemble the
review payload; the site-decision endpoint is Gate 1.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas, service
from app.core.config import database_url
from app.core.db import make_engine, make_session_factory
from app.core.enums import WebsiteState
from app.core.errors import (
    ApprovalRequiredError,
    ComplianceError,
    NotFoundError,
    StaleContentError,
    TransitionError,
)
from app.models.website import Website
from app.render.site_html import render_site

_session_factory: object | None = None


def get_session() -> Iterator[Session]:
    """DB session per request. Overridden in tests to use the test session."""
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory(make_engine(database_url()))
    session = _session_factory()  # type: ignore[operator]
    try:
        yield session
    finally:
        session.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Local Web Outreach — Operator Console API", version="0.1.0")
    # Dev CORS: the console runs from a local file/preview origin. Tighten before deploy.
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/pipeline", response_model=list[schemas.BusinessSummary])
    def pipeline(session: Session = Depends(get_session)):
        return service.list_pipeline(session)

    @app.get("/api/review-queue", response_model=list[schemas.ReviewItem])
    def review_queue(session: Session = Depends(get_session)):
        return service.list_review_queue(session)

    @app.get("/api/review/{business_id}", response_model=schemas.ReviewItem)
    def review_item(business_id: uuid.UUID, session: Session = Depends(get_session)):
        try:
            return service.get_review_item(session, business_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/businesses/{business_id}", response_model=schemas.BusinessDetail)
    def business_detail(business_id: uuid.UUID, session: Session = Depends(get_session)):
        try:
            return service.get_detail(session, business_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/approvals", response_model=list[schemas.ApprovalOut])
    def approvals(session: Session = Depends(get_session)):
        return service.list_approvals(session)

    def _run_decision(session: Session, fn, business_id, payload):
        """Shared error mapping for the two approval gates."""
        try:
            result = fn(session, business_id, payload)
            session.commit()
            return result
        except NotFoundError as exc:
            session.rollback()
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except StaleContentError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (TransitionError, ApprovalRequiredError) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ComplianceError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/businesses/{business_id}/site-decision",
              response_model=schemas.DecisionResult)
    def site_decision(
        business_id: uuid.UUID,
        payload: schemas.SiteDecisionIn,
        session: Session = Depends(get_session),
    ):
        return _run_decision(session, service.decide_site, business_id, payload)

    @app.post("/api/businesses/{business_id}/email-decision",
              response_model=schemas.DecisionResult)
    def email_decision(
        business_id: uuid.UUID,
        payload: schemas.EmailDecisionIn,
        session: Session = Depends(get_session),
    ):
        return _run_decision(session, service.decide_email, business_id, payload)

    @app.post("/api/businesses/{business_id}/edit-draft",
              response_model=schemas.DraftEditResult)
    def edit_draft(
        business_id: uuid.UUID,
        payload: schemas.DraftEditIn,
        session: Session = Depends(get_session),
    ):
        return _run_decision(session, service.edit_draft, business_id, payload)

    @app.post("/api/claims/{claim_id}/verify", response_model=schemas.Claim)
    def verify_claim(
        claim_id: uuid.UUID,
        payload: schemas.ClaimVerifyIn,
        session: Session = Depends(get_session),
    ):
        return _run_decision(session, service.verify_claim, claim_id, payload)

    @app.get("/preview/{token}", response_class=HTMLResponse)
    def site_preview(token: str, session: Session = Depends(get_session)):
        """Serve a generated site as a real, viewable page.

        This is the link the operator reviews and the prospect eventually opens.
        It is a private proposal: unguessable token, noindex, and clearly marked
        DRAFT until the site is approved.
        """
        site = session.execute(
            select(Website).where(Website.preview_token == token)
        ).scalars().first()
        if site is None:
            raise HTTPException(status_code=404, detail="preview not found")
        html = render_site(site.content_json or {},
                           draft=site.state is not WebsiteState.APPROVED)
        return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow"})

    # Serve the Operator Console (static files) at the root, AFTER the /api routes
    # so they take precedence. `html=True` serves console/index.html at "/".
    console_dir = Path(__file__).resolve().parents[2] / "console"
    if console_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(console_dir), html=True), name="console")

    return app


app = create_app()
