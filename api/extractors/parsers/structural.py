"""Structural Steel attribute extractors for Common domain.

Extracts profile type (BEAM, CHANNEL, ANGLE) and section designation (ISMB 300, ISMC 200, ISA 75X75X8).
Conforms to specsheet.md Section 7.5.
"""

import re

from api.extractors.base import ExtractedValue

RE_BEAM = re.compile(r"(?<![A-Z0-9])(?:ISMB|ISLB|ISWB|ISHB|UB|UC)\s*[-.:]?\s*(?P<d>\d{2,4})(?![A-Z0-9])", re.IGNORECASE)
RE_CHANNEL = re.compile(r"(?<![A-Z0-9])(?:ISMC|ISLC|PFC)\s*[-.:]?\s*(?P<d>\d{2,4})(?![A-Z0-9])", re.IGNORECASE)
RE_ANGLE = re.compile(
    r"(?<![A-Z0-9])(?:ISA)\s*[-.:]?\s*(?P<a>\d{2,3})\s*[X*]\s*(?P<b>\d{2,3})\s*[X*]\s*(?P<t>\d{1,2}(?:\.\d+)?)(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_structural_designation(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts standard section designation (e.g. ISMB 300, ISMC 200, ISA 75X75X8)."""
    m_beam = RE_BEAM.search(text)
    if m_beam:
        prefix = m_beam.group(0).split()[0].upper()
        if not prefix.startswith("IS"):
            prefix = "ISMB"
        val = f"{prefix} {m_beam.group('d')}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m_beam.start(), m_beam.end()))

    m_chan = RE_CHANNEL.search(text)
    if m_chan:
        prefix = m_chan.group(0).split()[0].upper()
        if not prefix.startswith("IS"):
            prefix = "ISMC"
        val = f"{prefix} {m_chan.group('d')}"
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m_chan.start(), m_chan.end()))

    m_angle = RE_ANGLE.search(text)
    if m_angle:
        val = f"ISA {m_angle.group('a')}X{m_angle.group('b')}X{m_angle.group('t')}".upper()
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m_angle.start(), m_angle.end()))

    return ExtractedValue()


def extract_structural_profile(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts structural profile type (BEAM, CHANNEL, ANGLE)."""
    if RE_BEAM.search(text) or re.search(r"\b(?:BEAM|JOIST|I-SECTION)\b", text, re.IGNORECASE):
        return ExtractedValue(value="BEAM", confidence=0.95, source="rule")
    if RE_CHANNEL.search(text) or re.search(r"\b(?:CHANNEL|C-SECTION)\b", text, re.IGNORECASE):
        return ExtractedValue(value="CHANNEL", confidence=0.95, source="rule")
    if RE_ANGLE.search(text) or re.search(r"\b(?:ANGLE|L-SECTION)\b", text, re.IGNORECASE):
        return ExtractedValue(value="ANGLE", confidence=0.95, source="rule")
    return ExtractedValue()
