"""Off-The-Road (OTR) Tyres attribute extractors for Mining domain.

Implements physical parsing for tyre size designation (width, radial/bias construction,
rim diameter in inches), TRA tread codes (E3, E4, L5), star ratings, and ply ratings.
Conforms to specsheet.md Section 18.6.1.
"""

import re

from api.extractors.base import ExtractedValue

# Pattern matching 27.00R49, 27.00-49, 33.00 R 51, 59/80R63, 18.00-25, 23.5R25
RE_OTR_SIZE = re.compile(
    r"(?<![A-Z0-9])(?P<w>\d{2}(?:\.\d{1,2})?(?:/\d{2})?)\s*(?P<c>R|-)\s*(?P<rim>\d{2})(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_TREAD_CODE = re.compile(
    r"(?<![A-Z0-9])(?P<t>[EGL]-?[2-5]|L-?5S)(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_STAR_RATING = re.compile(
    r"(?<![A-Z0-9])(?P<s>\*{1,3}|[123]\s*STAR|\u2605{1,3})(?![A-Z0-9])",
    re.IGNORECASE,
)

RE_PLY_RATING = re.compile(
    r"(?<![A-Z0-9])(?P<pr>\d{2})\s*PR(?![A-Z0-9])",
    re.IGNORECASE,
)


def _parse_otr_size(text: str) -> dict | None:
    m = RE_OTR_SIZE.search(text)
    if not m:
        return None
    w = m.group("w")
    c_raw = m.group("c")
    rim = int(m.group("rim"))
    construction = "RADIAL" if c_raw.upper() == "R" else "BIAS"
    return {
        "section_width": w,
        "construction": construction,
        "rim_diameter_in": rim,
        "span": (m.start(), m.end()),
    }


def extract_otr_section_width(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts tyre nominal section width (e.g. 27.00, 33.00, 59/80)."""
    parsed = _parse_otr_size(text)
    if parsed:
        return ExtractedValue(
            value=parsed["section_width"],
            confidence=0.95,
            source="rule",
            evidence=parsed["span"],
        )
    return ExtractedValue()


def extract_otr_construction(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts tyre casing construction (RADIAL from 'R' or BIAS from '-')."""
    parsed = _parse_otr_size(text)
    if parsed:
        return ExtractedValue(
            value=parsed["construction"],
            confidence=0.95,
            source="rule",
            evidence=parsed["span"],
        )
    return ExtractedValue()


def extract_otr_rim_diameter(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts rim diameter in inches."""
    parsed = _parse_otr_size(text)
    if parsed:
        return ExtractedValue(
            value=parsed["rim_diameter_in"],
            confidence=0.95,
            source="rule",
            evidence=parsed["span"],
        )
    return ExtractedValue()


def extract_otr_tread_code(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts TRA tread classification code (e.g. E3, E4, L4, L5)."""
    m = RE_TREAD_CODE.search(text)
    if m:
        canonical = m.group("t").upper().replace("-", "")
        return ExtractedValue(
            value=canonical,
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()


def extract_otr_star_rating(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts carcass strength star rating (1_STAR, 2_STAR, 3_STAR)."""
    m = RE_STAR_RATING.search(text)
    if not m:
        return ExtractedValue()

    raw = m.group("s").upper()
    span = (m.start(), m.end())
    if "***" in raw or "\u2605\u2605\u2605" in raw or "3" in raw:
        return ExtractedValue(value="3_STAR", confidence=0.95, source="rule", evidence=span)
    if "**" in raw or "\u2605\u2605" in raw or "2" in raw:
        return ExtractedValue(value="2_STAR", confidence=0.95, source="rule", evidence=span)
    return ExtractedValue(value="1_STAR", confidence=0.95, source="rule", evidence=span)


def extract_otr_ply_rating(text: str, category: str | None = None) -> ExtractedValue:
    """Extracts ply rating (e.g. 36PR, 48PR)."""
    m = RE_PLY_RATING.search(text)
    if m:
        return ExtractedValue(
            value=f"{m.group('pr')}PR",
            confidence=0.95,
            source="rule",
            evidence=(m.start(), m.end()),
        )
    return ExtractedValue()
