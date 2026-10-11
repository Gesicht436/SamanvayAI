# Core Utilities Module (`api/core/`)

This directory contains pure Python standard library modules for mathematics, cryptography, and string comparison.
There are no third-party library dependencies.

---

## 1. Purpose

The `api/core/` package provides core functions for:
1. Generating and validating national material codes with check digits.
2. Building and verifying tamper-evident audit logs.
3. Calculating character trigram similarity matching PostgreSQL `pg_trgm`.
4. Comparing short strings (such as part numbers and brand names) using Jaro-Winkler distance.

---

## 2. Theoretical Background (Simplified Technical English)

### 2.1 Verhoeff Check Digit Algorithm (`verhoeff.py`)
Ordinary check digits (such as modulo 10) miss many human typing errors.
The Verhoeff algorithm uses group theory (the dihedral group $D_5$ of order 10).
It uses three mathematical tables:
- **Multiplication table ($D$):** A non-commutative operation on digits 0 through 9.
- **Permutation table ($P$):** Applies different permutations based on digit position.
- **Inverse table ($INV$):** Finds the exact check digit that balances the equation.

**What it guarantees:**
- It detects **100% of single-digit errors** (e.g. typing `4` instead of `7`).
- It detects **100% of adjacent transposition errors** (e.g. typing `28` instead of `82`).
- The code format is permanent: `MPNG-` + 10 digits + `-` + 1 check digit (17 characters).

### 2.2 Tamper-Evident Hash Chain (`hashchain.py`)
Audit logs must prove that nobody altered historical records.
This module links every audit record to the previous record using cryptographic hashes:
$$\text{hash}_n = \text{SHA-256}(\text{hash}_{n-1} + \text{canonical}(\text{record}_n))$$
- **Canonical JSON:** Keys are sorted alphabetically. Spacing is compact. Characters use UTF-8.
- If a user changes, deletes, or inserts an old row, every later hash becomes invalid.
- A verifier checks the chain from sequence 1 to the end. It returns the exact broken sequence number if someone tampers with data.

### 2.3 Trigram Similarity (`trigram.py`)
A trigram is a slice of three consecutive characters.
- Text is lowercased.
- Non-alphanumeric characters are split.
- Each word gets two leading spaces and one trailing space. For example, `"pipe"` becomes `"  pipe "`.
- Slices of length 3 are extracted: `{"  p", " pi", "pip", "ipe", "pe "}`.
- Similarity between text $A$ and text $B$ is the **Jaccard index**:
$$\text{sim}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
This matches the exact index logic of PostgreSQL `pg_trgm`.

### 2.4 Jaro-Winkler Similarity (`jaro_winkler.py`)
Calculates similarity based on common characters and transpositions.
It gives higher weight to strings that share a common prefix (up to 4 characters).
It is ideal for matching manufacturer codes, part numbers, and short brand tokens.
*Rule:* Similarity scores only rank candidates. They **never** decide identity on their own.

---

## 3. File Index

| File | Responsibilities |
|---|---|
| [__init__.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/__init__.py) | Exports core helper functions. |
| [verhoeff.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/verhoeff.py) | `check_digit()`, `is_valid()`, `make_code()`, `validate_code()`. |
| [hashchain.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/hashchain.py) | `canonical()`, `entry_hash()`, `build_chain()`, `verify_chain()`. |
| [hashchain_verify.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/hashchain_verify.py) | Command-line database audit chain verifier (`make audit-verify`). |
| [trigram.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/trigram.py) | `trigrams()`, `similarity()`, `top_k()`. |
| [jaro_winkler.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/core/jaro_winkler.py) | `jaro()`, `jaro_winkler()`. |

---

## 4. Manual Testing Guide

Run the unit tests using `uv`:

```powershell
# Run the core utilities test suite via uv
uv run pytest tests/test_core_utils.py -v

# Run the command-line audit log hash chain verifier against PostgreSQL
uv run python -m api.core.hashchain_verify
# or
make audit-verify
```

To test manually in an interactive Python shell:
```powershell
uv run python
```
```python
from api.core import make_code, validate_code, similarity

# 1. Generate and validate a code
code = make_code(4821937)
print("Generated Code:", code)  # MPNG-0004821937-3
print("Is valid?", validate_code(code))  # True

# 2. Check adjacent transposition error detection
tampered = "MPNG-0004821973-3"
print("Is tampered code valid?", validate_code(tampered))  # False

# 3. Check trigram similarity
print("Similarity:", similarity("GATE VALVE 150#", "VALVE GATE 150#"))
```

---

## 5. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [api/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/README.md): API documentation.
- [tests/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/README.md): Test suite overview.
