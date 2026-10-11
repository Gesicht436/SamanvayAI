"""Unit and integration tests for Prometheus observability metrics (Section 15.2).

Verifies:
  - Prometheus plain text exposition format.
  - Strict privacy invariant: forbidden labels (org_id, user_id, item_code, etc.) raise ValueError.
  - Counters, gauges, and histograms.
  - GET /metrics endpoint returns valid Prometheus metrics series.
"""

import pytest
from starlette.testclient import TestClient

from api.main import app
from api.services.observability import MetricsRegistry, validate_metric_labels


def test_metric_label_privacy_invariant() -> None:
    """Verify that tenant, user, and item identifiers are strictly forbidden in metric labels."""
    # Allowed labels
    validate_metric_labels({"sector": "POWER", "tier": "1"})
    validate_metric_labels({"doc_type": "INVOICE", "status": "UPLOADED"})
    validate_metric_labels({"action": "APPROVE", "domain": "COMMON"})
    validate_metric_labels({"stage": "retrieve"})

    # Forbidden labels must raise ValueError
    with pytest.raises(ValueError, match="privacy invariant"):
        validate_metric_labels({"org_id": "OIL-1"})

    with pytest.raises(ValueError, match="privacy invariant"):
        validate_metric_labels({"user_id": "user-123"})

    with pytest.raises(ValueError, match="privacy invariant"):
        validate_metric_labels({"item_code": "MAT-9988"})

    with pytest.raises(ValueError, match="privacy invariant"):
        validate_metric_labels({"actor": "admin"})

    with pytest.raises(ValueError, match="privacy invariant"):
        validate_metric_labels({"raw_text": "Sample gate valve description"})


def test_metrics_registry_counters_and_gauges() -> None:
    """Verify counters and gauges formatting in Prometheus exposition."""
    reg = MetricsRegistry()
    reg.inc_counter("samanvay_match_total", 5.0, {"sector": "COMMON", "tier": "1"})
    reg.inc_counter("samanvay_match_total", 2.0, {"sector": "COMMON", "tier": "2"})
    reg.set_gauge("samanvay_life_red_lots", 4.0)
    reg.set_gauge("samanvay_review_queue_depth", 12.0, {"domain": "STEEL"})

    text = reg.render_text()
    assert "# HELP samanvay_match_total Total match operations evaluated" in text
    assert "# TYPE samanvay_match_total counter" in text
    assert 'samanvay_match_total{sector="COMMON",tier="1"} 5.0' in text
    assert 'samanvay_match_total{sector="COMMON",tier="2"} 2.0' in text
    assert "# HELP samanvay_life_red_lots Current count of stock lots in RED risk state" in text
    assert "# TYPE samanvay_life_red_lots gauge" in text
    assert "samanvay_life_red_lots 4.0" in text
    assert 'samanvay_review_queue_depth{domain="STEEL"} 12.0' in text


def test_metrics_registry_histogram_buckets() -> None:
    """Verify Prometheus histogram bucket accumulation and sum/count."""
    reg = MetricsRegistry()
    reg.observe_histogram("samanvay_match_seconds", 0.045, {"stage": "classify"})
    reg.observe_histogram("samanvay_match_seconds", 0.120, {"stage": "classify"})

    text = reg.render_text()
    assert "# HELP samanvay_match_seconds Latency of match pipeline stages in seconds" in text
    assert "# TYPE samanvay_match_seconds histogram" in text
    assert 'samanvay_match_seconds_bucket{le="0.05",stage="classify"} 1' in text
    assert 'samanvay_match_seconds_bucket{le="0.25",stage="classify"} 2' in text
    assert 'samanvay_match_seconds_bucket{le="+Inf",stage="classify"} 2' in text
    assert 'samanvay_match_seconds_count{stage="classify"} 2' in text
    assert 'samanvay_match_seconds_sum{stage="classify"} 0.165' in text


def test_get_metrics_endpoint() -> None:
    """Verify GET /metrics HTTP endpoint returns status 200 with Prometheus text."""
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    # Check that required series exist in output
    assert "samanvay_review_queue_depth" in body
    assert "samanvay_life_red_lots" in body
    assert "samanvay_audit_chain_ok" in body
    assert "samanvay_audit_entries_total" in body
