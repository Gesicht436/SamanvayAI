# Database Seed Data (`db/seed/`)

This directory contains deterministic seed scripts to populate initial CPSE organizations, plants, and users.

---

## 1. Purpose

The seed data enables immediate local development and demonstration without hand-typing data.
It provides realistic, synthetic records respecting the **Organization Neutrality Principle** (Section 1.3).

---

## 2. Seeded Entities

### 2.1 Organizations
- `OIL-1`: Hydrocarbon & Refining enterprise (Oil & Gas sector).
- `POWER-1`: Thermal and renewable power generation enterprise (Power sector).
- `STEEL-1`: Integrated steel manufacturing enterprise (Steel sector).
- `MINE-1`: Coal and mineral exploration enterprise (Mining sector).

### 2.2 Users
Every enterprise has:
- A **Maker** with `role: MAKER` and domain tag `COMMON`.
- A **Checker** with `role: CHECKER` and domain tags matching their enterprise sector (e.g. `POWER`, `STEEL`, `MINING`, `REFINING`).

---

## 3. Manual Testing Guide

Run the seed script using `uv`:

```powershell
uv run python -m db.seed.seed_foundations
```

---

## 4. Connected Documentation

- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database infrastructure.
- [api/security/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/README.md): User roles and domain tags.
