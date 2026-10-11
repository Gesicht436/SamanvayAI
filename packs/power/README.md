# Power Sector Pack

## 1. Purpose
The Power Sector Pack contains master specifications for high-voltage power generation and distribution equipment. Covered families include power transformers, circuit breakers, and boiler tubes.

## 2. Theory
Power equipment demands high electrical and thermal safety standards. Transformers specify primary base kVA, voltage pairs, vector groups (such as `Dyn11`), and cooling methods (`ONAN`, `ONAF`). Boiler tubes operate under high thermal stress and require statutory IBR certification.

## 3. File Index
- `specs/transformers.yaml`: Master specification for power and distribution transformers (`POWER.TRANSFORMER`).
- `specs/breakers.yaml`: Specification for circuit breakers (`POWER.BREAKER`).
- `specs/boiler_tubes.yaml`: Specification for boiler tubes (`POWER.BOILER_TUBE`) requiring IBR statutory certificates.

## 4. Manual Testing
1. Verify transformer specification loading:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('POWER.TRANSFORMER'))"
   ```
2. Check boiler tube statutory attribute definition:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('POWER.BOILER_TUBE').attributes)"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Steel Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/steel/README.md)
