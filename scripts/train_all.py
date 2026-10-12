"""Unified ML Model Training Runner per Section 8.1.

Runs training stages in dependency order:
1. NER Token Classifier (`scripts/train_ner.py`)
2. Bi-Encoder Semantic Embedding (`scripts/train_biencoder.py`)
3. XGBoost Reranker (`scripts/train_reranker.py`)

Supports `--smoke` for end-to-end pipeline verification without network access or heavy training.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def run_pipeline(stages: list[str], smoke: bool = False) -> None:
    print(f"=== Running ML Pipeline Training (smoke={smoke}) ===")
    print(f"Stages to execute: {', '.join(stages)}\n")

    for stage in stages:
        started = time.perf_counter()
        print(f"--> Stage: {stage.upper()}")

        if stage == "ner":
            try:
                from scripts.train_ner import train_ner
                res = train_ner(
                    train_file="data/ml_training/ner_train.jsonl",
                    output_dir="models/ner_model" if not smoke else "models/smoke_ner",
                    epochs=1 if smoke else 3,
                    batch_size=2 if smoke else 16,
                    smoke_run=smoke,
                )
                elapsed = time.perf_counter() - started
                print(f"    Completed in {elapsed:.2f}s | Result: {res}")
            except (ImportError, RuntimeError, FileNotFoundError) as exc:
                print(f"    Skipped ({exc})")

        elif stage == "biencoder":
            try:
                from scripts.train_biencoder import train_biencoder
                res = train_biencoder(
                    train_file="data/ml_training/biencoder_pairs.jsonl",
                    output_dir="models/biencoder_model" if not smoke else "models/smoke_biencoder",
                    epochs=1 if smoke else 3,
                    batch_size=2 if smoke else 32,
                    smoke_run=smoke,
                )
                elapsed = time.perf_counter() - started
                print(f"    Completed in {elapsed:.2f}s | Result: {res}")
            except (ImportError, RuntimeError, FileNotFoundError) as exc:
                print(f"    Skipped ({exc})")

        elif stage == "reranker":
            try:
                from scripts.train_reranker import generate_smoke_data, train_reranker_from_rows
                if smoke:
                    smoke_rows = generate_smoke_data()
                    auc = train_reranker_from_rows(smoke_rows, output_path="models/smoke_reranker.xgb", n_estimators=10)
                else:
                    pairs_path = Path("data/ml_training/reranker_pairs.jsonl")
                    if not pairs_path.exists():
                        print(f"    Pairs file {pairs_path} not found. Skipping.")
                        continue
                    import json
                    with open(pairs_path, "r", encoding="utf-8") as f:
                        pairs = [json.loads(line) for line in f if line.strip()]
                    auc = train_reranker_from_rows(pairs, output_path="models/reranker.xgb")
                elapsed = time.perf_counter() - started
                print(f"    Completed in {elapsed:.2f}s | Validation AUC: {auc:.4f}")
            except (ImportError, RuntimeError) as exc:
                print(f"    Skipped ({exc})")
        else:
            print(f"    Unknown stage: {stage}")

        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all ML training stages")
    parser.add_argument("--smoke", action="store_true", help="Run quick smoke passes on synthetic data")
    parser.add_argument("--stage", default="ner,biencoder,reranker", help="Comma-separated stage list")
    args = parser.parse_args()

    stages = [s.strip().lower() for s in args.stage.split(",") if s.strip()]
    run_pipeline(stages, smoke=args.smoke)


if __name__ == "__main__":
    main()
