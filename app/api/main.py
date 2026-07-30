"""FastAPI app for the Operator Console.

The console (built with Claude design) talks to these endpoints by swapping its
mock `lib/api.js`; field names match its contract. Read endpoints assemble the
review payload; the site-decision endpoint is Gate 1.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api import schemas, service
from app.core.config import database_url
from app.core.db import make_engine, make_session_factory
from app.core.errors import (
    ApprovalRequiredError,
    NotFoundError,
    StaleContentError,
    TransitionError,
)

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

    return app


app = create_app()
