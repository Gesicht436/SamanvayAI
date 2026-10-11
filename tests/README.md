# Test Suite Module (`tests/`)

This directory contains automated unit, integration, and security tests for Samanvay.
All tests run with `uv run pytest`.

---

## 1. Test Suite Index

| Test File | Target Module | What It Verifies |
|---|---|---|
| [test_core_utils.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_core_utils.py) | `api/core/` | Verhoeff check digits, single-digit errors, adjacent transposition detection, Trigram similarity, Jaro-Winkler, and SHA-256 hash chains. |
| [test_auth.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_auth.py) | `api/security/` | HS256 JWT encoding/decoding, expiration handling, and Maker-Checker ($Maker \ne Checker$) rules. |
| [test_routes.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_routes.py) | `api/routers/` | Every API endpoint is audited against the public allow-list; unlisted routes require authentication. |
| [test_database_features.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_database_features.py) | `db/` | PostgreSQL append-only audit trigger (blocks `UPDATE`/`DELETE`), hash linkage, and Row-Level Security isolation across tenant organizations. |
| [test_normalize.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_normalize.py) | `api/services/` | Unicode script detection, Indic transliteration, quote mapping, fastener `STD` gating, and collision token preservation. |
| [test_uom.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_uom.py) | `api/services/` | Controlled UoM vocabulary, scalar conversions, rebar $d^2/162$, IS 808 section lookups, and `MissingConversionAttribute` guards. |
| [test_ingest.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_ingest.py) | `api/services/` | CSV and XLSX parsing, verbatim raw payloads, row error reporting, SHA-256 file hash idempotency, and transactional audit logging. |

---

## 2. Manual Testing Guide

Run tests using `uv`:

```powershell
# Run all tests in the repository
uv run pytest tests/ -v

# Run only core mathematical tests
uv run pytest tests/test_core_utils.py -v

# Run database integration tests (requires docker compose up -d db)
uv run pytest tests/test_database_features.py -v

# Run authentication and route security tests
uv run pytest tests/test_auth.py tests/test_routes.py -v

# Run text normalization and UoM tests
uv run pytest tests/test_normalize.py tests/test_uom.py -v

# Run master data ingestion tests
uv run pytest tests/test_ingest.py -v
```

---

## 3. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [api/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/README.md): Backend framework.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database migrations.
