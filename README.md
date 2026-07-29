# Local Web Outreach Platform

Fully-audited, human-approved pipeline that finds local businesses with weak/no
websites, researches them to sourced high-confidence dossiers, generates
state-of-the-art sites as private proposals, and runs approved cold outreach →
reply → payment. See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the full
architecture, phases, and invariants.

## Phase 1 — Data & Audit Spine (this repo, so far)

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
