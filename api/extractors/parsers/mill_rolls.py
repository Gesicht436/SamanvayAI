"""Rolling Mill Rolls attribute extractors for Steel domain.

Implements DRAWING mode attributes: normalized drawing number, drawing owner,
barrel diameter and length (mm), and revision level.
Conforms to specsheet.md Section 18.5.3.
"""

import re

from api.extractors.base import ExtractedValue

# 600X1800, 600 DIA X 1800 MM, 650X2000 MM
RE_BARREL = re.compile(
    r"(?<![A-Z0-9])(?P<dia>\d{3,4})\s*(?:MM)?\s*(?:DIA)?\s*[X*]\s*(?P<len>\d{3,4})\s*(?:MM|BARREL)?(?![A-Z0-9])",
    re.IGNORECASE,
)

# DRG NO: D-44120, DRAWING 12345-A, DRG.NO. BSP-MR-001
RE_DRAWING = re.compile(
    r"(?<![A-Z0-9])(?:DRG|DRAWING|DWG)\s*(?:NO|NUMBER|\.)?[:\- ]*\s*(?P<num>[A-Z0-9]+(?:-[A-Z0-9]+)*)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_REVISION = re.compile(
    r"(?<![A-Z0-9])(?:REV|REVISION)[:\- ]*\s*(?P<rev>[A-Z0-9]+)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_HARDNESS = re.compile(
    r"(?<![A-Z0-9])(?P<h>\d{2,3}(?:-\d{2,3})?)\s*(?P<u>HSC|HSD|HRC|BHN)(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_mill_roll_barrel_dia(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts roll barrel diameter in mm."""
    m = RE_BARREL.search(text)
    if m:
        val = int(m.group("dia"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_mill_roll_barrel_length(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts roll barrel length in mm."""
    m = RE_BARREL.search(text)
    if m:
        val = int(m.group("len"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_mill_roll_drawing_number(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts normalized drawing number (uppercase, internal spaces/hyphens collapsed)."""
    m = RE_DRAWING.search(text)
    if m:
        raw = m.group("num")
        norm = raw.upper().replace(" ", "").replace("-", "")
        return ExtractedValue(value=norm, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_mill_roll_drawing_owner(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts drawing owner organization or plant code."""
    t = text.upper()
    for plant in ("SAIL", "TATA", "JSW", "BSP", "RSP", "BSL", "DSP"):
        if re.search(rf"\b{plant}\b", t):
            val = "SAIL" if plant in ("SAIL", "BSP", "RSP", "BSL", "DSP") else plant
            return ExtractedValue(value=val, confidence=0.95, source="rule")
    return ExtractedValue()


def extract_mill_roll_revision(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts drawing revision identifier."""
    m = RE_REVISION.search(text)
    if m:
        val = f"REV_{m.group('rev').upper()}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_mill_roll_hardness(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts surface hardness range (e.g. 70-75 HSC)."""
    m = RE_HARDNESS.search(text)
    if m:
        val = f"{m.group('h')}_{m.group('u').upper()}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()
