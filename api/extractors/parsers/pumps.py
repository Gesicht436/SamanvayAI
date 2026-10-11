"""Centrifugal Pumps attribute extractors for Heavy Engineering domain.

Implements physical parsing for pump flow (converting L/S, LPM, GPM to m3/h),
head in metres (flagging PRESSURE_NOT_HEAD on pressure units), speed RPM,
OEM nozzle designations (e.g. 4X3-10), and API 610 pump types.
Conforms to specsheet.md Section 18.7.1.
"""

import re

from api.extractors.base import ExtractedValue
from api.extractors.parsers.pressure_class import extract_pressure_class

RE_FLOW = re.compile(
    r"(?<![A-Z0-9])(?P<q>\d+(?:\.\d+)?)\s*(?P<u>M3/HR|M3/H|M3H|L/S|LPM|US\s*GPM|IMP\s*GPM|GPM)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_HEAD = re.compile(
    r"(?<![A-Z0-9])(?P<h>\d+(?:\.\d+)?)\s*(?P<u>M|MTR|METRES?|FT|FEET)\s*(?:HEAD)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_PRESSURE_AS_HEAD = re.compile(
    r"(?<![A-Z0-9])(?P<p>\d+(?:\.\d+)?)\s*(?P<u>BAR|KG/CM2|PSI)\s*(?:HEAD)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_SPEED = re.compile(
    r"(?<![A-Z0-9])(?P<rpm>\d{3,4})\s*RPM(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_PUMP_TYPE = re.compile(
    r"(?<![A-Z0-9])(?:API\s*610\s*)?(?P<t>OH[1-6]|BB[1-5]|VS[1-7]|ISO\s*2858)(?![A-Z0-9])",
    re.IGNORECASE,
)

# 4X3-10 manufacturer size code (suction 4", discharge 3", impeller 10")
RE_NOZZLE_OEM = re.compile(
    r"(?<![A-Z0-9])(?P<s>\d+(?:\.5)?)\s*[X*]\s*(?P<d>\d+(?:\.5)?)\s*-\s*(?P<imp>\d+)(?![A-Z0-9])",
    re.IGNORECASE,
)

# Explicit nozzle syntax: 100X80 NB, 100X65, 65X40 CL16, SUCTION 100 NB DISCHARGE 80 NB
RE_NOZZLE_EXPLICIT = re.compile(
    r"(?<![A-Z0-9])(?P<s>\d{2,3})\s*[X*]\s*(?P<d>\d{2,3})(?:\s*(?:NB|MM))?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_IMPELLER_DIA = re.compile(
    r"(?<![A-Z0-9])(?P<dia>\d{3})\s*(?:MM)?\s*(?:IMPELLER|IMP)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_DRIVER_KW = re.compile(
    r"(?<![A-Z0-9])(?P<kw>\d+(?:\.\d+)?)\s*KW\s*(?:MOTOR|DRIVER)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_SEAL_PLAN = re.compile(
    r"(?<![A-Z0-9])PLAN\s*(?P<p>\d{1,2}[A-Z]?)(?![A-Z0-9])",
    re.IGNORECASE,
)

# Inch to NB lookup for common pump nozzle sizes
INCH_TO_NB: dict[float, int] = {
    1.0: 25,
    1.5: 40,
    2.0: 50,
    2.5: 65,
    3.0: 80,
    4.0: 100,
    6.0: 150,
    8.0: 200,
    10.0: 250,
    12.0: 300,
    14.0: 350,
    16.0: 400,
}


