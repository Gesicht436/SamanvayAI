"""Prometheus observability metrics service for Samanvay.

Implements Prometheus metrics registry and format generator per Section 15.2.
Guarantees bounded cardinality and privacy: strictly prohibits organization,
user, item, or sensitive text identifiers in metric labels.
"""

import threading
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.hashchain import verify_chain
from api.models.entities import AuditLog, Job, LifeAlert, StewardTask

FORBIDDEN_LABEL_KEYS = {
    "org",
    "org_id",
    "organisation",
    "organization",
    "user",
    "user_id",
    "actor",
    "item_code",
    "item_id",
    "raw_id",
    "golden_id",
    "description",
    "raw_text",
    "clean_text",
    "invoice_no",
}


def validate_metric_labels(labels: dict[str, str] | None) -> None:
    """Validate that metric labels do not contain forbidden identifiers."""
    if not labels:
        return
    for k in labels:
        k_lower = k.lower()
        if k_lower in FORBIDDEN_LABEL_KEYS or "org" in k_lower or "user" in k_lower or "item" in k_lower:
            raise ValueError(
                f"Metric label '{k}' violates privacy invariant: organization and item identifiers are strictly forbidden."
            )


class MetricsRegistry:
    """Thread-safe Prometheus metrics registry with strict label privacy guards."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "buckets": (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
                "counts": defaultdict(lambda: defaultdict(int)),
                "sums": defaultdict(float),
                "totals": defaultdict(int),
            }
        )
        self._descriptions: dict[str, tuple[str, str]] = {
            "samanvay_match_total": ("Total match operations evaluated", "counter"),
            "samanvay_docs_ingested_total": ("Total documents ingested by type and status", "counter"),
            "samanvay_steward_actions_total": ("Total steward actions by action and domain", "counter"),
            "samanvay_audit_entries_total": ("Total entries committed to tamper-evident audit log", "counter"),
            "samanvay_mtc_results_total": ("Total MTC certificates processed by conformance result", "counter"),
            "samanvay_ocr_fallback_total": ("Total OCR fallbacks triggered between engines", "counter"),
            "samanvay_match_seconds": ("Latency of match pipeline stages in seconds", "histogram"),
            "samanvay_ocr_page_seconds": ("Latency of OCR processing per page in seconds", "histogram"),
            "samanvay_reranker_seconds": ("Latency of ML reranker in seconds", "histogram"),
            "samanvay_review_queue_depth": ("Current depth of stewardship review queue by domain", "gauge"),
            "samanvay_life_red_lots": ("Current count of stock lots in RED risk state", "gauge"),
            "samanvay_jobs_queued": ("Current count of queued async worker jobs", "gauge"),
            "samanvay_audit_chain_ok": ("Integrity status of hash-chained audit log (1=OK, 0=Broken)", "gauge"),
        }

    def inc_counter(self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        validate_metric_labels(labels)
        label_key = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            self._counters[name][label_key] += amount

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        validate_metric_labels(labels)
        label_key = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            self._gauges[name][label_key] = value

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        validate_metric_labels(labels)
        label_key = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            hist = self._histograms[name]
            hist["sums"][label_key] += value
            hist["totals"][label_key] += 1
            for b in hist["buckets"]:
                if value <= b:
                    hist["counts"][label_key][b] += 1

    def render_text(self) -> str:
        """Render metrics in standard Prometheus exposition format."""
        lines: list[str] = []

        with self._lock:
            # Counters
            for name, series_map in sorted(self._counters.items()):
                help_text, metric_type = self._descriptions.get(name, ("Samanvay counter metric", "counter"))
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {metric_type}")
                for label_key, val in sorted(series_map.items()):
                    if label_key:
                        label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                        lines.append(f"{name}{{{label_str}}} {val}")
                    else:
                        lines.append(f"{name} {val}")

            # Gauges
            for name, series_map in sorted(self._gauges.items()):
                help_text, metric_type = self._descriptions.get(name, ("Samanvay gauge metric", "gauge"))
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {metric_type}")
                for label_key, val in sorted(series_map.items()):
                    if label_key:
                        label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                        lines.append(f"{name}{{{label_str}}} {val}")
                    else:
                        lines.append(f"{name} {val}")

            # Histograms
            for name, hist in sorted(self._histograms.items()):
                help_text, metric_type = self._descriptions.get(name, ("Samanvay histogram metric", "histogram"))
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {metric_type}")
                buckets: Sequence[float] = hist["buckets"]
                for label_key, total_count in sorted(hist["totals"].items()):
                    base_labels = dict(label_key)
                    for b in buckets:
                        b_count = hist["counts"][label_key][b]
                        b_labels = dict(base_labels)
                        b_labels["le"] = str(b)
                        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(b_labels.items()))
                        lines.append(f"{name}_bucket{{{label_str}}} {b_count}")
                    # +Inf bucket
                    inf_labels = dict(base_labels)
                    inf_labels["le"] = "+Inf"
                    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(inf_labels.items()))
                    lines.append(f"{name}_bucket{{{label_str}}} {total_count}")

                    # Sum and Count
                    sum_val = round(hist["sums"][label_key], 4)
                    if base_labels:
                        sum_labels = ",".join(f'{k}="{v}"' for k, v in sorted(base_labels.items()))
                        lines.append(f"{name}_sum{{{sum_labels}}} {sum_val}")
                        lines.append(f"{name}_count{{{sum_labels}}} {total_count}")
                    else:
                        lines.append(f"{name}_sum {sum_val}")
                        lines.append(f"{name}_count {total_count}")

        return "\n".join(lines) + "\n"


# Global singleton registry
metrics_registry = MetricsRegistry()


def collect_live_database_gauges(db: Session) -> None:
    """Collect real-time gauges from PostgreSQL for the /metrics scraper.

    Reads database aggregates without filtering by org, preserving system-level
    observability without leaking any tenant or item identifiers.
    """
    # 1. Stewardship queue depth by domain
    domain_counts = (
        db.execute(
            select(
                func.coalesce(StewardTask.payload["sector"].astext, "COMMON").label("domain"),
                func.count(StewardTask.id),
            )
            .where(StewardTask.state == "OPEN")
            .group_by("domain")
        )
        .all()
    )
    # Ensure default domains exist in metrics
    for dom in ["COMMON", "POWER", "STEEL", "MINING", "HEAVY_ENG"]:
        metrics_registry.set_gauge("samanvay_review_queue_depth", 0.0, {"domain": dom})
    for dom, count in domain_counts:
        metrics_registry.set_gauge("samanvay_review_queue_depth", float(count), {"domain": dom or "COMMON"})

    # 2. Stock lots in RED risk state
    red_lots_count = db.scalar(
        select(func.count(LifeAlert.id)).where(LifeAlert.risk == "RED", LifeAlert.state == "OPEN")
    ) or 0
    metrics_registry.set_gauge("samanvay_life_red_lots", float(red_lots_count))

    # 3. Queued jobs count
    queued_jobs = db.scalar(
        select(func.count(Job.id)).where(Job.state == "QUEUED")
    ) or 0
    metrics_registry.set_gauge("samanvay_jobs_queued", float(queued_jobs))

    # 4. Total audit entries committed
    audit_total = db.scalar(
        select(func.count(AuditLog.seq))
    ) or 0
    metrics_registry.inc_counter(
        "samanvay_audit_entries_total",
        amount=0.0,  # Ensure counter exists
    )
    # Set the counter directly to match audit log count
    metrics_registry._counters["samanvay_audit_entries_total"][()] = float(audit_total)

    # 5. Audit chain verification status
    try:
        chain_report = verify_chain(db)
        metrics_registry.set_gauge("samanvay_audit_chain_ok", 1.0 if chain_report.get("status") == "OK" else 0.0)
    except Exception:  # noqa: BLE001
        metrics_registry.set_gauge("samanvay_audit_chain_ok", 0.0)
