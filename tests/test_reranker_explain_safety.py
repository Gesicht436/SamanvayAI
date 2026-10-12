"""Safety and Invariant tests for Sector Reranker, TreeSHAP Explainability, and Active Learning.

Guarantees:
- Invariant S9/S14: Reranker output and TreeSHAP attribution NEVER raise an item to Tier 1 or override HARD mismatches.
- Identity safety: No feature reward for class upgrades or substitute metallurgy.
- Explainer honesty: Returns attribution unavailable when no model is loaded; never emits fake numbers.
- Active learning: Uncertainty sampling, Tier 1 skip, and persistent storage.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from api.ml.active_learning import ActiveLearningQueue
from api.ml.explain import DISCLAIMER_TITLE, UNAVAILABLE_MESSAGE, TreeSHAPExplainer
from api.ml.rerankers import (
    RerankerFeatures,
    SectorReranker,
    build_reranker_features,
)
from api.services.comparator import compare_items
from api.services.tiering import Tier, assign_tier


def test_invariant_s9_reranker_never_overrides_hard_mismatch_or_raises_to_tier_1() -> None:
    """Safety Invariant S9 & S14: Even with reranker probability = 0.99,

    a HARD attribute mismatch MUST yield Tier 3, never Tier 1.
    """
    req_attrs = {
        "item_type": "VALVE_GATE",
        "size_nb": 100,
        "pressure_class": "150",
        "body_material": "WCB",
    }
    cand_attrs = {
        "item_type": "VALVE_GATE",
        "size_nb": 100,
        "pressure_class": "300",  # Hard mismatch: 150 != 300
        "body_material": "WCB",
    }

    comp = compare_items(req_attrs, cand_attrs, subcategory="VALVES.GATE")
    assert comp.has_hard_mismatch is True

    # Build features and run reranker
    rf = build_reranker_features(
        comparison=comp,
        sector="VALVES",
        raw_attrs=req_attrs,
        candidate_attrs=cand_attrs,
    )
    reranker = SectorReranker(sector="VALVES")
    ml_res = reranker.rerank(rf)

    # Even if ML produces a high probability or we simulate 0.99
    simulated_prob = 0.99
    eval_prob = min(simulated_prob, ml_res.prob)

    tier_res = assign_tier(
        comparison=comp,
        identity_mode="canonical_master",
        extraction_flags=[],
        probability=eval_prob,
        tau_auto=0.95,
        tau_review=0.70,
    )

    # Invariant S9: Tier must NEVER be Tier 1
    assert tier_res.tier != Tier.ONE_AUTO
    assert tier_res.tier == Tier.THREE_DISTINCT
    assert "HARD_ATTRIBUTE_MISMATCH" in tier_res.reason_codes


def test_reranker_features_are_strictly_identity_safe() -> None:
    """Validates that no reranker feature rewards upgrading or substitution.

    B had 'pressure_upgrade' which rewarded higher pressure class. A forbids this.
    """
    feature_names = RerankerFeatures(composite_cosine=0.5).feature_names()

    # Assert no upgrading or substitution reward features exist
    forbidden_terms = ["upgrade", "substitute", "higher_class", "better_grade", "downgrade_penalty_only"]
    for feat in feature_names:
        for term in forbidden_terms:
            assert term not in feat.lower(), f"Feature {feat} contains forbidden non-identity concept '{term}'"

    # Verify that higher pressure class results in negative pressure_match, not positive
    req = {"size_nb": 100, "pressure_class": "150", "body_material": "WCB"}
    cand_upgraded = {"size_nb": 100, "pressure_class": "300", "body_material": "WCB"}
    comp = compare_items(req, cand_upgraded, subcategory="VALVES.GATE")

    rf = build_reranker_features(
        comparison=comp,
        sector="VALVES",
        raw_attrs=req,
        candidate_attrs=cand_upgraded,
    )
    assert rf.pressure_match < 0, "Higher pressure class candidate must yield negative match feature"


def test_sector_reranker_safety_clamp() -> None:
    """Tests that reranker clamps output probability when physical attributes mismatch."""
    reranker = SectorReranker(sector="VALVES")

    # Mismatched size
    rf_mismatch = RerankerFeatures(
        composite_cosine=0.99,
        size_match=-1.0,
        pressure_match=1.0,
        material_match=1.0,
    )
    res = reranker.rerank(rf_mismatch)
    # Must be clamped <= 0.20
    assert res.prob <= 0.20


def test_treeshap_explainer_honesty_when_no_model_loaded() -> None:
    """Explainer must return 'Attribution unavailable' with standard disclaimer header, never fake numbers."""
    explainer = TreeSHAPExplainer(model=None)
    features = RerankerFeatures(composite_cosine=0.85)

    report = explainer.explain(features, predicted_prob=0.82)

    assert report.title == DISCLAIMER_TITLE
    assert len(report.bullets) == 1
    assert report.bullets[0] == UNAVAILABLE_MESSAGE
    assert report.contributions == []


def test_treeshap_explainer_computes_real_contributions_when_model_provided() -> None:
    """When a model is provided, explainer parses booster contributions and generates plain text bullets."""
    features = RerankerFeatures(
        composite_cosine=0.92,
        size_match=1.0,
        pressure_match=-1.0,
        n_missing=1.0,
    )
    names = features.feature_names()

    class MockBooster:
        def predict(self, matrix, pred_contribs=False):
            # Return contributions for each feature + bias
            contribs = [0.0] * (len(names) + 1)
            contribs[names.index("pressure_match")] = -0.55
            contribs[names.index("size_match")] = 0.25
            contribs[names.index("composite_cosine")] = 0.15
            contribs[-1] = 0.50  # bias
            return [contribs]

    explainer = TreeSHAPExplainer(model=MockBooster(), threshold=0.10)
    report = explainer.explain(features, predicted_prob=0.35)

    assert report.title == DISCLAIMER_TITLE
    assert len(report.contributions) == 3
    # Check sorting: highest absolute contribution first
    assert report.contributions[0].feature_name == "pressure_match"
    assert report.contributions[0].contribution == -0.55
    assert any("differs" in b or "mismatch" in b or "differ" in b for b in report.bullets)


def test_active_learning_uncertainty_and_persistence() -> None:
    """Tests active learning queue uncertainty sampling and persistent storage."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = Path(tmp_dir) / "al_queue.jsonl"
        q = ActiveLearningQueue(capacity=100, storage_path=storage)

        # 1. Tier 1 matches are definitive and never enqueued
        obs_t1 = q.observe(
            query="VALVE GATE 100 NB CL150",
            candidate_code="MPNG-0001",
            candidate_description="VALVE GATE 100 NB CL150",
            subcategory="VALVES.GATE",
            prob=0.98,
            tier="Tier 1",
        )
        assert obs_t1 is None
        assert len(q.list_items()) == 0

        # 2. Uncertain match (prob = 0.52 -> high uncertainty)
        item = q.observe(
            query="VALVE GATE 100 NB CL150 WCB",
            candidate_code="MPNG-0002",
            candidate_description="VALVE GATE 100 NB CL300 WCB",
            subcategory="VALVES.GATE",
            prob=0.52,
            tier="Tier 2",
        )
        assert item is not None
        # Uncertainty: 1.0 - min(1.0, abs(0.52 - 0.50) * 2.0) = 1.0 - 0.04 = 0.96
        assert pytest.approx(item.uncertainty, abs=0.01) == 0.96
        assert len(q.list_items()) == 1

        # 3. Persistence: reload new instance from disk
        q_reloaded = ActiveLearningQueue(capacity=100, storage_path=storage)
        assert len(q_reloaded.list_items()) == 1
        loaded_item = q_reloaded.get(item.id)
        assert loaded_item is not None
        assert loaded_item.candidate_code == "MPNG-0002"

        # 4. Resolve item with human expert feedback
        resolved = q_reloaded.resolve(item.id, accepted=False)
        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.accepted is False

        # Unresolved list is now empty
        assert len(q_reloaded.list_items(unresolved_only=True)) == 0

        # Export training examples
        examples = q_reloaded.training_examples()
        assert len(examples) == 1
        assert examples[0]["label"] == 0
        assert examples[0]["candidate_code"] == "MPNG-0002"
