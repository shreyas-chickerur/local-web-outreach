PY := .venv/bin/python

.PHONY: install test lint typecheck check brief

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
