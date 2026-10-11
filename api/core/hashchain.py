"""Tamper-evident hash chain for audit records. Standard library only.

Each record's hash = sha256(prev_hash + canonical(record)).
Editing, deleting, or reordering any earlier record alters every subsequent hash.
"""

import hashlib
import json
from typing import Any

GENESIS = "0" * 64


def canonical(record: dict[str, Any]) -> str:
    """Produce deterministic JSON: sorted keys, compact separators, UTF-8 preserved."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_hash(prev_hash: str, record: dict[str, Any]) -> str:
    """Compute SHA-256 hash of prev_hash concatenated with canonical record."""
    return hashlib.sha256((prev_hash + canonical(record)).encode("utf-8")).hexdigest()


def build_chain(records: list[dict[str, Any]], prev_hash: str = GENESIS) -> list[dict[str, Any]]:
    """Return sequential chain entries for a list of records."""
    rows = []
    current_prev = prev_hash
    for i, rec in enumerate(records, start=1):
        h = entry_hash(current_prev, rec)
        rows.append({"seq": i, "record": rec, "prev_hash": current_prev, "hash": h})
        current_prev = h
    return rows


def verify_chain(rows: list[dict[str, Any]], genesis: str = GENESIS) -> tuple[bool, int | None]:
    """Return (ok, first_broken_seq_or_None). Checks order, linkage, and hashes."""
    prev = genesis
    expected_seq = 1
    for row in rows:
        if row.get("seq") != expected_seq or row.get("prev_hash") != prev:
            return False, row.get("seq")
        if entry_hash(prev, row.get("record", {})) != row.get("hash"):
            return False, row.get("seq")
        prev = row["hash"]
        expected_seq += 1
    return True, None
