#!/usr/bin/env python3
"""Check Samanvay release gates from a metrics JSON. Exit 1 if any gate fails.

Usage: python scripts/gate_check.py metrics.json
Standard library only.
"""

import json
import sys
from pathlib import Path

# Support running directly or as a module
try:
    from scripts.clopper_pearson import clopper_pearson
except ImportError:
    from clopper_pearson import clopper_pearson


def check(m: dict) -> list[tuple[str, bool, str]]:
    """Evaluates all hard release gates against the provided metrics dictionary."""
    results: list[tuple[str, bool, str]] = []

    # Gate 1: Hard-negative false merges
    n = m.get("hard_negative_pairs", 0)
    k = m.get("hard_negative_false_merges", 0)
    if n > 0:
        lo, hi = clopper_pearson(k, n)
        results.append(
            (
                "Hard-negative false merges",
                k == 0,
                f"{k}/{n} observed; 95% interval {lo:.2%} to {hi:.2%}",
            )
        )
    else:
        results.append(("Hard-negative false merges", False, "0 test pairs evaluated"))

    # Gate 2: Missing-attribute routing
    n_miss = m.get("missing_attr_cases", 0)
    ok_miss = m.get("missing_attr_routed_ok", 0)
    if n_miss > 0:
        lo, hi = clopper_pearson(ok_miss, n_miss)
        results.append(
            (
                "Missing-attribute routing",
                ok_miss == n_miss,
                f"{ok_miss}/{n_miss} routed to Tier 2; 95% interval {lo:.2%} to {hi:.2%}",
            )
        )
    else:
        results.append(("Missing-attribute routing", False, "0 missing-attribute cases evaluated"))

    # Gate 3: Low-confidence OCR in Tier 1
    low_ocr = m.get("low_ocr_in_tier1", 0)
    results.append(("Low-confidence OCR in Tier 1", low_ocr == 0, f"{low_ocr} found in Tier 1"))

    # Gate 4: MTC conforms against unverified reference
    mtc_unverified = m.get("mtc_conforms_unverified", 0)
    results.append(
        (
            "MTC conforms against unverified reference",
            mtc_unverified == 0,
            f"{mtc_unverified} found",
        )
    )

    # Gate 5: Auto-tier precision (dev)
    tp = m.get("auto_tier_tp", 0)
    fp = m.get("auto_tier_fp", 0)
    total_auto = tp + fp
    target = m.get("precision_target", 0.995)
    if total_auto == 0:
        results.append(("Auto-tier precision (dev)", False, "no auto-tier decisions to evaluate"))
    else:
        lo, hi = clopper_pearson(tp, total_auto)
        prec = tp / total_auto
        results.append(
            (
                "Auto-tier precision (dev)",
                prec >= target,
                f"{prec:.2%} ({tp}/{total_auto}); 95% interval {lo:.2%} to {hi:.2%}; target {target:.2%}",
            )
        )

    return results


def run_gate_check(metrics_path_or_dict: str | Path | dict) -> int:
    """Executes the gate check on a path or dictionary and prints a formatted report."""
    if isinstance(metrics_path_or_dict, (str, Path)):
        path = Path(metrics_path_or_dict)
        if not path.exists():
            print(f"Error: metrics file not found: {path}")
            return 2
        with open(path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    else:
        metrics = metrics_path_or_dict

    results = check(metrics)
    width = max(len(name) for name, _, _ in results)

    print("\n" + "=" * 70)
    print("Samanvay Release Gate Evaluation (Exact Clopper-Pearson)")
    print("=" * 70)
    for name, ok, detail in results:
        status_str = "PASS" if ok else "FAIL"
        print(f"[{status_str}] {name:<{width}}  {detail}")

    failed = [name for name, ok, _ in results if not ok]
    print("-" * 70)
    if not failed:
        print("GATE: ALL GATES PASSED")
        print("=" * 70 + "\n")
        return 0
    else:
        print("GATE: FAILED (" + "; ".join(failed) + ")")
        print("=" * 70 + "\n")
        return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    return run_gate_check(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
