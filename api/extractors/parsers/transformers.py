"""Power and Distribution Transformer attribute extractors.

Implements physical parsing for transformer ratings (kVA/MVA), primary/secondary voltages,
vector groups (Dyn11 canonicalization), cooling stages, and tap changers.
Conforms to specsheet.md Section 18.4.1.
"""

import re

from api.extractors.base import ExtractedValue

# Regex patterns
RE_RATING_DUAL = re.compile(
    r"(?<![A-Z0-9])(?P<r1>\d+(?:\.\d+)?)\s*/\s*(?P<r2>\d+(?:\.\d+)?)\s*(?P<u>MVA|KVA)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_RATING_SINGLE = re.compile(
    r"(?<![A-Z0-9])(?P<r>\d+(?:\.\d+)?)\s*(?P<u>MVA|KVA)(?![A-Z0-9])",
    re.IGNORECASE,
)
# Matches 33/11KV, 132/33 KV, 11/0.433KV, 11KV/415V, 11/.433 KV, 11/0.415
RE_VOLTAGE_PAIR = re.compile(
    r"(?<![A-Z0-9])(?P<v1>\d+(?:\.\d+)?)\s*(?P<u1>KV|V)?\s*/\s*(?P<v2>\d*(?:\.\d+)?)\s*(?P<u2>KV|V)(?![A-Z0-9])|"
    r"(?<![A-Z0-9])(?P<v1_b>\d+(?:\.\d+)?)\s*(?P<u1_b>KV|V)\s*/\s*(?P<v2_b>\d*(?:\.\d+)?)(?![A-Z0-9])",
    re.IGNORECASE,
)
# Vector group: Dyn11, DYN-11, YNyn0, YNd1
RE_VECTOR_GROUP = re.compile(
    r"(?<![A-Z0-9])(?P<hv>YN|Y|D|ZN|Z)(?:-)?(?P<lv>YN|Y|D|ZN|Z)(?:-)?(?P<clock>\d{1,2})(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_COOLING = re.compile(
    r"(?<![A-Z0-9])(?P<c>ONAN/ONAF|ONAF/ONAN|ONAN|ONAF|OFAF|ODAF|AN/AF|AN|AF)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_TAP_CHANGER = re.compile(
    r"(?<![A-Z0-9])(?P<t>OLTC|ON\s*LOAD|OCTC|OFF\s*CIRCUIT|NLTC|NO\s*LOAD)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_IMPEDANCE = re.compile(
    r"(?<![A-Z0-9])(?:%Z|IMPEDANCE|Z)?\s*(?P<z>\d+(?:\.\d+)?)\s*%(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_BIL = re.compile(
    r"(?<![A-Z0-9])(?P<bil>\d+(?:\.\d+)?)\s*(?:KV)?\s*BIL(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_PHASES = re.compile(
    r"(?<![A-Z0-9])(?P<p>1|3)\s*(?:PH|PHASE|PHASES)(?![A-Z0-9])",
    re.IGNORECASE,
)
RE_FREQ = re.compile(
    r"(?<![A-Z0-9])(?P<hz>50|60)\s*HZ(?![A-Z0-9])",
    re.IGNORECASE,
)


def _to_canonical_kva(val_str: str, unit_str: str) -> float:
    num = float(val_str)
    return num * 1000.0 if unit_str.upper() == "MVA" else num


