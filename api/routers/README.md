# API Routers Module (`api/routers/`)

This directory contains the FastAPI HTTP route definitions.

---

## 1. Purpose

The `api/routers/` directory exposes the REST endpoints of Samanvay:
1. System diagnostics and operational health status (`/health`).
2. Authentication and demo token generation (`/auth/demo-token`).
3. Cryptographic audit log verification (`/audit/verify`).

---

## 2. Endpoint Index

| Method | Endpoint | Protection | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Returns service readiness, clock mode, and demo status. |
| `POST` | `/auth/demo-token` | Public | Generates a signed HS256 JWT token for testing. |
| `GET` | `/audit/verify` | Authenticated | Verifies the sequential SHA-256 chain of `audit_log`. |
| `POST` | `/normalize` | Public | Normalizes raw description, transliterates Indic, expands abbrevs. |
| `POST` | `/uom/convert` | Public | Standardizes unit of measure and converts to canonical base. |
| `POST` | `/ingest/upload` | Authenticated | Ingests CSV or XLSX master data file with idempotency and audit trail. |
| `POST` | `/extract` | Public | Extracts typed attributes, confidence, evidence spans, and warning flags. |
| `GET` | `/extract/specs` | Public | Lists all registered subcategory specifications across loaded packs. |
| `GET` | `/extract/specs/{subcat}` | Public | Returns detailed specification attributes and identity mode. |
| `POST` | `/extract/sync` | Authenticated (Maker) | Synchronizes in-memory specifications into PostgreSQL database tables. |
| `POST` | `/compare` | Public | Compares requirement attributes with candidate attributes with verdicts. |
| `POST` | `/tier` | Public | Evaluates safety invariants S1-S15 and assigns harmonization tier (1, 2, 3). |
| `POST` | `/match` | Authenticated | End-to-end harmonization matching raw query to golden masters with calibrated scoring. |
| `POST` | `/tasks` | Authenticated (Maker) | Creates a new stewardship task proposal (LINK, CREATE_MASTER, MERGE, SPLIT, etc.). |
| `GET` | `/tasks` | Authenticated | Lists stewardship queue tasks with state and kind filtering. |
| `GET` | `/tasks/{task_id}` | Authenticated | Retrieves a single stewardship task by ID. |
| `POST` | `/tasks/{task_id}/approve` | Authenticated (Checker) | Approves task with Maker != Checker and domain tag validation. |
| `POST` | `/tasks/{task_id}/reject` | Authenticated (Checker) | Rejects task and captures negative feedback example. |
| `POST` | `/docs` | Authenticated | Ingests document via file upload or camera capture with duplicate check (S10). |
| `POST` | `/docs/paste` | Authenticated | Ingests raw text skipping OCR with `PASTED_TEXT` line flags. |
| `GET` | `/docs/{id}` | Authenticated | Retrieves document metadata, file hash, and invoice key. |
| `GET` | `/docs/{id}/lines` | Authenticated | Returns extracted lines with bounding boxes and OCR confidence. |
| `POST` | `/docs/precheck` | Authenticated | Pre-procurement duplicate check against golden masters without persisting items. |
| `POST` | `/docs/{id}/mtc` | Authenticated | Evaluates chemistry, derived CE/PREN, and reference conformance (S15). |
| `GET` | `/lots` | Authenticated | Lists stock lots with risk status, remaining days, and Stream A eligibility. |
| `GET` | `/lots/{id}` | Authenticated | Returns full lot details, remaining life across bases, and disposition ladder. |
| `POST` | `/lots/{id}/usage` | Authenticated | Records physical usage event, reducing quantity and remaining life (S8). |
| `GET` | `/lots/{id}/disposition` | Authenticated | Returns ordered 4-step FEFO disposition ladder. |

---

## 3. Manual Testing Guide

Start the development server using `uv`:

```powershell
uv run uvicorn api.main:app --reload --port 8000
```

### 3.1 Test Health Endpoint
```powershell
curl http://localhost:8000/health
```

### 3.2 Generate Demo Token
```powershell
curl -X POST http://localhost:8000/auth/demo-token `
  -H "Content-Type: application/json" `
  -d '{"sub": "operator-1", "org_id": "OIL-1", "role": "MAKER", "domains": ["COMMON"]}'
```

### 3.3 Test Text Normalization
```powershell
curl -X POST http://localhost:8000/normalize `
  -H "Content-Type: application/json" `
  -d '{"text": "वाल्व 2″ SS 304 GT #150", "category": "VALVES"}'
```

### 3.4 Test Canonical UoM Conversion
```powershell
curl -X POST http://localhost:8000/uom/convert `
  -H "Content-Type: application/json" `
  -d '{"qty": 1000, "raw_uom": "M", "category": "REBAR", "attributes": {"diameter_mm": 12}}'
```

### 3.5 Test Attribute Comparison Endpoint
```powershell
curl -X POST http://localhost:8000/compare `
  -H "Content-Type: application/json" `
  -d '{"subcategory": "VALVES.GATE", "requirement_attributes": {"size_nb": 100, "pressure_class": "ASME_150"}, "candidate_attributes": {"size_nb": 100, "pressure_class": "ASME_300"}}'
```

### 3.6 Test Safety Tiering Endpoint
```powershell
curl -X POST http://localhost:8000/tier `
  -H "Content-Type: application/json" `
  -d '{"subcategory": "VALVES.GATE", "requirement_attributes": {"size_nb": 100, "pressure_class": "ASME_150", "body_material": "A216_WCB", "end_connection": "FLANGED", "facing": "RF", "design_standard": "API_600", "trim_code": "TRIM_8", "bonnet_type": "BOLTED", "operator": "HANDWHEEL", "fire_safe": "API_607", "sour_service": "NO"}, "candidate_attributes": {"size_nb": 100, "pressure_class": "ASME_150", "body_material": "A216_WCB", "end_connection": "FLANGED", "facing": "RF", "design_standard": "API_600", "trim_code": "TRIM_8", "bonnet_type": "BOLTED", "operator": "HANDWHEEL", "fire_safe": "API_607", "sour_service": "NO"}, "probability": 0.98}'
```

### 3.7 Test End-to-End Match Endpoint
```powershell
curl -X POST http://localhost:8000/match `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <TOKEN>" `
  -d '{"text": "VALVE GATE 2 INCH 150# WCB FLANGED RF HANDWHEEL", "limit": 5}'
```

### 3.8 Test Stewardship Task Creation (Maker)
```powershell
curl -X POST http://localhost:8000/tasks `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <MAKER_TOKEN>" `
  -d '{"kind": "CREATE_MASTER", "payload": {"subcategory": "VALVES.GATE", "attributes": {"size_nb": 50, "pressure_class": "ASME_150"}}}'
```

### 3.9 Test Stewardship Task Approval (Checker)
```powershell
curl -X POST http://localhost:8000/tasks/1/approve `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <CHECKER_TOKEN>" `
  -d '{"rationale": "Verified specification and approved golden master"}'
```

### 3.10 Verify Audit Chain
```powershell
curl http://localhost:8000/audit/verify `
  -H "Authorization: Bearer <TOKEN>"
```

---

## 4. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [api/security/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/README.md): Authentication and authorization rules.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database schema and migrations.
