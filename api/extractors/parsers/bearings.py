"""Rolling Element Bearings attribute extractors for Common domain.

Extracts base designation (6312, 22212, NU 316), bearing family type,
and suffix cage materials.
Conforms to specsheet.md Section 7.5.
"""

import re

from api.extractors.base import ExtractedValue

RE_BASE_DESIGNATION = re.compile(
    r"(?<![A-Z0-9])(?P<prefix>NU|NJ|NUP|N|NN|NNU|UC|NA)?\s*(?P<num>[1-8]\d{2,4}|2\d{4}|3\d{4}|7\d{3})(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_CAGE = re.compile(
    r"\b(?P<word>BRASS|STEEL|POLYAMIDE)\s*CAGE\b|(?<![A-Z0-9])(?P<c>M|MA|MB|J|TN9|TVP|TN|ECJ)(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_bearing_base_designation(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts ISO/DIN bearing base designation number."""
    m = RE_BASE_DESIGNATION.search(text)
    if m:
        pref = (m.group("prefix") or "").upper().strip()
        num = m.group("num")
        val = f"{pref} {num}".strip() if pref else num
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_bearing_type(text: str, category: str | None = None) -> ExtractedValue:
    """Infers bearing type from designation or keywords."""
    t = text.upper()
    if re.search(r"\bSPHERICAL\s*ROLLER\b|\b2\d{4}\b", t):
        return ExtractedValue(value="SPHERICAL_ROLLER", confidence=0.95, source="rule")
    if re.search(r"\bCYLINDRICAL\s*ROLLER\b|\b(?:NU|NJ|NUP)\s*\d+\b", t):
        return ExtractedValue(value="CYLINDRICAL_ROLLER", confidence=0.95, source="rule")
    if re.search(r"\bTAPERED\s*ROLLER\b|\b3\d{4}\b", t):
        return ExtractedValue(value="TAPERED_ROLLER", confidence=0.95, source="rule")
    if re.search(r"\bDEEP\s*GROOVE\b|\b[6][0-9]{3}\b", t):
        return ExtractedValue(value="DEEP_GROOVE_BALL", confidence=0.95, source="rule")
    return ExtractedValue()


def extract_bearing_cage(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts cage material suffix or keyword (BRASS, STEEL, POLYAMIDE)."""
    m = RE_CAGE.search(text)
    if m:
        if m.group("word"):
            return ExtractedValue(
                value=m.group("word").upper(), confidence=0.98, source="rule", evidence=(m.start(), m.end())
            )
        c = (m.group("c") or "").upper()
        if c in ("M", "MA", "MB"):
            return ExtractedValue(value="BRASS", confidence=0.95, source="rule", evidence=(m.start(), m.end()))
        if c in ("J", "ECJ"):
            return ExtractedValue(value="STEEL", confidence=0.95, source="rule", evidence=(m.start(), m.end()))
        if c in ("TN9", "TVP", "TN"):
            return ExtractedValue(value="POLYAMIDE", confidence=0.95, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()
