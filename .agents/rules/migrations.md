---
trigger: model_decision
description: "Apply when writing or changing database migrations, row-level security, or the audit log."
---
Every state change writes an audit record in the same transaction. Add RLS tests with each new table.
Never edit an applied migration; add a new one. See docs/spec/09.md.
