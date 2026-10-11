"""Reinforcement Steel Bar attribute extractors for Common domain.

Extracts nominal bar diameter in mm (8 to 40 mm).
Conforms to specsheet.md Section 7.5.
"""

import re

from api.extractors.base import ExtractedValue

VALID_REBAR_DIAMETERS: set[int] = {8, 10, 12, 16, 20, 25, 28, 32, 36, 40}

# 25MM, 25 MM, 25 DIA, 25MM DIA, TMT 25MM
RE_REBAR_DIA = re.compile(
    r"(?<![A-Z0-9])(?P<d>\d{1,2})\s*(?:MM|DIA|MM\s*DIA)(?![A-Z0-9])|(?<![A-Z0-9])(?:TMT|REBAR|ROUND)\s*(?P<d2>\d{1,2})(?:\s*MM)?(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_rebar_diameter(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts nominal rebar diameter in mm."""
    m = RE_REBAR_DIA.search(text)
    if m:
        d_str = m.group("d") or m.group("d2")
        val = int(d_str)
        if val in VALID_REBAR_DIAMETERS:
            return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
        return ExtractedValue(value=val, confidence=0.85, source="rule", flags=["NON_STANDARD_REBAR_DIA"])
    return ExtractedValue()
