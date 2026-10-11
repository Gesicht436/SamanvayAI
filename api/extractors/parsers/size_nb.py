"""Piping size to Nominal Bore (NB) mm extractor.

Follows Section 7.1 specification and standard library first principles.
# VERIFY: VERIFY-003 - Pipe nominal bore mm equivalent to inches (ASME B36.10M / IS 1239)
"""

import re
from decimal import Decimal
from fractions import Fraction

from api.extractors.base import ExtractedValue

# Mapping of inch size (as Fraction) to nominal bore (NB in mm)
NB_BY_INCH: dict[Fraction, int] = {
    Fraction(1, 8): 6,
    Fraction(1, 4): 8,
    Fraction(3, 8): 10,
    Fraction(1, 2): 15,
    Fraction(3, 4): 20,
    Fraction(1): 25,
    Fraction(5, 4): 32,
    Fraction(3, 2): 40,
    Fraction(2): 50,
    Fraction(5, 2): 65,
    Fraction(3): 80,
    Fraction(7, 2): 90,
    Fraction(4): 100,
    Fraction(5): 125,
    Fraction(6): 150,
    Fraction(8): 200,
    Fraction(10): 250,
    Fraction(12): 300,
    Fraction(14): 350,
    Fraction(16): 400,
    Fraction(18): 450,
    Fraction(20): 500,
    Fraction(22): 550,
    Fraction(24): 600,
    Fraction(26): 650,
    Fraction(28): 700,
    Fraction(30): 750,
    Fraction(32): 800,
    Fraction(34): 850,
    Fraction(36): 900,
    Fraction(40): 1000,
    Fraction(42): 1050,
    Fraction(48): 1200,
}

VALID_NB: set[int] = set(NB_BY_INCH.values())

SIZE_CATEGORIES: set[str] = {
    "VALVES",
    "PIPES",
    "FLANGES",
    "FITTINGS",
}

# Regex to strip schedule notations so SCH 40 does not match as NB 40
RE_SCH = re.compile(r"(?:SCH(?:EDULE)?|SCHD)\s*\.?\s*(?:\d+S?|STD|XS|XXS)\b", re.IGNORECASE)

# Metric fastener pattern (e.g. M24X150MM)
RE_METRIC_FASTENER = re.compile(r"\bM\d+(?:\.\d+)?\s*[X*]\s*\d+(?:\.\d+)?(?:\s*MM)?\b", re.IGNORECASE)

# Direct DN / NB matches
RE_DN_PREFIX = re.compile(r"(?<![A-Z0-9])(?:DN|NB)\s*(?P<nb>\d{1,4})\b", re.IGNORECASE)
RE_DN_SUFFIX = re.compile(r"\b(?P<nb>\d{1,4})\s*(?:NB|DN)\b", re.IGNORECASE)

# Inch representation
RE_INCH = re.compile(
    r'(?<![A-Z0-9])(?P<n>\d+(?:[\s-]\d+/\d+|\.\d+|/\d+)?)\s*(?:INCHES|INCH|IN\b|"|\'\')(?!")',
    re.IGNORECASE,
)

# Millimetre representation (only valid standard NB)
RE_MM = re.compile(r"(?<![A-Z0-9.])(?P<mm>\d{2,4})\s*MM\b", re.IGNORECASE)

# Reducer pattern: e.g. 6X4, 6"X4", DN150 X DN100
RE_REDUCER_INCH = re.compile(
    r'(?<![A-Z0-9])(?P<n1>\d+(?:[\s-]\d+/\d+|\.\d+|/\d+)?)\s*(?:["\']|IN|INCH|INCHES)?\s*(?:X|\*)\s*(?P<n2>\d+(?:[\s-]\d+/\d+|\.\d+|/\d+)?)\s*(?:["\']|IN|INCH|INCHES)?\b',
    re.IGNORECASE,
)


def _parse_fraction(s: str) -> Fraction | None:
    """Parses mixed fraction ('1-1/2', '1 1/2'), simple fraction ('1/2'), or decimal/integer ('1.5', '6')."""
    clean = s.strip()
    try:
        if "-" in clean or " " in clean:
            parts = clean.replace("-", " ").split()
            if len(parts) == 2 and "/" in parts[1]:
                whole = int(parts[0])
                num, denom = parts[1].split("/")
                return Fraction(whole * int(denom) + int(num), int(denom))
        if "/" in clean:
            num, denom = clean.split("/")
            return Fraction(int(num), int(denom))
        if "." in clean:
            d = Decimal(clean)
            return Fraction(int(d * 1000), 1000)
        return Fraction(int(clean))
    except (ValueError, ZeroDivisionError, ArithmeticError):
        return None


def extract_size_nb(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts pipe Nominal Bore (NB in mm) from raw description text.

    Args:
        text: Raw material description.
        category: Subcategory (e.g. VALVES.GATE, FASTENERS.BOLT).

    Returns:
        ExtractedValue containing canonical NB integer, confidence, and raw evidence span.
    """
    if not text:
        return ExtractedValue()

    # Category gating: only piping, valve, flange, and fitting categories are allowed
    if category:
        cat_upper = category.upper()
        major = cat_upper.split(".")[0]
        if major not in SIZE_CATEGORIES and cat_upper not in SIZE_CATEGORIES:
            return ExtractedValue()

    # Reject if text describes a metric fastener (e.g. M24X150MM)
    if RE_METRIC_FASTENER.search(text):
        return ExtractedValue()

    # Mask schedule tokens with spaces of equal length to preserve exact character offsets
    masked_text = text
    for m in RE_SCH.finditer(text):
        s, e = m.span()
        masked_text = masked_text[:s] + (" " * (e - s)) + masked_text[e:]

    # Priority 1: Check DN / NB prefix or suffix
    for rx in (RE_DN_PREFIX, RE_DN_SUFFIX):
        m = rx.search(masked_text)
        if m:
            nb_val = int(m.group("nb"))
            if nb_val in VALID_NB:
                return ExtractedValue(
                    value=nb_val,
                    confidence=0.95,
                    source="rule",
                    evidence_span=m.span("nb"),
                )

    # Priority 2: Check reducer inches (e.g. 6" X 4", 6X4)
    m_red = RE_REDUCER_INCH.search(masked_text)
    if m_red:
        f1 = _parse_fraction(m_red.group("n1"))
        f2 = _parse_fraction(m_red.group("n2"))
        if f1 in NB_BY_INCH and f2 in NB_BY_INCH:
            primary_nb = NB_BY_INCH[f1]
            return ExtractedValue(
                value=primary_nb,
                confidence=0.95,
                source="rule",
                evidence_span=m_red.span("n1"),
            )

    # Priority 3: Check inch specification (e.g. 1-1/2", 6", 2 INCH)
    for m in RE_INCH.finditer(masked_text):
        raw_num = m.group("n")
        frac = _parse_fraction(raw_num)
        if frac is not None and frac in NB_BY_INCH:
            return ExtractedValue(
                value=NB_BY_INCH[frac],
                confidence=0.95,
                source="rule",
                evidence_span=m.span("n"),
            )

    # Priority 4: Check mm specification (e.g. 150 MM) only if it matches standard NB
    for m in RE_MM.finditer(masked_text):
        mm_val = int(m.group("mm"))
        if mm_val in VALID_NB:
            return ExtractedValue(
                value=mm_val,
                confidence=0.90,
                source="rule",
                evidence_span=m.span("mm"),
            )

    return ExtractedValue()