def extract_transformer_rating(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts base (ONAN) transformer rating in canonical kVA."""
    m_dual = RE_RATING_DUAL.search(text)
    if m_dual:
        base_kva = _to_canonical_kva(m_dual.group("r1"), m_dual.group("u"))
        return ExtractedValue(
            value=base_kva,
            confidence=0.95,
            source="rule",
            evidence=(m_dual.start(), m_dual.end()),
        )

    m_single = RE_RATING_SINGLE.search(text)
    if m_single:
        base_kva = _to_canonical_kva(m_single.group("r"), m_single.group("u"))
        span = (m_single.start(), m_single.end())
        flags = []
        # Flag if dual cooling is specified with only one rating number
        if "ONAN/ONAF" in text.upper():
            flags.append("RATING_STAGE_UNKNOWN")
        return ExtractedValue(value=base_kva, confidence=0.95, source="rule", evidence=span, flags=flags)

    return ExtractedValue()


def extract_transformer_rating_max(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts extended (e.g. ONAF) rating in kVA for dual-rated transformers."""
    m_dual = RE_RATING_DUAL.search(text)
    if m_dual:
        max_kva = _to_canonical_kva(m_dual.group("r2"), m_dual.group("u"))
        return ExtractedValue(
            value=max_kva,
            confidence=0.95,
            source="rule",
            evidence=(m_dual.start(), m_dual.end()),
        )
    return ExtractedValue()


def _parse_voltages(text: str) -> tuple[float, float, tuple[int, int], list[str]] | None:
    """Helper to parse HV and LV pair normalized to kV."""
    m = RE_VOLTAGE_PAIR.search(text)
    if not m:
        return None

    v1_raw = m.group("v1") or m.group("v1_b")
    v2_raw = m.group("v2") or m.group("v2_b")
    if not v1_raw or not v2_raw:
        return None

    try:
        v1 = float(v1_raw)
        v2 = float(v2_raw)
    except ValueError:
        return None

    u1 = ((m.group("u1") or m.group("u1_b")) or "").upper()
    u2 = ((m.group("u2") or m.group("u2_b")) or "").upper()

    # Normalize to kV
    if u1 == "V":
        v1 = v1 / 1000.0
    elif u1 == "KV":
        pass
    elif u2 == "V" and v1 > 100:
        v1 = v1 / 1000.0

    if u2 == "V":
        v2 = v2 / 1000.0
    elif u2 == "KV":
        pass
    elif u1 == "KV" and v2 > 100:
        v2 = v2 / 1000.0

    flags = []
    # If HV side is smaller than LV side, order was swapped in raw text
    if v1 < v2:
        flags.append("VOLTAGE_ORDER_SWAPPED")

    return (v1, v2, (m.start(), m.end()), flags)


def extract_transformer_hv(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts primary (HV) voltage in kV."""
    parsed = _parse_voltages(text)
    if parsed:
        v1, _, span, flags = parsed
        return ExtractedValue(value=round(v1, 3), confidence=0.95, source="rule", evidence=span, flags=flags)
    return ExtractedValue()


def extract_transformer_lv(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts secondary (LV) voltage in kV."""
    parsed = _parse_voltages(text)
    if parsed:
        _, v2, span, flags = parsed
        return ExtractedValue(value=round(v2, 3), confidence=0.95, source="rule", evidence=span, flags=flags)
    return ExtractedValue()


def extract_transformer_vector_group(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts vector group and canonicalizes to Dyn11 form."""
    # Negative lookahead for DYNAMIC
    if "DYNAMIC" in text.upper():
        cleaned = re.sub(r"\bDYNAMIC\b", "", text, flags=re.IGNORECASE)
    else:
        cleaned = text

    m = RE_VECTOR_GROUP.search(cleaned)
    if not m:
        return ExtractedValue()

    hv = m.group("hv").upper()
    lv = m.group("lv").lower()
    clock = m.group("clock")
    span = (m.start(), m.end())

    canonical = f"{hv}{lv}{clock}"
    flags = []
    if clock not in ("0", "1", "5", "6", "7", "11"):
        flags.append("VECTOR_GROUP_UNUSUAL")

    return ExtractedValue(value=canonical, confidence=0.95, source="rule", evidence=span, flags=flags)


def extract_transformer_cooling(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts cooling class (ONAN, ONAF, ONAN/ONAF, etc.)."""
    m = RE_COOLING.search(text)
    if m:
        return ExtractedValue(
            value=m.group("c").upper(),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_transformer_tap_changer(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts tap changer mechanism (ON_LOAD or OFF_CIRCUIT)."""
    m = RE_TAP_CHANGER.search(text)
    if not m:
        return ExtractedValue()

    token = m.group("t").upper().replace(" ", "")
    span = (m.start(), m.end())
    if token in ("OLTC", "ONLOAD"):
        return ExtractedValue(value="ON_LOAD", confidence=0.95, source="rule", evidence=span)
    return ExtractedValue(value="OFF_CIRCUIT", confidence=0.95, source="rule", evidence=span)


def extract_transformer_impedance(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts percent impedance (%Z)."""
    m = RE_IMPEDANCE.search(text)
    if m:
        return ExtractedValue(
            value=float(m.group("z")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_transformer_phases(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts phase count (1 or 3)."""
    m = RE_PHASES.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("p")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_transformer_frequency(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts frequency in Hz."""
    m = RE_FREQ.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("hz")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    # Standard Indian grid default 50 Hz per specsheet.md Section 18.4.1
    return ExtractedValue(
        value=50,
        confidence=0.85,
        source="rule",
        flags=["DEFAULT_GRID_FREQUENCY"],
    )
