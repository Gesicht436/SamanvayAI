# Heavy Engineering Sector Pack

## 1. Purpose
The Heavy Engineering Sector Pack provides specifications for complex engineered equipment, including API 610 centrifugal process pumps and custom made-to-drawing parts.

## 2. Theory
Centrifugal process pumps are engineered systems identified by API type (e.g. `OH2`, `BB2`), flow capacity, total head, and casing metallurgy. Fabricated and cast items use `DRAWING` identity mode where drawing number, owner, and revision level govern identity.

## 3. File Index
- `specs/pumps_centrifugal.yaml`: Deep specification for centrifugal pumps (`HEAVY.PUMP_CENTRIFUGAL`) with flow, head, speed, nozzle sizes, and seal arrangement.
- `specs/made_to_drawing.yaml`: Specification for custom fabricated parts (`HEAVY.DRAWING_PART`) requiring `DRAWING` identity mode.
- `lexicons/pump_material_class.toml`: Lexicon mapping API 610 casing materials (`S_6`, `C_6`, `A_8`, `I_1`, `D_1`).
- `lexicons/pump_seal_arrangement.toml`: Lexicon mapping mechanical seal arrangements (`SINGLE`, `DUAL_UNPRESSURIZED`, `DUAL_PRESSURIZED`, `DOUBLE`).
- `lexicons/pump_design_standard.toml`: Lexicon mapping pump design standards (`API_610`, `ISO_2858`, `ISO_5199`, `ASME_B73_1`).
- `fixtures/pumps_centrifugal.csv`: 45 test fixtures for centrifugal process pumps.
- `eval/pairs_pumps_centrifugal.csv`: 16 adversarial hard-negative test pairs for centrifugal pumps.
- `standards/seed.csv`: Standards reference seeds marked with `verified = false`.

## 4. Manual Testing
1. Verify `DRAWING` identity mode on custom parts:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_identity_mode('HEAVY.DRAWING_PART'))"
   ```
2. Verify pump specification loading:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('HEAVY.PUMP_CENTRIFUGAL'))"
   ```
3. Verify centrifugal pump attribute extraction:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('CENTRIFUGAL PUMP API 610 OH2 100 M3/HR @ 50 M HEAD 2950 RPM 4X3-10 CL300 S-6 DOUBLE SEAL 75 KW', 'HEAVY.PUMP_CENTRIFUGAL'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)

