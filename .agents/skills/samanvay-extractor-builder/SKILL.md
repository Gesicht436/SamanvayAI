---
name: samanvay-extractor-builder
description: Workflow and tested templates for writing attribute extractors for the Samanvay material-code project, covering lexicon extractors (TOML, no YAML library) and small Python parsers that return value, confidence, evidence span and flags. Use this skill whenever adding or changing how a material description is parsed (size, pressure class, material grade, cable cores, motor ratings, units), adding a new material family or sector pack, handling messy or multilingual descriptions, or writing extractor tests, even if the user just says "parse this field" or "add support for X".
---

# Samanvay extractor builder

An extractor turns noisy text such as `VLV GT 4" 150# WCB FLG RF` into typed attributes the comparator can trust. Everything downstream (tiering, safety invariants S1 to S15) assumes extractors follow the contract below, so the rules matter more than the regexes.

## The contract

Every extractor returns an `ExtractedValue` (see `scripts/extract_base.py`):

- `value`: the canonical value, or `None`.
- `confidence`: 0.0 to 1.0. Rules that match a whole well-formed token give 0.95; anything fuzzier gives less.
- `source`: `"rule"` for these extractors (the optional LLM or NER layers use their own labels).
- `evidence`: `(start, end)` offsets into the **raw** text so the UI can highlight why a value was chosen.
- `flags`: a list such as `EXTRACTION_CONFLICT`, `NON_STANDARD_RATING`, `LOW_OCR_CONFIDENCE`.

Three rules keep the safety invariants true:

1. **Never guess.** Invalid, conflicting or out-of-set values become `None` plus a flag. A wrong value silently creates a false merge; a missing value only sends the item to review (invariants S1, S2).
2. **Category gating lives in the registry**, not in callers. A `150` in a fastener description is not a pressure class.
3. **Keep systems apart.** `ASME_CLASS 150` and `PN 16` are different rating systems and never compare equal.

## Workflow for a new attribute

1. **Collect real strings first.** Ask for 20 to 40 examples from at least two organisations, including ugly ones (abbreviations, missing spaces, Hindi in Latin letters, OCR noise). Never design from the clean version.
2. **Choose the kind.** If the attribute is "one of a known set of values with synonyms", use a lexicon. If it needs arithmetic, ordering or a table (size to nominal bore, cable cores, motor ratings), write a Python parser.
3. **Write the tests before the extractor**, as a table of `(input, category, expected_value, expected_flags)`. Include the traps listed below. See `scripts/test_extractors.py` for the shape.
4. **Implement**, keep it pure, and return evidence spans on the raw text.
5. **Run the tests**, then run the cross-family check: the new extractor must return nothing on descriptions from other categories.
6. **Register** it in the subcategory's extractor list and note any `[VERIFY]` facts (standard numbers, rating tables) in the verification register instead of hard-coding them as certain.

## Lexicon extractors (TOML)

Use TOML instead of YAML: `tomllib` is in the standard library, so there is no parsing dependency. One file per domain, same structure the spec describes.

```toml
attribute = "body_material"
categories = ["VALVES", "FLANGES"]

[values.A216_WCB]
synonyms = ["WCB", "A216 WCB", "ASTM A216 GR WCB"]

[values.A351_CF8M]
synonyms = ["CF8M", "A351 CF8M"]
```

The engine in `extract_base.py` matches synonyms on token boundaries, prefers the longest synonym, and returns `None` plus `EXTRACTION_CONFLICT` when two different values match. Adding a value is a data edit, not a code change.

## Python parsers

Write one when logic is real. `scripts/pressure_class.py` is the worked example: prefix and suffix forms (`CLASS 300`, `300#`, `#600`), the valid class sets, PN handled separately, a bare `300 PSI` rejected, and `CLASS 150/300` flagged as a conflict instead of silently picking one.

## Traps to put in every test table

- Bare numbers without a unit or keyword.
- Two different values in one string (conflict).
- Same number in the wrong category (`M24X150MM` stud is not a size).
- Fractions and mixed numbers (`1-1/2"`, `1 1/2 INCH`).
- Case, spacing and punctuation variants (`cl150`, `CL.150`, `CL-150`).
- Hindi or other Indic text in Latin or native script: the lexicon needs per-language synonyms, and unknown tokens are kept, not dropped.
- OCR confusions (`O` for `0`, `l` for `1`): only repair inside numeric-looking tokens, and lower confidence when you do.
- Empty string, `None`, very long strings.

## Prefer your own function over a library

Parsing here is mostly `re`, `fractions`, `decimal` and `tomllib`. Do not add a parsing or fuzzy-matching package for it (see the `stdlib-first` skill).
