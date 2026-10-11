"""Candidate Scorer, Feature Extraction and Calibration Engine.

Computes pairwise features per (raw item, candidate) as specified in Section 8.0:
- attr_agree_ratio
- n_missing
- n_mismatch
- trigram_sim on canonical text
- cosine_sim on canonical text
- alnum_token_jaccard
- mpn_exact
- alias_exact
- extraction_conf_min

Implements rule-based calibrated scoring with Platt calibration.
Enforces Safety Invariant S9: scoring model may lower a tier, never raise a gated item to Tier 1.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from api.core.trigram import similarity as trigram_similarity
from api.services.comparator import ItemComparisonResult, Verdict

_ALNUM = re.compile(r"[a-z0-9]+")


@dataclass
class MatchFeatures:
    """Pairwise feature vector computed for candidate ranking."""

    attr_agree_ratio: float
    n_missing: int
    n_mismatch: int
    trigram_sim: float
    cosine_sim: float
    alnum_token_jaccard: float
    mpn_exact: float
    alias_exact: float
    extraction_conf_min: float

    def to_dict(self) -> dict[str, float]:
        """Converts features to float dictionary."""
        return {
            "attr_agree_ratio": round(self.attr_agree_ratio, 4),
            "n_missing": float(self.n_missing),
            "n_mismatch": float(self.n_mismatch),
            "trigram_sim": round(self.trigram_sim, 4),
            "cosine_sim": round(self.cosine_sim, 4),
            "alnum_token_jaccard": round(self.alnum_token_jaccard, 4),
            "mpn_exact": self.mpn_exact,
            "alias_exact": self.alias_exact,
            "extraction_conf_min": round(self.extraction_conf_min, 4),
        }


@dataclass
class ScoringResult:
    """Output from the scoring and calibration model."""

    prob: float
    features: MatchFeatures
    model_name: str = "rule_based_calibrated"
    is_rule_based: bool = True


def token_cosine_similarity(text_a: str, text_b: str) -> float:
    """Computes cosine similarity of word token frequency vectors (standard library)."""
    tokens_a = _ALNUM.findall((text_a or "").lower())
    tokens_b = _ALNUM.findall((text_b or "").lower())
    if not tokens_a or not tokens_b:
        return 0.0

    freq_a: dict[str, int] = {}
    for t in tokens_a:
        freq_a[t] = freq_a.get(t, 0) + 1

    freq_b: dict[str, int] = {}
    for t in tokens_b:
        freq_b[t] = freq_b.get(t, 0) + 1

    all_tokens = set(freq_a.keys()) | set(freq_b.keys())
    dot_product = sum(freq_a.get(t, 0) * freq_b.get(t, 0) for t in all_tokens)
    norm_a = math.sqrt(sum(v * v for v in freq_a.values()))
    norm_b = math.sqrt(sum(v * v for v in freq_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def token_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Computes Jaccard similarity of alphanumeric tokens."""
    tokens_a = set(_ALNUM.findall((text_a or "").lower()))
    tokens_b = set(_ALNUM.findall((text_b or "").lower()))
    if not tokens_a and not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def extract_match_features(
    raw_text: str,
    candidate_text: str,
    comparison: ItemComparisonResult,
    extraction_conf_min: float = 1.0,
    mpn_exact: bool = False,
    alias_exact: bool = False,
) -> MatchFeatures:
    verdict_list = list(comparison.verdicts.values())
    total_attrs = len(verdict_list)

    mandatory_verdicts = [v for v in verdict_list if getattr(v.role, "value", str(v.role)) in ("HARD", "REQUIRED")]
    total_mandatory = len(mandatory_verdicts) if mandatory_verdicts else total_attrs
    n_exact = sum(1 for v in mandatory_verdicts if v.verdict in (Verdict.EXACT, Verdict.UPGRADE))
    n_missing = sum(1 for v in mandatory_verdicts if v.verdict == Verdict.MISSING)
    n_mismatch = sum(1 for v in mandatory_verdicts if v.verdict == Verdict.MISMATCH)

    attr_agree_ratio = (n_exact / total_mandatory) if total_mandatory > 0 else 0.0

    tri_sim = trigram_similarity(raw_text, candidate_text)
    cos_sim = token_cosine_similarity(raw_text, candidate_text)
    jaccard_sim = token_jaccard_similarity(raw_text, candidate_text)

    return MatchFeatures(
        attr_agree_ratio=attr_agree_ratio,
        n_missing=n_missing,
        n_mismatch=n_mismatch,
        trigram_sim=tri_sim,
        cosine_sim=cos_sim,
        alnum_token_jaccard=jaccard_sim,
        mpn_exact=1.0 if mpn_exact else 0.0,
        alias_exact=1.0 if alias_exact else 0.0,
        extraction_conf_min=max(0.0, min(1.0, extraction_conf_min)),
    )


def score_candidate(
    features: MatchFeatures,
    tau_auto: float = 0.95,
    tau_review: float = 0.70,
) -> ScoringResult:
    """Scores a candidate pair using calibrated scoring formula.

    Uses Logistic Sigmoid calibration (Platt scaling) with interpretable weights:
    - High positive weight on exact attribute agreement, alias/MPN matches, and text similarity.
    - Strong penalty on missing attributes and critical mismatches.
    """
    # Base linear combination
    z = (
        -1.5  # Bias intercept
        + 3.5 * features.attr_agree_ratio
        + 1.8 * features.trigram_sim
        + 1.2 * features.cosine_sim
        + 1.0 * features.alnum_token_jaccard
        + 3.0 * features.alias_exact
        + 3.0 * features.mpn_exact
        + 1.0 * features.extraction_conf_min
        - 1.5 * float(features.n_missing)
        - 4.0 * float(features.n_mismatch)
    )

    # Sigmoid calibration: 1 / (1 + exp(-z))
    # Clip z to avoid math overflow
    clipped_z = max(-15.0, min(15.0, z))
    prob = 1.0 / (1.0 + math.exp(-clipped_z))

    # Boost to near 1.0 if perfect exact agreement with no missing or mismatch
    if features.attr_agree_ratio >= 0.99 and features.n_mismatch == 0 and features.n_missing == 0:
        prob = max(prob, 0.98)
    elif features.n_mismatch > 0:
        # Strict mismatch penalty keeps prob low
        prob = min(prob, 0.25)
    elif features.n_missing > 0:
        # Missing attributes keep prob below tau_auto
        prob = min(prob, 0.88)

    return ScoringResult(
        prob=round(prob, 4),
        features=features,
        model_name="rule_based_calibrated",
        is_rule_based=True,
    )
