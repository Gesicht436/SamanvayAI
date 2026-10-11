"""Threaded Fasteners attribute extractors for Common domain.

Extracts thread size (M24, 1 INCH), length mm, and fastener type.
Conforms to specsheet.md Section 7.5.
"""

import re

from api.extractors.base import ExtractedValue

# M24X150, M16 X 100, M20X120 MM
RE_METRIC_BOLT = re.compile(
    r"(?<![A-Z0-9])M(?P<dia>\d{1,2})\s*[X*]\s*(?P<len>\d{2,4})(?:\s*MM)?(?![A-Z0-9])",
    re.IGNORECASE,
)

# 1"-8 UNC X 6 1/2", 3/4" X 100
RE_INCH_BOLT = re.compile(
    r"(?<![A-Z0-9])(?P<dia>\d+(?:/\d+)?|\d+\.\d+)\s*(?:\"|INCH|IN)?\s*(?:-\s*\d+\s*UNC)?\s*[X*]\s*(?P<len>\d+(?:\s+\d+/\d+|\.\d+)?)\s*(?:\"|INCH|MM)?(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_fastener_thread_size(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts bolt thread size (e.g. M24, M16, 1_INCH)."""
    m_met = RE_METRIC_BOLT.search(text)
    if m_met:
        val = f"M{m_met.group('dia')}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m_met.start(), m_met.end()))

    m_inch = RE_INCH_BOLT.search(text)
    if m_inch:
        d = m_inch.group("dia")
        val = f"{d}_INCH"
        return ExtractedValue(value=val, confidence=0.95, source="rule", evidence=(m_inch.start(), m_inch.end()))

    return ExtractedValue()


def extract_fastener_length(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts bolt length in mm."""
    m_met = RE_METRIC_BOLT.search(text)
    if m_met:
        val = int(m_met.group("len"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m_met.start(), m_met.end()))
    return ExtractedValue()


def extract_fastener_type(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts fastener type (STUD_BOLT, HEX_BOLT)."""
    t = text.upper()
    if re.search(r"\bSTUD(?:\s*BOLT)?\b", t):
        return ExtractedValue(value="STUD_BOLT", confidence=0.98, source="rule")
    if re.search(r"\bHEX(?:\s*BOLT|\s*HEAD)?\b", t):
        return ExtractedValue(value="HEX_BOLT", confidence=0.98, source="rule")
    return ExtractedValue(value="STUD_BOLT", confidence=0.80, source="rule")
