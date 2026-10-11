"""Unit and property tests for optional ML extensions (Section 8.1)."""

import pytest

from api.config import get_settings
from api.ml.explain import DISCLAIMER_TITLE, TreeSHAPExplainer
from api.ml.ner import NERExtractor
from api.ml.rerankers import (
    RerankerFeatures,
    SectorReranker,
)
from api.ml.subvectors import (
    EmbeddingProvider,
    build_domain_texts,
    calculate_composite_cosine,
    cosine_similarity,
    measure_number_limitation_cosine,
    resolve_domain_weights,
)
from api.services.candidates import RetrievedCandidate, retrieve_candidates_in_memory


def test_build_domain_texts() -> None:
    """Tests attribute extraction mapping into four distinct domain texts."""
    attrs = {
        "size_nb": 100,
        "end_connection": "FLANGED",
        "facing": "RAISED_FACE",
        "body_material": "A216_WCB",
        "product_form": "CAST",
        "pressure_class": "ASME_150",
        "design_standard": "API_600",
        "indian_standard": "IS_1239",
    }
    domain_texts = build_domain_texts(attrs)

    assert "size nb: 100" in domain_texts["dim"]
    assert "facing: RAISED_FACE" in domain_texts["dim"]
    assert "body material: A216_WCB" in domain_texts["met"]
    assert "pressure class: ASME_150" in domain_texts["pt"]
    assert "design standard: API_600" in domain_texts["std"]
    assert "indian standard: IS_1239" in domain_texts["std"]


def test_embedding_provider_and_cosine() -> None:
    """Tests L2-normalized dense embeddings and cosine similarity properties."""
    provider = EmbeddingProvider(dimension=384)
    v1 = provider.encode("VALVE GATE 100 NB")
    v2 = provider.encode("VALVE GATE 100 NB")
    v3 = provider.encode("TRANSFORMER POWER 11KV")

    assert len(v1) == 384
    # Identical string yields unit cosine
    assert pytest.approx(cosine_similarity(v1, v2), abs=1e-4) == 1.0
    # Dissimilar strings have low cosine similarity
    assert cosine_similarity(v1, v3) < 0.50


def test_domain_weights_and_composite_cosine() -> None:
    """Tests domain weight resolution and active domain renormalization."""
    weights_valves = resolve_domain_weights("VALVES.GATE")
    assert weights_valves["dim"] == 0.30
    assert weights_valves["pt"] == 0.25

    weights_structural = resolve_domain_weights("STRUCTURAL.BEAM")
    assert weights_structural["pt"] == 0.00  # Structural carries no pressure rating

    # Active domain renormalization
    dom_a = {"dim": "size nb: 100", "met": "body material: WCB", "pt": "", "std": ""}
    dom_b = {"dim": "size nb: 100", "met": "body material: WCB", "pt": "", "std": ""}
    score, domain_cos = calculate_composite_cosine(dom_a, dom_b, subcategory="VALVES.GATE")
    assert score == 1.0
    assert domain_cos["dim"] == 1.0
    assert domain_cos["met"] == 1.0
    assert domain_cos["pt"] == 0.0


def test_number_limitation_demonstration() -> None:
    """Tests measured cosine calculation for Class 150 vs Class 300 pair (computed, never typed)."""
    res = measure_number_limitation_cosine()

    # Whole text cosine is high (>0.80) due to word overlap
    assert res["single_vector_cosine"] > 0.80
    # Pressure domain captures the rating divergence
    assert res["pt_domain_cosine"] < 1.0
    # Composite cosine is computed dynamically
    assert 0.0 < res["subvector_composite_cosine"] <= 1.0


def test_ner_extractor_bio_tagging() -> None:
    """Tests NER sequence classifier with BIO tagging across token classes."""
    extractor = NERExtractor()
    sample = "VALVE GATE 100 NB CL150 WCB RF FLG API600"
    spans = extractor.tokenize_and_tag(sample)

    labels = {s.label for s in spans}
    assert "ITEM_TYPE" in labels
    assert "SIZE" in labels
    assert "PRESSURE" in labels
    assert "METALLURGY" in labels
    assert "STANDARD" in labels

    # Check BIO tag prefixes
    assert any(s.bio_tag.startswith("B-") for s in spans)

    attrs = extractor.extract_attributes(sample)
    assert attrs["pressure"].source == "ner"
    assert "CL150" in attrs["pressure"].value


def test_sector_reranker_and_fallback() -> None:
    """Tests sector reranker scoring, identity-safe features, and sector fallback."""
    # Common sector reranker
    reranker_common = SectorReranker(sector="common")
    assert not reranker_common.is_fallback

    # Fallback to common for unknown sector
    reranker_unknown = SectorReranker(sector="aerospace_unknown")
    assert reranker_unknown.is_fallback
    assert reranker_unknown.sector == "common"

    # Perfect match features
    perfect_features = RerankerFeatures(
        composite_cosine=1.0,
        dim_cos=1.0,
        met_cos=1.0,
        pt_cos=1.0,
        std_cos=1.0,
        item_type_match=1.0,
        size_match=1.0,
        pressure_match=1.0,
        material_match=1.0,
        facing_match=1.0,
        standard_match=1.0,
        attr_coverage=1.0,
        n_missing=0.0,
    )
    score_perfect = reranker_common.predict_score(perfect_features)
    assert score_perfect >= 0.95


