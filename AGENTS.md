# Samanvay Agent Operating Rules

This document specifies the operational guidelines for AI coding agents and developers working on the Samanvay codebase.

---

## 1. Golden Rules

1. **Single Source of Truth:**
   - [specsheet.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md) is the authoritative specification.
   - Work on one phase and module at a time. Never jump ahead to future phases. Stop at the phase gate.
2. **Never Invent External Facts:**
   - Standards, clause numbers, statutory regulations, ERP field limits, and product ratings must never be invented.
   - Mark all unverified claims with `[VERIFY]` and add a row to [docs/verification.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md).
3. **Tooling & Versions:**
   - Always use `uv` for Python operations (`uv run ...`, `uv add ...`). Do not use global Python.
   - Resolve package versions at install time and record them in [docs/VERSIONS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/VERSIONS.md). Never pin versions from memory.
4. **Safety Invariants Are Immutable:**
   - Safety Invariants $S1$ to $S15$ are non-negotiable. Never loosen, skip, or disable a property test to pass CI.
   - If a requirement appears to conflict with an invariant, write the conflict in [docs/open-questions.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/open-questions.md) and stop.
5. **Prefer Data to Code:**
   - Adding a material family, abbreviation, or canonical term is a data edit (YAML/TOML). Write custom Python parsers only where physical arithmetic or algorithmic parsing is real.
6. **Transactional Audit Logging:**
   - Every state change in the application must write an audit record to `audit_log` within the exact same database transaction.
7. **Documentation Standard:**
   - Write all folder documentation in **80% ASD-STE100 (Simplified Technical English)**. Keep sentences short and clear.
   - Provide a `README.md` in every directory containing purpose, theory, file index, manual testing instructions, and cross-links.
8. **Commitment & Verification:**
   - Execute small, self-contained commits.
   - Run `uv run pytest` and lint checks before every commit.
