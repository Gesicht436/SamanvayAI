"""Jaro and Jaro-Winkler similarity. Standard library only."""


def jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0 if s1 else 0.0
    l1, l2 = len(s1), len(s2)
    if not l1 or not l2:
        return 0.0
    window = max(l1, l2) // 2 - 1
    window = max(window, 0)
    m1 = [False] * l1
    m2 = [False] * l2
    matches = 0
    for i, ch in enumerate(s1):
        lo, hi = max(0, i - window), min(i + window + 1, l2)
        for j in range(lo, hi):
            if not m2[j] and s2[j] == ch:
                m1[i] = m2[j] = True
                matches += 1
                break
    if not matches:
        return 0.0
    t = 0
    k = 0
    for i in range(l1):
        if m1[i]:
            while not m2[k]:
                k += 1
            if s1[i] != s2[k]:
                t += 1
            k += 1
    t //= 2
    return (matches / l1 + matches / l2 + (matches - t) / matches) / 3.0


def jaro_winkler(s1: str, s2: str, p: float = 0.1, max_prefix: int = 4) -> float:
    j = jaro(s1, s2)
    prefix = 0
    for a, b in zip(s1, s2):
        if a != b or prefix == max_prefix:
            break
        prefix += 1
    return j + prefix * p * (1.0 - j)
