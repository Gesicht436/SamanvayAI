---
name: safety-tests
description: Writes and maintains the property tests and mutation check for the safety invariants S1 to S14 that guard matching and tiering. Use when touching the comparator, tiering, scoring, lifecycle or document-duplicate code, or when asked about invariants or Tier 1 safety.
---

# Safety invariant tests

The invariants are in `docs/spec/06.md` (or section 6 of `SPEC.md`). Read them verbatim before you write anything. Do not paraphrase them from memory.

## Steps
1. List every invariant, S1 to S14, and map each to at least one Hypothesis property test named `test_S<n>_<short_description>`.
2. Generators must cover: missing attributes, mismatched attributes, extraction flags, low OCR confidence, expired and unknown-expiry lots, reordered input keys, and all three identity modes.
3. Run each property with at least 300 examples. Never lower the example count.
4. Write the mutation check: deliberately break the Tier 1 gating (for example let a missing HARD attribute pass) and confirm that the suite fails. Restore the code afterwards.
5. Add a golden-file verdict matrix for the attribute verdicts EXACT, MISSING, MISMATCH and UPGRADE.
6. Run `make test` and report which invariants are covered and the example counts.

## Hard rules
- Never use `skip`, `xfail`, a lower example count, or a weaker assertion to get a test passing.
- A failing invariant test means the code is wrong. Fix the code, or if the requirement itself seems wrong, write the conflict to `docs/open-questions.md` and stop.
- The scoring model may lower a tier, never raise a gated item to Tier 1.
