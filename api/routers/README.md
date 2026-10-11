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

### 3.5 Verify Audit Chain
```powershell
curl http://localhost:8000/audit/verify `
  -H "Authorization: Bearer <TOKEN>"
```

---

## 4. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [api/security/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/README.md): Authentication and authorization rules.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database schema and migrations.
