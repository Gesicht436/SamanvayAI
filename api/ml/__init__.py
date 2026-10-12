"""Optional Machine Learning Layer Package per Section 8.1.

Exports:
- subvectors: 4 domain subvectors, composite cosine scorer, vector recall, and number limitation measurement.
- ner: NER token classifier interface with BIO sequence tagging.
- rerankers: Sector XGBoost rerankers with identity-safe features and invariant S9/S14 guards.
- explain: TreeSHAP local feature attribution reporter with disclaimer header.
"""

from api.ml.active_learning import (
    ActiveLearningItem,
    ActiveLearningQueue,
    get_active_learning_queue,
)
from api.ml.explain import AttributionReport, FeatureContribution, TreeSHAPExplainer
from api.ml.ner import NERExtractor, TokenSpan
from api.ml.rerankers import (
    RerankerFeatures,
    RerankingResult,
    SectorReranker,
    build_reranker_features,
)
from api.ml.subvectors import (
    EmbeddingProvider,
    VectorRecallCandidate,
    build_domain_texts,
    calculate_composite_cosine,
    measure_number_limitation_cosine,
    resolve_domain_weights,
)

__all__ = [
    "ActiveLearningItem",
    "ActiveLearningQueue",
    "AttributionReport",
    "EmbeddingProvider",
    "FeatureContribution",
    "NERExtractor",
    "RerankerFeatures",
    "RerankingResult",
    "SectorReranker",
    "TokenSpan",
    "TreeSHAPExplainer",
    "VectorRecallCandidate",
    "build_domain_texts",
    "build_reranker_features",
    "calculate_composite_cosine",
    "get_active_learning_queue",
    "measure_number_limitation_cosine",
    "resolve_domain_weights",
]
