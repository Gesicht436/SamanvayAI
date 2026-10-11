# Steel Sector Pack

## 1. Purpose
The Steel Sector Pack defines specifications for metallurgical plant consumables and engineered components, specifically refractories and rolling mill rolls.

## 2. Theory
Refractory materials (bricks, castables, ramming mass) require strict chemistry tracking and shelf-life monitoring for monolithic materials. Mill rolls are manufactured to specific engineering drawings and operate in `DRAWING` identity mode.

## 3. File Index
- `specs/refractory.yaml`: Specification for refractories (`STEEL.REFRACTORY`) with shelf-life tracking.
- `specs/mill_rolls.yaml`: Specification for rolling mill rolls (`STEEL.MILL_ROLL`) using `DRAWING` identity mode.

## 4. Manual Testing
1. Verify `DRAWING` identity mode on mill rolls:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_identity_mode('STEEL.MILL_ROLL'))"
   ```
2. Verify expiry required flag on refractories:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('STEEL.REFRACTORY').expiry_required)"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Mining Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/mining/README.md)
