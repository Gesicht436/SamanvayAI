"""Tamper-evident hash chain for audit records. Standard library only.

Each record's hash = sha256(prev_hash + canonical(record)). Editing, deleting
or reordering any earlier record changes every later hash.
"""
import hashlib
import json

GENESIS = "0" * 64


def canonical(record: dict) -> str:
    """Stable JSON: sorted keys, compact separators, non-ASCII kept as-is."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_hash(prev_hash: str, record: dict) -> str:
    return hashlib.sha256((prev_hash + canonical(record)).encode("utf-8")).hexdigest()


def build_chain(records, prev_hash: str = GENESIS):
    """Return rows [{'seq', 'record', 'prev_hash', 'hash'}] for a list of records."""
    rows = []
    for i, rec in enumerate(records, start=1):
        h = entry_hash(prev_hash, rec)
        rows.append({"seq": i, "record": rec, "prev_hash": prev_hash, "hash": h})
        prev_hash = h
    return rows


def verify_chain(rows, genesis: str = GENESIS):
    """Return (ok, first_broken_seq_or_None). Checks order, linkage and hashes."""
    prev = genesis
    expected_seq = 1
    for row in rows:
        if row.get("seq") != expected_seq or row.get("prev_hash") != prev:
            return False, row.get("seq")
        if entry_hash(prev, row["record"]) != row.get("hash"):
            return False, row.get("seq")
        prev = row["hash"]
        expected_seq += 1
    return True, None
