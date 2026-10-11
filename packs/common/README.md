# Common Sector Pack

## 1. Purpose
The Common Sector Pack provides master specifications and dictionaries for items used across multiple public sector enterprises. These items include gate valves, pipes, flanges, and threaded fasteners.

## 2. Theory
Many engineering items share standard dimensional conventions across oil, gas, power, and manufacturing plants. Gate valves and flanges follow ASME and IS dimensional rules. Fasteners follow standard metric thread systems. Standardizing these common families enables cross-CPSE inventory pooling and transfer.

## 3. File Index
- `specs/valves_gate.yaml`: Specification for gate valves (size NB, pressure class, body material, facing, end connection).
- `specs/pipes.yaml`: Specification for standard industrial piping.
- `specs/flanges.yaml`: Specification for pipe flanges (weld neck, slip-on, blind).
- `specs/fasteners.yaml`: Specification for threaded bolts and studs.
- `lexicons/body_material.toml`: Lexicon mapping cast and forged valve body metallurgy (`A216_WCB`, `A351_CF8M`).
- `lexicons/end_connection.toml`: Lexicon mapping end connections (`FLANGED`, `BUTT_WELD`, `SOCKET_WELD`).
- `lexicons/facing.toml`: Lexicon mapping flange facing styles (`RF`, `FF`, `RTJ`).

## 4. Manual Testing
1. Load specifications in Python:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('VALVES.GATE'))"
   ```
2. Verify attribute extraction on a valve description:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('GATE VALVE 2 INCH CL300 WCB RF', 'VALVES.GATE'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Extractor Framework README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/extractors/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)
