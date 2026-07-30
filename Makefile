# Local Web Outreach — developer tasks
PY := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: venv install test test-unit test-func test-perf test-pg test-all cov lint typecheck migrate clean demo discover research-demo site-demo email-demo evals api

venv:
	python3.11 -m venv .venv
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -e ".[dev]"

# Fast suite: unit + functional (Postgres tests self-skip when no server).
test:
	$(PYTEST) -m "unit or functional"

test-unit:
	$(PYTEST) -m unit

test-func:
	$(PYTEST) -m functional

test-perf:
	$(PYTEST) -m performance -s

# Everything, including Postgres-backed tests.
test-all:
	$(PYTEST)

# Force the Postgres-only tests (fails loudly if no server, unlike the skips).
test-pg:
	$(PYTEST) -m postgres

# Coverage report (misses highlighted).
cov:
	$(PYTEST) --cov=app --cov=evals --cov-report=term-missing

lint:
	.venv/bin/ruff check app tests

typecheck:
	.venv/bin/mypy app

migrate:
	.venv/bin/alembic upgrade head

# Live demo on a real Frisco set — no API key required.
demo:
	$(PY) -m app.cli demo

# Real run. Usage: make discover LOCATION="Frisco, TX" CATEGORY=restaurant
discover:
	$(PY) -m app.cli discover "$(LOCATION)" $(if $(CATEGORY),--category "$(CATEGORY)")

# Research pipeline on bundled real Frisco data — no API key required.
research-demo:
	$(PY) -m app.cli research-demo

# Generate grounded site drafts from bundled Frisco research — no API key.
site-demo:
	$(PY) -m app.cli site-demo

# Compose outreach emails from bundled Frisco research — no API key.
email-demo:
	$(PY) -m app.cli email-demo

# Capability evals: A (research), B (site grounding), C (email compliance).
evals:
	$(PY) -m evals.research_eval
	$(PY) -m evals.site_eval
	$(PY) -m evals.email_eval

# Operator Console API (Phase 5). Set DATABASE_URL for a real DB; defaults to SQLite.
api:
	$(PY) -m uvicorn app.api.main:app --reload --port 8090

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache *.db
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
