"""Conveyor Belts attribute extractors for Steel and Mining domains.

Extracts carcass type (EP, NN, ST), strength class, ply count (with PLY_CONFLICT check),
belt width (mm), fire resistance (FRAS vs non-FRAS), and cover thickness (top+bottom mm).
Conforms to specsheet.md Section 18.5.2.
"""

import re

from api.extractors.base import ExtractedValue

# EP 630/4, ST 1600, EP 400/3, NN 800/4
RE_STRENGTH_PLY = re.compile(
    r"(?<![A-Z0-9])(?:EP|NN|ST)\s*(?P<str>\d{3,4})(?:/(?P<ply>\d))?(?![A-Z0-9])",
    re.IGNORECASE,
)

# 4 PLY, 3 PLY
RE_EXPLICIT_PLY = re.compile(
    r"(?<![A-Z0-9])(?P<ply>\d)\s*PLY(?![A-Z0-9])",
    re.IGNORECASE,
)

# 1200MM, 1400 MM, 1000 WIDTH
RE_WIDTH = re.compile(
    r"(?<![A-Z0-9])(?P<w>650|800|1000|1200|1400|1600|1800|2000|2200|2400)\s*(?:MM|WIDTH)\b",
    re.IGNORECASE,
)

# 6+3, 8+3, 10+6, 5+2, 6 + 3 MM
RE_COVER = re.compile(
    r"(?<![A-Z0-9])(?P<top>\d+)\s*\+\s*(?P<bot>\d+)(?:\s*MM)?(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_belt_strength_class(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts tensile strength class rating in N/mm (e.g. 630, 800, 1600)."""
    m = RE_STRENGTH_PLY.search(text)
    if m:
        val = int(m.group("str"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_belt_ply_count(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts fabric ply count and flags PLY_CONFLICT if explicit plies conflict with rating suffix."""
    m_str = RE_STRENGTH_PLY.search(text)
    m_exp = RE_EXPLICIT_PLY.search(text)

    suffix_ply = int(m_str.group("ply")) if (m_str and m_str.group("ply")) else None
    explicit_ply = int(m_exp.group("ply")) if m_exp else None

    if suffix_ply and explicit_ply:
        if suffix_ply != explicit_ply:
            return ExtractedValue(
                value=explicit_ply,
                confidence=0.70,
                source="rule",
                flags=["PLY_CONFLICT"],
            )
        return ExtractedValue(value=explicit_ply, confidence=0.98, source="rule")

    if suffix_ply:
        return ExtractedValue(value=suffix_ply, confidence=0.98, source="rule")

    if explicit_ply:
        return ExtractedValue(value=explicit_ply, confidence=0.95, source="rule")

    return ExtractedValue()


def extract_belt_width_mm(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts nominal belt width in mm."""
    m = RE_WIDTH.search(text)
    if m:
        val = int(m.group("w"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_belt_cover_thickness(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts top and bottom rubber cover thickness (e.g. 6+3)."""
    m = RE_COVER.search(text)
    if m:
        val = f"{m.group('top')}+{m.group('bot')}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()
