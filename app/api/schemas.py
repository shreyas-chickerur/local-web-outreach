"""Response/request models for the Operator Console API.

Field names deliberately mirror the frontend's ``api.js`` contract (snake_case:
opportunity_score, claim_id, needs_confirmation, source_url, content_hash) so the
console swaps its mock module for these endpoints without renaming anything.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class BusinessSummary(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    category: str | None
    status: str
    opportunity_score: int | None
    has_site: bool | None
    why: str  # latest transition reason, from the audit trail


class Weakness(BaseModel):
    issue: str
    severity: str
    evidence: str | None


class Claim(BaseModel):
    id: uuid.UUID
    field: str
    value: str | None
    status: str
    confidence: float
    corroborations: int
    sources: list[dict[str, Any]]
    # Set when a human vouched for it — the console shows who and when.
    verified_by: str | None = None
    verified_at: datetime | None = None
    verified_note: str | None = None
    ships_as_fact: bool = False


class WebsiteOut(BaseModel):
    version: int
    state: str
    preview_url: str
    content_hash: str
    content: dict[str, Any]  # the site content_json
    needs_confirmation: list[str]


class AuditItem(BaseModel):
    ts: str
    actor: str
    action: str          # raw machine action, shown as subtext
    title: str           # human-readable headline for this step
    reason: str | None


class EmailOut(BaseModel):
    id: uuid.UUID
    kind: str
    recipient: str
    subject: str
    body: str
    footer: str
    status: str
    content_hash: str


class ReviewItem(BaseModel):
    business: BusinessSummary
    address: str | None
    phone: str | None
    why: str
    weaknesses: list[Weakness]
    dossier: list[Claim]
    questions: list[str]
    website: WebsiteOut | None
    email: EmailOut | None
    gate: Literal["site", "email"]
    transition: str  # e.g. "SITE_DRAFTED → SITE_APPROVED"


class BusinessDetail(BaseModel):
    business: BusinessSummary
    address: str | None
    phone: str | None
    existing_site_url: str | None
    weaknesses: list[Weakness]
    dossier: list[Claim]
    websites: list[WebsiteOut]
    audit: list[AuditItem]


class ApprovalOut(BaseModel):
    id: uuid.UUID
    subject_type: str
    subject_id: uuid.UUID
    business_name: str | None
    decision: str
    approver: str
    content_hash: str | None
    notes: str | None
    decided_at: datetime


class SiteDecisionIn(BaseModel):
    decision: Literal["approve", "reject", "request_changes"]
    approver: str = "operator"
    # The content hash the operator actually reviewed — must match the current
    # draft, or the approval is rejected as stale.
    expected_content_hash: str
    notes: str | None = None


class EmailDecisionIn(BaseModel):
    decision: Literal["approve", "reject", "request_changes"]
    approver: str = "operator"
    expected_content_hash: str  # must match the current draft email, or 409 stale
    notes: str | None = None


class DraftEditIn(BaseModel):
    """An operator edit to the draft at the current gate. Not a gate decision:
    it changes no status and records no approval, but it re-hashes the draft."""

    subject_type: Literal["site", "email"]
    editor: str = "operator"
    # site edits
    heading: str | None = None
    subheading: str | None = None
    # email edits
    subject: str | None = None
    body: str | None = None


class DraftEditResult(BaseModel):
    ok: bool
    business_id: uuid.UUID
    gate: Literal["site", "email"]
    content_hash: str  # the NEW hash — the operator must approve against this


class ClaimVerifyIn(BaseModel):
    """A human vouching for a claim the machine could not corroborate."""

    verifier: str = "operator"
    # Optional corrected value — an operator checking a CONFLICT usually knows
    # which of the two candidates is right.
    value: str | None = None
    note: str | None = None


class DecisionResult(BaseModel):
    ok: bool
    business_id: uuid.UUID
    new_status: str
    approval_id: uuid.UUID
