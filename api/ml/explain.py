"""TreeSHAP Feature Attribution Explainer per Section 8.1(d).

Computes local feature contributions for the sector reranker and formats them
as plain-language explanation bullets for the diff inspector.

Standard Disclaimer Header:
  'Model score attribution (does not decide the tier)'

The deterministic attribute diff stays the authoritative explanation of the decision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from api.ml.rerankers import RerankerFeatures

logger = logging.getLogger(__name__)

DISCLAIMER_TITLE: str = "Model score attribution (does not decide the tier)"
UNAVAILABLE_MESSAGE: str = "Attribution unavailable: No trained TreeSHAP model is loaded."


@dataclass
class FeatureContribution:
    """Individual feature contribution to the model score."""

    feature_name: str
    contribution: float
    plain_text: str


@dataclass
class AttributionReport:
    """Complete TreeSHAP local attribution report."""

    title: str
    bullets: list[str]
    contributions: list[FeatureContribution]
    base_score: float
    final_score: float


def _format_feature_bullet(feature_name: str, contribution: float, features: RerankerFeatures) -> str:
    """Formats an identity-safe human-readable explanation bullet for a feature contribution."""
    sign_str = f"+{contribution:.2f}" if contribution >= 0 else f"{contribution:.2f}"

    if feature_name == "composite_cosine":
        return f"{sign_str}: Composite domain text similarity ({features.composite_cosine:.2f})"
    if feature_name == "dim_cos":
        return f"{sign_str}: Dimension domain subvector alignment ({features.dim_cos:.2f})"
    if feature_name == "met_cos":
        return f"{sign_str}: Metallurgy domain subvector alignment ({features.met_cos:.2f})"
    if feature_name == "pt_cos":
        return f"{sign_str}: Pressure/rating domain subvector alignment ({features.pt_cos:.2f})"
    if feature_name == "std_cos":
        return f"{sign_str}: Standard subvector alignment ({features.std_cos:.2f})"
    if feature_name == "item_type_match":
        if features.item_type_match > 0:
            return f"{sign_str}: Subcategory/item type matches candidate"
        return f"{sign_str}: Subcategory differs from candidate"
    if feature_name == "size_match":
        if features.size_match > 0:
            return f"{sign_str}: Primary size matches candidate"
        elif features.size_match < 0:
            return f"{sign_str}: Size attribute differs from candidate"
        return f"{sign_str}: Size attribute indeterminate"
    if feature_name == "pressure_match":
        if features.pressure_match > 0:
            return f"{sign_str}: Pressure rating matches candidate"
        elif features.pressure_match < 0:
            return f"{sign_str}: Pressure rating differs from candidate"
        return f"{sign_str}: Pressure rating indeterminate"
    if feature_name == "material_match":
        if features.material_match > 0:
            return f"{sign_str}: Material grade matches candidate"
        elif features.material_match < 0:
            return f"{sign_str}: Material grade differs from candidate"
        return f"{sign_str}: Material grade indeterminate"
    if feature_name == "facing_match":
        if features.facing_match > 0:
            return f"{sign_str}: Flange facing matches candidate"
        elif features.facing_match < 0:
            return f"{sign_str}: Flange facing differs from candidate"
        return f"{sign_str}: Flange facing indeterminate"
    if feature_name == "standard_match":
        if features.standard_match > 0:
            return f"{sign_str}: Design standard matches candidate"
        elif features.standard_match < 0:
            return f"{sign_str}: Design standard differs from candidate"
        return f"{sign_str}: Design standard indeterminate"
    if feature_name == "attr_coverage":
        return f"{sign_str}: Attribute coverage ({features.attr_coverage:.0%})"
    if feature_name == "n_missing":
        return f"{sign_str}: {int(features.n_missing)} required attribute(s) missing"
    if feature_name == "sector_idx":
        return f"{sign_str}: Sector domain alignment ({features.sector})"

    return f"{sign_str}: Feature '{feature_name}'"


class TreeSHAPExplainer:
    """Computes local TreeSHAP attributions and human-readable explanation bullets."""

    def __init__(self, model: Any | None = None, threshold: float = 0.05) -> None:
        self.model = model
        self.threshold = threshold

    def explain(
        self,
        features: RerankerFeatures,
        predicted_prob: float,
        model: Any | None = None,
    ) -> AttributionReport:
        """Calculates feature-level contributions and generates plain-language bullets.

        If a trained XGBoost model is provided, computes real TreeSHAP contributions
        via booster.predict(..., pred_contribs=True).
        If no model is loaded, returns an honest 'Attribution unavailable' report
        with zero fake numbers, preserving the disclaimer header.
        """
        active_model = model or self.model
        if active_model is None:
            return AttributionReport(
                title=DISCLAIMER_TITLE,
                bullets=[UNAVAILABLE_MESSAGE],
                contributions=[],
                base_score=0.50,
                final_score=predicted_prob,
            )

        # Attempt to compute real TreeSHAP contributions from the booster
        try:
            booster = getattr(active_model, "get_booster", lambda: active_model)()
            vec = features.to_vector()

            # Check if xgboost is available for DMatrix
            try:
                import xgboost as xgb
                matrix = xgb.DMatrix([vec])
                contrib_raw = booster.predict(matrix, pred_contribs=True)[0]
            except (ImportError, TypeError, ValueError, AttributeError):
                # Fallback to direct duck-typed predict call on booster/model
                contrib_raw = booster.predict([vec], pred_contribs=True)[0]

            feature_names = features.feature_names()
            # In XGBoost, pred_contribs returns [feat_1, ..., feat_n, bias]
            feat_contribs = contrib_raw[: len(feature_names)]
            bias = float(contrib_raw[-1]) if len(contrib_raw) > len(feature_names) else 0.0

            contributions: list[FeatureContribution] = []
            for name, val in zip(feature_names, feat_contribs):
                fval = float(val)
                if abs(fval) >= self.threshold:
                    bullet = _format_feature_bullet(name, fval, features)
                    contributions.append(
                        FeatureContribution(
                            feature_name=name,
                            contribution=round(fval, 4),
                            plain_text=bullet,
                        )
                    )

            # Sort by absolute contribution descending
            contributions.sort(key=lambda x: abs(x.contribution), reverse=True)

            bullets = [c.plain_text for c in contributions]
            if not bullets:
                bullets = ["No features exceeded the attribution threshold."]

            return AttributionReport(
                title=DISCLAIMER_TITLE,
                bullets=bullets,
                contributions=contributions,
                base_score=round(bias, 4),
                final_score=predicted_prob,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning("TreeSHAP contribution calculation failed: %s", exc)
            return AttributionReport(
                title=DISCLAIMER_TITLE,
                bullets=[f"Attribution unavailable: TreeSHAP computation error ({exc})"],
                contributions=[],
                base_score=0.50,
                final_score=predicted_prob,
            )

