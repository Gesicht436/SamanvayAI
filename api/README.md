# Samanvay Backend API (`api/`)

This directory contains the FastAPI asynchronous backend for Samanvay.

---

## 1. Architecture

The backend is built with:
- **FastAPI:** Asynchronous HTTP server and OpenAPI schema generator.
- **SQLAlchemy 2.0:** Relational ORM with `psycopg 3` PostgreSQL driver.
- **Pydantic v2:** Typed request and response validation.
- **Standard Library Core:** Algorithmic logic and cryptography implemented with zero external dependencies.

```
api/
├── core/       # Pure Python standard-library utilities (Verhoeff, HashChain, Trigram)
├── security/   # HS256 JWT authentication, Maker-Checker rules, domain tags
├── services/   # Script detector, text normalizer, canonical UoM, and tabular ingest
├── models/     # SQLAlchemy 2.0 ORM database models
├── routers/    # HTTP route controllers (/health, /auth, /audit, /normalize, /uom, /ingest)
├── config.py   # Pydantic Settings loaded from .env
├── database.py # Sync and async database session management with RLS
└── main.py     # FastAPI application lifecycle and middleware
```

---

## 2. Directory Index

| Subdirectory / File | Role |
|---|---|
| [core/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/README.md) | Standard-library mathematical and cryptographic functions. |
| [security/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/README.md) | JWT authentication, role guards, and Maker-Checker enforcement. |
| [services/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/README.md) | Core domain services (script detector, text normalizer, UoM engine, ingest parser). |
| [models/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/models/README.md) | PostgreSQL table declarations. |
| [routers/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/routers/README.md) | HTTP route handlers. |
| [config.py](file:///C:/Users/mayank\Developement/Projects/SamanvayAI/api/config.py) | Environment configuration. |
| [database.py](file:///C:/Users/mayank\Developement/Projects/SamanvayAI/api/database.py) | PostgreSQL session factory. |
| [main.py](file:///C:/Users/mayank\Developement/Projects/SamanvayAI/api/main.py) | Application entrypoint. |

---

## 3. Manual Testing Guide

Run the full API test suite using `uv`:

```powershell
uv run pytest tests/ -v
```

Start the application server:
```powershell
uv run uvicorn api.main:app --port 8000
```
Open interactive documentation at `http://localhost:8000/docs`.

---

## 4. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database migrations and schema.
- [docs/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/README.md): Technical records and registers.
