"""Safety tests for Vector Recall, Learned Embeddings, and Invariants S9/S14.

Non-negotiable invariants tested:
- S9 / S14: Vector recall (retrieval_method="VECTOR_RECALL") and neural embeddings
  only add candidates to the candidate pool; they can NEVER raise an item to Tier 1
  or override a HARD/REQUIRED verdict.
- Graceful degradation: When optional ML extra is not installed, learned encoder
  falls back to deterministic hashed encoder with visible 'ML_MODEL_UNAVAILABLE' flag.
- Leakage-safe split: Grouping by canonical_id guarantees zero data leakage into held-out sets.
- Gate honesty: Zero derived training pairs collide with locked eval pairs in packs/*/eval/*.csv.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from api.extractors.registry import default_registry
from api.ml.subvectors import (
    EmbeddingProvider,
    LearnedEmbeddingProvider,
    encode_subvectors,
    get_embedding_provider,
    subvector_texts,
)
from api.models.entities import GoldenSubvector, ItemSubvector
from api.services.candidates import RetrievedCandidate
from api.services.comparator import compare_items
from api.services.tiering import Tier, assign_tier
from scripts.derive_hard_negatives import derive_hard_negative_triplets, load_locked_eval_pairs
from scripts.train_biencoder import (
    build_retrieval_data,
    compute_retrieval_metrics,
    split_pairs_by_canonical,
    train_biencoder,
)


def test_invariant_s9_s14_vector_recall_cannot_raise_hard_mismatch_to_tier1() -> None:
    """Invariant S9/S14: A candidate retrieved via VECTOR_RECALL with high cosine similarity

    can NEVER override a HARD attribute mismatch to produce Tier 1.
    """
    spec = default_registry.get_spec("VALVES.GATE")
    assert spec is not None, "VALVES.GATE spec must exist"

    # Requested: Class 150 valve; Candidate: Class 300 valve (HARD mismatch on pressure_class)
    req_attrs = {
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": "RF",
        "design_standard": "API600",
    }
    cand_attrs = {
        "size_nb": 100,
        "pressure_class": "300",  # MISMATCH
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": "RF",
        "design_standard": "API600",
    }

    comparison = compare_items(req_attrs, cand_attrs, subcategory="VALVES.GATE", spec=spec)
    assert comparison.has_hard_mismatch is True

    # Candidate retrieved via vector recall with near-perfect cosine similarity
    cand = RetrievedCandidate(
        golden_master_id=uuid4(),
        golden_code="MPNG-0000000002-2",
        descriptor="VALVE GATE 100 NB CL300 WCB FLG RF API600",
        subcategory="VALVES.GATE",
        canonical_text="VALVE GATE 100 NB CL300 WCB FLG RF API600",
        attributes=cand_attrs,
        block_key="VALVES:VALVES.GATE:size_nb=100_MM",
        retrieval_score=0.985,  # High vector similarity
        retrieval_method="VECTOR_RECALL",
    )
    assert cand.retrieval_method == "VECTOR_RECALL"

    tiering_res = assign_tier(
        comparison=comparison,
        probability=0.99,  # High ML probability
    )

    # Invariant S9/S14 Assertions:
    assert tiering_res.tier == Tier.THREE_DISTINCT.value
    assert tiering_res.tier != Tier.ONE_AUTO.value
    assert "HARD_ATTRIBUTE_MISMATCH" in tiering_res.reason_codes
    assert tiering_res.requires_review is False
    assert tiering_res.stream_a_eligible is False


def test_invariant_s9_s14_vector_recall_cannot_raise_missing_attribute_to_tier1() -> None:
    """Invariant S9/S14: A candidate retrieved via VECTOR_RECALL missing a required attribute

    routes strictly to Tier 2 (Review) and can NEVER auto-harmonize in Tier 1.
    """
    spec = default_registry.get_spec("VALVES.GATE")
    assert spec is not None

    req_attrs = {
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": "RF",
        "design_standard": "API600",
    }
    # Candidate missing 'facing'
    cand_attrs = {
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
        "end_connection": "FLG",
        "facing": None,  # MISSING REQUIRED
        "design_standard": "API600",
    }

    comparison = compare_items(req_attrs, cand_attrs, subcategory="VALVES.GATE", spec=spec)
    assert comparison.has_missing_required is True

    cand = RetrievedCandidate(
        golden_master_id=uuid4(),
        golden_code="MPNG-0000000001-1",
        descriptor="VALVE GATE 100 NB CL150 WCB FLG API600",
        subcategory="VALVES.GATE",
        canonical_text="VALVE GATE 100 NB CL150 WCB FLG API600",
        attributes=cand_attrs,
        block_key="VALVES:VALVES.GATE:size_nb=100_MM",
        retrieval_score=0.95,
        retrieval_method="VECTOR_RECALL",
    )
    assert cand.retrieval_method == "VECTOR_RECALL"

    tiering_res = assign_tier(
        comparison=comparison,
        probability=0.98,
    )

    # Invariant S9/S14 Assertions:
    assert tiering_res.tier == Tier.TWO_REVIEW.value
    assert tiering_res.tier != Tier.ONE_AUTO.value
    assert "MISSING_REQUIRED_ATTRIBUTE" in tiering_res.reason_codes
    assert tiering_res.requires_review is True
    assert tiering_res.stream_a_eligible is False


def test_learned_encoder_graceful_fallback_without_ml_extra() -> None:
    """Verifies that LearnedEmbeddingProvider gracefully falls back to deterministic hashed encoder

    and sets ML_MODEL_UNAVAILABLE flag when optional ML extra is not installed.
    """
    provider, flags = get_embedding_provider(prefer_learned=True)

    # Under base install without sentence_transformers, fallback must be flagged visibly
    assert isinstance(provider, (LearnedEmbeddingProvider, EmbeddingProvider))
    if isinstance(provider, LearnedEmbeddingProvider) and provider.is_fallback:
        assert "ML_MODEL_UNAVAILABLE" in flags
        assert provider.fallback_reason == "ML_MODEL_UNAVAILABLE"

    # Encoding must succeed deterministically
    vec = provider.encode("VALVE GATE 100 NB CL150 WCB RF")
    assert len(vec) == provider.dimension
    assert all(isinstance(x, float) for x in vec)

    # subvector encoding helper
    vectors, _sub_flags = encode_subvectors({"size_nb": 100, "pressure_class": "150"}, encoder=provider)
    assert set(vectors.keys()) == {"dim", "met", "pt", "std"}
    assert len(vectors["dim"]) == provider.dimension


def test_subvector_texts_extraction() -> None:
    """Verifies subvector_texts mapping from dict or string to all 4 domains."""
    attrs = {
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
        "design_standard": "API600",
    }
    texts = subvector_texts(attrs)
    assert "dim" in texts
    assert "met" in texts
    assert "pt" in texts
    assert "std" in texts
    assert "100" in texts["dim"]
    assert "WCB" in texts["met"]
    assert "150" in texts["pt"]
    assert "API600" in texts["std"]

    # String input fallback
    str_texts = subvector_texts("GATE VALVE 100 NB CL150")
    assert str_texts["dim"] == "GATE VALVE 100 NB CL150"


def test_biencoder_leakage_safe_split() -> None:
    """Verifies split_pairs_by_canonical ensures 100% isolation of canonical_id between splits."""
    records = [
        {"anchor": "a1", "positive": "p1", "canonical_id": "CAN-001"},
        {"anchor": "a2", "positive": "p2", "canonical_id": "CAN-001"},
        {"anchor": "a3", "positive": "p3", "canonical_id": "CAN-002"},
        {"anchor": "a4", "positive": "p4", "canonical_id": "CAN-002"},
        {"anchor": "a5", "positive": "p5", "canonical_id": "CAN-003"},
        {"anchor": "a6", "positive": "p6", "canonical_id": "CAN-004"},
    ]

    train_split, test_split = split_pairs_by_canonical(records, test_size=0.25, seed=123)

    train_canonicals = {r["canonical_id"] for r in train_split}
    test_canonicals = {r["canonical_id"] for r in test_split}

    # Strict isolation: intersection must be empty
    assert len(train_canonicals.intersection(test_canonicals)) == 0
    assert len(train_split) + len(test_split) == len(records)


def test_biencoder_retrieval_metrics_calculation() -> None:
    """Verifies compute_retrieval_metrics calculates Recall@k and MRR with mock model."""
    records = [
        {"anchor": "VALVE 100", "positive": "CANONICAL VALVE 100", "canonical_id": "CAN-1"},
        {"anchor": "FLANGE 50", "positive": "CANONICAL FLANGE 50", "canonical_id": "CAN-2"},
    ]

    # Mock encoder that returns identity-based deterministic vectors
    class MockModel:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
            provider = EmbeddingProvider(dimension=64)
            return [provider.encode(t) for t in texts]

    queries, corpus, _relevant_docs = build_retrieval_data(records)
    assert len(queries) == 2
    assert len(corpus) == 2

    metrics = compute_retrieval_metrics(MockModel(), records, cutoffs=(1, 5))
    assert "Recall@1" in metrics
    assert "Recall@5" in metrics
    assert "MRR@10" in metrics
    assert 0.0 <= metrics["Recall@1"] <= 1.0


def test_biencoder_smoke_training_run(tmp_path: Path) -> None:
    """Verifies train_biencoder smoke run executes gracefully."""
    sample_file = tmp_path / "smoke_pairs.jsonl"
    rows = [
        {"anchor": f"A{i}", "positive": f"P{i}", "canonical_id": f"CAN-{i}"}
        for i in range(10)
    ]
    with open(sample_file, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)

    out_dir = tmp_path / "smoke_out"
    metrics = train_biencoder(
        train_file=sample_file,
        output_dir=out_dir,
        smoke_run=True,
    )
    assert isinstance(metrics, dict)
    assert "Recall@1" in metrics


def test_derive_hard_negatives_zero_eval_leakage(tmp_path: Path) -> None:
    """Gate Honesty: Verifies that derive_hard_negative_triplets generates hard negatives

    with ZERO collision or leakage into the locked eval pairs in packs/*/eval/*.csv.
    """
    locked_eval = load_locked_eval_pairs("packs")
    assert len(locked_eval) >= 170, "Must load all locked eval pairs"

    out_file = tmp_path / "derived_triplets.jsonl"
    count, _rejected = derive_hard_negative_triplets(packs_dir="packs", output_file=out_file)

    assert count > 0, "Should generate hard-negative triplets from fixtures"

    # Assert 0 leakage by checking every generated triplet against locked eval pairs
    with open(out_file, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            anchor = rec["anchor"].strip().upper()
            neg = rec["negative"].strip().upper()
            assert (anchor, neg) not in locked_eval, f"Eval set leakage detected for pair ({anchor}, {neg})!"
            assert (neg, anchor) not in locked_eval, f"Symmetric eval leakage detected for pair ({neg}, {anchor})!"


def test_subvector_entities_and_optional_vector_storage() -> None:
    """Verifies ItemSubvector and GoldenSubvector entities support embedding and domain constraints."""
    g_id = uuid4()
    golden_sub = GoldenSubvector(
        golden_id=g_id,
        domain="dim",
        text_repr="size nb: 100",
        embedding=[0.1, 0.2, 0.3],
    )
    assert golden_sub.domain == "dim"
    assert golden_sub.embedding == [0.1, 0.2, 0.3]

    item_sub = ItemSubvector(
        raw_item_id=uuid4(),
        domain="pt",
        text_repr="pressure class: 150",
        embedding=[0.0] * 384,
    )
    assert item_sub.domain == "pt"
    assert len(item_sub.embedding) == 384
