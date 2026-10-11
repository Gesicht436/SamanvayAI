# Samanvay Verification Register

This register records every external claim, statutory regulation, standard number, clause, or ERP field length marked `[VERIFY]` in [specsheet.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md) or in code.
Every claim must be checked against a primary source before inclusion in seed files or release demonstrations.

---

## 1. Verification Ledger

| ID | Claim / Fact | Standard / Citation | Code Location | Status | Verified By | Date | Notes |
|---|---|---|---|---|---|---|---|
| `VERIFY-001` | Verhoeff check digit calculation parameters ($D$, $P$, $INV$) | Dihedral group $D_5$ check digit algorithm | `api/core/verhoeff.py` | `VERIFIED` | Core Utils Test | 2026-10-11 | Validated with known test vectors `236` -> 3, `12345` -> 1, `0004821937` -> 3 |
| `VERIFY-002` | Tamper-evident hash chain linkage formula | SHA-256 hash chaining | `api/core/hashchain.py` | `VERIFIED` | Core Utils Test | 2026-10-11 | Validated with test vectors for single edit and delete detection |
| `VERIFY-003` | Pipe nominal bore (NB) mm equivalent to inches | ASME B36.10M / IS 1239 | `api/extractors/size.py` | `PENDING` | - | - | Check exact conversion up to 48 inches |
| `VERIFY-004` | Structural steel section kg/m properties | IS 808 | `db/seed/` | `PENDING` | - | - | Cross-check section dimensions for ISMB and ISMC |
| `VERIFY-005` | Motor HP to IEC kW conversion table | IS 12615 | `api/extractors/motor.py` | `PENDING` | - | - | Check exact kW equivalents for 75 HP (55 kW), 100 HP, etc. |
| `VERIFY-006` | Transformer vector group notations | IS 2026 / IEC 60076 | `packs/power/` | `PENDING` | - | - | Confirm canonical syntax for Dyn11 and YNyn0 |
| `VERIFY-007` | Ex Group I vs Group II statutory approval regime | PESO / DGMS approval | `api/services/compare.py`| `PENDING` | - | - | Verify DGMS approval requirement for coal mines |
| `VERIFY-008` | IBR statutory certification requirement for boiler tubes | Indian Boilers Regulations | `packs/power/` | `PENDING` | - | - | Confirm Form III-A requirement |
| `VERIFY-009` | Refractory grade reference chemistry limits | ISO 10081 / ASTM C27 | `db/seed/` | `PENDING` | - | - | Numbers entered by verifier, not hardcoded |
| `VERIFY-010` | EN 10204 Type 3.1 inspection certificate scope | EN 10204:2004 | `api/services/mtc.py` | `PENDING` | - | - | Confirm chemistry and mechanical test reporting rules |
