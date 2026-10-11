---
name: verify-claims
description: Handles every external fact marked VERIFY, such as standards, statutory rules, ERP field lengths, product data and life values, by logging it in docs/verification.md instead of inventing it. Use whenever you write or read a VERIFY marker, a standard number, a regulation, a rating, or a shelf-life value.
---

# Verify claims

You cannot verify external facts yourself from memory. Your job is to keep them visible and open until a human supplies a primary source.

## Steps
1. When code or data needs an external fact you were not given, write the marker `# VERIFY: <id>` in code, or `[VERIFY]` in Markdown, and use a placeholder with `verified = false`.
2. Add a row to `docs/verification.md` with columns: `id`, `claim`, `where used`, `primary source needed`, `status` (OPEN or VERIFIED), `checked by`, `date`.
3. Run `make verify-claims`. It must fail if any `# VERIFY:` marker in code has no row.
4. In your report, list new OPEN rows so the user can check them.

## Hard rules
- Never set a row to VERIFIED yourself. Only the user does, after reading the primary source.
- Never write a standard number, clause, statutory body, rating or shelf life from memory as if it were fact.
- Never state compliance with any standard or regulation in code comments, UI text or documents.
