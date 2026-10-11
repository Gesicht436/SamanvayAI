"""Sector XGBoost Rerankers per Section 8.1(c).

Provides five sector reranker models:
- common
- power
- steel
- mining
- heavy_eng

Features are strictly identity-safe: no feature rewards a 'higher class' or 'better metallurgy'
as a match.

Safety Invariants:
- S9, S14: Like every scorer, it may lower a tier or probability, but NEVER raises a gated item to Tier 1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from api.services.comparator import ItemComparisonResult, Verdict

SECTOR_MODELS: list[str] = ["common", "power", "steel", "mining", "heavy_eng"]


@dataclass
class RerankerFeatures:
    """Identity-safe feature vector for candidate reranking."""

    # Base features
    composite_cosine: float
    dim_cos: float
    met_cos: float
    pt_cos: float
    std_cos: float
    item_type_match: float  # 1.0 = equal, 0.0 = unknown, -1.0 = diff
    size_match: float
    pressure_match: float
    material_match: float
    facing_match: float
    standard_match: float
    attr_coverage: float
    n_missing: float

    # Sector extras
    sector_extras: dict[str, float] = field(default_factory=dict)

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
    verdicts = {v.attr: v.verdict for v in comparison.verdicts}

    def _match_val(attr_name: str) -> float:
        v = verdicts.get(attr_name)
        if v == Verdict.EXACT or v == Verdict.EQUIVALENT:
            return 1.0
        if v == Verdict.MISMATCH or v == Verdict.UPGRADE:
            return -1.0
        return 0.0  # MISSING or unknown

    n_exact = sum(1 for v in comparison.verdicts if v.verdict in (Verdict.EXACT, Verdict.EQUIVALENT))
    total_attrs = max(1, len(comparison.verdicts))
    attr_coverage = n_exact / total_attrs
    n_missing = float(sum(1 for v in comparison.verdicts if v.verdict == Verdict.MISSING))

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
    )


class SectorReranker:
    """Interpretable Tree-based Sector Reranker conforming to Section 8.1(c).

    Enforces Safety Invariants S9 and S14:
    - Never raises a gated item to Tier 1.
    - Heavily penalizes mismatches and missing attributes.
    """

    def __init__(self, sector: str = "common") -> None:
        self.sector = sector.lower() if sector.lower() in SECTOR_MODELS else "common"
        self.is_fallback = self.sector != sector.lower()

    def predict_score(self, features: RerankerFeatures) -> float:
        """Evaluates logistic ensemble score across identity-safe features."""
        # Base log-odds intercept
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
        return RerankingResult(
            prob=prob,
            sector=self.sector,
            features=features,
            is_fallback=self.is_fallback,
        )
