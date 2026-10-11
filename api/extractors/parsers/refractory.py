"""Refractory materials attribute extractors for Steel domain.

Implements physical parsing for refractory brick dimensions (including taper),
key chemistry percentages (Al2O3, MgO, C), shelf life, and service limits.
Conforms to specsheet.md Section 18.5.1.
"""

import re

from api.extractors.base import ExtractedValue

RE_DIMENSIONS = re.compile(
    r"(?<![A-Z0-9])(?P<l>\d{2,4})\s*[X*]\s*(?P<w>\d{2,4})\s*[X*]\s*(?P<t>\d{2,4}(?:/\d{2,4})?)(?:\s*MM)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_AL2O3 = re.compile(
    r"(?<![A-Z0-9])(?:AL2O3|ALUMINA)\s*(?:[-:]|\bIS\b)?\s*(?P<pct>\d{1,2}(?:\.\d+)?)\s*%(?:\s*MIN)?(?![A-Z0-9])|(?<![A-Z0-9])(?P<pct2>\d{1,2}(?:\.\d+)?)\s*%\s*(?:AL2O3|ALUMINA)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_MGO_C = re.compile(
    r"(?<![A-Z0-9])MGO(?:-C|\s*CARBON)?\s*(?P<mgo>\d{1,2}(?:\.\d+)?)?(?:.*?C\s*(?P<c>\d{1,2}(?:\.\d+)?)\s*%)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_MGO_DIRECT = re.compile(
    r"(?<![A-Z0-9])MGO\s*(?:[-:]|\bIS\b)?\s*(?P<mgo>\d{1,2}(?:\.\d+)?)\s*%(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_C_DIRECT = re.compile(
    r"(?<![A-Z0-9])C\s*(?:[-:]|\bIS\b)?\s*(?P<c>\d{1,2}(?:\.\d+)?)\s*%(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_SHELF_LIFE = re.compile(
    r"(?<![A-Z0-9])(?P<num>\d+)\s*(?P<u>DAYS?|MONTHS?|YEARS?)\s*(?:SHELF\s*LIFE)?(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_BULK_DENSITY = re.compile(
    r"(?<![A-Z0-9])(?:BD|BULK\s*DENSITY)?\s*(?P<bd>\d+(?:\.\d+)?)\s*(?:G/CC|GM/CC|G/CM3)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_SERVICE_TEMP = re.compile(
    r"(?<![A-Z0-9])(?P<deg>\d{3,4})\s*(?:DEG|°)?\s*C(?![A-Z0-9])",
    re.IGNORECASE,
)


def extract_refractory_dimensions(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts brick dimensions (e.g. 230X114X75 or 230X114X75/65)."""
    m = RE_DIMENSIONS.search(text)
    if m:
        val = f"{m.group('l')}X{m.group('w')}X{m.group('t')}".upper()
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_refractory_chemistry(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts key chemistry percentage representation."""
    # Check Al2O3
    m_al = RE_AL2O3.search(text)
    if m_al:
        pct = m_al.group("pct") or m_al.group("pct2")
        val = f"AL2O3_MIN_{int(float(pct))}"
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m_al.start(), m_al.end()),
        )

    # Check MgO-C
    m_mgo = RE_MGO_DIRECT.search(text)
    m_c = RE_C_DIRECT.search(text)
    if m_mgo and m_c:
        mgo_val = int(float(m_mgo.group("mgo")))
        c_val = int(float(m_c.group("c")))
        val = f"MGO_MIN_{mgo_val}_C_{c_val}"
        start = min(m_mgo.start(), m_c.start())
        end = max(m_mgo.end(), m_c.end())
        return ExtractedValue(value=val, confidence=0.95, source="rule", evidence=(start, end))

    if m_mgo:
        mgo_val = int(float(m_mgo.group("mgo")))
        val = f"MGO_MIN_{mgo_val}"
        return ExtractedValue(
            value=val,
            confidence=0.95,
            source="rule",
            evidence=(m_mgo.start(), m_mgo.end()),
        )

    return ExtractedValue()


def extract_refractory_shelf_life(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts shelf life converted to days."""
    m = RE_SHELF_LIFE.search(text)
    if not m:
        return ExtractedValue()

    num = int(m.group("num"))
    u = m.group("u").upper()
    span = (m.start(), m.end())

    if "MONTH" in u:
        days = num * 30
    elif "YEAR" in u:
        days = num * 365
    else:
        days = num

    return ExtractedValue(value=days, confidence=0.95, source="rule", evidence=span)


def extract_refractory_bulk_density(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts bulk density in g/cc."""
    m = RE_BULK_DENSITY.search(text)
    if m:
        return ExtractedValue(
            value=float(m.group("bd")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_refractory_service_temp(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts maximum service temperature in degrees Celsius."""
    m = RE_SERVICE_TEMP.search(text)
    if m:
        return ExtractedValue(
            value=int(m.group("deg")),
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_refractory_material_class(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts refractory material class, prioritizing composite classes over base oxides."""
    t = text.upper()
    # Composite classes first
    if re.search(r"\b(?:MAG(?:NESIA)?[\s\-]CARBON|MGO[\s\-]C|MG[\s\-]C)\b", t):
        return ExtractedValue(value="MAG_CARBON", confidence=0.98, source="rule")
    if re.search(r"\b(?:ALUMINA[\s\-]CARBON|AL2O3[\s\-]C|ALUMINA[\s\-]GRAPHITE)\b", t):
        return ExtractedValue(value="ALUMINA_CARBON", confidence=0.98, source="rule")
    if re.search(r"\b(?:MAG(?:NESIA)?[\s\-]CHROME|CHROME[\s\-]MAGNESITE)\b", t) or (
        re.search(r"\bMGO\b", t) and re.search(r"\bCR2O3\b", t)
    ):
        return ExtractedValue(value="MAG_CHROME", confidence=0.98, source="rule")
    if re.search(r"\b(?:HIGH[\s\-]ALUMINA|HI[\s\-]ALUMINA|BAUXITE|CORUNDUM)\b", t):
        return ExtractedValue(value="HIGH_ALUMINA", confidence=0.98, source="rule")
    if re.search(r"\b(?:FIRECLAY|FIRE[\s\-]CLAY|MEDIUM[\s\-]DUTY)\b", t):
        return ExtractedValue(value="FIRECLAY", confidence=0.98, source="rule")
    if re.search(r"\bSILICA\b", t):
        return ExtractedValue(value="SILICA", confidence=0.98, source="rule")
    if re.search(r"\b(?:MAGNESIA|MAGNESITE|DBM|DEAD[\s\-]BURNT)\b", t):
        return ExtractedValue(value="MAGNESIA", confidence=0.98, source="rule")
    # Base oxides infer material class if no explicit compound or mineral name
    if re.search(r"\bAL2O3\b|\bALUMINA\b", t):
        return ExtractedValue(value="HIGH_ALUMINA", confidence=0.95, source="rule")
    if re.search(r"\bMGO\b|\bBASIC\b", t):
        return ExtractedValue(value="MAGNESIA", confidence=0.95, source="rule")
    return ExtractedValue()
