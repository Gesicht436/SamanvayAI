# Samanvay Dependency and Tooling Versions

This file records exact package and tool versions resolved at installation time via `uv`. Never pin from memory.

---

## 1. Runtime Environment

- **Python:** 3.12.15 (managed via `uv`)
- **Package Manager:** `uv` 0.12.23
- **Database Engine:** PostgreSQL 18 (with extensions `pgvector`, `pg_trgm`, `pgcrypto`, `btree_gin`; development container image `pgvector/pgvector:pg17`)

---

## 2. Core Backend Dependencies

| Package | Resolved Version | Purpose |
|---|---|---|
| `fastapi` | 0.143.0 | Asynchronous REST API framework |
| `sqlalchemy` | 2.1.4 | Asynchronous SQL ORM and query builder |
| `alembic` | 1.20.0 | Database migration framework |
| `psycopg` | 3.3.6 | Native PostgreSQL 3 driver |
| `psycopg-binary` | 3.3.6 | Pre-compiled PostgreSQL binaries |
| `pydantic` | 2.14.0 | Schema validation and data modeling |
| `pydantic-settings` | 2.15.0 | Application configuration via environment variables |
| `structlog` | 26.1.0 | Structured JSON logging |
| `pyjwt` | 2.15.1 | JWT token encoding and verification |
| `openpyxl` | 3.1.5 | Microsoft Excel XLSX spreadsheet parser |
| `python-multipart` | 0.0.32 | Multipart/form-data parser for file uploads |
| `pyyaml` | 6.0.3 | YAML parser for sector pack specifications and lexicons |
| `pymupdf` | 1.28.2 | PDF text layer and raster rendering engine |
| `uvicorn` | 0.54.0 | ASGI web server implementation |


---

## 3. Development and Quality Dependencies

| Package | Resolved Version | Purpose |
|---|---|---|
| `pytest` | 9.1.1 | Unit and functional test runner |
| `pytest-asyncio` | 1.4.0 | Async test support for pytest |
| `hypothesis` | 6.168.5 | Property-based testing framework for invariants S1–S15 |
| `ruff` | 0.17.0 | Fast linter and formatter |
| `httpx` | 0.28.1 | Asynchronous HTTP client for API testing |
