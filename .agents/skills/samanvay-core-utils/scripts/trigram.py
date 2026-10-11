"""pg_trgm-style trigram similarity. Standard library only."""
import re

_WORD = re.compile(r"[a-z0-9]+")


def trigrams(text: str) -> set:
    """Lowercase, split on non-alphanumerics, pad each word with two spaces
    in front and one behind, collect 3-character windows (as pg_trgm does)."""
    grams = set()
    for word in _WORD.findall((text or "").lower()):
        padded = "  " + word + " "
        for i in range(len(padded) - 2):
            grams.add(padded[i:i + 3])
    return grams


def similarity(a: str, b: str) -> float:
    """Jaccard similarity of trigram sets, 0.0 to 1.0. Symmetric."""
    ta, tb = trigrams(a), trigrams(b)
    if not ta and not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def top_k(query: str, candidates, k: int = 10, min_score: float = 0.0):
    """Rank (id, text) pairs by similarity to query. Returns [(score, id, text)]."""
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
