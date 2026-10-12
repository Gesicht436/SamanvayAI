.PHONY: setup up down db-reset migrate seed test test-web test-pack test-mtc test-ml typecheck loadtest lint format check eval eval-gate demo audit-verify verify-claims

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

test-web:
	cd web && npm test

test-pack:
	@if [ -z "$(PACK)" ]; then echo "Specify PACK=<name>"; exit 1; fi
	uv run pytest tests/packs/test_$(PACK).py -v

test-mtc:
	uv run pytest tests/test_mtc_conformance.py -v
	uv run python scripts/eval_mtc_docs.py

test-ml:
	uv run pytest tests/test_ml_layer.py -v

typecheck:
	cd web && npm run build
	uv run ruff check .

loadtest:
	uv run python scripts/load_test.py

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

corpus-eval:
	uv run python scripts/generate_synthetic_docs.py

retrain-scorer:
	uv run python scripts/retrain_scorer.py --eval

