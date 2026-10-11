---
name: samanvay-eval-gate
description: Evaluation and release-gate skill for the Samanvay material-code project. Computes exact binomial (Clopper-Pearson) confidence bounds with no libraries, checks the hard release gates (hard-negative false merges, missing-attribute routing, low-confidence OCR in Tier 1, MTC conformance against unverified references, auto-tier precision), and writes honest result statements. Use this skill whenever reporting accuracy, precision, false-merge rate or any evaluation number, running or editing `make eval-gate`, preparing slides or a README with results, or when the user asks "is it safe", "how accurate is it" or "can we claim zero errors".
---

# Samanvay evaluation gate

Numbers in the pitch and README must survive a jury member asking "how do you know?". This skill makes every claim an observed rate with an interval, and blocks releases that break a hard gate.

## Reporting rules

- Report **observed rate and interval**, never "zero errors". "0 false merges in 150 hard negatives; the 95% upper bound is 2.4%" is honest and strong. "Zero false merges" is not.
- Use the exact Clopper-Pearson interval (`scripts/clopper_pearson.py`), two-sided by default, and say which.
- Report **per sector and per organisation**, not only overall, so one easy slice cannot hide a weak one. A gap above the configured parity threshold is a finding.
- State the split (train, dev, locked test), the number of pairs, and how the labels were produced (public, synthetic, steward-labelled). Never tune on the locked test set.
- Show the baselines side by side: cosine-only, trigram-only, the rule-based path, and (only when enabled) the optional ML layer.

## Hard gates

`scripts/gate_check.py` reads a metrics JSON and fails (exit code 1) if any of these is violated:

| Gate | Condition to pass |
|---|---|
| Hard-negative false merges | exactly 0 observed |
| Missing-attribute routing | 100% routed to Tier 2 or lower |
| Low-confidence OCR items in Tier 1 | 0 |
| MTC `CONFORMS` against an unverified reference | 0 |
| Auto-tier precision (dev) | at or above the target (default 0.995) |

Example input (`metrics.json`):

```json
{
  "hard_negative_pairs": 150,
  "hard_negative_false_merges": 0,
  "missing_attr_cases": 80,
  "missing_attr_routed_ok": 80,
  "low_ocr_in_tier1": 0,
  "mtc_conforms_unverified": 0,
  "auto_tier_tp": 398,
  "auto_tier_fp": 1,
  "precision_target": 0.995
}
```

Run:

```bash
python scripts/gate_check.py metrics.json
```

It prints each gate with the observed value and the 95% interval, and exits non-zero on failure. Wire it into `make eval-gate`.

## Writing the result sentence

Template: "On N locked-test pairs (sources), the system made K false merges; the 95% Clopper-Pearson upper bound is U%. Auto-tier precision on dev was P% (interval L% to H%) against a target of T%." If a gate fails, say so plainly and list the failing cases; do not lower the target to pass.

## When an interval is wider than you want

The only honest fixes are more labelled pairs or a narrower claim. Show the user the sample size needed: for 0 failures, the one-sided 95% upper bound is about 3/n, so 300 hard negatives are needed to support "under 1%".
