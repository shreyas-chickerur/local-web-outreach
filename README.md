# Local Web Outreach Platform

Fully-audited, human-approved pipeline that finds local businesses with weak/no
websites, researches them to sourced high-confidence dossiers, generates
state-of-the-art sites as private proposals, and runs approved cold outreach →
reply → payment. See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the full
architecture, phases, and invariants.

## Phase 6 — Email Composition + Gate 2 (built)

Compliant, personalized outreach email; the operator approves every one.
- `app/core/compliance.py` — CAN-SPAM footer (physical address + one-step opt-out), subject/footer
  validators, suppression-list check (exact email or domain).
- `app/ai/email_composer.py` — grounded `TemplateEmailComposer` (no key) + injectable `ClaudeEmailComposer`.
- `app/stages/outreach.py` — `compose_email`: SITE_APPROVED + has-email + not-suppressed + CAN-SPAM
  guards; persists a DRAFT `Email`, advances to `EMAIL_DRAFTED`. Nothing is sent (that's Phase 7).
- API: review-queue serves email-gate items; `POST /api/businesses/{id}/email-decision` (Gate 2,
  stale-hash guarded).

```bash
make email-demo    # compose outreach emails from bundled Frisco data — no key
```

## Phase 5 — Operator Console API (built)

FastAPI backend the console talks to (swap its mock `api.js` for these endpoints — field names match).
- Read: `GET /api/pipeline`, `/api/review-queue`, `/api/review/{id}`, `/api/businesses/{id}`, `/api/approvals`.
- Gate 1: `POST /api/businesses/{id}/site-decision` `{decision, approver, expected_content_hash, notes?}` —
  binds a hashed approval to the exact reviewed draft (stale hash → 409), then approve →
  SITE_APPROVED / reject → DISQUALIFIED / request_changes → re-draft, all via the audited state machine.

```bash
make api    # runs uvicorn on :8090 (DATABASE_URL optional; defaults to SQLite)
```

## Phase 4 — Website Generation (built, grounded)

A structured, industry-aware **site content model**, grounded entirely in VERIFIED claims.
- `app/stages/generate.py` — deterministic generator: every rendered fact carries its `claim_id`;
  unverified fields are omitted (flagged "needs confirmation"); reviews/testimonials are never
  fabricated (`validate_site_content` guard). Persists a private DRAFT `Website` (tokenized preview,
  noindex) and advances the business to `SITE_DRAFTED`.

```bash
make site-demo   # generate grounded site drafts from bundled Frisco research — no key
```

## Phase 3 — Research (built, confidence-gated)

Per business, a dossier of atomic, **sourced, confidence-scored** claims.
- `app/stages/entity_resolution.py` — canonicalize the target first; refuse to merge look-alikes.
- `app/stages/research.py` — corroboration engine: ≥2 independent sources → VERIFIED, 1 →
  UNVERIFIED, disagreeing → CONFLICT; unknown required fields → owner questions (never fabricated).
- `app/ai/research_runner.py` — injectable `ClaimExtractor`; `ClaudeClaimExtractor` (`claude-opus-5`)
  for live extraction, `PassthroughExtractor` for the bundled demo.
- `app/ai/validators.py` — hard guard: no claim persists without a `source_url`.

```bash
make research-demo   # runs the pipeline on real Frisco data — no API key
make evals           # capability-A eval: verified facts correct + no fabrication
```

Live extraction needs `ANTHROPIC_API_KEY` in `.env` and a real source collector (deferred).

## Phase 2 — Discovery & Qualification (built)

Location in → scored, geo-gated, de-duplicated qualified leads out.
- `app/adapters/places.py` — places sources (`StubPlacesSource`, `GooglePlacesSource`).
- `app/adapters/site_fetch.py` — the live-site fetcher (`HttpSiteFetcher`).
- `app/stages/discover.py` — geo-gate + dedup + persist as DISCOVERED (audited).
- `app/stages/qualify.py` — **independently probes the live site** (never trusts the source's
  "has website" field), records evidenced weaknesses, scores the opportunity, and advances to
  QUALIFIED / DISQUALIFIED via the spine.

## Phase 1 — Data & Audit Spine (built)

The durable backbone everything else hangs on:

- **State machine** (`app/core/state_machine.py`) — the only sanctioned way to
  change a business's status; refuses illegal transitions and enforces the two
  human approval gates.
- **Hash-chained audit ledger** (`app/core/audit.py`) — append-only,
  tamper-evident record of every transition and approval.
- **Immutable approvals** (`app/core/approvals.py`) — operator sign-offs bound to
  the exact content approved.
- **Append-only enforcement** — application-layer guard on every backend, plus
  PostgreSQL triggers as defense-in-depth (see the Alembic migration).

## Quickstart

```bash
make install     # create .venv (python3.11) and install
make test        # unit + functional (Postgres tests self-skip if no server)
make test-perf   # performance guardrails (prints throughput)
make test-all    # everything, including Postgres-backed tests
```

Postgres tests run automatically when a server is reachable via
`postgresql+psycopg2:///postgres` (override with `TEST_PG_ADMIN_URL`).

## Design invariants

1. No unverified fact ships. 2. No side-effect without a signed approval.
3. Everything is audited (append-only + hash chain). 4. Compliance enforced in
code. 5. Deliverability kill switch. 6. Generated sites are private proposals.

Full detail: [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md).
