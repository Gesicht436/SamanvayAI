#!/usr/bin/env python3
"""Check Samanvay release gates from a metrics JSON. Exit 1 if any gate fails.

Usage: python gate_check.py metrics.json
Standard library only.
"""
import json
import sys
from clopper_pearson import clopper_pearson


def check(m: dict):
    results = []

    n, k = m["hard_negative_pairs"], m["hard_negative_false_merges"]
    lo, hi = clopper_pearson(k, n)
    results.append(("Hard-negative false merges", k == 0,
                    f"{k}/{n} observed; 95% interval {lo:.2%} to {hi:.2%}"))

    n, ok = m["missing_attr_cases"], m["missing_attr_routed_ok"]
    lo, hi = clopper_pearson(ok, n)
    results.append(("Missing-attribute routing", ok == n,
                    f"{ok}/{n} routed; 95% interval {lo:.2%} to {hi:.2%}"))

    results.append(("Low-confidence OCR in Tier 1", m["low_ocr_in_tier1"] == 0,
                    f"{m['low_ocr_in_tier1']} found"))
    results.append(("MTC conforms against unverified reference", m["mtc_conforms_unverified"] == 0,
                    f"{m['mtc_conforms_unverified']} found"))

    tp, fp = m["auto_tier_tp"], m["auto_tier_fp"]
    n = tp + fp
    target = m.get("precision_target", 0.995)
    if n == 0:
        results.append(("Auto-tier precision (dev)", False, "no auto-tier decisions to evaluate"))
    else:
        lo, hi = clopper_pearson(tp, n)
        prec = tp / n
        results.append(("Auto-tier precision (dev)", prec >= target,
                        f"{prec:.2%} ({tp}/{n}); 95% interval {lo:.2%} to {hi:.2%}; target {target:.2%}"))
    return results


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        metrics = json.load(f)
    results = check(metrics)
    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<{width}}  {detail}")
    failed = [name for name, ok, _ in results if not ok]
    print("\nGATE: " + ("PASS" if not failed else "FAIL (" + "; ".join(failed) + ")"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