def extract_pump_flow(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated flow normalized to canonical m3/h."""
    m = RE_FLOW.search(text)
    if not m:
        return ExtractedValue()

    q = float(m.group("q"))
    u = m.group("u").upper().replace(" ", "")
    span = (m.start(), m.end())

    if u in ("M3/HR", "M3/H", "M3H"):
        val = q
    elif u == "L/S":
        val = round(q * 3.6, 2)
    elif u == "LPM":
        val = round(q * 0.06, 2)
    elif u in ("USGPM", "GPM"):
        val = round(q * 0.2271247, 2)
    elif u == "IMPGPM":
        val = round(q * 0.272765, 2)
    else:
        val = q

    return ExtractedValue(value=val, confidence=0.95, source="rule", evidence=span)


def extract_pump_head(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated liquid head in metres. Flags PRESSURE_NOT_HEAD on pressure units."""
    # Check for invalid pressure units in place of liquid head
    m_press = RE_PRESSURE_AS_HEAD.search(text)
    if m_press:
        span = (m_press.start(), m_press.end())
        return ExtractedValue(
            value=None,
            confidence=0.80,
            source="rule",
            evidence=span,
            flags=["PRESSURE_NOT_HEAD"],
        )

    m = RE_HEAD.search(text)
    if not m:
        return ExtractedValue()

    h = float(m.group("h"))
    u = m.group("u").upper()
    span = (m.start(), m.end())

    if u in ("FT", "FEET"):
        val = round(h * 0.3048, 2)
    else:
        val = h

    return ExtractedValue(value=val, confidence=0.95, source="rule", evidence=span)


def extract_pump_speed(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated pump speed in RPM."""
    m = RE_SPEED.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("rpm")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_pump_type(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts API 610 or ISO pump type classification (OH2, BB2, etc.)."""
    m = RE_PUMP_TYPE.search(text)
    if m:
        t = m.group("t").upper()
        if "ISO" in t:
            canonical = "ISO_2858"
        else:
            canonical = t.replace(" ", "")
        return ExtractedValue(
            value=canonical,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_pump_design_standard(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts pump design standard (API 610, ISO 2858, ISO 5199, ASME B73.1)."""
    if re.search(r"\b(?:API\s*610|ISO\s*13709)\b", text, re.IGNORECASE):
        return ExtractedValue(value="API_610", confidence=0.98, source="rule")
    if re.search(r"\b(?:ISO\s*2858|IS\s*5120)\b", text, re.IGNORECASE):
        return ExtractedValue(value="ISO_2858", confidence=0.98, source="rule")
    if re.search(r"\bISO\s*5199\b", text, re.IGNORECASE):
        return ExtractedValue(value="ISO_5199", confidence=0.98, source="rule")
    if re.search(r"\b(?:ASME|ANSI)\s*B73\.?1\b", text, re.IGNORECASE):
        return ExtractedValue(value="ASME_B73_1", confidence=0.98, source="rule")
    # Standard API 610 pump type codes OH1-OH6, BB1-BB5, VS1-VS7 infer API_610
    if re.search(r"\b(?:OH[1-6]|BB[1-5]|VS[1-7])\b", text, re.IGNORECASE):
        return ExtractedValue(
            value="API_610",
            confidence=0.95,
            source="rule",
            flags=["INFERRED_FROM_TYPE_CODE"],
        )
    return ExtractedValue()


def _parse_nozzle_sizes(text: str) -> tuple[int, int, tuple[int, int], list[str]] | None:
    """Helper parsing suction and discharge NB."""
    m_oem = RE_NOZZLE_OEM.search(text)
    if m_oem:
        s_inch = float(m_oem.group("s"))
        d_inch = float(m_oem.group("d"))
        s_nb = INCH_TO_NB.get(s_inch, int(s_inch * 25))
        d_nb = INCH_TO_NB.get(d_inch, int(d_inch * 25))
        span = (m_oem.start(), m_oem.end())
        return (s_nb, d_nb, span, ["OEM_SIZE_CODE"])

    m_exp = RE_NOZZLE_EXPLICIT.search(text)
    if m_exp:
        s_nb = int(m_exp.group("s"))
        d_nb = int(m_exp.group("d"))
        span = (m_exp.start(), m_exp.end())
        return (s_nb, d_nb, span, [])

    return None


def extract_pump_suction_nb(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts suction nozzle size in NB (mm)."""
    parsed = _parse_nozzle_sizes(text)
    if parsed:
        s_nb, _, span, flags = parsed
        return ExtractedValue(value=s_nb, confidence=0.95, source="rule", evidence=span, flags=flags)
    return ExtractedValue()


def extract_pump_discharge_nb(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts discharge nozzle size in NB (mm)."""
    parsed = _parse_nozzle_sizes(text)
    if parsed:
        _, d_nb, span, flags = parsed
        return ExtractedValue(value=d_nb, confidence=0.95, source="rule", evidence=span, flags=flags)
    return ExtractedValue()


def extract_pump_flange_class(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts nozzle flange rating class."""
    return extract_pressure_class(text, category="FLANGES")


def extract_pump_impeller_dia(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts impeller diameter in mm."""
    m = RE_IMPELLER_DIA.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("dia")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_pump_driver_kw(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts driver rating in kW."""
    m = RE_DRIVER_KW.search(text)
    if m:
        return ExtractedValue(
            value=float(m.group("kw")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_pump_seal_plan(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts API 682 mechanical seal flush plan (e.g. PLAN 11, PLAN 53A)."""
    m = RE_SEAL_PLAN.search(text)
    if m:
        return ExtractedValue(
            value=f"PLAN_{m.group('p').upper()}",
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()
