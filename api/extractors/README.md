# Attribute Extractor Framework and Spec Registry

## 1. Purpose
The `api/extractors` package parses noisy, unstructured material descriptions into strongly-typed attribute values. It extracts canonical values, numerical confidence scores, raw text character evidence spans, and warning flags while enforcing strict category gating.

## 2. Theory
Extraction forms Stage 3 of the harmonization pipeline. To preserve Safety Invariants $S1$ to $S15$, the extractor framework enforces five core principles:
1. **Never Guess:** Invalid, conflicting, or out-of-set values return `None` plus an explicit flag (such as `EXTRACTION_CONFLICT` or `NON_STANDARD_RATING`). A missing value routes the item to human review; an incorrect value creates an unsafe false merge.
2. **Category Gating:** Gating lives in the specification registry. An attribute extractor only runs when the item category matches allowed categories. For example, `M24X150MM` in `FASTENERS` never parses as a piping Nominal Bore.
3. **Evidence Spans on Raw Text:** Every extracted value returns `(start, end)` character offsets pointing directly into the unmodified input text, enabling UI diff inspectors to highlight evidence.
4. **Data Over Code:** Standard attribute lexicons live in TOML/YAML files. The engine uses token boundaries and longest-synonym precedence.
5. **Separation of Rating Systems:** Disparate physical rating systems (such as `ASME_CLASS` vs `PN`) are strictly separated and never compare equal.

## 3. File Index
- `base.py`: Declares `ExtractedValue` dataclass, `none_with()` constructor, and `BaseExtractor` abstract interface.
- `lexicon.py`: TOML/YAML dictionary extractor engine with token boundary regexes and conflict detection.
- `parsers/size_nb.py`: Piping Nominal Bore parser converting inches, fractions, and DN numbers to canonical mm integers.
- `parsers/pressure_class.py`: Pressure class parser separating ASME ratings from metric PN ratings.
- `registry.py`: Central specification registry loading sector packs, validating schemas, and dispatching extraction.

## 4. Manual Testing
1. Test direct attribute extraction:
   ```bash
   uv run python -c "from api.extractors.parsers.size_nb import extract_size_nb; print(extract_size_nb('GATE VALVE 1-1/2 INCH', 'VALVES'))"
   ```
2. Test pressure class conflict handling:
   ```bash
   uv run python -c "from api.extractors.parsers.pressure_class import extract_pressure_class; print(extract_pressure_class('VALVE CLASS 150/300', 'VALVES'))"
   ```
3. Test end-to-end multi-attribute extraction:
   ```bash
   uv run python -c "from api.extractors.registry import default_registry; default_registry.load_packs('packs'); print(default_registry.extract_attributes('GATE VALVE 4\" CL150 WCB FLG RF', 'VALVES.GATE'))"
   ```

## 5. Connected Documentation
- [Packs Master README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/packs/README.md)
- [API Services README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/README.md)
- [Architecture Decision Records](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/decisions.md)
- [Verification Register](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md)
