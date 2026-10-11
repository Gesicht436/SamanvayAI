"""Made to Drawing parts attribute extractors for Heavy Engineering domain.

Extracts normalized drawing number, drawing owner (OEM or customer),
material specification/grade, drawing revision level, and component item name.
Conforms to specsheet.md Section 18.7.3.
"""

import re

from api.extractors.base import ExtractedValue

# DRG NO: D-44120-1, DRAWING: BHEL/SK-9820-2, DWG NO: 50401 REV B
RE_DRAWING_FIELD = re.compile(
    r"(?<![A-Z0-9])(?:DRG|DRAWING|DWG)\s*(?:NO|NUMBER|\.)?[:\- ]*\s*(?P<num>[A-Z0-9]+(?:-[A-Z0-9]+)*)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_REVISION = re.compile(
    r"(?<![A-Z0-9])(?:REV|REVISION)[:\- ]*\s*(?P<rev>[A-Z0-9]+)(?![A-Z0-9])",
    re.IGNORECASE,
)

KNOWN_OWNERS = (
    "BHEL",
    "L&T",
    "LARSEN & TOUBRO",
    "SAIL",
    "TATA",
    "JSW",
    "JINDAL",
    "FLSMIDTH",
    "METSO",
    "SMS GROUP",
    "DANIELI",
    "THERMAX",
    "HEC",
    "HMT",
)

RE_ITEM_NAMES = re.compile(
    r"\b(PINION\s*SHAFT|BEARING\s*HOUSING|TRUNNION|COUPLING\s*HUB|LINER\s*PLATE|IMPELLER|SHEAVE|GEAR\s*WHEEL|BUSHING|DRIVE\s*SHAFT|SPINDLE)\b",
    re.IGNORECASE,
)

RE_MATERIAL = re.compile(
    r"\b(IS\s*2062(?:\s*E\d{3})?|IS\s*1030|EN\s*8|EN\s*9|EN\s*19|EN\s*24|AISI\s*4140|AISI\s*4340|ASTM\s*A148|ASTM\s*A216|SS\s*304|SS\s*316|SA\s*516\s*GR\s*70)\b",
    re.IGNORECASE,
)


def normalize_drawing_string(raw: str) -> str:
    """Normalizes drawing number: collapses spaces/hyphens inside base, preserves item suffix."""
    raw = raw.strip().upper()
    # Check if there is an item suffix like -1, -2, -01, etc.
    suffix_match = re.search(r"[-/ ](?P<suffix>\d+|ITEM\d+|SH\d+)$", raw)
    if suffix_match:
        suffix = suffix_match.group("suffix")
        base = raw[: suffix_match.start()]
        base_clean = re.sub(r"[-/\s]", "", base)
        return f"{base_clean}-{suffix}"
    # No suffix, clean entirely
    return re.sub(r"[-/\s]", "", raw)


def extract_drawing_number(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts normalized drawing number."""
    m = RE_DRAWING_FIELD.search(text)
    if m:
        raw = m.group("num")
        norm = normalize_drawing_string(raw)
        return ExtractedValue(value=norm, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_drawing_owner(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts drawing owner organization or OEM."""
    t_up = text.upper()
    for owner in KNOWN_OWNERS:
        if owner in t_up:
            norm_owner = "LT" if "L&T" in owner else owner.replace(" ", "_")
            return ExtractedValue(value=norm_owner, confidence=0.95, source="rule")
    return ExtractedValue()


def extract_drawing_revision(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts drawing revision code."""
    m = RE_REVISION.search(text)
    if m:
        rev = m.group("rev").upper()
        return ExtractedValue(value=f"REV_{rev}", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_drawing_material_grade(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts material grade/specification from description."""
    m = RE_MATERIAL.search(text)
    if m:
        val = re.sub(r"\s+", " ", m.group(1).upper()).strip()
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_drawing_item_name(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts component item name."""
    m = RE_ITEM_NAMES.search(text)
    if m:
        val = re.sub(r"\s+", " ", m.group(1).upper()).strip()
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()
