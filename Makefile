PYTHON ?= python3

.PHONY: fmt lint test test-unit test-integration check

fmt:
	$(PYTHON) -m ruff format .

lint:
	$(PYTHON) -m ruff check .

test: test-unit test-integration

test-unit:
	$(PYTHON) -m pytest tests/unit

test-integration:
	$(PYTHON) -m pytest tests/integration

check:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pytest
