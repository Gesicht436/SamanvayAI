"""Derive hard-negative training triplets from packs fixtures without leaking eval test pairs.

Enforces strict evaluation gate honesty:
- All rows in `packs/*/eval/pairs_*.csv` (the locked 170 test pairs) are blacklisted.
- Triplets (anchor, positive, negative) are derived from `packs/*/fixtures/*.csv`
  differing by exactly one critical attribute (e.g. pressure class, size, metallurgy).
- Every candidate triplet is checked against the locked eval pairs; matches are discarded.
- Outputs clean training triplets for bi-encoder training with TripletLoss.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_locked_eval_pairs(packs_dir: str | Path = "packs") -> set[tuple[str, str]]:
    """Loads all locked adversarial test pairs from packs/*/eval/*.csv."""
    locked: set[tuple[str, str]] = set()
    p_dir = Path(packs_dir)

    for eval_file in p_dir.glob("*/eval/*.csv"):
        with open(eval_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                req = row.get("req_text", "").strip().upper()
                cand = row.get("cand_text", "").strip().upper()
                if req and cand:
                    locked.add((req, cand))
                    locked.add((cand, req))  # Symmetric guard

    return locked


def load_fixture_records(packs_dir: str | Path = "packs") -> list[dict[str, Any]]:
    """Loads material fixtures from packs/*/fixtures/*.csv."""
    records: list[dict[str, Any]] = []
    p_dir = Path(packs_dir)

    for fix_file in p_dir.glob("*/fixtures/*.csv"):
        pack_name = fix_file.parent.parent.name
        family_name = fix_file.stem
        with open(fix_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                desc = row.get("description", "").strip()
                if not desc:
                    continue
                records.append({
                    "pack": pack_name,
                    "family": family_name,
                    "description": desc,
                    "attributes": {k: v.strip() for k, v in row.items() if k != "description" and v.strip()},
                    "fixture_id": f"{pack_name}-{family_name}-{idx}",
                })

    return records


def derive_hard_negative_triplets(
    packs_dir: str | Path = "packs",
    output_file: str | Path = "data/ml_training/hard_negative_triplets.jsonl",
) -> tuple[int, int]:
    """Derives hard-negative triplets from fixtures and guarantees 0 eval leakage.

    Returns (num_triplets_generated, num_eval_collisions_rejected).
    """
    locked_eval_pairs = load_locked_eval_pairs(packs_dir)
    fixtures = load_fixture_records(packs_dir)

    triplets: list[dict[str, Any]] = []
    collisions_rejected = 0

    # Group fixtures by family
    family_groups: dict[str, list[dict[str, Any]]] = {}
    for item in fixtures:
        family_groups.setdefault(item["family"], []).append(item)

    # For each family, find pairs differing by exactly 1 critical attribute
    critical_keys = {
        "size_nb",
        "pressure_class",
        "material_grade",
        "flange_type",
        "facing",
        "bore_schedule",
        "rating_kw",
        "voltage_kv",
        "primary_dimension",
    }

    for family, items in family_groups.items():
        for i in range(len(items)):
            item_a = items[i]
            desc_a = item_a["description"]
            attrs_a = item_a["attributes"]

            for j in range(i + 1, len(items)):
                item_b = items[j]
                desc_b = item_b["description"]
                attrs_b = item_b["attributes"]

                # Find differing keys
                all_keys = set(attrs_a.keys()) | set(attrs_b.keys())
                differing = [k for k in all_keys if attrs_a.get(k) != attrs_b.get(k)]

                if len(differing) == 1 and differing[0] in critical_keys:
                    diff_attr = differing[0]

                    # Check collision with locked eval pairs
                    pair_ab = (desc_a.upper(), desc_b.upper())
                    if pair_ab in locked_eval_pairs:
                        collisions_rejected += 1
                        continue

                    # Positive: canonical paraphrase / exact descriptor
                    positive = f"CANONICAL: {desc_a}"
                    triplets.append({
                        "anchor": desc_a,
                        "positive": positive,
                        "negative": desc_b,
                        "canonical_id": item_a["fixture_id"],
                        "difference_attribute": diff_attr,
                        "family": family,
                    })

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(t) + "\n" for t in triplets)

    return len(triplets), collisions_rejected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Derive hard-negative training pairs from fixtures")
    parser.add_argument("--packs-dir", type=str, default="packs")
    parser.add_argument("--output", type=str, default="data/ml_training/hard_negative_triplets.jsonl")
    args = parser.parse_args()

    count, rejected = derive_hard_negative_triplets(args.packs_dir, args.output)
    print(f"Generated {count} hard-negative triplets. Collisions rejected from eval gate: {rejected}.")
