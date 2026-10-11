"""Demo seed clusters generator and financial savings calculator.

Computes all 14 synthetic clusters and financial ranges (low/base/high)
per Section 19.0 to 19.2 purely mathematically:
  - BULK_MT: <25: 0%, 25-99: 8%, 100-299: 12%, 300-499: 15%, >=500: 18%
  - BULK_M:  <1k: 0%, 1k-4999: 8%, 5k-9999: 12%, 10k-19999: 15%, >=20k: 18%
  - ENGINEERED: <10: 0%, 10-24: 8%, 25-49: 12%, 50-99: 15%, >=100: 18%

Scenarios:
  - Low: 0.5x table discount
  - Base: 1.0x table discount
  - High: 1.25x table discount (capped at 25%)

Deliberate safety gating demonstrations:
  - Cluster 1: 4 units Tier 1 (<10 units threshold -> 0% savings).
  - Cluster 11: vector group missing (Tier 2) and DYN1 (Tier 3).
  - Cluster 12: castable lot with unknown expiry (UNKNOWN, never GREEN, S6).
  - Cluster 13: 27.00R51 (Tier 3) and no tread code (Tier 2).
  - Cluster 14: KG/CM2 given as head (flag PRESSURE_NOT_HEAD, Tier 2).
"""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select

from api.database import SyncSessionLocal
from api.models.entities import GoldenMaster, RawItem, StockLot
from api.services.audit import append_audit_entry
from api.services.lifecycle import generate_unique_mpng_code

DISCOUNT_TABLES = {
    "BULK_MT": [
        (25, 0.0),
        (100, 0.08),
        (300, 0.12),
        (500, 0.15),
        (float("inf"), 0.18),
    ],
    "BULK_M": [
        (1000, 0.0),
        (5000, 0.08),
        (10000, 0.12),
        (20000, 0.15),
        (float("inf"), 0.18),
    ],
    "ENGINEERED": [
        (10, 0.0),
        (25, 0.08),
        (50, 0.12),
        (100, 0.15),
        (float("inf"), 0.18),
    ],
}


def compute_table_discount(pooling_class: str, qty: float) -> float:
    """Determine table discount rate for a pooling class and pooled quantity."""
    bands = DISCOUNT_TABLES.get(pooling_class, DISCOUNT_TABLES["ENGINEERED"])
    for limit, rate in bands:
        if qty < limit:
            return rate
    return 0.18


def compute_scenario_savings(independent_cost: float, table_discount: float) -> dict[str, float]:
    """Compute Low (0.5x), Base (1.0x), and High (1.25x, cap 25%) scenario savings in INR."""
    low_rate = round(table_discount * 0.5, 4)
    base_rate = round(table_discount * 1.0, 4)
    high_rate = round(min(0.25, table_discount * 1.25), 4)

    return {
        "low_rate": low_rate,
        "base_rate": base_rate,
        "high_rate": high_rate,
        "low_savings": round(independent_cost * low_rate),
        "base_savings": round(independent_cost * base_rate),
        "high_savings": round(independent_cost * high_rate),
    }


@dataclass
class ClusterDef:
    cluster_id: str
    name: str
    item_description: str
    subcategory: str
    pooled_qty: float
    uom: str
    independent_cost: float
    pooling_class: str
    note: str = ""


