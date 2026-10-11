# Machine Learning Extensions (ML Layer)

This directory contains optional machine learning modules for Samanvay.
The layer is disabled by default (`ML_LAYER=off`).
The system is complete and safe without this layer.
You must enable this layer only when release gates pass.

---

## 1. Purpose

The ML layer improves candidate recall on noisy descriptions.
It provides sector-specific candidate ranking.
It never decides identity.
Deterministic rules and Safety Invariants $S1$ to $S15$ decide identity.

---

## 2. Theory and Architecture

### 2.1 Four Domain Subvectors
Material descriptions contain numbers, dimensions, grades, and standards.
Single text embeddings combine these words into one vector.
Numbers receive low weight in standard embeddings.
The subvector setup divides extracted attributes into four domain strings:
- `dim`: Dimensions, size, schedule, facing, end connections.
- `met`: Metallurgy, material grades, product forms.
- `pt`: Pressure classes, temperature ratings, electrical ratings.
- `std`: Design standards, IS codes, API standards.

Each domain text is encoded separately.
Composite cosine similarity is calculated using family weights:
$$\text{Score}_{\text{composite}} = \frac{\sum_{d} w_d \cdot \cos_d}{\sum_{d} w_d}$$
Active domains renormalize when a domain has no extracted attributes.

### 2.2 Sequence Classifier (NER)
`NERExtractor` tags tokens using BIO labels.
It recognizes 12 material token classes:
`ITEM_TYPE`, `SIZE`, `PRESSURE`, `METALLURGY`, `SCHEDULE`, `FACING`, `END_CONN`, `STANDARD`, `TRIM`, `RATING_ELEC`, `OEM_NAME`, `OEM_PN`.
Per Safety Invariant $S12$, NER is never the sole source for a HARD or statutory attribute.

### 2.3 Sector Rerankers
Gradient-boosted decision trees rank candidates for each sector:
- `common`
- `power`
- `steel`
- `mining`
- `heavy_eng`

All features are identity-safe. No feature gives positive score for a higher pressure class or better metallurgy.
Per Safety Invariants $S9$ and $S14$, the scorer can lower a tier or probability, but never raises an item to Tier 1.

### 2.4 TreeSHAP Feature Attribution
Calculates local feature contributions for reranker scores.
Presents explanation bullets with a mandatory header:
`Model score attribution (does not decide the tier)`.
The deterministic attribute diff is the true explanation of the decision.

---

## 3. File Index

| File | Description |
|---|---|
| `__init__.py` | Package exports for subvectors, NER, rerankers, and explainer. |
| `subvectors.py` | Domain text builder, composite cosine scorer, and number limitation measurement. |
| `ner.py` | Sequence classifier interface with BIO token tagging. |
| `rerankers.py` | Sector XGBoost rerankers with identity-safe feature extraction. |
| `explain.py` | TreeSHAP local feature attribution provider. |

---

## 4. Manual Testing

Run the number limitation demonstration script:
```powershell
uv run python scripts/demo_embedding_limitation.py
```

Run test suite:
```powershell
uv run pytest tests/test_ml_layer.py -v
```

Verify that Class 150 vs Class 300 generates Tier 3 Distinct:
```powershell
uv run python -c "from api.ml.subvectors import measure_number_limitation_cosine; print(measure_number_limitation_cosine())"
```

---

## 5. Cross-Links

- Main Specification: [specsheet.md (Section 8.1)](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md)
- Safety Invariants: [api/services/tiering.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/tiering.py)
- Attribute Registry: [api/extractors/registry.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/extractors/registry.py)
- Verification Ledger: [docs/verification.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md)
