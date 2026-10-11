# Database Migrations Module (`db/migrations/`)

This directory contains Alembic database migration scripts for PostgreSQL 18.

---

## 1. Purpose

The migrations define the relational schema, PostgreSQL extensions, triggers, and Row-Level Security policies.
It tracks database evolution version by version.

---

## 2. Hard Migration Rules (ASD-STE100)

1. **Never edit an applied migration:** Always create a new sequential migration script.
2. **Never drop audit triggers:** The audit log must remain strictly append-only.
3. **Tenant tables must have Row-Level Security:** Every table storing enterprise data must enable RLS using `app.current_org`.

---

## 3. Migration Sequence

| Revision ID | Description |
|---|---|
| `0001_initial_schema` | Enables extensions, creates Section 9.2 tables, installs append-only audit trigger, and configures Row-Level Security policies. |

---

## 4. Manual Testing Guide

Run migrations using `uv`:

```powershell
# Apply all migrations to the latest version
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current database migration state
uv run alembic current
```

---

## 5. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database infrastructure overview.
- [api/models/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/models/README.md): SQLAlchemy models.
