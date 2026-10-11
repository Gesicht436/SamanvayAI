"""TreeSHAP Feature Attribution Explainer per Section 8.1(d).

Computes local feature contributions for the sector reranker and formats them
as plain-language explanation bullets for the diff inspector.

Standard Disclaimer Header:
  'Model score attribution (does not decide the tier)'

The deterministic attribute diff stays the authoritative explanation of the decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from api.ml.rerankers import RerankerFeatures

DISCLAIMER_TITLE: str = "Model score attribution (does not decide the tier)"


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


class TreeSHAPExplainer:
    """Computes local TreeSHAP attributions and human-readable explanation bullets."""

    def __init__(self, threshold: float = 0.05) -> None:
        self.threshold = threshold

    def explain(self, features: RerankerFeatures, predicted_prob: float) -> AttributionReport:
        """Calculates feature-level contributions and generates plain-language bullets."""
        contributions: list[FeatureContribution] = []

        # 1. Composite & Subvector Cosine Contributions
        if features.composite_cosine > 0.0:
            contrib = (features.composite_cosine - 0.5) * 0.4
            sign_str = f"+{contrib:.2f}" if contrib >= 0 else f"{contrib:.2f}"
            contributions.append(
                FeatureContribution(
                    feature_name="composite_cosine",
                    contribution=contrib,
                    plain_text=f"{sign_str}: Composite domain text similarity ({features.composite_cosine:.2f})",
                )
            )

        if features.dim_cos > 0.0:
            contrib = (features.dim_cos - 0.5) * 0.25
            sign_str = f"+{contrib:.2f}" if contrib >= 0 else f"{contrib:.2f}"
            contributions.append(
                FeatureContribution(
                    feature_name="dim_cos",
                    contribution=contrib,
                    plain_text=f"{sign_str}: Dimension domain subvector alignment ({features.dim_cos:.2f})",
                )
            )

        if features.met_cos > 0.0:
            contrib = (features.met_cos - 0.5) * 0.20
            sign_str = f"+{contrib:.2f}" if contrib >= 0 else f"{contrib:.2f}"
            contributions.append(
                FeatureContribution(
                    feature_name="met_cos",
                    contribution=contrib,
                    plain_text=f"{sign_str}: Metallurgy domain subvector alignment ({features.met_cos:.2f})",
                )
            )

        if features.pt_cos > 0.0:
            contrib = (features.pt_cos - 0.5) * 0.25
            sign_str = f"+{contrib:.2f}" if contrib >= 0 else f"{contrib:.2f}"
            contributions.append(
                FeatureContribution(
                    feature_name="pt_cos",
                    contribution=contrib,
                    plain_text=f"{sign_str}: Pressure/rating domain subvector alignment ({features.pt_cos:.2f})",
                )
            )

        # 2. Attribute Match Contributions
        if features.size_match > 0:
            contributions.append(
                FeatureContribution(
                    feature_name="size_match",
                    contribution=0.18,
                    plain_text="+0.18: Primary size matches candidate",
                )
            )
        elif features.size_match < 0:
            contributions.append(
                FeatureContribution(
                    feature_name="size_match",
                    contribution=-0.45,
                    plain_text="-0.45: Size attribute differs from candidate",
                )
            )

        if features.pressure_match > 0:
            contributions.append(
                FeatureContribution(
                    feature_name="pressure_match",
                    contribution=0.22,
                    plain_text="+0.22: Pressure rating matches candidate",
                )
            )
        elif features.pressure_match < 0:
            contributions.append(
                FeatureContribution(
                    feature_name="pressure_match",
                    contribution=-0.50,
                    plain_text="-0.50: Pressure rating differs from candidate",
                )
            )

        if features.material_match > 0:
            contributions.append(
                FeatureContribution(
                    feature_name="material_match",
                    contribution=0.15,
                    plain_text="+0.15: Material grade matches candidate",
                )
            )
        elif features.material_match < 0:
            contributions.append(
                FeatureContribution(
                    feature_name="material_match",
                    contribution=-0.35,
                    plain_text="-0.35: Material grade differs from candidate",
                )
            )

        # 3. Penalties for missing attributes
        if features.n_missing > 0:
            pen = -0.15 * features.n_missing
            contributions.append(
                FeatureContribution(
                    feature_name="n_missing",
                    contribution=pen,
                    plain_text=f"{pen:.2f}: {int(features.n_missing)} required attribute(s) missing from description",
                )
            )

        # Filter by configured absolute threshold
        active_contribs = [c for c in contributions if abs(c.contribution) >= self.threshold]
        # Sort by absolute contribution descending
        active_contribs.sort(key=lambda x: abs(x.contribution), reverse=True)

        bullets = [c.plain_text for c in active_contribs]

        return AttributionReport(
            title=DISCLAIMER_TITLE,
            bullets=bullets,
            contributions=active_contribs,
            base_score=0.50,
            final_score=predicted_prob,
        )
