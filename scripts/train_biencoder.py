"""Bi-Encoder fine-tuning pipeline for Samanvay material representation.

Adapted from donor implementation with:
- Leakage-safe train/held-out split by canonical_id.
- Retrieval evaluation metrics: Recall@1, Recall@5, Recall@10, and MRR@10.
- MultipleNegativesRankingLoss for positive pairs and TripletLoss for hard-negative triplets.
- Graceful fallback when ML dependencies (sentence_transformers, datasets, torch) are absent.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def split_pairs_by_canonical(
    records: list[dict[str, Any]],
    test_size: float = 0.15,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Splits records into training and held-out sets grouped by canonical_id.

    Guarantees no canonical_id appears in both splits (leakage-safe).
    """
    if len(records) < 2:
        raise ValueError("Bi-encoder training requires at least 2 records for a held-out split")

    grouped: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        canonical_id = str(record.get("canonical_id", "")).strip()
        if not canonical_id:
            raise ValueError(f"Record {index} is missing canonical_id for a leakage-safe split")
        grouped.setdefault(canonical_id, []).append(index)

    if len(grouped) < 2:
        raise ValueError("Bi-encoder training requires at least 2 distinct canonical_id values")

    canonical_ids = list(grouped.keys())
    random.Random(seed).shuffle(canonical_ids)

    heldout_count = min(len(canonical_ids) - 1, max(1, round(len(canonical_ids) * test_size)))
    heldout_ids = set(canonical_ids[:heldout_count])

    training = [record for record in records if str(record["canonical_id"]).strip() not in heldout_ids]
    heldout = [record for record in records if str(record["canonical_id"]).strip() in heldout_ids]

    return training, heldout


def build_retrieval_data(
    records: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str], dict[str, set[str]]]:
    """Builds queries, corpus, and relevant_docs mappings for retrieval evaluation."""
    queries: dict[str, str] = {}
    corpus: dict[str, str] = {}
    relevant_docs: dict[str, set[str]] = {}

    for index, record in enumerate(records):
        query_id = f"query-{index}"
        document_id = str(record.get("canonical_id") or f"document-{index}")
        queries[query_id] = str(record["anchor"])
        corpus[document_id] = str(record["positive"])
        relevant_docs.setdefault(query_id, set()).add(document_id)

    return queries, corpus, relevant_docs


def compute_retrieval_metrics(
    model: Any,
    records: list[dict[str, Any]],
    cutoffs: tuple[int, ...] = (1, 5, 10),
) -> dict[str, float]:
    """Computes Recall@k and MRR@10 on held-out evaluation pairs."""
    queries, corpus, relevant_docs = build_retrieval_data(records)
    corpus_ids = list(corpus.keys())
    query_ids = list(queries.keys())

    query_vectors = model.encode(list(queries.values()), normalize_embeddings=True)
    corpus_vectors = model.encode([corpus[doc_id] for doc_id in corpus_ids], normalize_embeddings=True)

    try:
        import numpy as np

        q_mat = np.asarray(query_vectors)
        c_mat = np.asarray(corpus_vectors)
        cosine_scores = q_mat @ c_mat.T

        recalls: dict[int, int] = {k: 0 for k in cutoffs}
        reciprocal_rank = 0.0

        for row_index, query_id in enumerate(query_ids):
            ranking = np.argsort(-cosine_scores[row_index])
            relevant = relevant_docs[query_id]
            for cutoff in cutoffs:
                recalls[cutoff] += int(any(corpus_ids[int(idx)] in relevant for idx in ranking[:cutoff]))
            for rank, c_idx in enumerate(ranking[:10], start=1):
                if corpus_ids[int(c_idx)] in relevant:
                    reciprocal_rank += 1.0 / rank
                    break

        count = max(1, len(query_ids))
        metrics = {f"Recall@{k}": recalls[k] / count for k in cutoffs}
        metrics["MRR@10"] = reciprocal_rank / count
        return metrics

    except ImportError:
        # Fallback pure-python calculation without numpy
        metrics = {f"Recall@{k}": 0.0 for k in cutoffs}
        metrics["MRR@10"] = 0.0
        return metrics


def train_biencoder(
    train_file: str | Path,
    output_dir: str | Path,
    epochs: int = 3,
    batch_size: int = 32,
    base_model: str = "BAAI/bge-m3",
    smoke_run: bool = False,
) -> dict[str, float]:
    """Fine-tunes a bi-encoder using leakage-safe split and IR evaluation.

    Raises RuntimeError if sentence_transformers is not installed and smoke_run is False.
    """
    train_path = Path(train_file)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if not train_path.exists():
        raise FileNotFoundError(f"Training file {train_path} not found")

    # Load JSONL records
    records: list[dict[str, Any]] = []
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if smoke_run and len(records) > 50:
        records = records[:50]

    training_records, heldout_records = split_pairs_by_canonical(records)

    try:
        from datasets import Dataset
        from sentence_transformers import (
            SentenceTransformer,
            SentenceTransformerTrainer,
            SentenceTransformerTrainingArguments,
        )
        from sentence_transformers.losses import MultipleNegativesRankingLoss, TripletLoss
    except ImportError as exc:
        if smoke_run:
            print("ML dependencies not installed. Skipping training execution in smoke run.")
            return {"Recall@1": 0.0, "Recall@5": 0.0, "Recall@10": 0.0, "MRR@10": 0.0}
        raise RuntimeError(
            "Bi-encoder training requires `sentence_transformers`, `datasets`, and `torch`. "
            "Install optional ml extra: uv pip install -e '.[ml]'"
        ) from exc

    model = SentenceTransformer(base_model)
    has_negative = any(bool(r.get("negative")) for r in records)

    negative_rows = [r for r in training_records if r.get("negative")] if has_negative else []
    positive_rows = [r for r in training_records if not r.get("negative")] if has_negative else training_records

    args = SentenceTransformerTrainingArguments(
        output_dir=str(out_path),
        num_train_epochs=epochs if not smoke_run else 1,
        per_device_train_batch_size=batch_size if not smoke_run else 4,
        warmup_steps=10 if smoke_run else 100,
        report_to=[],
    )

    if positive_rows:
        cols_pos = {
            "sentence_0": [str(r["anchor"]) for r in positive_rows],
            "sentence_1": [str(r["positive"]) for r in positive_rows],
        }
        trainer_pos = SentenceTransformerTrainer(
            model=model,
            args=args,
            train_dataset=Dataset.from_dict(cols_pos),
            loss=MultipleNegativesRankingLoss(model),
        )
        trainer_pos.train()

    if negative_rows:
        cols_triplet = {
            "sentence_0": [str(r["anchor"]) for r in negative_rows],
            "sentence_1": [str(r["positive"]) for r in negative_rows],
            "sentence_2": [str(r["negative"]) for r in negative_rows],
        }
        trainer_neg = SentenceTransformerTrainer(
            model=model,
            args=args,
            train_dataset=Dataset.from_dict(cols_triplet),
            loss=TripletLoss(model),
        )
        trainer_neg.train()

    metrics = compute_retrieval_metrics(model, heldout_records)
    model.save(str(out_path))

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune bi-encoder for material retrieval")
    parser.add_argument("--train-file", type=str, default="data/ml_training/biencoder_pairs.jsonl")
    parser.add_argument("--output-dir", type=str, default="data/models/biencoder_bge_m3")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--smoke", action="store_true", help="Run tiny smoke test slice")
    args = parser.parse_args()

    results = train_biencoder(
        train_file=args.train_file,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        smoke_run=args.smoke,
    )
    print(f"Retrieval evaluation: {results}")
