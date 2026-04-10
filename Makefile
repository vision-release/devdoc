UV ?= uv
UV_CACHE_DIR ?= .uv-cache
RUN = UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run

.PHONY: help sync sync-dev fmt fmt-check lint test test-unit test-integration check build release-linux clean

help:
	@printf '%s\n' \
		'make sync            Install base dependencies' \
		'make sync-dev        Install dev dependencies' \
		'make fmt             Format the codebase' \
		'make fmt-check       Check formatting without writing' \
		'make lint            Run Ruff lint checks' \
		'make test            Run all tests' \
		'make test-unit       Run unit tests only' \
		'make test-integration Run integration tests only' \
		'make check           Run formatting check, lint, and tests' \
		'make build           Build source and wheel distributions' \
		'make release-linux   Build the Linux release binary' \
		'make clean           Remove local build artifacts'

sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync

sync-dev:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync --extra dev

fmt:
	$(RUN) ruff format .

fmt-check:
	$(RUN) ruff format --check .

lint:
	$(RUN) ruff check .

test: test-unit test-integration

test-unit:
	$(RUN) pytest tests/unit

test-integration:
	$(RUN) pytest tests/integration

check: fmt-check lint test

build:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) build

release-linux:
	./scripts/build-linux-release.sh

clean:
	rm -rf .uv-cache .pytest_cache .ruff_cache build dist
