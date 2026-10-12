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

## 3. Sector Reranker & Explainability (Section 8.3)

### Architecture Decision: Shared XGBoost Model with Sector Feature
- **Model Choice**: Single shared `xgboost.XGBClassifier` across all sectors with categorical `sector_id` feature, rather than 5 disconnected sector models.
- **Rationale**: Piping, valves, fittings, flanges, and electrical materials share identical physical verification principles (sizeNB, rating/class, ASTM metallurgy, standards). A single unified model maximizes training data sample density across common physical interactions while preventing catastrophic overfitting on smaller sectors (e.g. mining or heavy engineering). The `sector_id` feature allows trees to split on sector-specific tolerances where necessary.
- **Identity-Safe Features**: 14 ordered features (`composite_cosine`, `dim_cos`, `met_cos`, `pt_cos`, `std_cos`, `item_type_match`, `size_match`, `pressure_match`, `material_match`, `facing_match`, `standard_match`, `attr_coverage`, `n_missing`, `sector_id`). Upgrades and mismatches yield -1.0, never positive match points.
- **Safety Invariant S9/S14 Enforcement**:
  - Hard physical mismatches clamp output probability to $\le 0.20$.
  - Missing required attributes cap output probability to $\le 0.85$ (strictly below $\tau_{\text{auto}} = 0.95$).
  - Regardless of model score, `assign_tier` strictly enforces that hard attribute mismatches route to Tier 3 and never Tier 1.
- **TreeSHAP Explainability**: Local attribution computed directly from booster margins (`booster.predict(..., pred_contribs=True)`). When no trained model is loaded, the explainer returns an honest `'Attribution unavailable: No trained TreeSHAP model is loaded.'` report preserving the standard disclaimer header, emitting zero fake numbers.

### Active Learning Review Queue
- **Uncertainty Sampling**: $u = 1.0 - \min(1.0, 2 \times |\text{prob} - 0.5|)$. Matches closest to decision boundary are queued first.
- **Safety Rule**: Tier 1 matches are definitive master identities and are never enqueued.
- **Persistence**: Thread-safe queue writes atomically to `data/active_learning_queue.jsonl` with LRU eviction for unresolved items. Resolved expert decisions are exported via `training_examples()` to retrain the reranker.

### Training Commands & Hardware
- **Hardware**: CPU (single modern core sufficient) or CUDA GPU.
- **Estimated Time**: < 30 seconds for 50,000 pair records.
- **Smoke Command**:
  ```bash
  uv run python scripts/train_reranker.py --smoke
  ```
- **Full Training Command**:
  ```bash
  uv run python scripts/train_reranker.py \
    --input data/ml_training/reranker_pairs.jsonl \
    --output models/reranker.xgb
  ```
- **Unified Pipeline Training**:
  ```bash
  uv run python scripts/train_all.py --smoke
  ```