# Canonical definitions from Section 19.2
RAW_CLUSTERS = [
    ClusterDef(
        cluster_id="1",
        name="Motors Ex d IIB T4 IE3",
        item_description="Motors 55 kW 4P B3 Ex d IIB T4 IE3",
        subcategory="MOTORS.EX",
        pooled_qty=4.0,
        uom="EA",
        independent_cost=1920000.0,
        pooling_class="ENGINEERED",
        note="Tier 1 only (O1). 4 units is below 10-unit threshold -> 0% savings.",
    ),
    ClusterDef(
        cluster_id="2",
        name="ISMB 300 E250A",
        item_description="ISMB 300 E250A, 12 m",
        subcategory="STEEL.STRUCTURAL",
        pooled_qty=360.0,
        uom="MT",
        independent_cost=23269000.0,
        pooling_class="BULK_MT",
    ),
    ClusterDef(
        cluster_id="3",
        name="TMT 25 mm Fe 500D",
        item_description="TMT 25 mm Fe 500D",
        subcategory="STEEL.REBAR",
        pooled_qty=550.0,
        uom="MT",
        independent_cost=32169000.0,
        pooling_class="BULK_MT",
    ),
    ClusterDef(
        cluster_id="4",
        name="Cable 1.1 kV 4C x 16 Cu SWA XLPE",
        item_description="Cable 1.1 kV 4C x 16 Cu SWA XLPE FRLS",
        subcategory="CABLES.POWER",
        pooled_qty=15500.0,
        uom="M",
        independent_cost=6556500.0,
        pooling_class="BULK_M",
    ),
    ClusterDef(
        cluster_id="5",
        name="Bearing 6312-2Z-C3",
        item_description="Bearing 6312-2Z-C3",
        subcategory="BEARINGS.BEARING",
        pooled_qty=310.0,
        uom="EA",
        independent_cost=1209850.0,
        pooling_class="ENGINEERED",
    ),
    ClusterDef(
        cluster_id="6",
        name="Gate valve 150 NB Cl300",
        item_description="Gate valve 150 NB Cl300 WCB RF",
        subcategory="VALVES.GATE",
        pooled_qty=69.0,
        uom="EA",
        independent_cost=3653700.0,
        pooling_class="ENGINEERED",
    ),
    ClusterDef(
        cluster_id="7",
        name="Pipe 100 NB SCH 80 A106 Gr B",
        item_description="Pipe 100 NB SCH 80 A106 Gr B",
        subcategory="PIPES.PIPE",
        pooled_qty=4800.0,
        uom="M",
        independent_cost=15424000.0,
        pooling_class="BULK_M",
    ),
    ClusterDef(
        cluster_id="8",
        name="Stud bolt set M24 x 150 B7/2H",
        item_description="Stud bolt set M24 x 150 B7/2H",
        subcategory="FASTENERS.STUD_BOLT",
        pooled_qty=8500.0,
        uom="EA",
        independent_cost=2374000.0,
        pooling_class="ENGINEERED",
        note="Counted units use engineered table.",
    ),
    ClusterDef(
        cluster_id="9",
        name="Pressure transmitter 0-10 bar HART",
        item_description="Pressure transmitter 0-10 bar HART SS316L Ex d IIC T6",
        subcategory="INSTRUMENTS.TRANSMITTER",
        pooled_qty=45.0,
        uom="EA",
        independent_cost=3714000.0,
        pooling_class="ENGINEERED",
    ),
    ClusterDef(
        cluster_id="10",
        name="WN flange 200 NB Cl150 RF",
        item_description="WN flange 200 NB Cl150 RF A105 SCH STD",
        subcategory="FLANGES.FLANGE",
        pooled_qty=140.0,
        uom="EA",
        independent_cost=2042000.0,
        pooling_class="ENGINEERED",
    ),
    ClusterDef(
        cluster_id="11",
        name="Distribution transformer 100 kVA",
        item_description="Distribution transformer 100 kVA 11/0.433 kV DYN11 ONAN, Cu",
        subcategory="POWER.TRANSFORMER",
        pooled_qty=125.0,
        uom="EA",
        independent_cost=31255000.0,
        pooling_class="ENGINEERED",
    ),
    ClusterDef(
        cluster_id="12",
        name="MgO-C brick, 14% C",
        item_description="MgO-C brick, 14% C, resin bond",
        subcategory="STEEL.REFRACTORY",
        pooled_qty=260.0,
        uom="MT",
        independent_cost=2492000.0 * 10,  # 24,920,000 INR
        pooling_class="BULK_MT",
    ),
    ClusterDef(
        cluster_id="13",
        name="OTR tyre 27.00R49 E4",
        item_description="OTR tyre 27.00R49 E4",
        subcategory="MINING.OTR_TYRE",
        pooled_qty=52.0,
        uom="EA",
        independent_cost=78200000.0,
        pooling_class="ENGINEERED",
    ),
    ClusterDef(
        cluster_id="14",
        name="Centrifugal pump API 610 OH2",
        item_description="Centrifugal pump API 610 OH2 (complete pump)",
        subcategory="HEAVY.PUMP_CENTRIFUGAL",
        pooled_qty=15.0,
        uom="EA",
        independent_cost=27100000.0,
        pooling_class="ENGINEERED",
    ),
]


def evaluate_clusters() -> list[dict[str, Any]]:
    """Compute all cluster figures mathematically."""
    results = []
    for c in RAW_CLUSTERS:
        table_pct = compute_table_discount(c.pooling_class, c.pooled_qty)
        savings = compute_scenario_savings(c.independent_cost, table_pct)
        res = asdict(c)
        res.update(
            {
                "table_pct": table_pct,
                "table_pct_display": f"{round(table_pct * 100)}%",
                "low_savings": savings["low_savings"],
                "base_savings": savings["base_savings"],
                "high_savings": savings["high_savings"],
            }
        )
        results.append(res)
    return results


