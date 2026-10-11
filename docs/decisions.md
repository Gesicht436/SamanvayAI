# Architecture Decision Records (ADRs)

This document records architectural and technical design decisions made when the specification is silent or when an explicit design choice is selected.

---

## ADR 001: Standard Library First for Core Mathematical and Cryptographic Helpers
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** Core functionality requires check digit validation (Verhoeff), trigram text similarity, Jaro-Winkler distance, and hash-chained audit verification. Pulling third-party packages for these increases attack surface and breaks offline self-containment.
- **Decision:** Implement `verhoeff.py`, `hashchain.py`, `trigram.py`, and `jaro_winkler.py` using pure Python standard library modules (`hashlib`, `json`, `re`, `difflib`) as defined in [.agents/skills/stdlib-first](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/.agents/skills/stdlib-first/SKILL.md) and [.agents/skills/samanvay-core-utils](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/.agents/skills/samanvay-core-utils/SKILL.md).
- **Consequence:** Zero external runtime dependencies for mathematical utilities; easily verifiable and 100% offline-compatible.

---

## ADR 002: Dedicated Docker Compose Image for PostgreSQL Extensions
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** The system requires `pgvector`, `pg_trgm`, `pgcrypto`, and `btree_gin`.
- **Decision:** Use official `pgvector/pgvector:pg17` (or `pg18` once published) in `docker-compose.yml`, which bundles `pgvector` alongside standard PostgreSQL extensions.
- **Consequence:** Simplifies local and CI setup while matching target database engine specifications.

---

## ADR 003: 80% ASD-STE100 Documentation Standard for All Folders
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** Industrial and CPSE material harmonization involves complex engineering nuances (metallurgy, pressure classes, explosion-proof standards, statutory rules). Complex language creates ambiguity across team handovers.
- **Decision:** Mandate that all folder-level `README.md` files follow 80% ASD-STE100 (Simplified Technical English) with clear sections: Purpose, Theory, File Index, Manual Testing Guide, and Connected Documentation.
- **Consequence:** Drastically reduces cognitive load and allows any developer or AI agent to understand, test, and extend code immediately.

---

## ADR 004: Dual TOML and YAML Support for Pack Specs and Lexicons
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** The specification uses YAML in `specs/*.yaml` and `packs/<pack>/specs/`, while the stdlib-first skill emphasizes standard-library TOML (`tomllib`). Sector packs and custom dictionaries may be contributed in either format.
- **Decision:** The Spec and Lexicon Registry supports both `.toml` (via stdlib `tomllib`) and `.yaml`/`.yml` (via `pyyaml`). All specs validate against a common Pydantic schema enforcing `identity_mode` (`PARAMETRIC`, `OEM_PN`, `DRAWING`), attribute roles (`HARD`, `REQUIRED`, `SOFT`, `DIRECTIONAL`), and primary dimensions.
- **Consequence:** Developers and domain engineers can author definitions in clean YAML or zero-dependency TOML interchangeably.

