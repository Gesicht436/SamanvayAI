# Dictionaries and Reference Tables

This directory contains reference data files for text normalization, abbreviation expansion, Indic trade vocabulary, and structural section properties.

---

## 1. Purpose

The normalization engine and unit-of-measure engine require lookup tables.
These tables map non-standard terms, abbreviations, and Indian trade loanwords to canonical English uppercase terms.
These tables also provide standard physical properties for structural steel sections.

---

## 2. Theory and Rules

### 2.1 Category-Gated Abbreviations
Some abbreviations have different meanings in different material families.
For example:
- `FR` means `FRAME` in the `MOTORS` family.
- `FR` means `FLAME RETARDANT` in the `CABLES` family.
- `STD` means `STANDARD` in `PIPES` and `FLANGES`, but means `STUD` in `FASTENERS`.

Do not expand category-gated abbreviations without a known material category.
Expanding abbreviations without category context causes false attribute merges.
When category context is missing, leave the token unchanged and record a flag.

### 2.2 Indic Trade Loanwords
Enterprise purchase orders in Indian public sector enterprises often contain trade loanwords written in Indic scripts (Devanagari, Tamil, Telugu, Bengali).
For example:
- `वाल्व` maps to `VALVE`.
- `पाइप` maps to `PIPE`.
- `टन` maps to `MT`.

The text normalizer identifies Indic Unicode scripts and replaces trade loanwords with canonical English terms.

### 2.3 Structural Section Properties
Structural steel descriptions frequently specify standard profiles (such as `ISMB 300` or `ISMC 200`) without explicit linear weight.
The reference table `section_properties.csv` supplies linear mass ($kg/m$) according to Indian Standard IS 808.
If a description lacks linear weight, the unit-of-measure engine can calculate total mass from section designation and length.

---

## 3. File Index

- [abbreviations.json](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/dictionaries/abbreviations.json): Category-gated and general abbreviation definitions.
- [section_properties.csv](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/dictionaries/section_properties.csv): IS 808 structural steel profile weights per meter.
- [indic/hi.json](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/dictionaries/indic/hi.json): Hindi (Devanagari) trade vocabulary map.
- [indic/ta.json](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/dictionaries/indic/ta.json): Tamil trade vocabulary map.
- [indic/te.json](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/dictionaries/indic/te.json): Telugu trade vocabulary map.
- [indic/bn.json](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/dictionaries/indic/bn.json): Bengali trade vocabulary map.

---

## 4. Manual Verification

You can verify the dictionary files using Python via `uv`.

### 4.1 Verify JSON syntax
Run this command to validate that all JSON dictionaries contain valid syntax:
```powershell
uv run python -c "import json, glob; [json.load(open(f, encoding='utf-8')) for f in glob.glob('dictionaries/**/*.json', recursive=True)]; print('All JSON dictionaries valid.')"
```

### 4.2 Inspect section properties table
Run this command to inspect the IS 808 structural profile lookup:
```powershell
uv run python -c "import csv; rows = list(csv.DictReader(open('dictionaries/section_properties.csv'))); print(f'Loaded {len(rows)} sections.'); print('Sample:', rows[0])"
```

---

## 5. Related Documentation

- [Root README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): High-level system architecture and rules.
- [Services README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/README.md): Text normalization and UoM conversion services.
- [Verification Register](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md): Status of external standards verification (`VERIFY-004`).
