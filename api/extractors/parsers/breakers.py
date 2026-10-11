"""Circuit Breakers attribute extractors for Power domain.

Extracts rated voltage (kV), rated continuous current (A), short-circuit
breaking current (kA), duration (s), and pole count.
Conforms to specsheet.md Section 18.4.2.
"""

import re

from api.extractors.base import ExtractedValue

# 25KA/3S, 31.5 KA 3 SEC, 40 KA 1S, 25KA
RE_BREAKING = re.compile(
    r"(?<![A-Z0-9])(?P<ka>\d+(?:\.\d+)?)\s*KA(?:\s*(?:/|FOR)\s*(?P<s>\d+)\s*(?:S|SEC|SECS))?(?![A-Z0-9])",
    re.IGNORECASE,
)

# 1250A, 1600 A, 2000 AMP, 630A
RE_CURRENT = re.compile(
    r"(?<![A-Z0-9])(?P<a>\d{3,4})\s*(?:A|AMP|AMPS)(?![A-Z0-9])",
    re.IGNORECASE,
)

# 33KV, 11 KV, 415V, 0.415 KV
RE_VOLTAGE = re.compile(
    r"(?<![A-Z0-9])(?P<v>\d+(?:\.\d+)?)\s*(?P<u>KV|V)(?![A-Z0-9])",
    re.IGNORECASE,
)

# 3P, 4P, 3 POLE, 4 POLE
RE_POLES = re.compile(
    r"(?<![A-Z0-9])(?P<p>3|4)\s*(?:P|POLE|POLES)(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_breaker_breaking_ka(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated short-circuit breaking current in kA."""
    m = RE_BREAKING.search(text)
    if m:
        val = float(m.group("ka"))
        if val == int(val):
            val = int(val)
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_breaker_duration_s(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts short-time duration in seconds."""
    m = RE_BREAKING.search(text)
    if m and m.group("s"):
        val = int(m.group("s"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue(value=3, confidence=0.85, source="rule", flags=["DEFAULT_DURATION_3S"])


def extract_breaker_current(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated continuous current in Amperes."""
    m = RE_CURRENT.search(text)
    if m:
        val = int(m.group("a"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_breaker_voltage(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated system voltage in kV."""
    m = RE_VOLTAGE.search(text)
    if m:
        val = float(m.group("v"))
        u = m.group("u").upper()
        if u == "V" or val > 100:
            val = val / 1000.0
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_breaker_poles(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts number of poles (3 or 4)."""
    m = RE_POLES.search(text)
    if m:
        val = int(m.group("p"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue(value=3, confidence=0.85, source="rule", flags=["DEFAULT_3_POLE"])


def extract_breaker_mounting(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts mounting style (WITHDRAWABLE or FIXED)."""
    t = text.upper()
    if re.search(r"\b(?:WITHDRAWABLE|DRAWOUT|DRAW-OUT|TROLLEY)\b", t):
        return ExtractedValue(value="WITHDRAWABLE", confidence=0.98, source="rule")
    if re.search(r"\bFIXED\b", t):
        return ExtractedValue(value="FIXED", confidence=0.98, source="rule")
    return ExtractedValue()
