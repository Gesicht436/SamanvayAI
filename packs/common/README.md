# Common Sector Pack

## 1. Purpose
The Common Sector Pack provides master specifications and dictionaries for items used across multiple public sector enterprises. These items include gate valves, electric motors, power cables, structural steel, rebar, bearings, pipes, flanges, fasteners, and process instrumentation.

## 2. Theory
Many engineering items share standard dimensional conventions across oil, gas, power, steel, mining, and heavy engineering plants. Gate valves, pipes, and flanges follow ASME and IS dimensional rules. Structural sections follow standard IS rolling tables. Fasteners follow standard metric thread systems. Standardizing these common families enables cross-CPSE inventory pooling and transfer.

## 3. File Index
- `specs/valves_gate.yaml`: Deep specification for gate valves.
- `specs/motors_ex.yaml`: Deep specification for electric motors with Ex hazardous area markings.
- `specs/pipes.yaml`: Standard specification for industrial piping (`PIPES.PIPE`).
- `specs/flanges.yaml`: Standard specification for pipe flanges (`FLANGES.FLANGE`).
- `specs/cables.yaml`: Standard specification for power cables (`CABLES.POWER`).
- `specs/structural.yaml`: Standard specification for structural steel sections (`STEEL.STRUCTURAL`).
- `specs/rebar.yaml`: Standard specification for reinforcement steel bars (`STEEL.REBAR`).
- `specs/bearings.yaml`: Standard specification for rolling element bearings (`BEARINGS.BEARING`).
- `specs/fasteners.yaml`: Standard specification for threaded bolts and studs (`FASTENERS.STUD_BOLT`).
- `specs/instrumentation.yaml`: Standard specification for process transmitters (`INSTRUMENTS.TRANSMITTER`).
- `lexicons/`: Sector dictionaries mapping standard metallurgical grades, schedules, facings, trims, insulation types, and connections.
- `fixtures/`: Test fixture CSV files for all common families (>= 22 test fixtures each).
- `eval/`: Adversarial hard-negative test pair CSV files (>= 10 test pairs each).
- `standards/seed.csv`: Standards reference seeds marked with `verified = false`.

## 4. Manual Testing
1. Load specifications in Python:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.list_subcategories())"
   ```
2. Verify attribute extraction on a cable description:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('POWER CABLE 1.1KV 3.5C X 240 SQMM AL XLPE ARMOURED', 'CABLES.POWER'))"
   ```
3. Verify extraction on a structural steel section:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('STRUCTURAL STEEL BEAM ISMB 300 IS 2062 E250A', 'STEEL.STRUCTURAL'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Extractor Framework README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/extractors/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)
