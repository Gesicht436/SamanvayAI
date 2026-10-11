#!/usr/bin/env python3
"""List places that assign or return Tier 1 outside the allowed module(s).

Usage: python scan_tier1.py [repo_root] [--allow tiering.py ...]
Standard library only. A reviewing aid, not a proof.
"""

import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"\btier\s*=\s*1\b"),
    re.compile(r"\btier\s*=\s*Tier\.(?:ONE|ONE_AUTO|T1)\b"),
    re.compile(r"\breturn\s+1\b.*#.*tier", re.IGNORECASE),
    re.compile(r"Tier\.(?:ONE|T1)\b"),
    re.compile(r"[\"']tier[\"']\s*:\s*1\b"),
]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist"}


def main(argv: list[str]) -> int:
    args = argv[1:]
    allow = {"tiering.py"}
    root = "."
    i = 0
    while i < len(args):
        if args[i] == "--allow" and i + 1 < len(args):
            allow.add(args[i + 1])
            i += 2
        else:
            root = args[i]
            i += 1
    hits = 0
    for path in Path(root).rglob("*"):
        if path.suffix not in {".py", ".ts", ".tsx", ".js"} or SKIP_DIRS & set(path.parts):
            continue
        if path.name in allow or path.name.startswith("test_") or ".test." in path.name:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(lines, 1):
            if any(p.search(line) for p in PATTERNS):
                print(f"{path}:{n}: {line.strip()}")
                hits += 1
    print(f"\n{hits} location(s) outside {sorted(allow)} to review against S1 to S4, S9, S13, S14.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
