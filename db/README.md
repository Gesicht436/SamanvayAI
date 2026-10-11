# Database Management (`db/`)

This directory contains database migrations, seed data, and schema management utilities for Samanvay.

---

## 1. Architecture

Samanvay uses a single datastore architecture: **PostgreSQL 18** with:
- `pgvector`: High-dimensional vector embeddings (no separate vector database).
- `pg_trgm`: Fast trigram text similarity indexing for description blocking.
- `pgcrypto`: Cryptographic hashing for audit log triggers (`digest(..., 'sha256')`).
- `btree_gin`: Composite GIN indexes for JSONB attribute indexing.

---

## 2. Security and Data Protection

### 2.1 Row-Level Security (RLS)
Enterprise data isolation is enforced at the database level:
- Tenant tables (`documents`, `doc_lines`, `raw_items`, etc.) enable RLS.
- Policies evaluate: `org_id = current_setting('app.current_org', true)`.
- If the session variable is unset or empty, queries return 0 rows (fail closed).

### 2.2 Tamper-Evident Audit Log Trigger
The `audit_log` table is protected by PostgreSQL triggers:
- Linear sequencing uses transaction advisory lock: `pg_advisory_xact_lock(727001)`.
- Hashes are calculated automatically:
  $$\text{this\_hash} = \text{SHA-256}(\text{prev\_hash} \,\|\, \text{record\_fields})$$
- Triggers raise exceptions on any `UPDATE`, `DELETE`, or `TRUNCATE` operations.

---

## 3. Directory Index

| Subdirectory / File | Role |
|---|---|
| [migrations/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/migrations/README.md) | Alembic migration versions and environment configuration. |
| [seed/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/seed/README.md) | Synthetic CPSE enterprise and user seeds. |
| [reset.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/reset.py) | Full schema purge utility for clean testing. |

---

## 4. Manual Testing Guide

Perform database operations using `uv`:

```powershell
# 1. Reset database to empty state
uv run python -m db.reset

# 2. Run all migrations
uv run alembic upgrade head

# 3. Seed foundation organizations and users
uv run python -m db.seed.seed_foundations
```

---

## 5. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System overview.
- [api/models/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/models/README.md): SQLAlchemy entity models.
- [docs/verification.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md): Verification register.
