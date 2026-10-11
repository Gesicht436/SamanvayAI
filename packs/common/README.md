# Common Sector Pack

## 1. Purpose
The Common Sector Pack provides master specifications and dictionaries for items used across multiple public sector enterprises. These items include gate valves, pipes, flanges, and threaded fasteners.

## 2. Theory
Many engineering items share standard dimensional conventions across oil, gas, power, and manufacturing plants. Gate valves and flanges follow ASME and IS dimensional rules. Fasteners follow standard metric thread systems. Standardizing these common families enables cross-CPSE inventory pooling and transfer.

## 3. File Index
- `specs/valves_gate.yaml`: Deep specification for gate valves (size NB, pressure class, body material, facing, end connection, trim code, bonnet, operator).
- `specs/motors_ex.yaml`: Deep specification for electric motors with Ex hazardous area markings (Group I coal vs Group II surface, temp class, frame, mounting).
- `specs/pipes.yaml`: Specification for standard industrial piping.
- `specs/flanges.yaml`: Specification for pipe flanges (weld neck, slip-on, blind).
- `specs/fasteners.yaml`: Specification for threaded bolts and studs.
- `lexicons/body_material.toml`: Lexicon mapping cast and forged valve metallurgy (`A216_WCB`, `A105`, `CAST_IRON`, `A351_CF8`, `A351_CF8M`, `A217_WC6`, `A352_LCB`).
- `lexicons/end_connection.toml`: Lexicon mapping end connections (`FLANGED`, `BUTT_WELD`, `SOCKET_WELD`, `THREADED`).
- `lexicons/facing.toml`: Lexicon mapping flange facing styles (`RF`, `FF`, `RTJ`).
- `lexicons/trim_code.toml`: Lexicon mapping API 600 trim numbers (`TRIM_1` through `TRIM_16`).
- `lexicons/bonnet_type.toml`: Lexicon mapping bonnet construction (`BOLTED`, `PRESSURE_SEAL`, `WELDED`).
- `lexicons/operator.toml`: Lexicon mapping valve actuation (`HANDWHEEL`, `GEAR_OPERATED`, `ACTUATED`).
- `lexicons/fire_safe.toml`: Lexicon mapping fire testing certification (`FIRE_SAFE`).
- `lexicons/sour_service.toml`: Lexicon mapping NACE MR0175 sour service compliance.
- `lexicons/motor_mounting.toml`: Lexicon mapping IEC motor mounting types (`B3`, `B5`, `B35`, `V1`).
- `lexicons/motor_enclosure.toml`: Lexicon mapping motor enclosure styles (`TEFC`, `SPDP`, `TENV`).
- `lexicons/design_standard.toml`: Lexicon mapping API, BS, and IS valve and electrical standards.
- `fixtures/valves_gate.csv`: 45 test fixtures for gate valves.
- `fixtures/motors_ex.csv`: 45 test fixtures for explosion-proof electric motors.
- `eval/pairs_valves_gate.csv`: 16 adversarial hard-negative test pairs for gate valves.
- `eval/pairs_motors_ex.csv`: 16 adversarial hard-negative test pairs for electric motors.
- `standards/seed.csv`: Standards reference seeds marked with `verified = false`.

## 4. Manual Testing
1. Load specifications in Python:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('VALVES.GATE'))"
   ```
2. Verify attribute extraction on a valve description:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('GATE VALVE 2 INCH CL300 WCB RF API 600 TRIM 8', 'VALVES.GATE'))"
   ```
3. Verify extraction on an explosion-proof motor:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('MOTOR 55 KW 4P B3 TEFC Ex d IIB T4 Gb IE3', 'MOTORS.EX'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Extractor Framework README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/extractors/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)

