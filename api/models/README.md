# Database Models Module (`api/models/`)

This directory contains SQLAlchemy 2.0 ORM models for all relational tables defined in [specsheet.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md) Section 9.2.

---

## 1. Purpose

The models map application objects to PostgreSQL 18 tables:
1. Multi-tenant organizational metadata and users.
2. The golden master material catalog and CPSE code aliases.
3. Ingested raw line items and document records.
4. Maker-Checker stewardship tasks and feedback logs.
5. The tamper-evident append-only audit trail.

---

## 2. Table Groups (Simplified Technical English)

### 2.1 Governance and Identity
- `organizations`: Stores participating enterprises (e.g. `OIL-1`, `POWER-1`, `STEEL-1`, `MINE-1`).
- `users`: Stores actors, their system roles (`MAKER`, `CHECKER`, etc.), and domain tags (`domains`).
- `golden_masters`: Master catalog items with permanent `MPNG-` codes and normalized canonical descriptors.
- `golden_aliases`: Cross-references mapping each CPSE's internal item codes, drawing numbers, or OEM part numbers to the single golden master.

### 2.2 Ingestion and Documents
- `documents`: Uploaded POs, GRNs, invoices, and MTC certificates with SHA-256 hashes for duplicate detection.
- `doc_lines`: Bounding boxes, extracted OCR lines, and line-level confidence scores.
- `raw_items`: Raw lines from CSV/XLSX or documents with unedited payloads preserved verbatim.

### 2.3 Stewardship and Audit
- `steward_tasks`: Human validation tasks enforcing Maker $\ne$ Checker separation.
- `audit_log`: Append-only hash chain recording every create, update, merge, and split.

---

## 3. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Migrations, seeds, and Row-Level Security.
- [api/security/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/README.md): Role and domain authorization.
