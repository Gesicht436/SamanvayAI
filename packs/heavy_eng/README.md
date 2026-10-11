# Heavy Engineering Sector Pack

## 1. Purpose
The Heavy Engineering Sector Pack provides specifications for complex engineered equipment, including API 610 centrifugal process pumps and custom made-to-drawing parts.

## 2. Theory
Centrifugal process pumps are engineered systems identified by API type (e.g. `OH2`, `BB2`), flow capacity, total head, and casing metallurgy. Fabricated and cast items use `DRAWING` identity mode where drawing number, owner, and revision level govern identity.

## 3. File Index
- `specs/pumps_centrifugal.yaml`: Master specification for centrifugal pumps (`HEAVY.PUMP_CENTRIFUGAL`).
- `specs/made_to_drawing.yaml`: Specification for custom fabricated parts (`HEAVY.DRAWING_PART`) requiring `DRAWING` identity mode.

## 4. Manual Testing
1. Verify `DRAWING` identity mode on custom parts:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_identity_mode('HEAVY.DRAWING_PART'))"
   ```
2. Verify pump specification loading:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('HEAVY.PUMP_CENTRIFUGAL'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)
