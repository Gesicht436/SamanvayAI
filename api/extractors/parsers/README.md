# Physical Attribute Parsers

## 1. Purpose
The `api/extractors/parsers/` directory contains deterministic, rule-based Python parsers for physical attributes, sizing calculations, unit conversions, and domain-specific rules across all deep and standard families.

## 2. Theory
Physical attributes require algorithmic parsing when simple lexicon lookup is insufficient. These operations include:
- Unit arithmetic (converting HP to IEC standard kW ratings, gallons/litres to cubic metres per hour).
- Hazardous area parsing (distinguishing Ex Group I coal mine equipment from Ex Group II surface equipment per Safety Invariant S11).
- Vector group canonicalization (normalizing transformer vector configurations such as `Dyn11`).
- Geometry parsing (refractory taper dimensions, OEM pump nozzle codes like `4X3-10`).
- Strict validation (flagging pressure units in head fields as `PRESSURE_NOT_HEAD`, wall basis omissions as `WALL_BASIS_UNKNOWN`).
- Drawing normalization (collapsing hyphens/spaces inside drawing base numbers while keeping sheet/item suffixes).

All parsers return an `ExtractedValue` instance with value, confidence, evidence character span, and audit flags.

## 3. File Index
- `__init__.py`: Public exports for all parser functions.
- `size_nb.py`: Nominal bore pipe and valve sizing parser.
- `pressure_class.py`: ASME and ISO PN pressure rating class parser.
- `motors.py`: Electric motor ratings, frame standards, poles, speed, and Ex explosion-proof markings.
- `transformers.py`: Power transformer ratings (kVA/MVA), primary/secondary voltages, vector groups, cooling, and tap changers.
- `refractory.py`: Refractory brick dimensions, tapers, key chemistry percentages, and shelf-life conversions.
- `otr_tyres.py`: Mining OTR tyre dimensions (radial/bias), rim diameters, tread codes, star ratings, and ply ratings.
- `pumps.py`: Centrifugal pump flow conversions, liquid head, speed RPM, nozzle sizes, and API 610 classifications.
- `cables.py`: Power cables core counts, cross-sectional area (sqmm), and voltage grades.
- `structural.py`: Structural steel section designations (ISMB, ISMC, ISA) and profile geometries.
- `rebar.py`: Reinforcement steel bar diameter verification and non-standard diameter flagging.
- `bearings.py`: Rolling element bearing base designations, ISO types, and cage materials.
- `fasteners.py`: Metric and inch threaded fastener diameters, bolt lengths, and fastener types.
- `instrumentation.py`: Process transmitters calibrated ranges (min, max, unit) and process connections.
- `breakers.py`: Circuit breaker voltage, continuous current, short-circuit breaking current, and poles.
- `boiler_tubes.py`: Boiler tube outside diameter, wall thickness, wall basis verification, and statutory IBR certification.
- `conveyor_belts.py`: Conveyor belt strength classes, fabric ply conflict checks, widths, and rubber cover thicknesses.
- `mill_rolls.py`: Rolling mill roll drawing numbers, barrel dimensions, drawing revisions, and surface hardness.
- `wire_ropes.py`: Wire rope nominal diameter, strand construction, tensile grade, and statutory DGMS mining approval.
- `hydraulic_hoses.py`: Hydraulic hose dash sizes, DN millimetres, and working pressure conflict checks.
- `made_to_drawing.py`: Engineered drawing parts normalized drawing numbers, owner organizations, revisions, and item names.

## 4. Manual Testing
1. Test cable cores and sizing parser:
   ```bash
   uv run python -c "from api.extractors.parsers.cables import extract_cable_conductor_size; print(extract_cable_conductor_size('CABLE 1.1KV 3.5C X 240 SQMM AL'))"
   ```
2. Test boiler tube wall basis safety check:
   ```bash
   uv run python -c "from api.extractors.parsers.boiler_tubes import extract_boiler_tube_wall_basis; print(extract_boiler_tube_wall_basis('BOILER TUBE 50.8 OD X 4.5 WT SA213 T11'))"
   ```
3. Test conveyor belt ply conflict check:
   ```bash
   uv run python -c "from api.extractors.parsers.conveyor_belts import extract_belt_ply_count; print(extract_belt_ply_count('CONVEYOR BELT EP 630/4 1200MM 3 PLY'))"
   ```

## 5. Connected Documentation
- [Extractor Framework README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/extractors/README.md)
- [Common Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/common/README.md)
- [Power Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/power/README.md)
- [Steel Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/steel/README.md)
- [Mining Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/mining/README.md)
- [Heavy Engineering Sector Pack README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/heavy_eng/README.md)
