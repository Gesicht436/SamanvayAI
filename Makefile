.PHONY: setup up down db-reset migrate seed test test-pack lint format check eval eval-gate demo audit-verify verify-claims

setup:
	uv sync

up:
	docker compose up -d

down:
	docker compose down

db-reset:
	uv run python -m db.reset

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m db.seed.seed_foundations

test:
	uv run pytest tests/ -v

test-pack:
	@if [ -z "$(PACK)" ]; then echo "Specify PACK=<name>"; exit 1; fi
	uv run pytest tests/packs/test_$(PACK).py -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint test

eval:
	uv run python scripts/eval_harness.py

eval-gate:
	uv run python scripts/eval_harness.py

demo:
	uv run python -m scripts.seed_clusters
	uv run uvicorn api.main:app --host 0.0.0.0 --port 8000

audit-verify:
	uv run python -m api.core.hashchain_verify

verify-claims:
	uv run python -m scripts.verify_claims
