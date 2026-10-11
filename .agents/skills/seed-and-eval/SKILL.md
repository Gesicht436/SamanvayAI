---
name: seed-and-eval
description: Generates synthetic seed data and demo clusters by script and runs the evaluation harness with baselines, intervals and parity reports. Use when creating seed or demo data, fixtures at scale, cluster tables, or when running or changing evaluation.
---

# Seed data and evaluation

See `docs/spec/14.md` (evaluation) and `docs/spec/19.md` (demo clusters).

## Steps for seed data
1. Generate all data from scripts under `scripts/`. Never type totals, counts or savings by hand.
2. Label all data synthetic. Use neutral organisation labels (`OIL-1`, `POWER-2`, `STEEL-1`, `MINE-1`, `HEAVY-1`). Never attribute invented quantities or prices to real organisations.
3. Use a fixed random seed and record it so the data can be reproduced.
4. Compute cluster tables from the inputs with the discount class and scenario rules in section 19.

## Steps for evaluation
1. Keep the train, dev and test splits separate. Never tune thresholds on the test split.
2. Run `make eval`. Report all baselines side by side with the system.
3. Report an interval for every headline rate (use an exact binomial interval for zero-failure results), not just a point value.
4. Report per-organisation and per-sector parity and flag any group that deviates beyond the configured margin; label groups with fewer than 100 test pairs as low-sample.
5. Write the report to `reports/eval-<date>.md`, then run `make eval-gate`.

## Hard rules
- Never claim a figure that the scripts did not produce.
- Never present savings as anything other than a scenario range.
