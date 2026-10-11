# Sector Domain Packs Master Directory

## 1. Purpose
The `packs/` directory contains sector-specific domain packs covering Oil & Gas, Power, Steel, Mining, and Heavy Engineering. Each pack encapsulates its subcategory specifications, lexicons, and domain configurations in an isolated folder.

## 2. Theory
A modular pack structure isolates domain complexity and guarantees system resilience. Sector domain packs operate under an independent lifecycle:
- Core systems do not hardcode subcategories or attributes.
- Adding a new family or sector is a YAML or TOML file addition.
- Any sector pack can be mounted or unmounted without breaking core platform services or other packs.

## 3. File Index
- `common/`: Common equipment across CPSEs (valves, pipes, flanges, fasteners).
- `power/`: Power generation and transmission equipment (transformers, breakers, boiler tubes).
- `steel/`: Steel and metallurgy plant equipment (refractories, mill rolls).
- `mining/`: Mining operations consumables (OTR tyres).
- `heavy_eng/`: Heavy engineering and rotating machinery (centrifugal pumps, made-to-drawing parts).

## 4. Manual Testing
1. Load all sector packs across the repository:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; n = default_registry.load_packs('packs'); print(f'Successfully loaded {n} specifications across all packs.')"
   ```
2. Verify unmounting resilience by loading a single pack:
   ```bash
   uv run python -c "from api.extractors.registry import SpecRegistry; r = SpecRegistry(); r.load_packs('packs/common'); print('Common pack subcategories:', r.list_subcategories())"
   ```

## 5. Connected Documentation
- [API Extractor Framework README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/extractors/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)
- [Steel Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/steel/README.md)
- [Mining Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/mining/README.md)
- [Heavy Engineering Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/heavy_eng/README.md)
