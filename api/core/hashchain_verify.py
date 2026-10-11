"""Command-line verifier for the cryptographic audit log hash chain.

Conforms to specsheet.md Section 9.4, 22.2:
- Queries all audit_log records sequentially from PostgreSQL.
- Verifies SHA-256 hash chaining and trigger-computed checksums from genesis to current head.
- Reports number of verified records and chain integrity status.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct CLI script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text

from api.core.hashchain import GENESIS
from api.database import get_sync_engine


def verify_database_audit_log() -> int:
    """Read audit_log sequentially and verify cryptographic integrity."""
    engine = get_sync_engine()

    with engine.connect() as conn:
        res = conn.execute(
            text(
                "SELECT seq, at, actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash "
                "FROM audit_log ORDER BY seq ASC"
            )
        )
        rows = res.fetchall()

    if not rows:
        print("Audit log is empty (0 records). Verification OK.")
        return 0

    expected_prev = GENESIS
    for r in rows:
        # 1. Verify prev_hash linkage
        if r.prev_hash != expected_prev:
            print(
                f"ERROR: Audit log tamper detected! Broken link at seq={r.seq}: "
                f"expected prev_hash {expected_prev}, got {r.prev_hash}",
                file=sys.stderr,
            )
            return 1

        # 2. Recompute this_hash using exact PostgreSQL trigger payload formula
        at_str = r.at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        actor_str = str(r.actor) if r.actor else ""
        before_str = json.dumps(r.before) if r.before is not None else ""
        after_str = json.dumps(r.after) if r.after is not None else ""
        rationale_str = r.rationale or ""

        payload = (
            r.prev_hash
            + f"{at_str}|{actor_str}|{r.action}|{r.entity}|{r.entity_id}|{before_str}|{after_str}|{rationale_str}"
        )
        computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if computed_hash != r.this_hash:
            print(
                f"ERROR: Audit log tamper detected! Row content mismatch at seq={r.seq}: "
                f"expected hash {computed_hash}, got {r.this_hash}",
                file=sys.stderr,
            )
            return 1

        expected_prev = r.this_hash

    head_hash = rows[-1].this_hash
    print(f"Verified {len(rows)} audit log records.")
    print(f"Head Hash: {head_hash}")
    print("Chain Status: OK (Cryptographically intact).")
    return 0


def main() -> int:
    return verify_database_audit_log()


if __name__ == "__main__":
    sys.exit(main())
