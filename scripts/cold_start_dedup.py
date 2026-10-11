"""Cold-Start Deduplication CLI Script.

Executes cold-start clustering on inventory datasets (or generated synthetic datasets at scale).
Outputs the Intra-Organisation Deduplication Report ("N items collapse to M masters").
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.services.cold_start import ColdStartEngine, RawItemRecord

# Synthetic description templates for scale testing
SYNTHETIC_TEMPLATES = [
    (
        "VALVES.GATE",
        [
            "GATE VALVE 100 NB CL150 A216 WCB FLANGED RF API600",
            "VLV GT 100NB 150# WCB FLG RF API 600",
            "100 NB CLASS 150 GATE VALVE CAST STEEL BODY FLANGED",
            "VALVE GATE 4 INCH 150# A216 WCB FLANGED RF",
        ],
        {"unit_price": 12500.0, "qty_range": (5, 50)},
    ),
    (
        "PIPES.PIPE",
        [
            "SEAMLESS PIPE 200 NB SCH 40 ASTM A106 GR B BE",
            "SMLS PIPE 200NB SCH40 A106-B BEVELLED END",
            "PIPE 8 INCH SCH 40 SMLS ASTM A106 GR B BE",
            "CARBON STEEL SEAMLESS PIPE 200 NB SCH 40 A106 GR B",
        ],
        {"unit_price": 8500.0, "qty_range": (10, 200)},
    ),
    (
        "CABLES.POWER",
        [
            "POWER CABLE 1.1KV 4C X 16 SQMM AL XLPE ARMOURED",
            "1.1 KV 4CX16 AL XLPE ARMOURED CABLE",
            "CABLE POWER 4C 16 SQMM ALUMINIUM CONDUCTOR XLPE",
            "4CX16 SQMM 1100V AL XLPE SWA CABLE",
        ],
        {"unit_price": 450.0, "qty_range": (100, 2000)},
    ),
    (
        "MOTORS.EX",
        [
            "INDUCTION MOTOR 75 KW 4 POLE 415V FOOT B3 TEFC FLAMEPROOF EX D IIC T4",
            "MOTOR 75KW 4P 415V 1500RPM B3 FLP EX D IIC T4",
            "100 HP 4 POLE FLAMEPROOF INDUCTION MOTOR 415V 50HZ",
            "75 KW 4 POLE FOOT MOUNTED SQUIRREL CAGE MOTOR EX D IIC T4",
        ],
        {"unit_price": 185000.0, "qty_range": (1, 10)},
    ),
    (
        "BEARINGS.BEARING",
        [
            "DEEP GROOVE BALL BEARING 6312 2RS C3",
            "BEARING 6312-2RS/C3 SKF",
            "BALL BEARING 6312 2RS1 C3",
            "BEARING 6312 2RS C3 OPEN/SEALED",
        ],
        {"unit_price": 3200.0, "qty_range": (10, 100)},
    ),
    (
        "STEEL.STRUCTURAL",
        [
            "STEEL BEAM ISMB 300 GRADE E250A LENGTH 12M",
            "ISMB 300 STRUCTURAL STEEL BEAM E250",
            "BEAM ISMB 300 IS 2062 E250A 12 METER",
            "STRUCTURAL BEAM ISMB 300 E250A",
        ],
        {"unit_price": 65000.0, "qty_range": (5, 80)},
    ),
    (
        "FASTENERS.STUD_BOLT",
        [
            "STUD BOLT M24X150MM ASTM A193 B7 WITH 2 NUTS A194 2H",
            "STUD M24 X 150 A193 B7 / 2H",
            "FASTENER STUD BOLT M24X150 B7/2H",
            "STUD BOLT M24*150MM B7 WITH 2H NUTS",
        ],
        {"unit_price": 280.0, "qty_range": (50, 1000)},
    ),
    (
        "STEEL.CONVEYOR_BELT",
        [
            "CONVEYOR BELT EP 800/4 1400MM 5+2 GRADE M DIN 22102",
            "EP 800/4 1400 MM BELT 5+2 M GRADE",
            "BELTING CONVEYOR EP 800/4 WIDTH 1400MM",
            "CONVEYOR BELT EP 800/4 1400MM COVER 5+2",
        ],
        {"unit_price": 4200.0, "qty_range": (50, 500)},
    ),
]


def generate_synthetic_dataset(n_items: int, seed: int = 42) -> list[RawItemRecord]:
    """Generates synthetic inventory items with intentional duplicates across templates."""
    rng = random.Random(seed)
    items: list[RawItemRecord] = []

    # Choose number of distinct intended master concepts
    # Duplicate factor ~ 3.5 items per master
    n_masters = max(1, n_items // 3)

    for m_idx in range(n_masters):
        family, variants, pricing = rng.choice(SYNTHETIC_TEMPLATES)
        base_price = pricing["unit_price"] * (0.9 + 0.2 * rng.random())
        # Pick 2 to 6 variants of this same master
        k_variants = rng.randint(2, 5)

        for _ in range(k_variants):
            if len(items) >= n_items:
                break
            desc = rng.choice(variants)
            # Add small random noise: extra spaces or trailing stock codes
            if rng.random() > 0.5:
                desc = desc + f" STORE-{rng.randint(1, 9)}"

            qty = rng.randint(pricing["qty_range"][0], pricing["qty_range"][1])
            unit_price = round(base_price * (0.95 + 0.1 * rng.random()), 2)
            item_code = f"RAW-{len(items) + 1:06d}"

            items.append(
                RawItemRecord(
                    item_code=item_code,
                    description=desc,
                    qty=float(qty),
                    unit_price_inr=unit_price,
                    org_id="OIL-1",
                    plant="REFINERY-1",
                    category_hint=family.split(".")[0],
                )
            )

    return items[:n_items]


def main() -> None:
    parser = argparse.ArgumentParser(description="Cold-Start Master Deduplication Pipeline")
    parser.add_argument("--count", type=int, default=500, help="Number of items for synthetic run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="", help="Path to write report markdown")
    args = parser.parse_args()

    print(f"Generating synthetic dataset: {args.count} items (seed={args.seed})...")
    items = generate_synthetic_dataset(args.count, seed=args.seed)

    print("Running ColdStartEngine...")
    engine = ColdStartEngine(packs_dir="packs")

    start_time = time.perf_counter()
    _clusters, report = engine.process_items(items)
    elapsed = time.perf_counter() - start_time

    print(f"\nProcessing complete in {elapsed:.2f} seconds ({len(items) / elapsed:.1f} items/sec).")
    print(f"Total items: {report.total_items}")
    print(f"Proposed masters: {report.total_masters}")
    print(f"Deduplication rate: {report.dedup_percentage:.1f}%")
    print(f"Total catalog value: INR {report.total_stock_value_inr:,.2f}")
    print(f"Duplicate stock value: INR {report.duplicate_stock_value_inr:,.2f}")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report.summary_markdown, encoding="utf-8")
        print(f"Saved report to: {out_path}")
    else:
        print("\n" + report.summary_markdown[:800] + "\n...")


if __name__ == "__main__":
    main()
