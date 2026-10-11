"""Process Instrumentation attribute extractors for Common domain.

Extracts calibrated pressure range (min, max, unit), process connections,
and explosion protection.
Conforms to specsheet.md Section 7.5.
"""

import re

from api.extractors.base import ExtractedValue

# 0-10 BAR, 0-100 KG/CM2, 0 TO 250 PSI, -1 TO 10 BAR
RE_RANGE = re.compile(
    r"(?<![A-Z0-9])(?P<min>-?\d+(?:\.\d+)?)\s*(?:-|TO)\s*(?P<max>\d+(?:\.\d+)?)\s*(?P<u>BAR|KG/CM2|PSI|KPA|MPA)(?![A-Z0-9])",
    re.IGNORECASE,
)

# 1/2" NPT(F), 1/2 NPT F, 1/4" NPT(F), 1/2" NPT(M)
RE_PROCESS_CONN = re.compile(
    r"(?<![A-Z0-9])(?P<s>1/2|1/4|3/4|1)\s*(?:\"|INCH)?\s*NPT\s*\(?(?P<gender>F|M|FEMALE|MALE)\)?(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_instrument_range_max(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts upper range limit (URL)."""
    m = RE_RANGE.search(text)
    if m:
        val = float(m.group("max"))
        if val == int(val):
            val = int(val)
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_instrument_range_min(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts lower range limit (LRL)."""
    m = RE_RANGE.search(text)
    if m:
        val = float(m.group("min"))
        if val == int(val):
            val = int(val)
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_instrument_range_unit(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts measurement range engineering unit."""
    m = RE_RANGE.search(text)
    if m:
        u = m.group("u").upper()
        return ExtractedValue(value=u, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()


def extract_instrument_process_conn(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts process connection size and gender (e.g. 1/2_NPT_F)."""
    m = RE_PROCESS_CONN.search(text)
    if m:
        size = m.group("s")
        g = "F" if m.group("gender").upper().startswith("F") else "M"
        val = f"{size}_NPT_{g}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    return ExtractedValue()
