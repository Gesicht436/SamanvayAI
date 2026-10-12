# Machine Learning Training Documentation

This document describes the training pipelines, split rules, loss formulations, and reproducibility commands for Samanvay ML models.

---

## 1. Bi-Encoder Representation Model (Section 8.1)

### Architecture
- **Base Pretrained Model**: `BAAI/bge-m3` (dense retrieval, 1024-dim, normalized).
- **Domains**: Encodes material descriptions and domain-specific subvector views (`dim`, `met`, `pt`, `std`).
- **Loss Functions**:
  - Positive pairs: `MultipleNegativesRankingLoss` (in-batch negatives).
  - Hard-negative triplets: `TripletLoss` with margin $m = 0.5$.

### Leakage-Safe Split Rule
1. **Eval Gate Honesty**: Every row in `packs/*/eval/pairs_*.csv` (the locked 170 adversarial pairs) is strictly reserved for release gate evaluation (`scripts/eval_harness.py`). No evaluation pair may ever enter the training set.
2. **Derivation Guard**: `scripts/derive_hard_negatives.py` constructs hard-negative triplets from developer fixtures (`packs/*/fixtures/*.csv`) where negative differs by exactly one critical attribute (`size_nb`, `pressure_class`, `material_grade`, `flange_type`, etc.). Every candidate pair is symmetrically checked against `packs/*/eval/*.csv` and discarded if a collision occurs.
3. **Canonical Grouping**: In `scripts/train_biencoder.py`, the dataset is split by `canonical_id`. All records sharing a canonical identity are placed exclusively into either the train split (85%) or the held-out evaluation split (15%). This ensures zero memorization of specific SKU patterns.

### Full Training Command & Expected Hardware
- **Hardware**: 1x NVIDIA A100 (40GB) or RTX 4090 (24GB), CUDA 12.x.
- **Estimated Time**: ~45 minutes for 3 epochs on 8,000 pairs + derived triplets.
- **Command**:
  ```bash
  uv run python scripts/train_biencoder.py \
    --train-file data/ml_training/hard_negative_triplets.jsonl \
    --output-dir data/models/biencoder_bge_m3 \
    --epochs 3 \
    --batch-size 32
  ```

---

## 2. Token Classifier (NER) (Section 8.2)

### Architecture
- **Base Pretrained Model**: `xlm-roberta-base` token classification head.
- **Token Classes**: Aligned with Samanvay's 12 token classes (`ITEM_TYPE`, `SIZE`, `PRESSURE`, `METALLURGY`, `SCHEDULE`, `FACING`, `STANDARD`, `PRODUCT_FORM`, `COATING`, `MANUFACTURER`, `END_CONN`, `O`).
- **Cross-Validation Rule (Invariant S12)**: NER output is never the sole source of HARD or statutory attributes. Disagreement between NER and deterministic extractors lowers attribute confidence and triggers steward review.

### Full Training Command
- **Hardware**: 1x NVIDIA GPU (16GB VRAM).
- **Estimated Time**: ~25 minutes for 5 epochs.
- **Command**:
  ```bash
  uv run python scripts/train_ner.py \
    --train-file data/ml_training/ner_train.jsonl \
    --output-dir data/models/ner_xlm_roberta \
    --epochs 5 \
    --batch-size 16
  ```

---

## 3. Sector Reranker (Section 8.3)

### Architecture
- **Model**: Gradient boosted decision trees (`xgboost.XGBClassifier`).
- **Safety Invariant S9**: Reranker feature space is strictly identity-safe. No feature rewards an upgraded pressure class or superior metallurgy as a match.
- **Explainability**: Local feature importance via TreeSHAP (`shap.TreeExplainer`) with attribution disclaimer.

### Full Training Command
- **Hardware**: Modern multi-core CPU (8 cores) or CUDA GPU.
- **Estimated Time**: ~5 minutes.
- **Command**:
  ```bash
  uv run python scripts/train_reranker.py \
    --data-dir data/ml_training/reranker \
    --output-dir data/models/reranker_xgboost
  ```
