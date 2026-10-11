---
name: add-family
description: Adds a new material family (a subcategory such as a valve, transformer or pump) to a domain pack with its spec, lexicon, parser, fixtures and hard negatives. Use when asked to build, add or extend a family, a domain, or a sector pack.
---

# Add a material family

Inputs you need: the pack (`common`, `power`, `steel`, `mining`, `heavy_eng`), the family name, and its depth (deep or standard). The depth table is in `docs/spec/02.md`; the family definitions are in `docs/spec/18.md` (power, steel, mining, heavy engineering) and `docs/spec/07.md` (common families). Attribute roles are in `docs/spec/05.md`.

## Steps
1. Read the family's section and the attribute-role rules. Do not rely on memory for any standard, rating or conversion.
2. Write the tests first: table-driven parser tests using the test strings given in the spec, plus failure cases (invalid value gives `None` plus a flag, never a guess).
3. Create `packs/<pack>/specs/<family>.yaml` with: `subcategory`, `segment`, `identity_mode`, `safety_critical`, `pooling_class`, `expiry_required` where relevant, `primary_dimension`, and `attributes` (each with `name`, `role` HARD, REQUIRED or SOFT, optional `when`, optional `statutory`).
4. Create `packs/<pack>/lexicons/<family>.yaml`. Write a Python parser in `packs/<pack>/parsers/` only when the logic is real.
5. Parser rules: category gating, an evidence span for every value, `None` plus a flag for invalid values, and `MissingConversionAttribute` when a conversion needs an unknown attribute.
6. Create fixtures in `packs/<pack>/fixtures/<family>.csv`: deep families need 40 or more rows, standard families 20 or more, with messy real-world spellings.
7. Create hard-negative pairs in `packs/<pack>/eval/pairs.csv`: deep 15 or more, standard 8 or more, each pair differing in exactly one criterion.
8. Add standards as reference IDs only with `verified = false`, in `packs/<pack>/standards/seed.csv`.
9. Run `make test-pack PACK=<pack>`. Report extraction accuracy per attribute.
10. Confirm that no hard negative reaches Tier 1 and that every missing-attribute case lands in Tier 2.

## Hard rules
- Do not invent standard numbers, clause numbers, ratings or regulations. Mark each as `[VERIFY]` and add a row to `docs/verification.md` (use the `verify-claims` skill).
- Do not edit another pack or the core to make this family work. If the core must change, stop and write the reason to `docs/open-questions.md`.
- A family is not finished until step 9 and step 10 are reported with real output.
