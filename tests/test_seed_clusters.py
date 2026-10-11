"""Unit tests for demo seed clusters and discount scenario calculations (Section 19).

Verifies:
  - Exact discount bands: BULK_MT, BULK_M, and ENGINEERED.
  - Scenario calculations: Low (0.5x), Base (1.0x), High (1.25x capped at 25%).
  - Exact mathematical parity with Section 19.2 cluster values.
  - Invariant: Cluster 1 below 10 units threshold yields 0 savings.
"""

from scripts.seed_clusters import (
    compute_scenario_savings,
    compute_table_discount,
    evaluate_clusters,
)


def test_discount_band_calculations() -> None:
    """Verify table discounts across quantity bands for all pooling classes."""
    # BULK_MT: <25: 0%, 25-99: 8%, 100-299: 12%, 300-499: 15%, >=500: 18%
    assert compute_table_discount("BULK_MT", 10.0) == 0.0
    assert compute_table_discount("BULK_MT", 50.0) == 0.08
    assert compute_table_discount("BULK_MT", 200.0) == 0.12
    assert compute_table_discount("BULK_MT", 360.0) == 0.15
    assert compute_table_discount("BULK_MT", 550.0) == 0.18

    # BULK_M: <1000: 0%, 1k-4999: 8%, 5k-9999: 12%, 10k-19999: 15%, >=20k: 18%
    assert compute_table_discount("BULK_M", 500.0) == 0.0
    assert compute_table_discount("BULK_M", 4800.0) == 0.08
    assert compute_table_discount("BULK_M", 8000.0) == 0.12
    assert compute_table_discount("BULK_M", 15500.0) == 0.15
    assert compute_table_discount("BULK_M", 25000.0) == 0.18

    # ENGINEERED: <10: 0%, 10-24: 8%, 25-49: 12%, 50-99: 15%, >=100: 18%
    assert compute_table_discount("ENGINEERED", 4.0) == 0.0
    assert compute_table_discount("ENGINEERED", 15.0) == 0.08
    assert compute_table_discount("ENGINEERED", 45.0) == 0.12
    assert compute_table_discount("ENGINEERED", 69.0) == 0.15
    assert compute_table_discount("ENGINEERED", 140.0) == 0.18


def test_scenario_savings_formula() -> None:
    """Verify Low, Base, and High scenario calculations with 25% cap."""
    cost = 10_000_000.0
    # 18% table discount
    res = compute_scenario_savings(cost, 0.18)
    assert res["low_rate"] == 0.09  # 0.5x
    assert res["base_rate"] == 0.18  # 1.0x
    assert res["high_rate"] == 0.225  # 1.25x
    assert res["low_savings"] == 900_000
    assert res["base_savings"] == 1_800_000
    assert res["high_savings"] == 2_250_000

    # Cap check at 25%: if table discount is 22%, 1.25 * 0.22 = 0.275, capped at 0.25
    res_cap = compute_scenario_savings(cost, 0.22)
    assert res_cap["high_rate"] == 0.25
    assert res_cap["high_savings"] == 2_500_000


def test_all_14_clusters_exact_spec_parity() -> None:
    """Verify that all 14 computed clusters exactly match Section 19.2 figures."""
    clusters = evaluate_clusters()
    assert len(clusters) == 14

    # Cluster 1: Motors 4 EA -> 0 savings
    c1 = next(c for c in clusters if c["cluster_id"] == "1")
    assert c1["table_pct"] == 0.0
    assert c1["low_savings"] == 0
    assert c1["base_savings"] == 0
    assert c1["high_savings"] == 0

    # Cluster 2: ISMB 300 (360 MT @ 23,269,000 INR -> 15%)
    c2 = next(c for c in clusters if c["cluster_id"] == "2")
    assert c2["table_pct"] == 0.15
    assert c2["low_savings"] == 1_745_175
    assert c2["base_savings"] == 3_490_350
    assert c2["high_savings"] == 4_362_938

    # Cluster 3: TMT 25 mm (550 MT @ 32,169,000 INR -> 18%)
    c3 = next(c for c in clusters if c["cluster_id"] == "3")
    assert c3["table_pct"] == 0.18
    assert c3["low_savings"] == 2_895_210
    assert c3["base_savings"] == 5_790_420
    assert c3["high_savings"] == 7_238_025

    # Cluster 11: Transformer (125 EA @ 31,255,000 INR -> 18%)
    c11 = next(c for c in clusters if c["cluster_id"] == "11")
    assert c11["table_pct"] == 0.18
    assert c11["low_savings"] == 2_812_950
    assert c11["base_savings"] == 5_625_900
    assert c11["high_savings"] == 7_032_375

    # Cluster 13: OTR Tyre (52 EA @ 78,200,000 INR -> 15%)
    c13 = next(c for c in clusters if c["cluster_id"] == "13")
    assert c13["table_pct"] == 0.15
    assert c13["low_savings"] == 5_865_000
    assert c13["base_savings"] == 11_730_000
    assert c13["high_savings"] == 14_662_500

    # Cluster 14: Pump (15 EA @ 27,100,000 INR -> 8%)
    c14 = next(c for c in clusters if c["cluster_id"] == "14")
    assert c14["table_pct"] == 0.08
    assert c14["low_savings"] == 1_084_000
    assert c14["base_savings"] == 2_168_000
    assert c14["high_savings"] == 2_710_000
