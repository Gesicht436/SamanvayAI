---
name: stdlib-first
description: Coding policy for writing Python (and small amounts of JS/TS) with as few third-party libraries as possible. Use this skill whenever writing or reviewing code in this project, choosing a dependency, adding anything to requirements.txt or package.json, or when the user says "write my own function", "without a library", "fewer dependencies" or "stdlib". Also use it before importing a package for something small like string similarity, retries, CSV/JSON handling, date maths, hashing, CLI parsing, or validation, even if the user does not mention dependencies. Includes an import auditor script.
---

# Stdlib first

The owner of this project prefers writing their own small functions over pulling in libraries. This skill turns that preference into a repeatable decision, so code stays readable, offline-friendly and easy to explain to a jury.

## The decision rule

Before importing a third-party package, walk these questions in order and stop at the first "yes":

1. **Does the standard library already do it?** Check `hashlib`, `hmac`, `secrets`, `json`, `csv`, `tomllib`, `sqlite3`, `statistics`, `difflib`, `unicodedata`, `re`, `fractions`, `decimal`, `datetime`, `zoneinfo`, `argparse`, `dataclasses`, `typing`, `itertools`, `functools`, `heapq`, `bisect`, `concurrent.futures`, `asyncio`, `http.server`, `urllib`, `unittest`, `logging`. Use it.
2. **Can it be written in under about 60 lines and fully tested?** Write it, put it in `core/` or `utils/`, and add a table-driven test. Typical candidates: trigram or Jaro-Winkler similarity, Verhoeff check digit, hash-chain audit, retry with backoff, unit conversion, Clopper-Pearson bound, token bucket, LRU cache, simple templating, slugify, pagination helpers.
3. **Is it a place where hand-rolling is a risk to the user?** Do not hand-roll these, use the vetted library or stdlib primitive and say why: cryptographic primitives and password hashing (use `hashlib.scrypt`/`hmac`/`secrets` from the stdlib, never your own cipher or hash), JWT signature verification, TLS, database wire protocols, PDF and image decoding, OCR, ML models and embeddings, regex engines, and the web framework itself.
4. **Otherwise** pick the smallest well-maintained library, pin an exact version, and write one line in `docs/decisions.md` saying why the stdlib or an own function was not enough.

## Why the "do not hand-roll" list exists

Own functions are good when the failure mode is a wrong answer you can test. They are bad when the failure mode is a silent security hole (crypto, auth) or a format with years of edge cases (PDF, images). Saying this out loud keeps the preference from turning into risk.

## Project-specific notes

- Lexicons and config: prefer TOML (`tomllib` is stdlib) or JSON over YAML, which needs PyYAML. If the spec says YAML, keep the file layout and mention the swap in `docs/decisions.md`.
- Passwords: `hashlib.scrypt` with a random salt from `secrets`, compare with `hmac.compare_digest`.
- Tests: `unittest` from the stdlib is enough. Use table-driven cases.
- Frontend: no state-management or utility library for things like debounce, deep clone (`structuredClone`), date formatting (`Intl.DateTimeFormat`), or fetch wrappers (`fetch` plus a 20-line helper).
- Libraries that stay because they are the product: the web framework, the database driver, the OCR and embedding runtimes, the PDF reader.

## Audit the repository

Run the auditor to list third-party imports and which ones have a stdlib or own-function alternative worth considering:

```bash
python scripts/audit_imports.py <repo-root>
```

It reads Python files with `ast`, separates stdlib, local and third-party imports, and prints a count per package with a hint where one is available. Treat hints as prompts for a decision, not as orders.

## When you do write an own function

- Keep it pure (inputs to outputs, no hidden state) and put the docstring on what it guarantees.
- Add a table-driven test with at least one hostile input (empty string, unicode, None, very long input).
- Do not copy a library's API surface. Write only what this project calls.
