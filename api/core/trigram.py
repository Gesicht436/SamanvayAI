"""pg_trgm-style trigram similarity. Standard library only."""

import re
from typing import Any

_WORD = re.compile(r"[a-z0-9]+")


def trigrams(text: str) -> set[str]:
    """Lowercase, extract words, pad each word with 2 leading spaces and 1 trailing space,
    and collect 3-character slices (identical to PostgreSQL pg_trgm).
    """
    grams: set[str] = set()
    for word in _WORD.findall((text or "").lower()):
        padded = "  " + word + " "
        for i in range(len(padded) - 2):
            grams.add(padded[i : i + 3])
    return grams


def similarity(a: str, b: str) -> float:
    """Jaccard similarity of trigram sets in range [0.0, 1.0]. Symmetric."""
    ta, tb = trigrams(a), trigrams(b)
    if not ta and not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def top_k(
    query: str, candidates: list[tuple[Any, str]], k: int = 10, min_score: float = 0.0
) -> list[tuple[float, Any, str]]:
    """Rank (id, text) candidate pairs by trigram similarity to query."""
    qt = trigrams(query)
    scored = []
    for cid, text in candidates:
        ct = trigrams(text)
        union = qt | ct
        s = (len(qt & ct) / len(union)) if union else 0.0
        if s >= min_score:
            scored.append((s, cid, text))
    scored.sort(key=lambda x: (-x[0], str(x[1])))
    return scored[:k]