def test_safety_invariants_s9_s14_in_reranker() -> None:
    """Enforces Safety Invariants S9 and S14:

    Reranker score may lower probability or tier, but NEVER raises a gated item to Tier 1.
    A mismatch on size, pressure class, or material is severely capped (<= 0.20).
    """
    reranker = SectorReranker(sector="power")

    # Critical pressure mismatch
    mismatch_features = RerankerFeatures(
        composite_cosine=0.92,
        dim_cos=1.0,
        met_cos=1.0,
        pt_cos=0.3,
        std_cos=1.0,
        item_type_match=1.0,
        size_match=1.0,
        pressure_match=-1.0,  # Critical mismatch
        material_match=1.0,
        facing_match=1.0,
        standard_match=1.0,
        attr_coverage=0.9,
        n_missing=0.0,
    )
    score_mismatch = reranker.predict_score(mismatch_features)
    # Strictly capped at <= 0.20
    assert score_mismatch <= 0.20

    # Missing attributes cannot reach auto-tier
    missing_features = RerankerFeatures(
        composite_cosine=0.90,
        dim_cos=1.0,
        met_cos=1.0,
        pt_cos=1.0,
        std_cos=1.0,
        item_type_match=1.0,
        size_match=1.0,
        pressure_match=1.0,
        material_match=1.0,
        facing_match=1.0,
        standard_match=1.0,
        attr_coverage=0.7,
        n_missing=2.0,  # 2 missing mandatory attributes
    )
    score_missing = reranker.predict_score(missing_features)
    # Capped at <= 0.85 (below tau_auto 0.95)
    assert score_missing <= 0.85


def test_treeshap_feature_attribution_report() -> None:
    """Tests TreeSHAP feature attribution provider and plain-language bullets."""
    explainer = TreeSHAPExplainer(threshold=0.05)
    features = RerankerFeatures(
        composite_cosine=0.95,
        dim_cos=0.95,
        met_cos=0.95,
        pt_cos=0.40,
        std_cos=0.90,
        item_type_match=1.0,
        size_match=1.0,
        pressure_match=-1.0,
        material_match=1.0,
        facing_match=1.0,
        standard_match=1.0,
        attr_coverage=0.85,
        n_missing=1.0,
    )

    report = explainer.explain(features, predicted_prob=0.18)

    assert report.title == DISCLAIMER_TITLE
    assert report.title == "Model score attribution (does not decide the tier)"
    assert len(report.bullets) > 0
    # Should include bullets explaining pressure mismatch penalty
    assert any("pressure" in b.lower() for b in report.bullets)
    # Should include missing attribute penalty
    assert any("missing" in b.lower() for b in report.bullets)


def test_vector_recall_candidate_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests Stage 5 vector recall in candidate retrieval when ml_layer is on."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ml_layer", "on")

    candidate_pool = [
        RetrievedCandidate(
            golden_master_id="gm-1",
            golden_code="MPNG-0000000001-1",
            descriptor="VALVE GATE 100 NB CL150 WCB FLG RF API600",
            subcategory="VALVES.GATE",
            canonical_text="VALVE GATE 100 NB CL150 WCB FLG RF API600",
            attributes={
                "size_nb": 100,
                "pressure_class": "150",
                "body_material": "WCB",
                "end_connection": "FLG",
                "facing": "RF",
                "design_standard": "API600",
            },
            block_key="VALVES:VALVES.GATE:size_nb=100_MM",
        ),
        RetrievedCandidate(
            golden_master_id="gm-2",
            golden_code="MPNG-0000000002-2",
            descriptor="VALVE GATE 150 NB CL300 WCB FLG RF API600",
            subcategory="VALVES.GATE",
            canonical_text="VALVE GATE 150 NB CL300 WCB FLG RF API600",
            attributes={
                "size_nb": 150,
                "pressure_class": "300",
                "body_material": "WCB",
                "end_connection": "FLG",
                "facing": "RF",
                "design_standard": "API600",
            },
            block_key="VALVES:VALVES.GATE:size_nb=150_MM",
        ),
    ]

    extracted = {
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": "RF",
        "design_standard": "API600",
    }

    # When querying with partial text, candidates are retrieved
    results = retrieve_candidates_in_memory(
        candidate_pool=candidate_pool,
        clean_text="VLV GT 100 CL150",
        subcategory="VALVES.GATE",
        extracted_attrs=extracted,
        top_k=5,
    )

    assert len(results) > 0
    assert any(c.golden_code == "MPNG-0000000001-1" for c in results)
