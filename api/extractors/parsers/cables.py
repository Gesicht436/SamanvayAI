"""Power Cables attribute extractors for Common domain.

Extracts core count (1C, 2C, 3C, 3.5C, 4C), conductor cross-section (sqmm),
and rated system voltage (kV).
Conforms to specsheet.md Section 7.5 and Section 18.2.
"""

import re

from api.extractors.base import ExtractedValue

# 3.5C X 240 SQMM, 4C X 16 SQMM, 1C X 630 SQMM, 3 CORE 300 SQMM, 3.5CX240
RE_CORE_SQMM = re.compile(
    r"(?<![A-Z0-9])(?P<cores>\d(?:\.5)?)\s*(?:C|CORE|CORES)\s*[X*]?\s*(?P<sqmm>\d+(?:\.\d+)?)\s*(?:SQMM|SQ\.MM|SQ\s*MM|MM2)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_SQMM_STANDALONE = re.compile(
    r"(?<![A-Z0-9])(?P<sqmm>\d+(?:\.\d+)?)\s*(?:SQMM|SQ\.MM|SQ\s*MM|MM2)(?![A-Z0-9])",
    re.IGNORECASE,
)

# 1.1KV, 3.3 KV, 11 KV, 33KV, 6.6KV
RE_VOLTAGE = re.compile(
    r"(?<![A-Z0-9])(?P<v>0\.6/1|1\.1|3\.3|6\.6|11|22|33|66)\s*KV(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_cable_core_count(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts number of cores (e.g. 1, 2, 3, 3.5, 4)."""
    m = RE_CORE_SQMM.search(text)
    if m:
        c_str = m.group("cores")
        val = float(c_str) if "." in c_str else int(c_str)
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_cable_conductor_size(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts conductor size in sqmm."""
    m = RE_CORE_SQMM.search(text)
    if m and m.group("sqmm"):
        val = float(m.group("sqmm"))
        if val == int(val):
            val = int(val)
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )

    m2 = RE_SQMM_STANDALONE.search(text)
    if m2:
        val = float(m2.group("sqmm"))
        if val == int(val):
            val = int(val)
        return ExtractedValue(
            value=val,
            confidence=0.90,
            source="rule",
            evidence=(m2.start(), m2.end()),
        )

    return ExtractedValue()


def extract_cable_voltage(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated voltage in kV."""
    m = RE_VOLTAGE.search(text)
    if m:
        v_str = m.group("v")
        if v_str == "0.6/1":
            val = 1.1
        else:
            val = float(v_str)
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()
