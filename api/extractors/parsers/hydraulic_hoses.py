"""Hydraulic Hoses attribute extractors for Heavy Engineering domain.

Extracts standard class, dash size, DN size in mm, working pressure (bar),
and flags PRESSURE_CONFLICT when stated pressure conflicts with standard class rating.
Conforms to specsheet.md Section 18.7.2.
"""

import re

from api.extractors.base import ExtractedValue

# Dash size mapping to DN mm and nominal inch
DASH_TO_DN = {
    4: 6,
    6: 10,
    8: 12,
    10: 16,
    12: 19,
    16: 25,
    20: 31,
    24: 38,
    32: 51,
}

# Approximate max working pressure (bar) by standard class and dash size
MAX_CLASS_WP = {
    "SAE_100R1AT": {4: 225, 6: 180, 8: 160, 10: 130, 12: 105, 16: 88},
    "EN_853_1SN": {4: 225, 6: 180, 8: 160, 10: 130, 12: 105, 16: 88},
    "SAE_100R2AT": {4: 400, 6: 330, 8: 275, 10: 250, 12: 215, 16: 165},
    "EN_853_2SN": {4: 400, 6: 330, 8: 275, 10: 250, 12: 215, 16: 165},
    "EN_856_4SP": {6: 450, 8: 400, 10: 385, 12: 350, 16: 280},
    "EN_856_4SH": {12: 420, 16: 380, 20: 325, 24: 280},
}

# -8, -08, DASH 8, DASH -8
RE_DASH = re.compile(
    r"(?<![A-Z0-9])(?:DASH\s*)?-(?P<dash>0?[468]|1[026]|2[04]|32)(?![A-Z0-9])",
    re.IGNORECASE,
)

# DN12, DN 12, DN 25
RE_DN = re.compile(
    r"\bDN\s*(?P<dn>6|10|12|16|19|20|25|31|32|38|51)\b",
    re.IGNORECASE,
)

# 1/2", 3/8", 1", 3/4"
RE_INCH = re.compile(
    r"(?<![A-Z0-9])(?P<inch>1/4|3/8|1/2|5/8|3/4|1|1-1/4|1-1/2|2)(?:\s*(?:\"|INCH|IN))(?![A-Z0-9])",
    re.IGNORECASE,
)

# 275 BAR, 400 BAR WP, 2500 PSI, 3000 PSI WP
RE_PRESSURE = re.compile(
    r"(?<![A-Z0-9])(?P<p>\d{2,5})\s*(?P<u>BAR|PSI)\s*(?:WP|WORKING\s*PRESSURE)?(?![A-Z0-9])",
    re.IGNORECASE,
)

INCH_TO_DASH = {
    "1/4": 4,
    "3/8": 6,
    "1/2": 8,
    "5/8": 10,
    "3/4": 12,
    "1": 16,
    "1-1/4": 20,
    "1-1/2": 24,
    "2": 32,
}


def extract_hose_dash_size(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts hydraulic hose dash size (e.g. -8)."""
    m = RE_DASH.search(text)
    if m:
        dash_int = int(m.group("dash"))
        return ExtractedValue(value=f"-{dash_int}", confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    m_inch = RE_INCH.search(text)
    if m_inch:
        inch_str = m_inch.group("inch")
        if inch_str in INCH_TO_DASH:
            dash_int = INCH_TO_DASH[inch_str]
            return ExtractedValue(
                value=f"-{dash_int}", confidence=0.92, source="rule", evidence=(m_inch.start(), m_inch.end())
            )
    m_dn = RE_DN.search(text)
    if m_dn:
        dn_int = int(m_dn.group("dn"))
        for d, dn in DASH_TO_DN.items():
            if dn == dn_int:
                return ExtractedValue(
                    value=f"-{d}", confidence=0.90, source="rule", evidence=(m_dn.start(), m_dn.end())
                )
    return ExtractedValue()


def extract_hose_dn_mm(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts nominal bore diameter in mm (DN)."""
    m = RE_DN.search(text)
    if m:
        val = int(m.group("dn"))
        return ExtractedValue(value=val, confidence=0.98, source="rule", evidence=(m.start(), m.end()))
    # Infer from dash if DN is not explicitly stated
    m_dash = RE_DASH.search(text)
    if m_dash:
        dash_int = int(m_dash.group("dash"))
        if dash_int in DASH_TO_DN:
            return ExtractedValue(value=DASH_TO_DN[dash_int], confidence=0.90, source="rule")
    m_inch = RE_INCH.search(text)
    if m_inch:
        inch_str = m_inch.group("inch")
        if inch_str in INCH_TO_DASH:
            dash_int = INCH_TO_DASH[inch_str]
            if dash_int in DASH_TO_DN:
                return ExtractedValue(value=DASH_TO_DN[dash_int], confidence=0.88, source="rule")
    return ExtractedValue()


def extract_hose_working_pressure_bar(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts stated working pressure in bar, and checks for PRESSURE_CONFLICT."""
    m = RE_PRESSURE.search(text)
    if not m:
        return ExtractedValue()

    raw_p = int(m.group("p"))
    unit = m.group("u").upper()
    bar_val = round(raw_p / 14.5038) if unit == "PSI" else raw_p

    # Check for pressure conflict if standard class and dash size can be identified
    t_up = text.upper()
    identified_class = None
    if "R1AT" in t_up or "1SN" in t_up:
        identified_class = "SAE_100R1AT"
    elif "R2AT" in t_up or "2SN" in t_up:
        identified_class = "SAE_100R2AT"
    elif "4SP" in t_up:
        identified_class = "EN_856_4SP"
    elif "4SH" in t_up:
        identified_class = "EN_856_4SH"

    flags = []
    if identified_class and identified_class in MAX_CLASS_WP:
        dash_m = RE_DASH.search(text)
        if dash_m:
            d_val = int(dash_m.group("dash"))
            max_p = MAX_CLASS_WP[identified_class].get(d_val)
            if max_p and bar_val > (max_p * 1.35):
                # Stated pressure is > 35% higher than nominal max rating for this class/size
                flags.append("PRESSURE_CONFLICT")

    return ExtractedValue(
        value=bar_val,
        confidence=0.75 if "PRESSURE_CONFLICT" in flags else 0.98,
        source="rule",
        flags=flags,
        evidence=(m.start(), m.end()),
    )
