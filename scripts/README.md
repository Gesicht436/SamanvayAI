# Developer and Operational Scripts (`scripts/`)

This directory contains command-line scripts for operations, dependency auditing, and token generation.

---

## 1. Purpose

The scripts provide developer conveniences:
1. Generating signed JWT demo tokens for testing API endpoints.
2. Auditing project imports against the standard-library-first policy.

---

## 2. File Index

| Script | Purpose |
|---|---|
| [cold_start_dedup.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/cold_start_dedup.py) | CLI for cold-start deduplication clustering, report generation, and scale benchmarking. |
| [scan_tier1.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/scan_tier1.py) | Static safety auditor ensuring `assign_tier` in `tiering.py` is the single source of Tier 1 truth. |
| [generate_standard_fixtures.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/generate_standard_fixtures.py) | Generates test fixtures and adversarial hard-negatives for all 15 standard material families. |
| [demo_token.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/demo_token.py) | Generates a signed HS256 JWT access token with selectable role and domain tags. |
| [audit_imports.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/audit_imports.py) | Scans Python files to detect third-party packages and suggests standard-library alternatives. |
| [verify_claims.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/verify_claims.py) | Verifies that every `# VERIFY:` marker in code has a corresponding registered claim in `docs/verification.md`. |

---

## 3. Manual Testing Guide

Run scripts using `uv`:

```powershell
# Run cold-start deduplication benchmark CLI (10,000 synthetic items)
uv run python scripts/cold_start_dedup.py --count 10000

# Run static safety scan for unauthorized Tier 1 leaks
uv run python scripts/scan_tier1.py .

# Generate a Maker token for OIL-1
uv run python scripts/demo_token.py --org OIL-1 --role MAKER --domains COMMON

# Generate a Checker token with domain tags for POWER-1
uv run python scripts/demo_token.py --org POWER-1 --role CHECKER --domains POWER COMMON

# Run import auditor across the codebase
uv run python scripts/audit_imports.py

# Run verification claims checker across the codebase
uv run python -m scripts.verify_claims
# or
make verify-claims
```

---

## 4. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System overview.
- [api/security/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/README.md): Authentication rules.
- [docs/VERSIONS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/VERSIONS.md): Tracked package versions.
