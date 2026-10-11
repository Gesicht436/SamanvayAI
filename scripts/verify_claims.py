"""Verification claims checker script.

Conforms to specsheet.md Section 22.2 and skill verify-claims:
- Scans codebase for '# VERIFY: <id>' markers.
- Verifies that every marker in code has a corresponding ledger row in docs/verification.md.
- Exits with 1 if any marker in code is missing from docs/verification.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VERIFICATION_DOC = ROOT_DIR / "docs" / "verification.md"

MARKER_REGEX = re.compile(r"#\s*VERIFY:\s*(VERIFY-\d+)", re.IGNORECASE)
TABLE_ROW_REGEX = re.compile(r"\|\s*`(VERIFY-\d+)`\s*\|", re.IGNORECASE)

DIRS_TO_SCAN = ["api", "db", "dictionaries", "scripts", "packs", "tests"]


def parse_verification_ledger() -> dict[str, str]:
    """Parse docs/verification.md and return map of {verify_id: status}."""
    if not VERIFICATION_DOC.exists():
        print(f"ERROR: Verification ledger not found at {VERIFICATION_DOC}", file=sys.stderr)
        sys.exit(1)

    ledger: dict[str, str] = {}
    with open(VERIFICATION_DOC, encoding="utf-8") as f:
        for line in f:
            match = TABLE_ROW_REGEX.search(line)
            if match:
                vid = match.group(1).upper()
                parts = [p.strip() for p in line.split("|")]
                status = parts[5] if len(parts) > 5 else "UNKNOWN"
                ledger[vid] = status
    return ledger


def scan_codebase_markers() -> list[tuple[str, Path, int]]:
    """Scan code files for '# VERIFY: <id>' markers."""
    markers: list[tuple[str, Path, int]] = []
    for dir_name in DIRS_TO_SCAN:
        d = ROOT_DIR / dir_name
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".csv", ".json", ".yaml", ".yml", ".sql"):
                try:
                    with open(p, encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, start=1):
                            match = MARKER_REGEX.search(line)
                            if match:
                                markers.append((match.group(1).upper(), p.relative_to(ROOT_DIR), line_no))
                except OSError as err:
                    print(f"Warning reading {p}: {err}", file=sys.stderr)
    return markers


def main() -> int:
    ledger = parse_verification_ledger()
    markers = scan_codebase_markers()

    print(f"Loaded {len(ledger)} registered claims from {VERIFICATION_DOC.name}.")
    print(f"Found {len(markers)} '# VERIFY:' markers in codebase.")

    missing_from_ledger: list[tuple[str, Path, int]] = []
    for vid, path, line_no in markers:
        if vid not in ledger:
            missing_from_ledger.append((vid, path, line_no))

    if missing_from_ledger:
        print("\nERROR: Found code markers not registered in docs/verification.md:", file=sys.stderr)
        for vid, path, line_no in missing_from_ledger:
            print(f"  - {vid} at {path}:{line_no}", file=sys.stderr)
        return 1

    verified_count = sum(1 for status in ledger.values() if "VERIFIED" in status.upper())
    pending_count = len(ledger) - verified_count

    print("\nVerification Register Status:")
    print(f"  - VERIFIED claims: {verified_count}")
    print(f"  - PENDING claims:  {pending_count}")
    print("All codebase markers match registered claims. Verification check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
