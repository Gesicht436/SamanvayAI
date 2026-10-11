# Steel Sector Pack

## 1. Purpose
The Steel Sector Pack defines specifications for metallurgical plant consumables and engineered components, specifically refractories and rolling mill rolls.

## 2. Theory
Refractory materials (bricks, castables, ramming mass) require strict chemistry tracking and shelf-life monitoring for monolithic materials. Mill rolls are manufactured to specific engineering drawings and operate in `DRAWING` identity mode.

## 3. File Index
- `specs/refractory.yaml`: Deep specification for refractories (`STEEL.REFRACTORY`) with shelf-life tracking and shape/chemistry dimensions.
- `specs/mill_rolls.yaml`: Specification for rolling mill rolls (`STEEL.MILL_ROLL`) using `DRAWING` identity mode.
- `lexicons/refractory_form.toml`: Lexicon mapping refractory forms (`BRICK`, `CASTABLE`, `RAMMING_MASS`, `GUNNING_MIX`, `MORTAR`, `FIBRE`, `PRECAST_SHAPE`).
- `lexicons/refractory_material_class.toml`: Lexicon mapping refractory materials (`MAG_CARBON`, `HIGH_ALUMINA`, `FIRECLAY`, `MAGNESIA`, `MAG_CHROME`, `ALUMINA_CARBON`, `SILICA`).
- `lexicons/refractory_shape.toml`: Lexicon mapping brick shapes (`STRAIGHT`, `ARCH`, `WEDGE`).
- `lexicons/refractory_cement_class.toml`: Lexicon mapping castable cement classes (`CONVENTIONAL`, `LOW_CEMENT`, `ULTRA_LOW`, `CEMENT_FREE`).
- `lexicons/refractory_bond.toml`: Lexicon mapping refractory binder systems (`RESIN`, `PITCH`, `CERAMIC`, `CHEMICAL`, `HYDRAULIC`).
- `fixtures/refractory.csv`: 45 test fixtures for refractories.
- `eval/pairs_refractory.csv`: 16 adversarial hard-negative test pairs for refractories.
- `standards/seed.csv`: Standards reference seeds marked with `verified = false`.

## 4. Manual Testing
1. Verify `DRAWING` identity mode on mill rolls:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_identity_mode('STEEL.MILL_ROLL'))"
   ```
2. Verify expiry required flag on refractories:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('STEEL.REFRACTORY').expiry_required)"
   ```
3. Verify extraction on a refractory brick description:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('REFRACTORY BRICK MAG-CARBON MGO 97% C 14% 230X114X75 STRAIGHT RESIN BOND 1750 C 180 DAYS', 'STEEL.REFRACTORY'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Mining Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/mining/README.md)

