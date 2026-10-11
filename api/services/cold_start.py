"""Cold-Start Clustering and Deduplication Engine.

Implements the cold-start harmonization pipeline from Section 8.0:
1. Normalizes and classifies raw items across subcategories.
2. Extracts physical attributes using the specification registry.
3. Groups items by block_key.
4. Inside each block, clusters by exact HARD + REQUIRED attribute signature.
5. Identical signatures become proposed DRAFT masters with member provenance.
6. Near-signatures differing only by missing attributes link as needs_review.
7. Generates Intra-Organisation Deduplication Report:
   'N item codes collapse to M masters', top clusters, stock value tied up in duplicates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from api.core.verhoeff import make_code
from api.extractors.registry import AttributeRole, default_registry
from api.services.candidates import compute_block_key
from api.services.classify import classify_subcategory
from api.services.lifecycle import generate_canonical_text, generate_descriptor
from api.services.normalize import normalize_text


@dataclass
class RawItemRecord:
    """A raw inventory or procurement item record."""

    item_code: str
    description: str
    qty: float = 1.0
    unit_price_inr: float = 0.0
    org_id: str | None = None
    plant: str | None = None
    category_hint: str | None = None


@dataclass
class ClusteredMaster:
    """A proposed golden master cluster aggregating duplicate raw items."""

    cluster_id: str
    subcategory: str
    block_key: str
    signature: dict[str, Any]
    descriptor: str
    canonical_text: str
    items: list[RawItemRecord] = field(default_factory=list)
    total_qty: float = 0.0
    total_value_inr: float = 0.0
    proposed_golden_code: str = ""
    near_matches: list[str] = field(default_factory=list)  # Cluster IDs differing only by missing attributes

    @property
    def member_count(self) -> int:
        return len(self.items)

    @property
    def is_duplicate_cluster(self) -> bool:
        return len(self.items) > 1


@dataclass
class DedupReport:
    """Comprehensive Intra-Organisation Deduplication Report."""

    total_items: int
    total_masters: int
    dedup_percentage: float
    total_stock_value_inr: float
    duplicate_stock_value_inr: float
    clusters: list[ClusteredMaster]
    subcategory_breakdown: dict[str, dict[str, Any]]
    summary_markdown: str


class ColdStartEngine:
    """Orchestrates cold-start classification, extraction, and clustering."""

    def __init__(self, packs_dir: str = "packs"):
        default_registry.load_packs(packs_dir)

    def process_items(
        self,
        raw_items: list[RawItemRecord],
        seed_seq_start: int = 100_000,
    ) -> tuple[list[ClusteredMaster], DedupReport]:
        """Clusters raw items into proposed DRAFT golden masters.

        Args:
            raw_items: List of raw inventory item records.
            seed_seq_start: Sequence integer counter for generating MPNG- codes.

        Returns:
            tuple of (list of ClusteredMaster, DedupReport)
        """
        if not raw_items:
            empty_report = DedupReport(
                total_items=0,
                total_masters=0,
                dedup_percentage=0.0,
                total_stock_value_inr=0.0,
                duplicate_stock_value_inr=0.0,
                clusters=[],
                subcategory_breakdown={},
                summary_markdown="# Intra-Organisation Deduplication Report\n\nNo items processed.\n",
            )
            return [], empty_report

        total_value = sum(i.qty * i.unit_price_inr for i in raw_items)

        # 1. Normalize, classify, and extract each item
        processed_items: list[dict[str, Any]] = []
        for item in raw_items:
            norm_res = normalize_text(item.description, category=item.category_hint)
            clean_text = norm_res.clean_text

            class_res = classify_subcategory(clean_text, category_hint=item.category_hint)
            sub = class_res.subcategory or "COMMON.UNKNOWN"

            extracted = default_registry.extract_attributes(clean_text, sub)
            # Flatten extracted values
            flat_attrs: dict[str, Any] = {k: ev.value for k, ev in extracted.items() if ev.value is not None}

            block_key, is_partial = compute_block_key(sub, flat_attrs)

            processed_items.append(
                {
                    "raw_record": item,
                    "clean_text": clean_text,
                    "subcategory": sub,
                    "flat_attrs": flat_attrs,
                    "block_key": block_key,
                    "is_partial": is_partial,
                }
            )

        # 2. Group by block_key, then cluster by exact HARD + REQUIRED attribute signature
        # Signature: sorted tuple of (attr, str(value)) for HARD and REQUIRED attributes
        clusters_map: dict[tuple[str, str, str], ClusteredMaster] = {}
        seq_counter = seed_seq_start

        for item_info in processed_items:
            sub = item_info["subcategory"]
            b_key = item_info["block_key"]
            flat = item_info["flat_attrs"]
            raw_rec = item_info["raw_record"]

            spec = default_registry.get_spec(sub)
            hard_required_keys: set[str] = set()
            if spec:
                for a in spec.attributes:
                    if a.role in (AttributeRole.HARD, AttributeRole.REQUIRED):
                        hard_required_keys.add(a.name)
            else:
                hard_required_keys = set(flat.keys())

            sig_pairs = tuple(
                sorted((k, str(flat[k])) for k in hard_required_keys if k in flat and flat[k] is not None)
            )
            sig_str = json.dumps(sig_pairs)
            cluster_lookup_key = (sub, b_key, sig_str)

            if cluster_lookup_key not in clusters_map:
                seq_counter += 1
                golden_code = make_code(seq_counter)
                descriptor = generate_descriptor(sub, flat)
                canonical_text = generate_canonical_text(descriptor)
                cluster_id = f"CLUST-{seq_counter}"

                clusters_map[cluster_lookup_key] = ClusteredMaster(
                    cluster_id=cluster_id,
                    subcategory=sub,
                    block_key=b_key,
                    signature=dict(sig_pairs),
                    descriptor=descriptor,
                    canonical_text=canonical_text,
                    items=[],
                    total_qty=0.0,
                    total_value_inr=0.0,
                    proposed_golden_code=golden_code,
                )

            cluster = clusters_map[cluster_lookup_key]
            cluster.items.append(raw_rec)
            cluster.total_qty += raw_rec.qty
            cluster.total_value_inr += raw_rec.qty * raw_rec.unit_price_inr

        all_clusters = list(clusters_map.values())

        # 3. Identify near-signatures differing only by missing attributes within each block
        # If sig(A) is a strict non-empty subset of sig(B), link as near-match (Tier 2 review)
        clusters_by_block: dict[tuple[str, str], list[ClusteredMaster]] = {}
        for c in all_clusters:
            key = (c.subcategory, c.block_key)
            clusters_by_block.setdefault(key, []).append(c)

        for block_clusts in clusters_by_block.values():
            if len(block_clusts) < 2:
                continue
            for i, c1 in enumerate(block_clusts):
                set1 = set(c1.signature.items())
                for j, c2 in enumerate(block_clusts):
                    if i != j:
                        set2 = set(c2.signature.items())
                        # If set1 is a subset of set2 and they share at least one attribute
                        if set1 and set1 < set2:
                            c1.near_matches.append(c2.cluster_id)

        # Sort clusters by total value and item count descending
        all_clusters.sort(key=lambda c: (c.member_count, c.total_value_inr), reverse=True)

        total_items_count = len(raw_items)
        total_masters_count = len(all_clusters)
        dedup_pct = (
            ((total_items_count - total_masters_count) / total_items_count * 100.0) if total_items_count > 0 else 0.0
        )
        duplicate_value = sum(c.total_value_inr for c in all_clusters if c.is_duplicate_cluster)

        # Subcategory breakdown
        breakdown: dict[str, dict[str, Any]] = {}
        for c in all_clusters:
            sub = c.subcategory
            if sub not in breakdown:
                breakdown[sub] = {
                    "items": 0,
                    "masters": 0,
                    "duplicate_clusters": 0,
                    "total_value_inr": 0.0,
                }
            breakdown[sub]["items"] += c.member_count
            breakdown[sub]["masters"] += 1
            if c.is_duplicate_cluster:
                breakdown[sub]["duplicate_clusters"] += 1
            breakdown[sub]["total_value_inr"] += c.total_value_inr

        # Generate markdown summary report in 80% ASD-STE100
        summary_md = self._render_report_markdown(
            total_items=total_items_count,
            total_masters=total_masters_count,
            dedup_pct=dedup_pct,
            total_value=total_value,
            duplicate_value=duplicate_value,
            top_clusters=all_clusters[:10],
            breakdown=breakdown,
        )

        report = DedupReport(
            total_items=total_items_count,
            total_masters=total_masters_count,
            dedup_percentage=round(dedup_pct, 2),
            total_stock_value_inr=round(total_value, 2),
            duplicate_stock_value_inr=round(duplicate_value, 2),
            clusters=all_clusters,
            subcategory_breakdown=breakdown,
            summary_markdown=summary_md,
        )

        return all_clusters, report

    def _render_report_markdown(
        self,
        total_items: int,
        total_masters: int,
        dedup_pct: float,
        total_value: float,
        duplicate_value: float,
        top_clusters: list[ClusteredMaster],
        breakdown: dict[str, dict[str, Any]],
    ) -> str:
        """Renders the executive deduplication report in 80% ASD-STE100."""
        lines = [
            "# Intra-Organisation Master Deduplication Report",
            "",
            "## 1. Executive Summary",
            f"- **Total Raw Items Ingested:** {total_items:,}",
            f"- **Collapsed Unique Masters (Proposed DRAFT):** {total_masters:,}",
            f"- **Deduplication Rate:** **{dedup_pct:.1f}%**",
            f"- **Total Catalog Inventory Value:** INR {total_value:,.2f}",
            f"- **Inventory Value Tied Up in Duplicate Clusters:** INR {duplicate_value:,.2f}",
            "",
            "## 2. Top Duplicate Clusters by Member Count",
            "",
            "| Cluster ID | Golden Code | Subcategory | Items | Total Qty | Inventory Value (INR) | Standard Descriptor |",
            "|---|---|---|---|---|---|---|",
        ]

        for c in top_clusters:
            desc_short = c.descriptor[:55] + ("..." if len(c.descriptor) > 55 else "")
            lines.append(
                f"| `{c.cluster_id}` | `{c.proposed_golden_code}` | `{c.subcategory}` | {c.member_count} | {c.total_qty:,.1f} | {c.total_value_inr:,.2f} | `{desc_short}` |"
            )

        lines.extend(
            [
                "",
                "## 3. Subcategory Breakdown",
                "",
                "| Subcategory | Raw Items | Proposed Masters | Duplicate Clusters | Value (INR) |",
                "|---|---|---|---|---|",
            ]
        )

        for sub, stats in sorted(breakdown.items(), key=lambda x: x[1]["items"], reverse=True):
            lines.append(
                f"| `{sub}` | {stats['items']} | {stats['masters']} | {stats['duplicate_clusters']} | {stats['total_value_inr']:,.2f} |"
            )

        lines.append("")
        return "\n".join(lines)
