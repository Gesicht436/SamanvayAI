"""Exact binomial (Clopper-Pearson) confidence interval. Standard library only."""
import math


def _log_pmf(n: int, k: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log1p(-p))


def _cdf(n: int, k: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    total = 0.0
    for i in range(k + 1):
        lp = _log_pmf(n, i, p)
        if lp > -math.inf:
            total += math.exp(lp)
    return min(total, 1.0)


def _bisect(f, lo=0.0, hi=1.0, iters=100):
    """Find root of a monotone f on [lo, hi] with f(lo) and f(hi) of opposite sign."""
    flo = f(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, confidence: float = 0.95, two_sided: bool = True):
    """Return (lower, upper) for k successes (or failures) out of n trials."""
    if n <= 0 or k < 0 or k > n:
        raise ValueError("need 0 <= k <= n and n > 0")
    alpha = 1.0 - confidence
    a = alpha / 2 if two_sided else alpha
    # upper: p such that P(X <= k | p) = a   (decreasing in p)
    upper = 1.0 if k == n else _bisect(lambda p: _cdf(n, k, p) - a)
    # lower: p such that P(X >= k | p) = a, i.e. 1 - P(X <= k-1 | p) = a (increasing in p)
    lower = 0.0 if k == 0 else _bisect(lambda p: (1.0 - _cdf(n, k - 1, p)) - a)
    return lower, upper


def upper_bound_zero_failures(n: int, confidence: float = 0.95, two_sided: bool = False) -> float:
    """Closed form for 0 failures in n trials."""
    alpha = 1.0 - confidence
    a = alpha / 2 if two_sided else alpha
    return 1.0 - a ** (1.0 / n)


def trials_needed_for_zero_failures(target_upper: float, confidence: float = 0.95, two_sided: bool = False) -> int:
    """Smallest n with 0 failures whose upper bound is <= target_upper."""
    alpha = 1.0 - confidence
    a = alpha / 2 if two_sided else alpha
    return math.ceil(math.log(a) / math.log(1.0 - target_upper))
