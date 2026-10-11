---
name: samanvay-core-utils
description: Tested, standard-library-only reference implementations for the Samanvay material-code project (Verhoeff check digit for MPNG codes, pg_trgm-style trigram similarity, Jaro-Winkler, and a tamper-evident hash chain for the audit log). Use this skill whenever the project needs a national material code with a check digit, fuzzy text matching of material descriptions, candidate blocking, an audit trail or hash-chain verifier, or whenever the user asks to write these as their own functions instead of using a library.
---

# Samanvay core utilities (no third-party libraries)

Four small modules in `scripts/`, each pure Python standard library, each with table-driven tests in `scripts/test_core_utils.py`. Copy them into `api/core/` and keep the tests with them. Run the tests with:

```bash
python -m unittest scripts/test_core_utils.py -v
```

## What is here and when to use it

| Module | Use for | Notes |
|---|---|---|
| `verhoeff.py` | Generating and validating the check digit in `MPNG-<10 digits>-<check>` | Detects every single-digit error and every adjacent transposition (the tests prove it for the sample code). |
| `trigram.py` | Candidate generation and the fuzzy stage of 4.5 | Mirrors PostgreSQL `pg_trgm`: lowercase words, padded with two spaces in front and one behind, Jaccard similarity. Use it in Python tests and for in-memory blocking; use the database `pg_trgm` index in production queries. |
| `jaro_winkler.py` | Short token comparison (part numbers, brand names) | Returns 0.0 to 1.0. A similarity helps ranking; it never decides identity (spec invariants S9 and S14). |
| `hashchain.py` | Audit log verification, export checking, tests | The database trigger writes the real chain; this module recomputes it from exported rows so a verifier can run outside the database. |

## Rules for using them

- **Similarity never decides identity.** Both similarity functions return scores for ranking and candidate recall. Tiering is done by the attribute comparator. If you find yourself comparing a similarity to a threshold to link two items, stop and route it through the comparator.
- **Do not change the code format.** `MPNG-` + 10 digits + `-` + 1 check digit, 17 characters. Codes are opaque and permanent.
- **Canonical JSON for hashing.** `hashchain.canonical()` sorts keys and uses compact separators so the same record always hashes the same way on every machine.
- **Add a test before changing any function.** These are the places where a silent bug corrupts data for everyone.

## Extending

If a new helper is needed (for example a token-set ratio), write it next to these, keep it pure, and add three kinds of tests: normal cases, empty and unicode input, and a property such as symmetry (`sim(a, b) == sim(b, a)`).
