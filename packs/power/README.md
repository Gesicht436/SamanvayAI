# Power Sector Pack

## 1. Purpose
The Power Sector Pack contains master specifications for high-voltage power generation and distribution equipment. Covered families include power transformers, circuit breakers, and boiler tubes.

## 2. Theory
Power equipment demands high electrical and thermal safety standards. Transformers specify primary base kVA, voltage pairs, vector groups (such as `Dyn11`), and cooling methods (`ONAN`, `ONAF`). Circuit breakers require rated continuous currents and short-circuit withstand ratings. Boiler tubes operate under high thermal stress, specify outside diameter and wall thickness (never nominal bore), and require statutory Indian Boiler Regulations (IBR) certification.

## 3. File Index
- `specs/transformers.yaml`: Deep specification for power and distribution transformers (`POWER.TRANSFORMER`).
- `specs/breakers.yaml`: Standard specification for circuit breakers (`POWER.BREAKER`).
- `specs/boiler_tubes.yaml`: Standard specification for boiler tubes (`POWER.BOILER_TUBE`).
- `lexicons/insulation_medium.toml`: Lexicon mapping transformer insulation dielectric (`MINERAL_OIL`, `SYNTHETIC_ESTER`, `DRY_CAST_RESIN`).
- `lexicons/winding_material.toml`: Lexicon mapping transformer conductors (`COPPER`, `ALUMINIUM`).
- `lexicons/installation.toml`: Lexicon mapping installation environments (`OUTDOOR`, `INDOOR`).
- `lexicons/breaker_type.toml`: Lexicon mapping circuit breaker technologies (`VCB`, `SF6`, `ACB`).
- `lexicons/boiler_grade.toml`: Lexicon mapping boiler tube alloy metallurgy (`T22`, `T11`, `T91`, `A1`, `C`).
- `fixtures/transformers.csv`: 45 test fixtures for transformers.
- `fixtures/breakers.csv`: 22 test fixtures for circuit breakers.
- `fixtures/boiler_tubes.csv`: 22 test fixtures for boiler tubes.
- `eval/pairs_transformers.csv`: 16 adversarial hard-negative test pairs for transformers.
- `eval/pairs_breakers.csv`: 10 adversarial hard-negative test pairs for breakers.
- `eval/pairs_boiler_tubes.csv`: 10 adversarial hard-negative test pairs for boiler tubes.
- `standards/seed.csv`: Standards reference seeds marked with `verified = false`.

## 4. Manual Testing
1. Verify transformer specification loading:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('POWER.TRANSFORMER'))"
   ```
2. Verify circuit breaker attribute extraction:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('VACUUM CIRCUIT BREAKER 11KV 1250A 25KA/3S 3P WITHDRAWABLE', 'POWER.BREAKER'))"
   ```
3. Verify boiler tube extraction:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('BOILER TUBE 60.3 OD X 5.6 WT MWT SA213 T22 SEAMLESS IBR', 'POWER.BOILER_TUBE'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Steel Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/steel/README.md)
