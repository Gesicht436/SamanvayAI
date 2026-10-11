"""Pressure class parser for piping, valve, and flange components.

Follows Section 7.2 specification and standard library first principles.
# VERIFY: VERIFY-011 - ASME B16.5 / B16.34 and ISO 7268 (PN) standard pressure classes
"""

import re

from api.extractors.base import ExtractedValue, none_with

CLASSES_FLANGED: set[int] = {150, 300, 600, 900, 1500, 2500}
CLASSES_FORGED: set[int] = {800}
CLASSES_FITTING: set[int] = {2000, 3000, 6000, 9000}
VALID_CLASSES: set[int] = CLASSES_FLANGED | CLASSES_FORGED | CLASSES_FITTING

PN_VALID: set[float] = {2.5, 6, 10, 16, 25, 40, 63, 100, 160, 250, 320, 400}

PRESSURE_CATEGORIES: set[str] = {"VALVES", "PIPES", "FLANGES", "FITTINGS", "HEAVY", "PUMPS"}

RE_CLASS_PREFIX = re.compile(
    r"(?<![A-Z0-9])(?:CLASS|CLS|CL|RATING|ANSI|ASA)\s*[-.:#]?\s*(?P<c>\d{2,4})(?!\d)",
    re.IGNORECASE,
)
RE_CLASS_SUFFIX = re.compile(r"(?<!\d)(?P<c>\d{3,4})\s*(?:#|LBS?|LBF)(?![A-Z0-9])", re.IGNORECASE)
RE_HASH_PREFIX = re.compile(r"(?<![A-Z0-9])#\s*(?P<c>\d{3,4})(?!\d)", re.IGNORECASE)
RE_PN = re.compile(r"(?<![A-Z0-9])PN\s*[-.:]?\s*(?P<pn>\d{1,3}(?:\.5)?)(?!\d)", re.IGNORECASE)
RE_SLASH = re.compile(
    r"(?:CLASS|CLS|CL|RATING)\s*[-.:#]?\s*\d{3,4}\s*/\s*\d{3,4}",
    re.IGNORECASE,
)


def extract_pressure_class(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts standardized ASME or PN pressure class from description text.

    Args:
        text: Raw material description.
        category: Subcategory (e.g. VALVES.GATE, FLANGES.FLANGE).

    Returns:
        ExtractedValue containing canonical class (e.g. ASME_150, PN_16), confidence, and evidence span.
    """
    if not text:
        return ExtractedValue()

    if category:
        cat_upper = category.upper()
        major = cat_upper.split(".")[0]
        if major not in PRESSURE_CATEGORIES and cat_upper not in PRESSURE_CATEGORIES:
            return ExtractedValue()

    t = text.upper()

    # Ambiguous slash syntax (e.g. CLASS 150/300) indicates an extraction conflict
    if RE_SLASH.search(t):
        return none_with("EXTRACTION_CONFLICT")

    found: list[tuple[str, int | float, tuple[int, int]]] = []

    for rx in (RE_CLASS_PREFIX, RE_CLASS_SUFFIX, RE_HASH_PREFIX):
        for m in rx.finditer(t):
            val = int(m.group("c"))
            if val in VALID_CLASSES:
                found.append(("ASME_CLASS", val, m.span("c")))
            elif float(val) in PN_VALID:
                found.append(("PN", float(val), m.span("c")))
            else:
                found.append(("ASME_CLASS", val, m.span("c")))

    for m in RE_PN.finditer(t):
        found.append(("PN", float(m.group("pn")), m.span("pn")))

    if not found:
        return ExtractedValue()

    # Ensure all matches resolve to the exact same system and number
    distinct = {(s, n) for s, n, _ in found}
    if len(distinct) > 1:
        return none_with("EXTRACTION_CONFLICT")

    system, num, span = found[0]

    if system == "ASME_CLASS":
        if num not in VALID_CLASSES:
            return none_with("NON_STANDARD_RATING", span)
        return ExtractedValue(
            value=f"ASME_{num}",
            confidence=0.95,
            source="rule",
            evidence_span=span,
        )

    # PN system
    if num not in PN_VALID:
        return none_with("NON_STANDARD_RATING", span)

    shown = int(num) if num == int(num) else num
    return ExtractedValue(
        value=f"PN_{shown}",
        confidence=0.95,
        source="rule",
        evidence_span=span,
    )
