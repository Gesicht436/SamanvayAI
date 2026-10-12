"""NER Token Classifier fine-tuning script with BIO alignment and per-label PR reporting.

Reconciles B's 6 label types with A's 12 canonical token classes:
- ITEM_TYPE -> ITEM_TYPE
- SIZE -> SIZE
- PRESSURE_RATING -> PRESSURE
- METALLURGY -> METALLURGY
- FACING_END -> FACING / END_CONN
- STANDARD -> STANDARD
Remaining classes (SCHEDULE, TRIM, RATING_ELEC, OEM_NAME, OEM_PN) supported via extended rules.

Safety Invariant S12:
NER output is never the sole source of a HARD or statutory attribute;
all predictions are cross-checked against deterministic extractors.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# A's 12 canonical token classes
TOKEN_CLASSES = [
    "ITEM_TYPE",
    "SIZE",
    "PRESSURE",
    "METALLURGY",
    "SCHEDULE",
    "FACING",
    "END_CONN",
    "STANDARD",
    "TRIM",
    "RATING_ELEC",
    "OEM_NAME",
    "OEM_PN",
]

# Mapping from B's 6 labels to A's canonical classes
B_TO_A_LABEL_MAPPING = {
    "ITEM_TYPE": "ITEM_TYPE",
    "SIZE": "SIZE",
    "PRESSURE_RATING": "PRESSURE",
    "METALLURGY": "METALLURGY",
    "FACING_END": "FACING",
    "STANDARD": "STANDARD",
}

BIO_LABEL_NAMES = ["O"] + [f"{p}-{cls}" for cls in TOKEN_CLASSES for p in ("B", "I")]
LABEL_TO_ID = {name: i for i, name in enumerate(BIO_LABEL_NAMES)}
ID_TO_LABEL = {i: name for name, i in LABEL_TO_ID.items()}


def map_b_label_to_canonical(label: str, text_span: str = "") -> str:
    """Reconciles B's label name to A's 12 canonical token classes."""
    norm_label = label.strip().upper()
    if norm_label == "FACING_END":
        # Disambiguate facing vs end_connection if span text is known
        text_up = text_span.strip().upper()
        if any(term in text_up for term in ("BW", "SW", "FLG", "THD", "NPT", "THREADED", "SOCKET")):
            return "END_CONN"
        return "FACING"

    return B_TO_A_LABEL_MAPPING.get(norm_label, norm_label if norm_label in TOKEN_CLASSES else "O")


def compute_per_label_metrics(
    true_sequences: list[list[str]],
    pred_sequences: list[list[str]],
    labels: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """Calculates exact per-label Precision, Recall, and F1 on sequence predictions.

    Does not invent or assume metrics; computes strictly from observed counts.
    """
    target_labels = labels or TOKEN_CLASSES

    # Count entity-level TP, FP, FN per class
    stats: dict[str, dict[str, int]] = {
        cls: {"tp": 0, "fp": 0, "fn": 0} for cls in target_labels
    }

    def extract_entities(seq: list[str]) -> set[tuple[str, int, int]]:
        entities: set[tuple[str, int, int]] = set()
        curr_label: str | None = None
        curr_start: int = 0

        for i, tag in enumerate(seq):
            if tag.startswith("B-"):
                if curr_label:
                    entities.add((curr_label, curr_start, i))
                curr_label = tag[2:]
                curr_start = i
            elif tag.startswith("I-"):
                tag_label = tag[2:]
                if curr_label and tag_label == curr_label:
                    continue
                else:
                    if curr_label:
                        entities.add((curr_label, curr_start, i))
                    curr_label = tag_label
                    curr_start = i
            else:  # "O"
                if curr_label:
                    entities.add((curr_label, curr_start, i))
                    curr_label = None

        if curr_label:
            entities.add((curr_label, curr_start, len(seq)))
        return entities

    for true_seq, pred_seq in zip(true_sequences, pred_sequences, strict=False):
        true_ents = extract_entities(true_seq)
        pred_ents = extract_entities(pred_seq)

        for ent in pred_ents:
            cls = ent[0]
            if cls in stats:
                if ent in true_ents:
                    stats[cls]["tp"] += 1
                else:
                    stats[cls]["fp"] += 1

        for ent in true_ents:
            cls = ent[0]
            if cls in stats and ent not in pred_ents:
                stats[cls]["fn"] += 1

    results: dict[str, dict[str, float]] = {}
    f1_sum = 0.0
    active_classes = 0

    for cls in target_labels:
        tp = stats[cls]["tp"]
        fp = stats[cls]["fp"]
        fn = stats[cls]["fn"]

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        results[cls] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
        if (tp + fn) > 0:
            f1_sum += f1
            active_classes += 1

    results["macro_f1"] = round(f1_sum / max(1, active_classes), 4)
    return results


def train_ner(
    train_file: str | Path,
    output_dir: str | Path,
    epochs: int = 3,
    batch_size: int = 16,
    base_model: str = "microsoft/deberta-v3-small",
    smoke_run: bool = False,
) -> dict[str, Any]:
    """Trains NER token classification model and reports held-out per-label PR.

    Raises RuntimeError if transformers/torch is absent and smoke_run is False.
    """
    t_path = Path(train_file)
    o_path = Path(output_dir)
    o_path.mkdir(parents=True, exist_ok=True)

    if not t_path.exists():
        raise FileNotFoundError(f"Training file {t_path} not found")

    records: list[dict[str, Any]] = []
    with open(t_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if smoke_run and len(records) > 40:
        records = records[:40]

    # Split 85% train, 15% held-out test
    split_idx = int(len(records) * 0.85)
    train_records = records[:split_idx]
    eval_records = records[split_idx:]

    try:
        from datasets import Dataset
        from transformers import (
            AutoModelForTokenClassification,
            AutoTokenizer,
            DataCollatorForTokenClassification,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        if smoke_run:
            print("Transformers/torch not installed. Emulating smoke run metrics.")
            mock_metrics = {
                cls: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
                for cls in TOKEN_CLASSES
            }
            mock_metrics["macro_f1"] = 0.0
            return mock_metrics
        raise RuntimeError(
            "NER training requires `transformers` and `torch`. "
            "Install optional ml extra: uv pip install -e '.[ml]'"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(
        base_model,
        num_labels=len(BIO_LABEL_NAMES),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )

    def align_bio(batch: dict[str, list[Any]]) -> dict[str, list[Any]]:
        encoded = tokenizer(batch["text"], truncation=True, return_offsets_mapping=True)
        all_labels: list[list[int]] = []

        for offsets, ents, text_str in zip(encoded["offset_mapping"], batch["labels"], batch["text"], strict=False):
            token_labels = [LABEL_TO_ID["O"]] * len(offsets)
            for ent in ents:
                start = int(ent["start"])
                end = int(ent["end"])
                span_txt = text_str[start:end]
                canon_label = map_b_label_to_canonical(str(ent["label"]), span_txt)

                matched = [
                    idx for idx, (tok_s, tok_e) in enumerate(offsets)
                    if tok_e > start and tok_s < end
                ]
                for pos, tok_idx in enumerate(matched):
                    prefix = "B" if pos == 0 else "I"
                    full_tag = f"{prefix}-{canon_label}"
                    if full_tag in LABEL_TO_ID:
                        token_labels[tok_idx] = LABEL_TO_ID[full_tag]

            all_labels.append(token_labels)

        encoded["labels"] = all_labels
        encoded.pop("offset_mapping")
        return encoded

    train_ds = Dataset.from_list(train_records).map(align_bio, batched=True)
    eval_ds = Dataset.from_list(eval_records).map(align_bio, batched=True)

    args = TrainingArguments(
        output_dir=str(o_path),
        num_train_epochs=epochs if not smoke_run else 1,
        per_device_train_batch_size=batch_size if not smoke_run else 4,
        save_strategy="epoch",
        logging_steps=20,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorForTokenClassification(tokenizer),
    )
    trainer.train()

    # Predict on held-out test split and calculate per-label metrics
    preds_raw = trainer.predict(eval_ds)
    import numpy as np

    pred_ids = np.argmax(preds_raw.predictions, axis=-1)
    true_seqs: list[list[str]] = []
    pred_seqs: list[list[str]] = []

    for p_row, t_row in zip(pred_ids, preds_raw.label_ids, strict=False):
        t_seq = [ID_TO_LABEL[t] for t in t_row if t != -100 and t in ID_TO_LABEL]
        p_seq = [ID_TO_LABEL[p] for p, t in zip(p_row, t_row, strict=False) if t != -100 and p in ID_TO_LABEL]
        true_seqs.append(t_seq)
        pred_seqs.append(p_seq)

    metrics = compute_per_label_metrics(true_seqs, pred_seqs)
    model.save_pretrained(str(o_path))
    tokenizer.save_pretrained(str(o_path))

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune NER token classifier with BIO alignment")
    parser.add_argument("--train-file", type=str, default="data/ml_training/ner_train.jsonl")
    parser.add_argument("--output-dir", type=str, default="data/models/ner_deberta")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--smoke", action="store_true", help="Run tiny smoke test slice")
    cli_args = parser.parse_args()

    results = train_ner(
        train_file=cli_args.train_file,
        output_dir=cli_args.output_dir,
        epochs=cli_args.epochs,
        batch_size=cli_args.batch_size,
        smoke_run=cli_args.smoke,
    )
    print(f"Held-out per-label evaluation: {json.dumps(results, indent=2)}")
