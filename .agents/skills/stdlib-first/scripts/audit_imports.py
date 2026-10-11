#!/usr/bin/env python3
"""List third-party imports in a Python repo and suggest stdlib / own-function alternatives.

Usage: python audit_imports.py [repo_root]
Pure standard library.
"""
import ast
import sys
from collections import Counter
from pathlib import Path

HINTS = {
    "requests": "urllib.request for simple calls; keep requests only if you need sessions and retries you do not want to write",
    "yaml": "tomllib (read-only) or json for config; PyYAML only if YAML is mandated",
    "pyyaml": "tomllib or json",
    "dateutil": "datetime + zoneinfo",
    "pytz": "zoneinfo",
    "attr": "dataclasses",
    "attrs": "dataclasses",
    "toolz": "itertools + functools",
    "more_itertools": "itertools",
    "fuzzywuzzy": "own trigram or Jaro-Winkler function; difflib.SequenceMatcher for a quick baseline",
    "rapidfuzz": "own trigram/Jaro-Winkler if the volume is small; keep if you need speed at 100k+ items",
    "thefuzz": "own trigram or difflib",
    "levenshtein": "own 20-line edit distance",
    "tenacity": "own retry-with-backoff helper",
    "retry": "own retry-with-backoff helper",
    "click": "argparse",
    "typer": "argparse",
    "tqdm": "print progress every N items",
    "colorama": "ANSI escape codes",
    "termcolor": "ANSI escape codes",
    "slugify": "unicodedata + re",
    "unidecode": "unicodedata.normalize('NFKD', s)",
    "simplejson": "json",
    "ujson": "json",
    "orjson": "json (only keep if profiling shows JSON is a bottleneck)",
    "cachetools": "functools.lru_cache or a 25-line own cache",
    "numpy": "keep for embeddings; avoid for plain loops or statistics (use statistics, math)",
    "pandas": "csv + dicts for small data; keep only for real tabular analysis",
    "scipy": "own Clopper-Pearson via bisection on the binomial CDF (see samanvay-eval-gate)",
    "jwt": "do NOT hand-roll; keep a vetted JWT library",
    "pyjwt": "do NOT hand-roll; keep a vetted JWT library",
    "bcrypt": "hashlib.scrypt with secrets.token_bytes salt",
    "passlib": "hashlib.scrypt with secrets.token_bytes salt",
    "cryptography": "do NOT hand-roll; keep",
    "pydantic": "keep if it is the API contract layer; dataclasses for internal types",
    "fastapi": "framework: keep",
    "uvicorn": "server: keep",
    "psycopg": "database driver: keep",
    "psycopg2": "database driver: keep",
    "asyncpg": "database driver: keep",
}


def stdlib_names():
    names = set(getattr(sys, "stdlib_module_names", ()))
    names.add("__future__")
    return names


def top_level(mod):
    return mod.split(".")[0]


def local_packages(root: Path):
    found = set()
    for p in root.iterdir():
        if p.is_dir() and (p / "__init__.py").exists():
            found.add(p.name)
        elif p.suffix == ".py":
            found.add(p.stem)
    for p in root.rglob("__init__.py"):
        found.add(p.parent.name)
    for p in root.rglob("*.py"):          # sibling modules imported by bare name
        found.add(p.stem)
    return found


def iter_imports(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield top_level(a.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield top_level(node.module)


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist"}
    std = stdlib_names()
    local = local_packages(root)
    counts = Counter()
    for path in root.rglob("*.py"):
        if skip & set(path.parts):
            continue
        for mod in set(iter_imports(path)):
            if mod in std or mod in local:
                continue
            counts[mod] += 1
    if not counts:
        print("No third-party imports found.")
        return 0
    print(f"Third-party imports under {root}:\n")
    for mod, n in counts.most_common():
        hint = HINTS.get(mod.lower(), "no hint: decide using the rule in SKILL.md")
        print(f"  {mod:<18} {n:>3} file(s)   {hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
