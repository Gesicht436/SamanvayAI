# API review fixes

This document records the fixes made after reviewing the current `api/` implementation. The review used the current source tree only; it did not consult prior commits or removed documentation.

## Authentication and runtime configuration

- Removed caller-controlled identity, organization, role, and domain claims from the demo-token request. The demo issuer now creates only a fixed `MAKER` identity for the configured demo organization with the `COMMON` domain.
- The demo-token endpoint returns `404` unless `DEMO_MODE=true`, and rejects subjects other than `demo-user`.
- Changed the default `DEMO_MODE` to false and removed the built-in JWT signing key. Startup now fails unless `JWT_SECRET` is configured, is at least 32 characters, and is not the documented placeholder or old development key.
- Updated `.env.example` to show a replacement-only secret value and disabled demo mode by default.
- CORS now uses an explicit comma-separated origin list (`CORS_ORIGINS`) and no longer enables credentials or wildcard origins.
- Prometheus metrics now require an `ADMIN` token. Dashboard and catalog-health routes now require authentication and use only the caller's tenant. Health output no longer exposes runtime mode or ML configuration.

## Tenant isolation and authorization

- The async database dependency now obtains the authenticated user and configures `app.current_org` for the session. A synchronous tenant-scoped session helper was added and applied to synchronous API routes. The context is cleared before the connection is returned to the pool, including after internal commits.
- OEM batch/proposal reads and mutations check the caller's organization. Onboarding and proposal review require `MAKER` or `ADMIN`; publication requires `CHECKER` or `ADMIN` and a UUID subject; supersession management requires `ADMIN`.
- Pool indent listing no longer lets an ordinary user opt into cross-tenant rows. Only `ADMIN` may use the cross-organization listing mode. Pool creation rejects duplicate indent IDs and cross-tenant indents for non-admin users, and locks selected open indents while changing their state.
- Tender-pool lists show only pools led by or involving the caller's organization. Tender-pack requests return `404` for pools outside the caller's organization.
- Transfer review requires `CHECKER` or `ADMIN`, and the caller must belong to one of the organizations in the transfer. Unknown or out-of-order state transitions return `409`; terminal states cannot be re-approved. Approval locks the lot and fails if the available quantity is insufficient. Pending transfer quantities are reserved when validating new requests.
- Transfer list filters now map `INCOMING` to the receiving organization and `OUTGOING` to the sending organization. Invalid directions are rejected.
- Life-alert acknowledgement now joins through the stock lot and scopes changes to the caller's organization.
- Document-line promotion now verifies the owning document's tenant in the service query. Bulk promotion also confirms document ownership before loading its lines.
- Stewardship task listing filters on the tenant captured at creation. Fetch, approval, and rejection return `404` for tasks outside the caller's organization.
- Ingest job status is tenant-scoped. The worker endpoint requires `ADMIN` and only dequeues jobs belonging to that caller's organization. New job payloads keep uploaded files in tenant-keyed storage paths instead of base64 JSON; the worker checks that paths stay under the configured ingest-storage root and removes files after terminal processing. Legacy base64 jobs remain processable for rollout compatibility. Error details returned and stored in job records are generic; logs retain exception details for diagnosis without returning them to API callers.

## Input and decision controls

- Both tabular ingest and document upload read at most one byte over the configured `UPLOAD_MAX_MB` limit and return `413` when the limit is exceeded. The setting is constrained to 1–100 MB.
- Match tiering now uses `TAU_AUTO` and `TAU_REVIEW` from settings instead of hard-coded values.
- The transfer review service independently checks role and tenant when those contexts are supplied, so route-layer changes are reinforced in the service.
- Synchronous SQLAlchemy sessions use `expire_on_commit=False`, avoiding implicit post-commit refreshes after tenant context is changed.

## Regression coverage added

`tests/test_api_hardening.py` exercises:

- Attempts to supply admin role, another tenant, and elevated domain claims to the demo issuer; returned JWT claims remain fixed.
- Forged demo subjects and disabled demo mode.
- Missing, short, and known placeholder JWT secrets.
- An upload just one byte over the configured size limit, confirming rejection before database use.
- Transfer review attempts by an unrelated tenant, an unauthorized role, and an already terminal transfer.
- Pool creation with an empty ID list, duplicate IDs, and an indent belonging to another tenant.
- Ingest job lookup SQL with an explicit tenant predicate.
- Ingest job file persistence outside JSON, worker path traversal rejection, and payload readback.
- Tenant filtering in stewardship-task SQL.
- Tenant ownership in document-line promotion SQL.

`tests/conftest.py` sets an isolated test signing key and enables the demo issuer for the route tests. `tests/test_routes.py` now asserts that demo token output remains `MAKER` scoped to `OIL-1`.

## Verification performed

- Python compilation passed for `api/` and `tests/`.
- `pytest -q tests/test_api_hardening.py tests/test_auth.py`: **21 passed**.
- Ruff checks passed on the changed Python files after import cleanup.
- The pre-existing `tests/test_routes.py` request-based run stalled after its route-protection case passed in this Windows environment. It was stopped after waiting; it is not counted as passing verification.

## Deployment note

Set a unique random `JWT_SECRET` of at least 32 characters, set `CORS_ORIGINS` to the intended browser origins, and leave `DEMO_MODE=false` outside development/test. The database role used by the API must support the tenant-context policy expected by `app.current_org`.