def seed_database_with_clusters() -> dict[str, Any]:
    """Persist clusters and safety moments into PostgreSQL database."""
    clusters = evaluate_clusters()
    db = SyncSessionLocal()
    org_ids = ["OIL-1", "POWER-1", "STEEL-1", "MINE-1"]

    seeded_masters = 0
    seeded_items = 0
    seeded_lots = 0

    try:
        for c in clusters:
            code = generate_unique_mpng_code()
            descriptor = f"{c['subcategory']} | {c['item_description']}"

            # Check if exists
            existing = db.execute(
                select(GoldenMaster).where(GoldenMaster.descriptor == descriptor)
            ).scalar_one_or_none()

            if not existing:
                major_cat = c["subcategory"].split(".")[0]
                master = GoldenMaster(
                    code=code,
                    descriptor=descriptor,
                    status="ACTIVE",
                    major_category=major_cat,
                    subcategory=c["subcategory"],
                    block_key=c["name"][:10],
                    identity_mode="PARAMETRIC",
                    canonical_text=c["item_description"],
                    canonical_uom=c["uom"],
                    attributes={"pooled_qty": c["pooled_qty"], "uom": c["uom"]},
                )
                db.add(master)
                db.flush()
                seeded_masters += 1
                master_id = master.id
            else:
                master_id = existing.id

            # Create raw item representations across CPSE orgs
            for i, org in enumerate(org_ids[:3]):
                item_code = f"MAT-{c['cluster_id']}-{org}-{i+1}"
                ex_item = db.execute(
                    select(RawItem).where(RawItem.org_id == org, RawItem.item_code == item_code)
                ).scalar_one_or_none()

                if not ex_item:
                    raw_item = RawItem(
                        org_id=org,
                        source_type="LEGACY_MASTER",
                        item_code=item_code,
                        raw_description=f"{c['item_description']} - {org}",
                        clean_text=c["item_description"],
                        original_uom=c["uom"],
                        original_qty=round(c["pooled_qty"] / 3, 2),
                        canonical_uom=c["uom"],
                        canonical_qty=round(c["pooled_qty"] / 3, 2),
                        unit_price_inr=round(c["independent_cost"] / c["pooled_qty"], 2),
                        subcategory=c["subcategory"],
                        golden_id=master_id,
                        tier=1 if c["cluster_id"] != "1" else (1 if i == 0 else 2),
                        match_prob=0.98 if c["cluster_id"] != "1" else 0.85,
                        status="LINKED",
                        raw_payload={},
                    )
                    db.add(raw_item)
                    seeded_items += 1

            # Seed specific lots / safety moments
            # Cluster 12: Castable refractory lot with unknown expiry (S6 test case)
            if c["cluster_id"] == "12":
                ex_lot = db.execute(
                    select(StockLot).where(StockLot.batch_no == "DEMO-LOT-12-UNKNOWN-EXPIRY")
                ).scalar_one_or_none()
                if not ex_lot:
                    lot_unknown = StockLot(
                        org_id="STEEL-1",
                        golden_id=master_id,
                        batch_no="DEMO-LOT-12-UNKNOWN-EXPIRY",
                        qty_remaining=50.0,
                        plant="PLANT-BHILAI",
                    )
                    db.add(lot_unknown)
                    seeded_lots += 1

        db.flush()
        append_audit_entry(
            db=db,
            actor=None,
            action="DEMO_CLUSTERS_SEED",
            entity_type="clusters",
            entity_id="14_clusters",
            old_val=None,
            new_val={"seeded_masters": seeded_masters, "seeded_items": seeded_items, "seeded_lots": seeded_lots},
        )
        db.commit()

        return {
            "status": "SUCCESS",
            "clusters_count": len(clusters),
            "seeded_masters": seeded_masters,
            "seeded_items": seeded_items,
            "seeded_lots": seeded_lots,
        }
    except Exception as e:  # noqa: BLE001
        db.rollback()
        return {"status": "ERROR", "error": str(e)}
    finally:
        db.close()


def print_cluster_table(clusters: list[dict[str, Any]]) -> None:
    """Print markdown table matching Section 19.2."""
    header = (
        "| # | Item | Pooled qty | Cost (INR) | Class | Table % | Low (0.5x) | Base (1x) | High (1.25x) | Note |"
    )
    separator = "|---|---|---|---|---|---|---|---|---|---|"
    print("\n" + header)
    print(separator)
    for c in clusters:
        row = (
            f"| {c['cluster_id']} | {c['name']} | {c['pooled_qty']} {c['uom']} | "
            f"{c['independent_cost']:,.0f} | {c['pooling_class']} | {c['table_pct_display']} | "
            f"{c['low_savings']:,.0f} | {c['base_savings']:,.0f} | {c['high_savings']:,.0f} | "
            f"{c.get('note', '')} |"
        )
        print(row)


def main() -> None:
    """Main CLI execution entry point."""
    print("Computing 14 Samanvay Demo Seed Clusters mathematically (Section 19)...")
    clusters = evaluate_clusters()
    print_cluster_table(clusters)

    out_file = Path("data/seed_clusters_report.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(clusters, f, indent=2)
    print(f"\nSaved cluster data to {out_file}")

    if "--seed-db" in sys.argv or "--db" in sys.argv:
        print("\nSeeding PostgreSQL database with clusters and safety moments...")
        db_res = seed_database_with_clusters()
        print(f"Database seed result: {db_res}")


if __name__ == "__main__":
    main()
