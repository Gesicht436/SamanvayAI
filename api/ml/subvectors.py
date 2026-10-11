"""Four Domain Subvectors and Vector Recall per Section 8.1.

Encodes golden masters and raw items across four focused attribute domains:
- `dim`: size, schedule, facing, end connection, primary dimension.
- `met`: material grade, product form, coating.
- `pt`: pressure class, temperature rating, electrical rating.
- `std`: design standard, Indian standard, OISD, MESC, EIL references.

Calculates composite cosine similarity using subcategory domain weights:
  composite = sum(w_d * cos_d) / sum(w_d)

Safety Invariants:
- S9, S14: Vector recall (retrieval_method="VECTOR_RECALL") only adds candidates;
  it NEVER raises an item to Tier 1.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any

# Default family domain weights per Section 8.1
DOMAIN_WEIGHTS_BY_FAMILY: dict[str, dict[str, float]] = {
    "VALVES": {"dim": 0.30, "met": 0.30, "pt": 0.25, "std": 0.15},
    "PIPES": {"dim": 0.35, "met": 0.30, "pt": 0.20, "std": 0.15},
    "MOTORS": {"dim": 0.40, "met": 0.15, "pt": 0.25, "std": 0.20},
    "TRANSFORMERS": {"dim": 0.45, "met": 0.15, "pt": 0.20, "std": 0.20},
    "STRUCTURAL": {"dim": 0.50, "met": 0.35, "pt": 0.00, "std": 0.15},
    "REFRACTORIES": {"dim": 0.40, "met": 0.45, "pt": 0.00, "std": 0.15},
    "TYRES": {"dim": 0.55, "met": 0.25, "pt": 0.00, "std": 0.20},
    "PUMPS": {"dim": 0.35, "met": 0.25, "pt": 0.25, "std": 0.15},
}

DEFAULT_DOMAIN_WEIGHTS: dict[str, float] = {"dim": 0.35, "met": 0.30, "pt": 0.20, "std": 0.15}

_DOMAIN_ATTRIBUTE_MAP: dict[str, set[str]] = {
    "dim": {
        "size_nb",
        "size_nb_mm",
        "size_inch",
        "schedule",
        "facing",
        "end_connection",
        "wall_thickness_mm",
        "outer_diameter_mm",
        "length_m",
        "cable_cores",
        "conductor_size_sqmm",
        "frame_size",
        "section_width_in",
        "rim_diameter_in",
        "primary_dimension",
        "flange_rating",
    },
    "met": {
        "body_material",
        "material_grade",
        "product_form",
        "coating",
        "insulation_type",
        "conductor_material",
        "winding_material",
        "trim_material",
        "wetted_parts",
    },
    "pt": {
        "pressure_class",
        "rating_kw",
        "voltage_kv",
        "temperature_rating",
        "power_rating_kva",
        "pressure_bar",
        "rated_rpm",
        "flow_m3hr",
        "head_m",
    },
    "std": {
        "design_standard",
        "indian_standard",
        "oisd_standard",
        "mesc_code",
        "oil_standard",
        "astm_standard",
        "api_standard",
        "is_standard",
        "iec_standard",
        "din_standard",
    },
}


def build_domain_texts(attributes: dict[str, Any]) -> dict[str, str]:
    """Builds short focused texts for the 4 domains from extracted attributes.

    Returns:
        dict with keys 'dim', 'met', 'pt', 'std'.
    """
    domain_texts: dict[str, list[str]] = {"dim": [], "met": [], "pt": [], "std": []}

    for key, val in attributes.items():
        if val is None or val == "":
            continue
        val_str = str(val).strip()
        key_lower = key.lower()

        for domain, attr_set in _DOMAIN_ATTRIBUTE_MAP.items():
            if key_lower in attr_set:
                clean_key = key_lower.replace("_", " ")
                domain_texts[domain].append(f"{clean_key}: {val_str}")
                break

    return {
        domain: "; ".join(parts) if parts else ""
        for domain, parts in domain_texts.items()
    }


class EmbeddingProvider:
    """Deterministic, standard-library feature embedding provider.

    Computes L2-normalized dense embedding vectors (dim=384 or 1024)
    using stable token and character n-gram hashing.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def encode(self, text: str) -> list[float]:
        """Encodes input text into an L2-normalized float vector."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        cleaned = text.strip().lower()
        vec = [0.0] * self.dimension

        tokens = re.findall(r"[a-z0-9]+", cleaned)
        for token in tokens:
            # Word token hash
            h_word = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h_word % self.dimension
            vec[idx] += 1.0

            # Character n-grams (3-grams) for subword matching
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    ngram = token[i : i + 3]
                    h_ng = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
                    vec[h_ng % self.dimension] += 0.5

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    # If vectors are already L2-normalized, dot product is cosine similarity
    return max(-1.0, min(1.0, dot))


def resolve_domain_weights(subcategory: str) -> dict[str, float]:
    """Finds starting domain weights for subcategory family."""
    sub_upper = (subcategory or "").upper()
    for fam_key, weights in DOMAIN_WEIGHTS_BY_FAMILY.items():
        if fam_key in sub_upper:
            return weights.copy()
    return DEFAULT_DOMAIN_WEIGHTS.copy()


def calculate_composite_cosine(
    raw_domain_texts: dict[str, str],
    candidate_domain_texts: dict[str, str],
    subcategory: str,
    embedder: EmbeddingProvider | None = None,
) -> tuple[float, dict[str, float]]:
    """Calculates composite subvector cosine similarity across active domains.

    Score:
      composite = sum(w_d * cos_d) / sum(w_d)
    over active domains. A domain with no extracted attributes gets weight 0
    and the rest are renormalized.
    """
    if embedder is None:
        embedder = EmbeddingProvider()

    weights = resolve_domain_weights(subcategory)
    domain_cosines: dict[str, float] = {}

    active_weight_sum = 0.0
    weighted_cos_sum = 0.0

    for domain in ("dim", "met", "pt", "std"):
        text_a = raw_domain_texts.get(domain, "")
        text_b = candidate_domain_texts.get(domain, "")

        if not text_a or not text_b:
            # Inactive domain: no attributes extracted in one or both
            domain_cosines[domain] = 0.0
            continue

        vec_a = embedder.encode(text_a)
        vec_b = embedder.encode(text_b)
        cos_d = cosine_similarity(vec_a, vec_b)
        domain_cosines[domain] = round(cos_d, 4)

        w = weights.get(domain, 0.0)
        if w > 0.0:
            active_weight_sum += w
            weighted_cos_sum += w * cos_d

    if active_weight_sum > 0.0:
        composite = weighted_cos_sum / active_weight_sum
    else:
        composite = 0.0

    return round(max(0.0, min(1.0, composite)), 4), domain_cosines


@dataclass
class VectorRecallCandidate:
    """Candidate returned via subvector recall."""

    golden_master_id: str
    golden_code: str
    descriptor: str
    composite_cosine: float
    domain_cosines: dict[str, float]
    retrieval_method: str = "VECTOR_RECALL"


def measure_number_limitation_cosine(
    text_a: str = "VALVE GATE 100 NB CL150 WCB FLG RF API600",
    text_b: str = "VALVE GATE 100 NB CL300 WCB FLG RF API600",
) -> dict[str, float]:
    """Computes measured cosine of Class 150 vs Class 300 pair per Section 8.1.

    Demonstrates plainly:
    - Single-vector cosine across the full text is misleadingly high (e.g. >0.90)
      because textual word overlap swamps the single numeric rating token.
    - Subvector setup isolates the 'pt' rating domain, allowing deterministic
      guards to intercept the critical difference.
    """
    embedder = EmbeddingProvider(dimension=384)

    # 1. Single-vector whole text cosine
    vec_a = embedder.encode(text_a)
    vec_b = embedder.encode(text_b)
    single_vec_cosine = cosine_similarity(vec_a, vec_b)

    # 2. Subvector setup
    attrs_a = {
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": "RF",
        "design_standard": "API600",
    }
    attrs_b = {
        "size_nb": 100,
        "pressure_class": "300",
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": "RF",
        "design_standard": "API600",
    }
    dom_a = build_domain_texts(attrs_a)
    dom_b = build_domain_texts(attrs_b)

    composite_cosine_score, domain_cos = calculate_composite_cosine(
        dom_a, dom_b, subcategory="VALVES.GATE", embedder=embedder
    )

    return {
        "single_vector_cosine": round(single_vec_cosine, 4),
        "subvector_composite_cosine": composite_cosine_score,
        "pt_domain_cosine": domain_cos.get("pt", 0.0),
        "dim_domain_cosine": domain_cos.get("dim", 0.0),
        "met_domain_cosine": domain_cos.get("met", 0.0),
        "std_domain_cosine": domain_cos.get("std", 0.0),
    }
