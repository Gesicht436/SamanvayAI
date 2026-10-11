---
name: db-migration
description: Creates or changes database tables and migrations with row-level security, audit logging and tests. Use when adding a table or column, writing an Alembic migration, changing RLS or the audit log, or editing the schema.
---

# Database migrations

The schema is in `docs/spec/09.md` (or section 9 of `SPEC.md`). Follow it exactly.

## Steps
1. Write the Alembic migration. Never edit a migration that has already been applied; add a new one.
2. For every new table that holds organisation data: enable row-level security, add the policies, and add the table to the RLS list in the spec if it is missing.
3. Any state change must write an audit record in the same transaction. Do not add a code path that changes state without auditing.
4. Do not weaken the append-only audit triggers, the hash chain, or the checks that stop a maker approving their own proposal.
5. Write tests: RLS isolation with at least four organisations, audit append-only behaviour, and constraint checks.
6. Run `make db-reset`, then `make migrate`, then `make test`. All must pass from an empty database.
7. Record anything the spec did not decide in `docs/decisions.md`.

## Hard rules
- No destructive change (drop or rename) without a stated reason in `docs/decisions.md`.
- Keep identifiers opaque: never encode attributes into a code.
- If a required tenant column is missing, stop and ask; do not guess a default organisation.
