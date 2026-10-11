# Documentation Directory (`docs/`)

This directory contains project records, verification registers, architecture decisions, and version logs.

---

## 1. Directory Purpose

The `docs/` directory maintains project records. It preserves history, records technical choices, and tracks external facts.
All documents follow the **80% ASD-STE100 (Simplified Technical English)** standard.
Sentences are short and direct to eliminate ambiguity.

---

## 2. File Index

| File | Purpose |
|---|---|
| [VERSIONS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/VERSIONS.md) | Records exact versions of Python, packages, and tools installed via `uv`. |
| [verification.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md) | The verification register. Tracks every `[VERIFY]` external claim. |
| [PROGRESS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/PROGRESS.md) | Tracks phase execution status, completed items, and gate outputs. |
| [decisions.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/decisions.md) | Architecture Decision Records (ADRs). |
| [open-questions.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/open-questions.md) | Records unresolved questions or safety conflicts. |
| [limitations.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/limitations.md) | Discloses known scope boundaries and hardware limits honestly. |

---

## 3. How to Update Documentation

1. **When you add a new library:**
   - Record the exact version in [VERSIONS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/VERSIONS.md). Do not guess.
2. **When you encounter an external standard or claim:**
   - Add a row to [verification.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md). Mark it `PENDING` until confirmed with a primary source.
3. **When you complete a build phase:**
   - Record the gate output in [PROGRESS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/PROGRESS.md) and update [implemented_till_now.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/implemented_till_now.md).

---

## 4. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): High-level system overview.
- [implementation_plan.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/implementation_plan.md): Master building plan.
- [implemented_till_now.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/implemented_till_now.md): Live progress tracker.
