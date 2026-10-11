# Security and Authentication Module (`api/security/`)

This directory implements authentication and role governance for Samanvay.
It uses HS256 JSON Web Tokens (JWT) and enforces Maker-Checker separation.

---

## 1. Purpose

The security module ensures that:
1. Every API call comes from an authenticated user with a tenant organization (`org_id`).
2. Makers cannot approve their own proposed changes (Maker $\ne$ Checker).
3. Safety-critical subcategories require domain-tagged Checkers (e.g. `POWER`, `STEEL`, `COMMON`).

---

## 2. Theoretical Background (Simplified Technical English)

### 2.1 Tenant Context in JWT
Each JWT token contains claims:
- `sub`: The unique identifier of the user (UUID or user ID).
- `org_id`: The tenant organization ID (e.g. `OIL-1`, `POWER-1`).
- `role`: One of `MAKER`, `CHECKER`, `PROCUREMENT`, `SITE_ENGINEER`, `CFO`, `AUDITOR`, `ADMIN`.
- `domains`: An array of domain tags assigned to the user (e.g. `["COMMON", "POWER"]`).

When a request arrives, the token is verified. The user's `org_id` is set into the database session (`app.current_org`). Row-Level Security (RLS) then isolates tenant data automatically.

### 2.2 Maker-Checker Governance (Section 4.7, 9.4)
Harmonizing national material codes carries industrial safety implications.
- A **Maker** (Store officer, cataloguer) reviews documents, extracts attributes, and proposes links.
- A **Checker** (Materials manager, engineering authority) validates and approves proposals.
- **Rule:** A user cannot approve a proposal they created.
- **Rule for Safety-Critical Items:** The Checker must possess the domain tag for that equipment segment.

---

## 3. File Index

| File | Responsibilities |
|---|---|
| [__init__.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/__init__.py) | Exports security interfaces and dependencies. |
| [jwt_auth.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/security/jwt_auth.py) | Token creation, verification, `get_current_user`, `require_role`, `require_domain`. |

---

## 4. Manual Testing Guide

Run the security unit tests using `uv`:

```powershell
uv run pytest tests/test_auth.py -v
```

Generate a demo token using Python:
```powershell
uv run python -c "from api.security import create_access_token; print(create_access_token('user-1', 'OIL-1', 'MAKER', ['COMMON']))"
```

---

## 5. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [api/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/README.md): API framework overview.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database and Row-Level Security.
