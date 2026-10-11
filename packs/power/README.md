# Power Sector Pack

## 1. Purpose
The Power Sector Pack contains master specifications for high-voltage power generation and distribution equipment. Covered families include power transformers, circuit breakers, and boiler tubes.

## 2. Theory
Power equipment demands high electrical and thermal safety standards. Transformers specify primary base kVA, voltage pairs, vector groups (such as `Dyn11`), and cooling methods (`ONAN`, `ONAF`). Boiler tubes operate under high thermal stress and require statutory IBR certification.

## 3. File Index
- `specs/transformers.yaml`: Deep specification for power and distribution transformers (`POWER.TRANSFORMER`).
- `specs/breakers.yaml`: Specification for circuit breakers (`POWER.BREAKER`).
- `specs/boiler_tubes.yaml`: Specification for boiler tubes (`POWER.BOILER_TUBE`) requiring IBR statutory certificates.
- `lexicons/insulation_medium.toml`: Lexicon mapping transformer insulation dielectric (`MINERAL_OIL`, `SYNTHETIC_ESTER`, `DRY_CAST_RESIN`).
- `lexicons/winding_material.toml`: Lexicon mapping transformer conductors (`COPPER`, `ALUMINIUM`).
- `lexicons/installation.toml`: Lexicon mapping installation environments (`OUTDOOR`, `INDOOR`).
- `fixtures/transformers.csv`: 45 test fixtures for power and distribution transformers.
- `eval/pairs_transformers.csv`: 16 adversarial hard-negative test pairs for transformers.
- `standards/seed.csv`: Standards reference seeds marked with `verified = false`.

## 4. Manual Testing
1. Verify transformer specification loading:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('POWER.TRANSFORMER'))"
   ```
2. Verify transformer attribute extraction:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('POWER TRANSFORMER 10 MVA 33/11 KV 3 PHASE 50 HZ DYN11 ONAN MINERAL OIL OLTC IS 2026', 'POWER.TRANSFORMER'))"
   ```
3. Check boiler tube statutory attribute definition:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('POWER.BOILER_TUBE').attributes)"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Steel Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/steel/README.md)

