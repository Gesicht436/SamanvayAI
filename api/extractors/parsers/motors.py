"""Electric Motors and Hazardous Area Ex attribute extractors.

Implements physical parsing for motor ratings, IEC frames, efficiency classes,
and IEC 60079 / DGMS explosion-proof markings (Ex Group I vs Group II).
Conforms to specsheet.md Section 7.4 and Section 18.6.3.
"""

import re

from api.extractors.base import ExtractedValue, none_with

# Standard IEC kW ratings (IS 12615 / IEC 60034-30-1)
IEC_KW = [
    0.75,
    1.1,
    1.5,
    2.2,
    3.0,
    3.7,
    4.0,
    5.5,
    7.5,
    11.0,
    15.0,
    18.5,
    22.0,
    30.0,
    37.0,
    45.0,
    55.0,
    75.0,
    90.0,
    110.0,
    132.0,
    160.0,
    200.0,
    250.0,
    315.0,
    355.0,
    400.0,
    450.0,
    500.0,
]

# Standard HP to IEC kW mapping (75 HP is 55 kW per spec Section 7.4)
HP_TO_IEC = {
    1.0: 0.75,
    1.5: 1.1,
    2.0: 1.5,
    3.0: 2.2,
    5.0: 3.7,
    7.5: 5.5,
    10.0: 7.5,
    15.0: 11.0,
    20.0: 15.0,
    25.0: 18.5,
    30.0: 22.0,
    40.0: 30.0,
    50.0: 37.0,
    60.0: 45.0,
    75.0: 55.0,
    100.0: 75.0,
    125.0: 90.0,
    150.0: 110.0,
    200.0: 150.0,
}

RPM_TO_POLES = {3000: 2, 1500: 4, 1000: 6, 750: 8}

# Regex patterns
RE_POWER = re.compile(
    r"(?<![A-Z0-9])(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>KW|HP)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_POLES = re.compile(
    r"(?<![A-Z0-9])(?P<p>[2468])\s*(?:P|POLE|POLES)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_RPM = re.compile(
    r"(?<![A-Z0-9])(?P<rpm>\d{3,4})\s*RPM(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_FRAME_IEC = re.compile(
    r"(?<![A-Z0-9])(?P<f>\d{2,3}[SML])(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_FRAME_NEMA = re.compile(
    r"(?<![A-Z0-9])(?P<f>\d{3}T)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_EFFICIENCY = re.compile(
    r"(?<![A-Z0-9])(?P<eff>IE[1-4]|EFF[1-3])(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_VOLTAGE = re.compile(
    r"(?<![A-Z0-9])(?P<v>\d+(?:\.\d+)?)\s*(?P<u>V|KV)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_FREQ = re.compile(
    r"(?<![A-Z0-9])(?P<hz>50|60)\s*HZ(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_APPROVAL = re.compile(
    r"(?<![A-Z0-9])(?P<auth>DGMS|PESO|CCOE|ATEX|IECEX)\s*[-/:]?\s*(?P<no>[A-Z0-9/_-]+)(?![A-Z0-9])",
    re.IGNORECASE,
)

# Ex regex matching: "Ex d I", "Ex d IIB T4 Gb", "Ex e I Mb", "Ex d I/IIB"
RE_EX_STRING = re.compile(
    r"(?<![A-Z0-9])(?:EX|EEX)\s+(?P<type>D|E|NA|IA|IB|IC|TB|P)\b(?:\s+(?P<grp>I/IIB|I/IIC|I/II|II[ABC]|II|I)\b)?(?:\s+(?P<temp>T[1-6])\b)?(?:\s+(?P<epl>MA|MB|MC|GA|GB|GC|DA|DB|DC)\b)?",
    re.IGNORECASE,
)


