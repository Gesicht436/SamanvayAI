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
| [demo_token.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/demo_token.py) | Generates a signed HS256 JWT access token with selectable role and domain tags. |
| [audit_imports.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/audit_imports.py) | Scans Python files to detect third-party packages and suggests standard-library alternatives. |
| [verify_claims.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/verify_claims.py) | Verifies that every `# VERIFY:` marker in code has a corresponding registered claim in `docs/verification.md`. |

---

## 3. Manual Testing Guide

Run scripts using `uv`:

```powershell
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
