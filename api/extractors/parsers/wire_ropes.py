"""Wire Ropes attribute extractors for Mining and Heavy Engineering domains.

Extracts diameter (mm), rope construction (e.g. 6X36 WS), tensile grade (MPa or N/mm2),
and statutory mine winding approval.
Conforms to specsheet.md Section 18.6.2.
"""

import re

from api.extractors.base import ExtractedValue

# 24MM, 32 MM DIA, 28 MM
RE_DIAMETER = re.compile(
    r"(?<![A-Z0-9])(?P<dia>\d{1,2}(?:\.\d+)?)\s*(?:MM|DIA|\bMM\b\s*DIA)(?![A-Z0-9])",
    re.IGNORECASE,
)

# 6X36 WS, 6X19 S, 8X19 S, 6X41 SFW, 6*36WS
RE_CONSTRUCTION = re.compile(
    r"(?<![A-Z0-9])(?P<strands>\d{1,2})\s*[X*]\s*(?P<wires>\d{1,2})\s*(?P<type>WS|SFW|S|W|FI)?(?![A-Z0-9])",
    re.IGNORECASE,
)

# 1570 N/MM2, 1770 MPA, 1960 N/SQ.MM, 1770 GRADE
RE_TENSILE = re.compile(
    r"(?<![A-Z0-9])(?P<grade>1470|1570|1670|1770|1870|1960|2160)\s*(?:N/MM2|N/MM\^2|MPA|N/SQ\.?MM|GRADE)?(?![A-Z0-9])",
    re.IGNORECASE,
)

# DGMS approval, Statutory mine winding
RE_DGMS = re.compile(
    r"\b(DGMS\s*(?:APPROVED|APPROVAL)?|STATUTORY\s*MINE\s*WINDING|MINE\s*WINDING)\b",
    re.IGNORECASE,
)


def extract_wire_rope_diameter_mm(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts wire rope nominal diameter in mm."""
    m = RE_DIAMETER.search(text)
    if m:
        raw = m.group("dia")
        val = float(raw) if "." in raw else int(raw)
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_wire_rope_construction(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rope construction designation (e.g. 6X36 WS)."""
    m = RE_CONSTRUCTION.search(text)
    if m:
        strands = m.group("strands")
        wires = m.group("wires")
        ctype = m.group("type")
        val = f"{strands}X{wires}"
        if ctype:
            val += f" {ctype.upper()}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_wire_rope_tensile_grade(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts wire nominal tensile strength grade in N/mm2 / MPa."""
    m = RE_TENSILE.search(text)
    if m:
        val = int(m.group("grade"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_wire_rope_approval(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts statutory DGMS approval or mine winding certification status."""
    m = RE_DGMS.search(text)
    if m:
        return ExtractedValue(value="DGMS_WINDING", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue(value="STANDARD_INDUSTRIAL", confidence=0.80, source="rule")
