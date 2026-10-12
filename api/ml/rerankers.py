"""Sector XGBoost Rerankers per Section 8.1(c).

Provides five sector reranker models:
- common
- power
- steel
- mining
- heavy_eng

Architecture Choice:
One shared XGBoost model with a categorical sector feature encoding.
Reason: Maximizes statistical representation transfer on shared physical properties
(size, pressure, materials, standards) across all material families, while preventing
overfitting on small sector slices. Sector-specific nuances are preserved through
sector extra features.

Identity-Safety Guarantee:
Features are strictly identity-safe: no feature rewards a 'higher class' or 'better metallurgy'
as a match. Upgrade items receive negative verdicts (-1.0), never positive match points.

Safety Invariants:
- S9, S14: Like every scorer, it may lower a tier or probability, but NEVER raises a gated item to Tier 1.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.services.comparator import ItemComparisonResult, Verdict

logger = logging.getLogger(__name__)

SECTOR_MODELS: list[str] = ["common", "power", "steel", "mining", "heavy_eng"]
SECTOR_TO_ID: dict[str, float] = {s: float(i) for i, s in enumerate(SECTOR_MODELS)}


@dataclass
class RerankerFeatures:
    """Identity-safe feature vector for candidate reranking."""

    # Base features
    composite_cosine: float = 0.0
    dim_cos: float = 0.0
    met_cos: float = 0.0
    pt_cos: float = 0.0
    std_cos: float = 0.0
    item_type_match: float = 0.0  # 1.0 = equal, 0.0 = unknown, -1.0 = diff
    size_match: float = 0.0
    pressure_match: float = 0.0
    material_match: float = 0.0
    facing_match: float = 0.0
    standard_match: float = 0.0
    attr_coverage: float = 0.0
    n_missing: float = 0.0

    # Sector extras
    sector_extras: dict[str, float] = field(default_factory=dict)
    sector: str = "common"

    @classmethod
    def feature_names(cls) -> list[str]:
        return [
            "composite_cosine",
            "dim_cos",
            "met_cos",
            "pt_cos",
            "std_cos",
            "item_type_match",
            "size_match",
            "pressure_match",
            "material_match",
            "facing_match",
            "standard_match",
            "attr_coverage",
            "n_missing",
            "sector_id",
        ]

    def to_vector(self) -> list[float]:
        """Returns ordered float vector for XGBoost model inference."""
        sec_id = SECTOR_TO_ID.get(self.sector.lower(), 0.0)
        return [
            float(self.composite_cosine),
            float(self.dim_cos),
            float(self.met_cos),
            float(self.pt_cos),
            float(self.std_cos),
            float(self.item_type_match),
            float(self.size_match),
            float(self.pressure_match),
            float(self.material_match),
            float(self.facing_match),
            float(self.standard_match),
            float(self.attr_coverage),
            float(self.n_missing),
            sec_id,
        ]

    def to_dict(self) -> dict[str, float]:
        """Flattens feature dictionary for SHAP and tree attribution."""
        base: dict[str, float] = {
            "composite_cosine": round(self.composite_cosine, 4),
            "dim_cos": round(self.dim_cos, 4),
            "met_cos": round(self.met_cos, 4),
            "pt_cos": round(self.pt_cos, 4),
            "std_cos": round(self.std_cos, 4),
            "item_type_match": self.item_type_match,
            "size_match": self.size_match,
            "pressure_match": self.pressure_match,
            "material_match": self.material_match,
            "facing_match": self.facing_match,
            "standard_match": self.standard_match,
            "attr_coverage": round(self.attr_coverage, 4),
            "n_missing": self.n_missing,
            "sector_id": SECTOR_TO_ID.get(self.sector.lower(), 0.0),
        }
        for k, v in self.sector_extras.items():
            base[f"extra_{k}"] = round(v, 4)
        return base


@dataclass
class RerankingResult:
    """Output from the sector reranker model."""

    prob: float
    sector: str
    features: RerankerFeatures
    is_fallback: bool
    is_model_fallback: bool = False
    fallback_reason: str | None = None
    model_name: str = "xgboost_sector_reranker"


def build_reranker_features(
    comparison: ItemComparisonResult,
    composite_cosine: float = 0.0,
    domain_cosines: dict[str, float] | None = None,
    sector: str = "common",
    raw_attrs: dict[str, Any] | None = None,
    candidate_attrs: dict[str, Any] | None = None,
) -> RerankerFeatures:
    """Extracts identity-safe features from comparison verdicts and subvectors."""
    dom_cos = domain_cosines or {}
    verdicts = {attr: res.verdict for attr, res in comparison.verdicts.items()}

    def _match_val(attr_name: str) -> float:
        v = verdicts.get(attr_name)
        if v == Verdict.EXACT:
            return 1.0
        if v in (Verdict.MISMATCH, Verdict.UPGRADE):
            return -1.0
        return 0.0  # MISSING or unknown

    n_exact = sum(1 for res in comparison.verdicts.values() if res.verdict == Verdict.EXACT)
    total_attrs = max(1, len(comparison.verdicts))
    attr_coverage = n_exact / total_attrs
    n_missing = float(sum(1 for res in comparison.verdicts.values() if res.verdict == Verdict.MISSING))

    # Sector specific extras
    extras: dict[str, float] = {}
    r_attrs = raw_attrs or {}
    c_attrs = candidate_attrs or {}

    sec_lower = (sector or "common").lower()
    if "power" in sec_lower:
        extras["vector_group_equal"] = 1.0 if r_attrs.get("vector_group") == c_attrs.get("vector_group") and r_attrs.get("vector_group") else 0.0
        extras["winding_match"] = 1.0 if r_attrs.get("winding_material") == c_attrs.get("winding_material") and r_attrs.get("winding_material") else 0.0
    elif "steel" in sec_lower:
        extras["form_equal"] = 1.0 if r_attrs.get("product_form") == c_attrs.get("product_form") and r_attrs.get("product_form") else 0.0
        extras["bond_match"] = 1.0 if r_attrs.get("bond_type") == c_attrs.get("bond_type") and r_attrs.get("bond_type") else 0.0
    elif "mining" in sec_lower:
        extras["rim_match"] = 1.0 if r_attrs.get("rim_diameter_in") == c_attrs.get("rim_diameter_in") and r_attrs.get("rim_diameter_in") else 0.0
        extras["tread_code_equal"] = 1.0 if r_attrs.get("tread_code") == c_attrs.get("tread_code") and r_attrs.get("tread_code") else 0.0
    elif "heavy_eng" in sec_lower:
        extras["pump_type_equal"] = 1.0 if r_attrs.get("pump_type") == c_attrs.get("pump_type") and r_attrs.get("pump_type") else 0.0
        extras["seal_plan_match"] = 1.0 if r_attrs.get("seal_plan") == c_attrs.get("seal_plan") and r_attrs.get("seal_plan") else 0.0

    return RerankerFeatures(
        composite_cosine=composite_cosine,
        dim_cos=dom_cos.get("dim", 0.0),
        met_cos=dom_cos.get("met", 0.0),
        pt_cos=dom_cos.get("pt", 0.0),
        std_cos=dom_cos.get("std", 0.0),
        item_type_match=_match_val("item_type"),
        size_match=_match_val("size_nb"),
        pressure_match=_match_val("pressure_class"),
        material_match=_match_val("body_material"),
        facing_match=_match_val("facing"),
        standard_match=_match_val("design_standard"),
        attr_coverage=attr_coverage,
        n_missing=n_missing,
        sector_extras=extras,
        sector=sec_lower,
    )


class SectorReranker:
    """Interpretable Tree-based Sector Reranker conforming to Section 8.1(c).

    Enforces Safety Invariants S9 and S14:
    - Never raises a gated item to Tier 1.
    - Heavily penalizes mismatches and missing attributes.
    """

    def __init__(
        self,
        sector: str = "common",
        model_path: str | Path | None = None,
        model: Any = None,
    ) -> None:
        self.sector = sector.lower() if sector.lower() in SECTOR_MODELS else "common"
        self.is_fallback: bool = self.sector != sector.lower()
        self.model = model
        self.is_model_fallback: bool = self.model is None
        self.fallback_reason: str | None = None

        if self.model is None and model_path is not None and Path(model_path).exists():
            try:
                from xgboost import XGBClassifier

                self.model = XGBClassifier()
                self.model.load_model(str(model_path))
                self.is_model_fallback = False
            except Exception as exc:  # noqa: BLE001
                self.model = None
                self.is_model_fallback = True
                self.fallback_reason = "ML_MODEL_UNAVAILABLE"
                logger.info("SectorReranker falling back to formula: %s", exc)
        elif self.model is None:
            self.is_model_fallback = True
            self.fallback_reason = "ML_MODEL_UNAVAILABLE"

    def predict_score(self, features: RerankerFeatures) -> float:
        """Evaluates model score across identity-safe features."""
        # 1. Real XGBoost model if loaded
        if self.model is not None:
            try:
                vec = features.to_vector()
                raw_prob = float(self.model.predict_proba([vec])[0][1])
                prob = max(0.0, min(1.0, raw_prob))

                # Hard guardrails: S9, S14
                # An ML score can never override a HARD attribute mismatch
                if features.size_match < 0 or features.pressure_match < 0 or features.material_match < 0:
                    prob = min(prob, 0.20)
                elif features.n_missing > 0:
                    prob = min(prob, 0.85)

                return round(prob, 4)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Trained model prediction failed, falling back to formula: %s", exc)

        # 2. Interpretable logistic formula fallback
        z = -1.2

        # Weighted contributions from identity-safe features
        z += 2.8 * features.composite_cosine
        z += 1.5 * features.dim_cos
        z += 1.2 * features.met_cos
        z += 1.5 * features.pt_cos
        z += 0.8 * features.std_cos

        # Attribute agreement boosts
        z += 1.5 * features.size_match
        z += 1.8 * features.pressure_match
        z += 1.4 * features.material_match
        z += 0.8 * features.facing_match
        z += 1.0 * features.standard_match
        z += 2.0 * features.attr_coverage

        # Severe penalty on missing attributes and critical mismatches
        z -= 1.8 * features.n_missing

        # Penalize negative matches heavily
        if features.size_match < 0:
            z -= 5.0
        if features.pressure_match < 0:
            z -= 6.0
        if features.material_match < 0:
            z -= 4.0

        # Sector extras contributions
        for extra_val in features.sector_extras.values():
            z += 0.5 * extra_val

        # Logistic sigmoid calibration
        clipped_z = max(-15.0, min(15.0, z))
        prob = 1.0 / (1.0 + math.exp(-clipped_z))

        # Hard guardrails: S9, S14
        # If any core attribute is mismatched, score cannot exceed 0.20
        if features.size_match < 0 or features.pressure_match < 0 or features.material_match < 0:
            prob = min(prob, 0.20)
        elif features.n_missing > 0:
            # Missing attributes cap score below auto threshold (0.95)
            prob = min(prob, 0.85)

        return round(prob, 4)

    def rerank(self, features: RerankerFeatures) -> RerankingResult:
        """Executes reranking prediction with sector provenance."""
        prob = self.predict_score(features)
        model_name = "xgboost_sector_reranker" if self.model is not None else "fallback_formula"
        return RerankingResult(
            prob=prob,
            sector=self.sector,
            features=features,
            is_fallback=self.is_fallback,
            is_model_fallback=self.is_model_fallback,
            fallback_reason=self.fallback_reason,
            model_name=model_name,
        )