def extract_motor_power(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated motor power in canonical kW, converting HP if needed."""
    matches = list(RE_POWER.finditer(text))
    if not matches:
        return ExtractedValue()
    if len(matches) > 1:
        # Check if all matches represent identical values
        vals = [m.group(0).upper().replace(" ", "") for m in matches]
        if len(set(vals)) > 1:
            return none_with("EXTRACTION_CONFLICT", (matches[0].start(), matches[-1].end()))

    m = matches[0]
    num = float(m.group("num"))
    unit = m.group("unit").upper()
    span = (m.start(), m.end())

    if unit == "HP":
        if num in HP_TO_IEC:
            return ExtractedValue(value=HP_TO_IEC[num], confidence=0.95, source="rule", evidence=span)
        # Non-standard HP conversion
        raw_kw = round(num * 0.7457, 2)
        return ExtractedValue(
            value=raw_kw,
            confidence=0.85,
            source="rule",
            evidence=span,
            flags=["NON_STANDARD_RATING"],
        )

    # Unit is KW
    for std_kw in IEC_KW:
        if abs(num - std_kw) / std_kw <= 0.02:
            return ExtractedValue(value=std_kw, confidence=0.95, source="rule", evidence=span)

    # Keep raw kW if non-standard rating
    return ExtractedValue(
        value=num,
        confidence=0.85,
        source="rule",
        evidence=span,
        flags=["NON_STANDARD_RATING"],
    )


def extract_motor_poles(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts motor pole count (2, 4, 6, 8) from explicit pole text or rpm."""
    m_p = RE_POLES.search(text)
    if m_p:
        poles = int(m_p.group("p"))
        return ExtractedValue(value=poles, confidence=0.95, source="rule", evidence=(m_p.start(), m_p.end()))

    m_rpm = RE_RPM.search(text)
    if m_rpm:
        rpm = int(m_rpm.group("rpm"))
        span = (m_rpm.start(), m_rpm.end())
        # Check synchronous or asynchronous speed ranges
        if 2800 <= rpm <= 3050:
            return ExtractedValue(value=2, confidence=0.90, source="rule", evidence=span)
        if 1400 <= rpm <= 1520:
            return ExtractedValue(value=4, confidence=0.90, source="rule", evidence=span)
        if 930 <= rpm <= 1020:
            return ExtractedValue(value=6, confidence=0.90, source="rule", evidence=span)
        if 700 <= rpm <= 760:
            return ExtractedValue(value=8, confidence=0.90, source="rule", evidence=span)

    return ExtractedValue()


def extract_motor_speed(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rated motor speed in RPM."""
    m = RE_RPM.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("rpm")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_motor_frame(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts motor frame size (e.g. 250M, 160L), flagging NEMA frames."""
    m_nema = RE_FRAME_NEMA.search(text)
    if m_nema:
        return ExtractedValue(
            value=m_nema.group("f").upper(),
            confidence=0.90,
            source="rule",
            evidence=(m_nema.start(), m_nema.end()),
            flags=["NEMA_FRAME"],
        )

    m_iec = RE_FRAME_IEC.search(text)
    if m_iec:
        return ExtractedValue(
            value=m_iec.group("f").upper(),
            confidence=0.95,
            source="rule",
            evidence=(m_iec.start(), m_iec.end()),
        )
    return ExtractedValue()


def extract_motor_efficiency(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts motor energy efficiency class (IE1-IE4 or legacy EFF1-EFF3)."""
    m = RE_EFFICIENCY.search(text)
    if m:
        return ExtractedValue(
            value=m.group("eff").upper(),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_motor_voltage(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts motor voltage normalized to V."""
    m = RE_VOLTAGE.search(text)
    if m:
        val = float(m.group("v"))
        unit = m.group("u").upper()
        norm_v = int(val * 1000) if unit == "KV" else int(val)
        return ExtractedValue(
            value=norm_v,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_motor_frequency(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts motor frequency in Hz."""
    m = RE_FREQ.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("hz")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_motor_statutory(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts statutory approval number (e.g. DGMS, PESO, CCOE)."""
    m = RE_APPROVAL.search(text)
    if m:
        auth = m.group("auth").upper()
        no = m.group("no").strip(" /:-_").upper()
        val = f"{auth}_{no}"
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def _parse_raw_ex_string(text: str) -> dict | None:
    """Helper parsing raw Ex hazardous area markings."""
    m = RE_EX_STRING.search(text)
    if not m:
        return None

    ex_type = f"Ex {m.group('type').lower()}"
    raw_grp = (m.group("grp") or "").upper()
    temp_class = m.group("temp").upper() if m.group("temp") else None
    epl = m.group("epl").capitalize() if m.group("epl") else None
    span = (m.start(), m.end())

    ex_groups = "II"
    gas_group = None

    if raw_grp in ("I/IIB", "I/IIC", "I/II"):
        ex_groups = "I, II"
        gas_group = raw_grp.split("/")[-1] if "/" in raw_grp and raw_grp != "I/II" else None
    elif raw_grp == "I":
        ex_groups = "I"
        gas_group = None
        temp_class = None  # Group I has no gas group or temperature class
    elif raw_grp in ("IIA", "IIB", "IIC"):
        ex_groups = "II"
        gas_group = raw_grp
    elif raw_grp == "II":
        ex_groups = "II"
        gas_group = None

    return {
        "ex_type": ex_type,
        "ex_groups": ex_groups,
        "gas_group": gas_group,
        "temp_class": temp_class,
        "epl": epl,
        "span": span,
    }


def extract_motor_ex_type(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts protection type (Ex d, Ex e, Ex nA, etc.)."""
    parsed = _parse_raw_ex_string(text)
    if parsed and parsed["ex_type"]:
        return ExtractedValue(value=parsed["ex_type"], confidence=0.95, source="rule", evidence=parsed["span"])
    return ExtractedValue()


def extract_motor_ex_groups(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts Ex regime groups ('I', 'II', or 'I, II')."""
    parsed = _parse_raw_ex_string(text)
    if parsed and parsed["ex_groups"]:
        return ExtractedValue(value=parsed["ex_groups"], confidence=0.95, source="rule", evidence=parsed["span"])
    return ExtractedValue()


def extract_motor_gas_group(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts gas group (IIA, IIB, IIC) for Group II surface equipment."""
    parsed = _parse_raw_ex_string(text)
    if parsed and parsed["gas_group"]:
        return ExtractedValue(value=parsed["gas_group"], confidence=0.95, source="rule", evidence=parsed["span"])
    return ExtractedValue()


def extract_motor_temp_class(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts temperature class (T1-T6) for Group II surface equipment."""
    parsed = _parse_raw_ex_string(text)
    if parsed and parsed["temp_class"]:
        return ExtractedValue(value=parsed["temp_class"], confidence=0.95, source="rule", evidence=parsed["span"])
    return ExtractedValue()


def extract_motor_epl(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts Equipment Protection Level (Ma/Mb for Group I, Ga/Gb/Gc for Group II)."""
    parsed = _parse_raw_ex_string(text)
    if parsed and parsed["epl"]:
        return ExtractedValue(value=parsed["epl"], confidence=0.95, source="rule", evidence=parsed["span"])
    return ExtractedValue()
