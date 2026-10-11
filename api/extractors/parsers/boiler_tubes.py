"""Boiler Tubes attribute extractors for Power domain.

Extracts outside diameter (OD mm), wall thickness (WT mm), wall basis
(MINIMUM or NOMINAL), material specification, spec body (ASME vs ASTM),
and statutory IBR certificate flags.
Conforms to specsheet.md Section 18.4.3.
"""

import re

from api.extractors.base import ExtractedValue

# 60.3 OD X 5.6 WT, 50.8 X 4.5 MWT, 51.0MM OD X 4.0MM WT
RE_OD_WALL = re.compile(
    r"(?<![A-Z0-9])(?P<od>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:OD)?\s*[X*]\s*(?P<wall>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:WT|WALL|THK)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_OD_ALONE = re.compile(
    r"(?<![A-Z0-9])(?P<od>\d+(?:\.\d+)?)\s*(?:MM)?\s*OD(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_WALL_ALONE = re.compile(
    r"(?<![A-Z0-9])(?P<wall>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:WT|WALL|THK|MWT|NWT)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_WALL_BASIS = re.compile(
    r"(?<![A-Z0-9])(?P<b>MWT|MINIMUM\s*WALL|MIN\s*WALL|NWT|NOMINAL\s*WALL|NOM\s*WALL)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_SPEC_BODY = re.compile(
    r"(?<![A-Z0-9])(?P<sb>ASME\s*SA|SA-?|ASTM\s*A|ASTM-?|A-?)(?P<num>213|210|192)(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_boiler_tube_od(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts outside diameter in mm (never NB)."""
    m = RE_OD_WALL.search(text)
    if m:
        val = float(m.group("od"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    m_alone = RE_OD_ALONE.search(text)
    if m_alone:
        val = float(m_alone.group("od"))
        return ExtractedValue(value=val, confidence=0.95, source="rule", evidence=(m_alone.start(), m_alone.end()))
    return ExtractedValue()


def extract_boiler_tube_wall(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts wall thickness in mm."""
    m = RE_OD_WALL.search(text)
    if m:
        val = float(m.group("wall"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    m_alone = RE_WALL_ALONE.search(text)
    if m_alone:
        val = float(m_alone.group("wall"))
        return ExtractedValue(value=val, confidence=0.95, source="rule", evidence=(m_alone.start(), m_alone.end()))
    return ExtractedValue()


def extract_boiler_tube_wall_basis(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts wall basis (MINIMUM or NOMINAL).

    Flags WALL_BASIS_UNKNOWN if not stated in requisition per specsheet.md 18.4.3.
    """
    m = RE_WALL_BASIS.search(text)
    if m:
        b = m.group("b").upper()
        if "M" in b:
            return ExtractedValue(value="MINIMUM", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
        if "N" in b:
            return ExtractedValue(value="NOMINAL", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue(value=None, confidence=0.0, source="rule", flags=["WALL_BASIS_UNKNOWN"])


def extract_boiler_tube_spec_body(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts specification issuing body (ASME_SA vs ASTM_A)."""
    m = RE_SPEC_BODY.search(text)
    if m:
        sb = m.group("sb").upper()
        if "SA" in sb:
            return ExtractedValue(value="ASME_SA", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
        if "A" in sb or "ASTM" in sb:
            return ExtractedValue(value="ASTM_A", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    if "SA213" in text.upper() or "SA210" in text.upper():
        return ExtractedValue(value="ASME_SA", confidence=0.95, source="rule")
    if "A213" in text.upper() or "A210" in text.upper():
        return ExtractedValue(value="ASTM_A", confidence=0.95, source="rule")
    return ExtractedValue()


def extract_boiler_tube_material_spec(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts standard specification number (SA213, SA210, SA192)."""
    m = RE_SPEC_BODY.search(text)
    if m:
        sb = "SA" if "SA" in m.group("sb").upper() else "A"
        val = f"{sb}{m.group('num')}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_boiler_tube_route(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts manufacturing route (SEAMLESS_HOT_FINISHED vs SEAMLESS_COLD_DRAWN)."""
    t = text.upper()
    if re.search(r"\bCOLD\s*DRAWN\b|\bCD\b", t):
        return ExtractedValue(value="SEAMLESS_COLD_DRAWN", confidence=0.98, source="rule")
    if re.search(r"\bHOT\s*FINISHED\b|\bHF\b", t):
        return ExtractedValue(value="SEAMLESS_HOT_FINISHED", confidence=0.98, source="rule")
    if re.search(r"\bSEAMLESS\b|\bSMLS\b", t):
        return ExtractedValue(value="SEAMLESS_HOT_FINISHED", confidence=0.90, source="rule")
    return ExtractedValue()


def extract_boiler_tube_ibr(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts statutory IBR certification status."""
    t = text.upper()
    if re.search(r"\bIBR\b|\bINDIAN\s*BOILER\b|\bFORM\s*III\b", t):
        return ExtractedValue(value="IBR_FORM_III_A", confidence=0.98, source="rule")
    return ExtractedValue()
