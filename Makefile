PY := .venv/bin/python

.PHONY: install test lint typecheck check brief design ui

install:
	python3.11 -m venv .venv
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check app tests

typecheck:
	.venv/bin/mypy app

check: lint typecheck test

# Research one company: make brief Q="Craftway Kitchen, Frisco, TX"
brief:
	$(PY) -m app.cli brief "$(Q)"

# One design run for a lead from a prompt; a new version, its cost recorded.
# make design LEAD=8 PROMPT=prompts/fish-shack/v2.md
design:
	$(PY) -m app.design.bridge $(LEAD) "$(PROMPT)"

# The workbench UI: http://127.0.0.1:8099
ui:
	$(PY) -m app.web.server
