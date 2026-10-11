# Steel Sector Pack

## 1. Purpose
The Steel Sector Pack defines specifications for metallurgical plant consumables and engineered components, specifically refractories, heavy conveyor belts, and rolling mill rolls.

## 2. Theory
Refractory materials (bricks, castables, ramming mass) require strict chemistry tracking and shelf-life monitoring for monolithic materials. Mill rolls are manufactured to specific engineering drawings and operate in `DRAWING` identity mode. Conveyor belts are critical material-handling items identified by carcass type, tensile rating (e.g. EP 800/4), belt width, cover grades, and fire resistance.

## 3. File Index
- `specs/refractory.yaml`: Deep specification for refractories (`STEEL.REFRACTORY`) with shelf-life tracking and shape/chemistry dimensions.
- `specs/conveyor_belts.yaml`: Specification for heavy conveyor belts (`STEEL.CONVEYOR_BELT`) with carcass type, rating, and width.
- `specs/mill_rolls.yaml`: Specification for rolling mill rolls (`STEEL.MILL_ROLL`) using `DRAWING` identity mode.
- `lexicons/refractory_form.toml`: Lexicon mapping refractory forms (`BRICK`, `CASTABLE`, `RAMMING_MASS`, `GUNNING_MIX`, `MORTAR`, `FIBRE`, `PRECAST_SHAPE`).
- `lexicons/refractory_material_class.toml`: Lexicon mapping refractory materials (`MAG_CARBON`, `HIGH_ALUMINA`, `FIRECLAY`, `MAGNESIA`, `MAG_CHROME`, `ALUMINA_CARBON`, `SILICA`).
- `lexicons/refractory_shape.toml`: Lexicon mapping brick shapes (`STRAIGHT`, `ARCH`, `WEDGE`).
- `lexicons/refractory_cement_class.toml`: Lexicon mapping castable cement classes (`CONVENTIONAL`, `LOW_CEMENT`, `ULTRA_LOW`, `CEMENT_FREE`).
- `lexicons/refractory_bond.toml`: Lexicon mapping refractory binder systems (`RESIN`, `PITCH`, `CERAMIC`, `CHEMICAL`, `HYDRAULIC`).
- `lexicons/conveyor_carcass.toml`: Lexicon mapping conveyor carcass construction (`EP`, `NN`, `STEEL_CORD`, `COTTON`).
- `lexicons/conveyor_fire.toml`: Lexicon mapping fire-resistant conveyor grades (`FR`, `NON_FR`).
- `lexicons/mill_roll_type.toml`: Lexicon mapping mill roll functions (`WORK_ROLL`, `BACKUP_ROLL`, `EDGER_ROLL`).
- `fixtures/refractory.csv`: 45 test fixtures for refractories.
- `fixtures/conveyor_belts.csv`: 22 test fixtures for conveyor belts.
- `fixtures/mill_rolls.csv`: 22 test fixtures for mill rolls.
- `eval/pairs_refractory.csv`: 16 adversarial hard-negative test pairs for refractories.
- `eval/pairs_conveyor_belts.csv`: 10 adversarial hard-negative test pairs for conveyor belts.
- `eval/pairs_mill_rolls.csv`: 10 adversarial hard-negative test pairs for mill rolls.
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
3. Verify extraction on a conveyor belt description:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('CONVEYOR BELT EP 800/4 1400MM 5+2 GRADE M DIN 22102', 'STEEL.CONVEYOR_BELT'))"
   ```
4. Verify extraction on a refractory brick description:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('REFRACTORY BRICK MAG-CARBON MGO 97% C 14% 230X114X75 STRAIGHT RESIN BOND 1750 C 180 DAYS', 'STEEL.REFRACTORY'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Mining Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/mining/README.md)

