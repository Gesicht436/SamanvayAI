# Mining Sector Pack

## 1. Purpose
The Mining Sector Pack defines specifications for heavy open-cast and underground mining consumables, specifically off-the-road (OTR) haul truck tyres.

## 2. Theory
OTR tyres represent high-value capital expenditure in open-cast mines (Coal India, NMDC). Tyres are categorized by section width, rim diameter, construction (radial vs bias), and standardized tread codes (e.g. `E3`, `E4`, `L5`). Age tracking from sidewall manufacturing date codes is mandatory to prevent blowout risks.

## 3. File Index
- `specs/otr_tyres.yaml`: Master specification for mining OTR tyres (`MINING.OTR_TYRE`) with mandatory expiry tracking.

## 4. Manual Testing
1. Verify OTR tyre specification loading:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.get_spec('MINING.OTR_TYRE'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [Heavy Engineering Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/heavy_eng/README.md)
- [Steel Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/steel/README.md)
