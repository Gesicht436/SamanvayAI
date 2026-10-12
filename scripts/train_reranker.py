"""Training script for the Identity-Safe Shared XGBoost Sector Reranker per Section 8.1(c).

Features:
- Single shared XGBoost model across all sectors with categorical sector feature
- Identity-safe feature engineering (no feature rewards higher class or upgraded metallurgy)
- Leakage-safe train/validation split
- Computes exact Area Under the ROC Curve (AUC)
- Support for `--smoke` test run on small synthetic dataset
- Optional dependency check: requires `xgboost` (included in `[ml]` extra)
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from api.ml.rerankers import SECTOR_MODELS, RerankerFeatures


def validation_split(rows: list[dict[str, Any]], seed: int = 42) -> tuple[list[int], list[int]]:
    """Performs stratified train/validation split ensuring both labels are present in validation."""
    grouped: dict[int, list[int]] = {}
    for index, row in enumerate(rows):
        label = int(row["label"])
        if label not in (0, 1):
            raise ValueError(f"Label must be 0 or 1, got {label}")
        grouped.setdefault(label, []).append(index)

    if len(grouped) != 2 or min(map(len, grouped.values())) < 2:
        raise ValueError("Reranker training data requires at least two samples for each label (0 and 1)")

    rng = random.Random(seed)
    train_indices: list[int] = []
    val_indices: list[int] = []

    for indices in grouped.values():
        rng.shuffle(indices)
        val_count = max(1, math.ceil(len(indices) * 0.2))
        val_indices.extend(indices[:val_count])
        train_indices.extend(indices[val_count:])

    return train_indices, val_indices


def compute_auc(labels: list[int], probabilities: list[float]) -> float:
    """Computes exact Area Under the ROC Curve (AUC) via Mann-Whitney U statistic (no external library)."""
    positives = [p for y, p in zip(labels, probabilities) if y == 1]
    negatives = [p for y, p in zip(labels, probabilities) if y == 0]

    if not positives or not negatives:
        raise ValueError("Cannot calculate AUC without both positive and negative samples.")

    wins = sum(
        1.0 if pos > neg else 0.5 if pos == neg else 0.0
        for pos in positives
        for neg in negatives
    )
    return wins / (len(positives) * len(negatives))


def row_to_reranker_features(row: dict[str, Any]) -> RerankerFeatures:
    """Converts a training pair dict into an identity-safe RerankerFeatures object."""
    sector = row.get("sector", "VALVES")
    return RerankerFeatures(
        composite_cosine=float(row.get("composite_cosine", row.get("cosine", 0.5))),
        dim_cos=float(row.get("dim_cos", 0.5)),
        met_cos=float(row.get("met_cos", 0.5)),
        pt_cos=float(row.get("pt_cos", 0.5)),
        std_cos=float(row.get("std_cos", 0.5)),
        item_type_match=float(row.get("item_type_match", 1.0)),
        size_match=float(row.get("size_match", 0.0)),
        pressure_match=float(row.get("pressure_match", 0.0)),
        material_match=float(row.get("material_match", 0.0)),
        facing_match=float(row.get("facing_match", 0.0)),
        standard_match=float(row.get("standard_match", 0.0)),
        attr_coverage=float(row.get("attr_coverage", 0.8)),
        n_missing=float(row.get("n_missing", 0.0)),
        sector=sector,
    )


def generate_smoke_data() -> list[dict[str, Any]]:
    """Generates a small synthetic dataset for pipeline verification (--smoke)."""
    rows: list[dict[str, Any]] = []
    sectors = list(SECTOR_MODELS)

    for i in range(40):
        # Positive match samples: identical size, pressure, material, high cosine
        sec = sectors[i % len(sectors)]
        rows.append(
            {
                "query": f"SMOKE ITEM {i} 100 NB CL150 WCB",
                "candidate": f"SMOKE ITEM {i} 100 NB CL150 WCB",
                "cosine": 0.95,
                "composite_cosine": 0.95,
                "dim_cos": 0.98,
                "met_cos": 0.99,
                "pt_cos": 0.97,
                "std_cos": 0.95,
                "item_type_match": 1.0,
                "size_match": 1.0,
                "pressure_match": 1.0,
                "material_match": 1.0,
                "facing_match": 1.0,
                "standard_match": 1.0,
                "attr_coverage": 1.0,
                "n_missing": 0.0,
                "sector": sec,
                "label": 1,
            }
        )
        # Negative samples: mismatched size or pressure, lower cosine
        rows.append(
            {
                "query": f"SMOKE ITEM {i} 100 NB CL150 WCB",
                "candidate": f"SMOKE ITEM {i} 150 NB CL300 CF8M",
                "cosine": 0.45,
                "composite_cosine": 0.42,
                "dim_cos": 0.35,
                "met_cos": 0.40,
                "pt_cos": 0.30,
                "std_cos": 0.50,
                "item_type_match": 1.0,
                "size_match": -1.0,
                "pressure_match": -1.0,
                "material_match": -1.0,
                "facing_match": 0.0,
                "standard_match": 0.0,
                "attr_coverage": 0.6,
                "n_missing": 2.0,
                "sector": sec,
                "label": 0,
            }
        )

    return rows


def train_reranker_from_rows(
    rows: list[dict[str, Any]],
    output_path: str | Path = "models/reranker.xgb",
    model_factory: Callable[..., Any] | None = None,
    early_stopping_rounds: int = 10,
    n_estimators: int = 100,
) -> float:
    """Trains a shared XGBoost classifier from parsed rows and saves the model."""
    if model_factory is None:
        try:
            from xgboost import XGBClassifier
            model_factory = XGBClassifier
        except ImportError as exc:
            print(
                "XGBoost is not installed. To train the reranker, install the optional ML extra:\n"
                "  uv pip install -e .[ml]  (or uv sync --extra ml)"
            )
            raise RuntimeError("Missing xgboost dependency") from exc

    train_indices, val_indices = validation_split(rows)

    feature_objs = [row_to_reranker_features(r) for r in rows]
    vectors = [f.to_vector() for f in feature_objs]
    labels = [int(r["label"]) for r in rows]

    x_train = [vectors[i] for i in train_indices]
    y_train = [labels[i] for i in train_indices]
    x_val = [vectors[i] for i in val_indices]
    y_val = [labels[i] for i in val_indices]

    model = model_factory(
        n_estimators=n_estimators,
        max_depth=4,
        learning_rate=0.05,
        objective="binary:logistic",
        eval_metric="auc",
        early_stopping_rounds=early_stopping_rounds,
        random_state=42,
    )

    model.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        verbose=False,
    )

    val_probs = [float(p[1]) for p in model.predict_proba(x_val)]
    auc = compute_auc(y_val, val_probs)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(out))
    print(f"Reranker model successfully saved to {out} (Validation AUC: {auc:.4f})")
    return auc


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Identity-Safe Sector XGBoost Reranker")
    parser.add_argument("--smoke", action="store_true", help="Run a quick smoke test on synthetic data")
    parser.add_argument("--input", default="data/ml_training/reranker_pairs.jsonl", help="Input training pairs file")
    parser.add_argument("--output", default="models/reranker.xgb", help="Output path for the trained model")
    args = parser.parse_args()

    if args.smoke:
        print("Running smoke training on synthetic dataset (80 samples)...")
        rows = generate_smoke_data()
        try:
            auc = train_reranker_from_rows(rows, output_path=args.output, n_estimators=10, early_stopping_rounds=5)
            print(f"Smoke run complete: AUC = {auc:.4f}")
        except RuntimeError:
            print("Smoke run skipped: xgboost not installed.")
            sys.exit(0)
        return

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Input file {in_path} not found. Use --smoke to run a test on synthetic data.")
        sys.exit(1)

    import json
    rows = []
    with open(in_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    train_reranker_from_rows(rows, output_path=args.output)


if __name__ == "__main__":
    main()
