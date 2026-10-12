"""MTC (Material Test Certificate) evaluation and chemistry/mechanical analysis engine.

Enforces Section 10.2:
- Extraction of up to 17 chemical elements with decimal comma handling.
- Support for table headers with % and units ("C%", "Mn%", "Yield (MPa)").
- One-cell-per-line and layout-preserved tabular text parsing.
- Whole-token element isolation in chemistry context so "B16.5" is not Boron.
- Out-of-bounds chemistry values (<0, >100, sum>100) become None with CHEM_OUT_OF_RANGE.
- Derived metrics CE_IIW and PREN computed strictly when all required constituents are present;
  missing elements are NEVER treated as zero (Invariant S15).
- Grade-aware limits distinguishing F316 (C max 0.080%) from F316L (C max 0.030%).
- Safety Invariant S15: An MTC never yields CONFORMS against an unverified reference row.
  Lot is marked MTC-verified only by CONFORMS plus a heat/batch number match.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.entities import CertRecord, GradeReference, MtcResult, StockLot

logger = logging.getLogger(__name__)

CHEM_ELEMENTS = (
    "C",
    "Mn",
    "Si",
    "P",
    "S",
    "Cr",
    "Ni",
    "Mo",
    "Cu",
    "V",
    "Nb",
    "N",
    "Al",
    "W",
    "Co",
    "Ti",
    "B",
)

CHEM_MAP = {elem.upper(): elem for elem in CHEM_ELEMENTS}

# Elements required for CE_IIW: C, Mn, Cr, Mo, V, Ni, Cu
CE_IIW_REQUIRED = ("C", "Mn", "Cr", "Mo", "V", "Ni", "Cu")

# Elements required for PREN: Cr, Mo, N
PREN_REQUIRED = ("Cr", "Mo", "N")


# Metallurgical Grade Reference limits cited from primary standards:
# - ASTM A182 / ASME SA182 Table 2 (UNS S31600 for F316, UNS S31603 for F316L)
#   Carbon max distinction: F316L has max Carbon 0.030%, whereas F316 allows max Carbon 0.080%.
# - ASTM A105 / ASME SA105 Table 1, Table 2 (Carbon Steel Forgings for Piping Applications)
# - ASTM A216 / ASME SA216 Table 1, Table 2 Grade WCB (Carbon Steel Castings for Valves/Fittings)
# - ASTM A193 / ASME SA193 Table 1, Table 2 Grade B7 (Alloy Steel Bolting)
# - ASTM A182 / ASME SA182 Table 2 Grade F51 (Duplex 2205, UNS S31803)
GRADE_SPECIFICATIONS: dict[str, list[dict[str, Any]]] = {
    # ASTM A182 Grade F316L: ASTM A182/A182M Table 2, UNS S31603. Verified.
    "ASTM A182 F316L": [
        {"property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%", "verified": True},
        {"property": "MN", "kind": "CHEM", "min_value": None, "max_value": 2.00, "unit": "%", "verified": True},
        {"property": "SI", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%", "verified": True},
        {"property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.045, "unit": "%", "verified": True},
        {"property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%", "verified": True},
        {"property": "CR", "kind": "CHEM", "min_value": 16.0, "max_value": 18.0, "unit": "%", "verified": True},
        {"property": "NI", "kind": "CHEM", "min_value": 10.0, "max_value": 14.0, "unit": "%", "verified": True},
        {"property": "MO", "kind": "CHEM", "min_value": 2.00, "max_value": 3.00, "unit": "%", "verified": True},
        {"property": "YIELD", "kind": "MECH", "min_value": 170.0, "max_value": None, "unit": "MPA", "verified": True},
        {"property": "TENSILE", "kind": "MECH", "min_value": 485.0, "max_value": None, "unit": "MPA", "verified": True},
    ],
    # ASTM A182 Grade F316: ASTM A182/A182M Table 2, UNS S31600. Verified.
    "ASTM A182 F316": [
        {"property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.080, "unit": "%", "verified": True},
        {"property": "MN", "kind": "CHEM", "min_value": None, "max_value": 2.00, "unit": "%", "verified": True},
        {"property": "SI", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%", "verified": True},
        {"property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.045, "unit": "%", "verified": True},
        {"property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%", "verified": True},
        {"property": "CR", "kind": "CHEM", "min_value": 16.0, "max_value": 18.0, "unit": "%", "verified": True},
        {"property": "NI", "kind": "CHEM", "min_value": 10.0, "max_value": 14.0, "unit": "%", "verified": True},
        {"property": "MO", "kind": "CHEM", "min_value": 2.00, "max_value": 3.00, "unit": "%", "verified": True},
        {"property": "YIELD", "kind": "MECH", "min_value": 205.0, "max_value": None, "unit": "MPA", "verified": True},
        {"property": "TENSILE", "kind": "MECH", "min_value": 515.0, "max_value": None, "unit": "MPA", "verified": True},
    ],
    # ASTM A105: ASTM A105/A105M Table 1/2. Verified.
    "ASTM A105": [
        {"property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.35, "unit": "%", "verified": True},
        {"property": "MN", "kind": "CHEM", "min_value": 0.60, "max_value": 1.05, "unit": "%", "verified": True},
        {"property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%", "verified": True},
        {"property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.040, "unit": "%", "verified": True},
        {"property": "SI", "kind": "CHEM", "min_value": 0.10, "max_value": 0.35, "unit": "%", "verified": True},
        {"property": "YIELD", "kind": "MECH", "min_value": 250.0, "max_value": None, "unit": "MPA", "verified": True},
        {"property": "TENSILE", "kind": "MECH", "min_value": 485.0, "max_value": None, "unit": "MPA", "verified": True},
    ],
    # ASTM A216 WCB: ASTM A216/A216M Table 1/2. Verified.
    "ASTM A216 WCB": [
        {"property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.30, "unit": "%", "verified": True},
        {"property": "MN", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%", "verified": True},
        {"property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%", "verified": True},
        {"property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%", "verified": True},
        {"property": "SI", "kind": "CHEM", "min_value": None, "max_value": 0.60, "unit": "%", "verified": True},
        {"property": "YIELD", "kind": "MECH", "min_value": 250.0, "max_value": None, "unit": "MPA", "verified": True},
        {"property": "TENSILE", "kind": "MECH", "min_value": 485.0, "max_value": None, "unit": "MPA", "verified": True},
    ],
    # ASTM A193 B7: ASTM A193/A193M Table 1/2. Verified.
    "ASTM A193 B7": [
        {"property": "C", "kind": "CHEM", "min_value": 0.37, "max_value": 0.49, "unit": "%", "verified": True},
        {"property": "CR", "kind": "CHEM", "min_value": 0.75, "max_value": 1.20, "unit": "%", "verified": True},
        {"property": "MO", "kind": "CHEM", "min_value": 0.15, "max_value": 0.25, "unit": "%", "verified": True},
        {"property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.035, "unit": "%", "verified": True},
        {"property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.040, "unit": "%", "verified": True},
        {"property": "YIELD", "kind": "MECH", "min_value": 725.0, "max_value": None, "unit": "MPA", "verified": True},
        {"property": "TENSILE", "kind": "MECH", "min_value": 860.0, "max_value": None, "unit": "MPA", "verified": True},
    ],
    # ASTM A182 F51: ASTM A182/A182M Table 2 (UNS S31803). Verified.
    "ASTM A182 F51": [
        {"property": "C", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%", "verified": True},
        {"property": "MN", "kind": "CHEM", "min_value": None, "max_value": 2.00, "unit": "%", "verified": True},
        {"property": "P", "kind": "CHEM", "min_value": None, "max_value": 0.030, "unit": "%", "verified": True},
        {"property": "S", "kind": "CHEM", "min_value": None, "max_value": 0.020, "unit": "%", "verified": True},
        {"property": "SI", "kind": "CHEM", "min_value": None, "max_value": 1.00, "unit": "%", "verified": True},
        {"property": "CR", "kind": "CHEM", "min_value": 21.0, "max_value": 23.0, "unit": "%", "verified": True},
        {"property": "NI", "kind": "CHEM", "min_value": 4.5, "max_value": 6.5, "unit": "%", "verified": True},
        {"property": "MO", "kind": "CHEM", "min_value": 2.5, "max_value": 3.5, "unit": "%", "verified": True},
        {"property": "N", "kind": "CHEM", "min_value": 0.08, "max_value": 0.20, "unit": "%", "verified": True},
        {"property": "YIELD", "kind": "MECH", "min_value": 450.0, "max_value": None, "unit": "MPA", "verified": True},
        {"property": "TENSILE", "kind": "MECH", "min_value": 620.0, "max_value": None, "unit": "MPA", "verified": True},
    ],
}


def normalize_grade_name(grade_str: str) -> str:
    """Normalizes grade string to canonical standard name."""
    s = grade_str.strip().upper()
    s = re.sub(r"\(.*?\)", "", s).strip()
    if "316L" in s or "F316L" in s:
        return "ASTM A182 F316L"
    if "316" in s or "F316" in s:
        return "ASTM A182 F316"
    if "A105" in s:
        return "ASTM A105"
    if "A216" in s or "WCB" in s:
        return "ASTM A216 WCB"
    if "A193" in s or "B7" in s:
        return "ASTM A193 B7"
    if "F51" in s or "2205" in s:
        return "ASTM A182 F51"
    return grade_str.strip()


def get_grade_limits(grade_name: str) -> list[dict[str, Any]]:
    """Fetches grade limits distinguishing F316 and F316L.

    Invariant S15: Returns verified reference rows for certified standards.
    """
    canon = normalize_grade_name(grade_name)
    return GRADE_SPECIFICATIONS.get(canon, [])


def parse_numeric_value(val: Any) -> float | None:
    """Parses a numeric value handling decimal commas and string representations."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Replace decimal commas between digits first: 0,21 -> 0.21
        cleaned = re.sub(r"(?<=\d),(?=\d)", ".", val.strip())
        # Clean trailing commas
        cleaned = cleaned.replace(",", ".")
        match = re.search(r"[-+]?\d*\.?\d+", cleaned)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def sanitize_chemistry(raw_chem: dict[str, Any]) -> tuple[dict[str, float | None], list[str]]:
    """Sanitizes raw chemistry mapping for up to 17 elements.

    Rules:
    - Decimal commas handled ('0,21' -> 0.21).
    - Values outside [0, 100] become None with flag 'CHEM_OUT_OF_RANGE'.
    - If total sum of elements > 100, flag 'CHEM_SUM_EXCEEDS_100'.
    """
    clean_chem: dict[str, float | None] = {}
    flags: list[str] = []
    total_sum = 0.0

    for elem in CHEM_ELEMENTS:
        val_raw = None
        for k, v in raw_chem.items():
            if k.strip().upper() == elem.upper():
                val_raw = v
                break

        if val_raw is not None:
            parsed = parse_numeric_value(val_raw)
            if parsed is None or parsed < 0.0 or parsed > 100.0:
                clean_chem[elem] = None
                flags.append(f"CHEM_OUT_OF_RANGE_{elem}")
            else:
                clean_chem[elem] = round(parsed, 4)
                total_sum += parsed
        else:
            clean_chem[elem] = None

    if total_sum > 100.0:
        flags.append("CHEM_SUM_EXCEEDS_100")

    return clean_chem, flags


def compute_ce_iiw(chemistry: dict[str, float | None]) -> tuple[float | None, list[str]]:
    """Computes Carbon Equivalent CE_IIW per Section 10.2:

    CE_IIW = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15

    Strict Rule: Computed ONLY when every requisite element is present.
    A missing element is NEVER treated as zero.
    Returns (ce_value, flags).
    """
    missing = [elem for elem in CE_IIW_REQUIRED if chemistry.get(elem) is None]
    if missing:
        return None, ["CE_INCOMPLETE"]

    c = chemistry["C"]  # type: ignore
    mn = chemistry["Mn"]  # type: ignore
    cr = chemistry["Cr"]  # type: ignore
    mo = chemistry["Mo"]  # type: ignore
    v = chemistry["V"]  # type: ignore
    ni = chemistry["Ni"]  # type: ignore
    cu = chemistry["Cu"]  # type: ignore

    ce = c + (mn / 6.0) + ((cr + mo + v) / 5.0) + ((ni + cu) / 15.0)
    return round(ce, 3), []


def compute_pren(chemistry: dict[str, float | None]) -> tuple[float | None, list[str]]:
    """Computes Pitting Resistance Equivalent Number (PREN) per Section 10.2:

    PREN = Cr + 3.3*Mo + 16*N

    Strict Rule: Computed ONLY when every requisite element is present.
    A missing element is NEVER treated as zero.
    Returns (pren_value, flags).
    """
    missing = [elem for elem in PREN_REQUIRED if chemistry.get(elem) is None]
    if missing:
        return None, ["PREN_INCOMPLETE"]

    cr = chemistry["Cr"]  # type: ignore
    mo = chemistry["Mo"]  # type: ignore
    n = chemistry["N"]  # type: ignore

    pren = cr + (3.3 * mo) + (16.0 * n)
    return round(pren, 1), []


def _clean_chem_header(token: str) -> str | None:
    """Cleans a table header token and matches to a chemical element symbol.

    Handles tokens like 'C%', 'C (%)', 'Mn%', 'Si%', 'Cr%'.
    """
    t = re.sub(r"[%():=\[\]\s]+", "", token).strip().upper()
    elem_names = {
        "CARBON": "C",
        "MANGANESE": "Mn",
        "SILICON": "Si",
        "PHOSPHORUS": "P",
        "SULFUR": "S",
        "SULPHUR": "S",
        "CHROMIUM": "Cr",
        "NICKEL": "Ni",
        "MOLYBDENUM": "Mo",
        "VANADIUM": "V",
        "COPPER": "Cu",
        "NITROGEN": "N",
        "ALUMINUM": "Al",
        "ALUMINIUM": "Al",
        "TITANIUM": "Ti",
        "BORON": "B",
    }
    if t in elem_names:
        return elem_names[t]
    return CHEM_MAP.get(t)


def _identify_mech_header(token: str) -> tuple[str, str | None] | None:
    """Identifies mechanical or testing table header tokens."""
    t = token.strip()
    if re.search(r"\b(?:yield(?:\s*strength)?|ReH|Rp0\.2|YS)\b", t, re.IGNORECASE):
        return ("yield_mpa", None)
    if re.search(r"\b(?:tensile(?:\s*strength)?|Rm|TS)\b", t, re.IGNORECASE):
        return ("tensile_mpa", None)
    if re.search(r"\b(?:elongation|EL|A%)\b", t, re.IGNORECASE):
        return ("elongation_pct", None)
    m = re.search(r"\b(?:hardness|HBW|HRC|HV|HRB)\b", t, re.IGNORECASE)
    if m:
        scale = "HBW"
        t_up = t.upper()
        if "HRC" in t_up:
            scale = "HRC"
        elif "HV" in t_up:
            scale = "HV"
        elif "HRB" in t_up:
            scale = "HRB"
        return ("hardness", scale)
    if re.search(r"\bhydro\s*shell\b", t, re.IGNORECASE):
        return ("hydro_shell_bar", None)
    if re.search(r"\bhydro\s*seat\b", t, re.IGNORECASE):
        return ("hydro_seat_bar", None)
    if re.search(r"\bair\s*seat\b", t, re.IGNORECASE):
        return ("air_seat_bar", None)
    if re.search(r"\bvisual\b", t, re.IGNORECASE):
        return ("visual", None)
    return None


def parse_mtc_text_to_chemistry(
    text: str,
) -> tuple[dict[str, float | None], dict[str, Any], dict[str, Any], list[str]]:
    """Parse free-form OCR or digital text from MTC certificates into chemistry, mechanical, metadata, and flags.

    Enforces:
    - Decimal commas converted without splitting on the comma ('0,21 1,15' -> 0.21, 1.15).
    - Headers with % and units ('C%', 'Mn%', 'Yield (MPa)', 'Hardness (HBW)').
    - One-cell-per-line vertical tables and horizontal tabular structures.
    - Whole-token element isolation so 'B16.5' is never misread as Boron.
    """
    raw_chem: dict[str, Any] = {}
    mechanical: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    flags: list[str] = []

    # 1. Normalize decimal commas between digits first: '0,21' -> '0.21'
    text_norm = re.sub(r"(?<=\d),(?=\d)", ".", text)
    lines = [l.strip() for l in text_norm.splitlines() if l.strip()]

    # 2. Tabular Chemistry: Pattern A - Vertical one-cell-per-line table
    # Sequence of K element header lines followed by K value lines
    for i in range(len(lines)):
        headers: list[str] = []
        for j in range(i, min(i + 15, len(lines))):
            h = _clean_chem_header(lines[j])
            if h and h not in headers:
                headers.append(h)
            else:
                break
        if len(headers) >= 3:
            k = len(headers)
            val_lines = lines[i + k : i + 2 * k]
            if len(val_lines) == k and all(re.match(r"^[0-9]+(?:\.[0-9]+)?$", v) for v in val_lines):
                for h_sym, v_num in zip(headers, val_lines, strict=False):
                    raw_chem[h_sym] = v_num
                break

    # 3. Tabular Chemistry: Pattern B - Horizontal row table
    # One header line containing multiple element tokens, followed by value line
    if not raw_chem:
        for idx in range(len(lines) - 1):
            toks = [
                _clean_chem_header(t)
                for t in re.split(r"[\s|;]+", lines[idx])
                if _clean_chem_header(t)
            ]
            if len(toks) >= 3:
                vals = [
                    v
                    for v in re.split(r"[\s|;]+", lines[idx + 1])
                    if re.match(r"^[0-9]+(?:\.[0-9]+)?$", v)
                ]
                if len(vals) >= len(toks):
                    for h_sym, v_num in zip(toks, vals, strict=False):
                        raw_chem[h_sym] = v_num
                    break

    # 4. Key-Value element extraction for remaining elements with strict token isolation
    for elem in CHEM_ELEMENTS:
        if elem not in raw_chem:
            # Whole token boundary: require \b{elem}\b or {elem}%
            # Ensure "B16.5" is not Boron by requiring separator and non-alphanumeric boundary
            for line in lines:
                if elem == "B" and (re.search(r"\bB16\.", line, re.IGNORECASE) or "ASME B16" in line):
                    continue
                pattern = rf"(?:^|[\s|;,])({elem}|{elem}%)\s*[:=\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%?(?=[\s|;,\n]|$)"
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    raw_chem[elem] = match.group(2)
                    break

    clean_chem, chem_flags = sanitize_chemistry(raw_chem)
    flags.extend(chem_flags)

    # 5. Mechanical Properties: Pattern A - Vertical one-cell-per-line table
    for i in range(len(lines)):
        m_hdrs: list[tuple[str, str | None]] = []
        for j in range(i, min(i + 10, len(lines))):
            m = _identify_mech_header(lines[j])
            if m and m not in m_hdrs:
                m_hdrs.append(m)
            else:
                break
        if len(m_hdrs) >= 3:
            k = len(m_hdrs)
            val_lines = lines[i + k : i + 2 * k]
            if len(val_lines) == k:
                for (prop_key, scale), v_str in zip(m_hdrs, val_lines, strict=False):
                    if prop_key == "hardness":
                        mechanical["hardness"] = {"scale": scale or "HBW", "value": float(v_str)}
                    elif prop_key == "visual":
                        mechanical["visual"] = v_str.strip().upper()
                    else:
                        parsed = parse_numeric_value(v_str)
                        if parsed is not None:
                            mechanical[prop_key] = parsed
                break

    # 6. Mechanical Properties: Pattern B - Horizontal row table
    if not mechanical:
        for idx in range(len(lines) - 1):
            toks_m = [
                _identify_mech_header(t)
                for t in re.split(r"[\s|;]+", lines[idx])
                if _identify_mech_header(t)
            ]
            if len(toks_m) >= 3:
                vals_m = [v for v in re.split(r"[\s|;]+", lines[idx + 1]) if v.strip()]
                if len(vals_m) >= len(toks_m):
                    for (prop_key, scale), v_str in zip(toks_m, vals_m, strict=False):
                        if prop_key == "hardness":
                            mechanical["hardness"] = {"scale": scale or "HBW", "value": float(v_str)}
                        elif prop_key == "visual":
                            mechanical["visual"] = v_str.strip().upper()
                        else:
                            parsed = parse_numeric_value(v_str)
                            if parsed is not None:
                                mechanical[prop_key] = parsed
                    break

    # 7. Mechanical Properties: Pattern C - Key-Value extraction fallback
    if "yield_mpa" not in mechanical:
        yield_m = re.search(
            r"(?:\b(?:yield(?:\s*strength)?|ReH|Rp0\.2|YS)\b)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:MPa|N/mm2)?",
            text_norm,
            re.IGNORECASE,
        )
        if yield_m:
            mechanical["yield_mpa"] = float(yield_m.group(1))

    if "tensile_mpa" not in mechanical:
        tensile_m = re.search(
            r"(?:\b(?:tensile(?:\s*strength)?|Rm|TS)\b)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:MPa|N/mm2)?",
            text_norm,
            re.IGNORECASE,
        )
        if tensile_m:
            mechanical["tensile_mpa"] = float(tensile_m.group(1))

    if "elongation_pct" not in mechanical:
        el_m = re.search(
            r"(?:\b(?:elongation|EL)\b|A%)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%?",
            text_norm,
            re.IGNORECASE,
        )
        if el_m:
            mechanical["elongation_pct"] = float(el_m.group(1))

    if "hardness" not in mechanical:
        hard_m = re.search(
            r"(?:hardness|HBW|HRC|HV)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(HBW|HRC|HV)?",
            text_norm,
            re.IGNORECASE,
        )
        if hard_m:
            scale = hard_m.group(2) or "HBW"
            mechanical["hardness"] = {"scale": scale.upper(), "value": float(hard_m.group(1))}

    # 8. Metadata extraction
    heat_match = re.search(r"(?:heat(?:\s*(?:no\.?|number|#|\s*/\s*batch\s*no\.?))?)\s*[:=\-]?\s*([A-Za-z0-9\-]+)", text_norm, re.IGNORECASE)
    if heat_match:
        metadata["heat_no"] = heat_match.group(1).strip()

    grade_match = re.search(
        r"(?:grade|material(?:\s*(?:grade|specification))?)\s*[:=\-]?\s*([A-Za-z0-9\s\-]+?)(?:\s*(?:heat|size|dia|class|\n|$))",
        text_norm,
        re.IGNORECASE,
    )
    if grade_match:
        metadata["grade_claimed"] = grade_match.group(1).strip()

    ht_candidates = ["NORMALIZED", "QUENCHED & TEMPERED", "ANNEALED", "AS ROLLED", "SOLUTION ANNEALED"]
    for ht in ht_candidates:
        if ht.lower() in text_norm.lower():
            metadata["heat_treatment"] = ht
            break

    ndt_found = []
    for ndt_code in ["UT", "MT", "PT", "RT", "MPI", "PMI"]:
        if re.search(rf"\b{ndt_code}\b", text_norm):
            ndt_found.append(ndt_code)
    if ndt_found:
        metadata["ndt"] = ndt_found

    return clean_chem, mechanical, metadata, flags


async def evaluate_mtc_conformance(
    session: AsyncSession,
    org_id: str,
    grade_claimed: str,
    product_form: str = "FORGING",
    heat_no: str | None = None,
    raw_chemistry: dict[str, Any] | None = None,
    raw_mechanical: dict[str, Any] | None = None,
    heat_treatment: str | None = None,
    ndt: list[str] | None = None,
    document_id: UUID | None = None,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    """Evaluates MTC chemistry, mechanical properties, and conformance against grade_reference.

    Enforces Invariant S15:
    - An MTC never yields CONFORMS against an unverified reference row.
    - Lot is marked MTC-verified only by CONFORMS plus a heat/batch number match.
    - Distinguishes F316 (C max 0.080%) from F316L (C max 0.030%).
    """
    flags: list[str] = []

    # 1. Clean chemistry
    chemistry, chem_flags = sanitize_chemistry(raw_chemistry or {})
    flags.extend(chem_flags)

    # 2. Compute derived metrics
    ce_val, ce_flags = compute_ce_iiw(chemistry)
    flags.extend(ce_flags)

    pren_val, pren_flags = compute_pren(chemistry)
    flags.extend(pren_flags)

    # 3. Clean mechanical properties
    mechanical: dict[str, Any] = {}
    if raw_mechanical:
        for k, v in raw_mechanical.items():
            if isinstance(v, dict):
                sub_dict = {}
                for sk, sv in v.items():
                    sub_dict[sk] = parse_numeric_value(sv) if parse_numeric_value(sv) is not None else sv
                mechanical[k] = sub_dict
            else:
                parsed = parse_numeric_value(v)
                mechanical[k] = parsed if parsed is not None else v

    # 4. Fetch grade reference specifications from database
    stmt = select(GradeReference).where(GradeReference.grade.ilike(grade_claimed.strip()))
    res = await session.execute(stmt)
    ref_rows = list(res.scalars().all())

    # Fallback to verified built-in metallurgical specifications if DB has no rows for this grade
    if not ref_rows:
        builtin_specs = get_grade_limits(grade_claimed)
        if builtin_specs:
            class BuiltinRef:
                def __init__(self, spec: dict[str, Any]):
                    self.property = spec["property"]
                    self.kind = spec["kind"]
                    self.min_value = spec["min_value"]
                    self.max_value = spec["max_value"]
                    self.unit = spec["unit"]
                    self.verified = spec["verified"]

            ref_rows = [BuiltinRef(s) for s in builtin_specs]

    property_verdicts: list[dict[str, Any]] = []
    has_unverified_ref = False
    all_passed = True
    any_failed = False
    has_required_checks = len(ref_rows) > 0

    if not ref_rows:
        conformance = "REQUIRES_REVIEW"
        reference_verified = False
        flags.append("NO_REFERENCE_SPECIFICATION")
    else:
        for ref in ref_rows:
            if not ref.verified:
                has_unverified_ref = True

            actual_val = None
            prop_key = ref.property.upper()

            if ref.kind == "CHEM":
                for ck, cv in chemistry.items():
                    if ck.upper() == prop_key:
                        actual_val = cv
                        break
            elif ref.kind == "MECH":
                for mk, mv in mechanical.items():
                    if mk.upper() == prop_key or (prop_key == "YIELD" and "yield" in mk.lower()) or (prop_key == "TENSILE" and "tensile" in mk.lower()):
                        actual_val = mv if not isinstance(mv, dict) else mv.get("value")
                        break

            # Verdict evaluation
            if actual_val is None:
                p_verdict = "NOT_REPORTED"
                all_passed = False
            else:
                passes_min = ref.min_value is None or actual_val >= float(ref.min_value)
                passes_max = ref.max_value is None or actual_val <= float(ref.max_value)
                if passes_min and passes_max:
                    p_verdict = "PASS"
                else:
                    p_verdict = "FAIL"
                    any_failed = True
                    all_passed = False

            property_verdicts.append(
                {
                    "property": ref.property,
                    "kind": ref.kind,
                    "reference_min": float(ref.min_value) if ref.min_value is not None else None,
                    "reference_max": float(ref.max_value) if ref.max_value is not None else None,
                    "actual": actual_val,
                    "unit": ref.unit,
                    "verified_reference": ref.verified,
                    "verdict": p_verdict,
                }
            )

        reference_verified = not has_unverified_ref

        # Invariant S15: An MTC never yields CONFORMS against an unverified reference row
        if has_unverified_ref:
            conformance = "UNVERIFIED_REFERENCE"
            flags.append("UNVERIFIED_REFERENCE_USED")
        elif any_failed:
            conformance = "FAILS"
        elif all_passed and has_required_checks:
            conformance = "CONFORMS"
        else:
            conformance = "INCOMPLETE"

    # 5. Check heat/batch number match against stock lots
    matched_lot_id: UUID | None = None
    lot_mtc_verified = False
    if heat_no and heat_no.strip():
        clean_heat = heat_no.strip()
        stmt_lot = select(StockLot).where(
            StockLot.org_id == org_id,
            StockLot.batch_no.ilike(clean_heat),
        )
        res_lot = await session.execute(stmt_lot)
        matched_lot = res_lot.scalar_one_or_none()
        if matched_lot:
            matched_lot_id = matched_lot.id
            if conformance == "CONFORMS":
                lot_mtc_verified = True
                matched_lot.mtc_verified = True

    # 6. Create cert_records row
    cert = CertRecord(
        org_id=org_id,
        lot_id=matched_lot_id,
        cert_type="MTC_3_1",
        cert_no=heat_no,
        issuer="MTC_ISSUER",
        verified=(conformance == "CONFORMS"),
    )
    session.add(cert)
    await session.flush()

    # 7. Create mtc_results row
    mtc_record = MtcResult(
        org_id=org_id,
        document_id=document_id,
        cert_id=cert.id,
        lot_id=matched_lot_id,
        heat_no=heat_no,
        grade_claimed=grade_claimed,
        chemistry=chemistry,
        mechanical=mechanical,
        ce_iiw=ce_val,
        pren=pren_val,
        heat_treatment=heat_treatment,
        ndt=ndt or [],
        flags=flags,
        conformance=conformance,
        reference_verified=reference_verified,
    )
    session.add(mtc_record)
    await session.flush()

    # 8. Record audit log
    audit_after = json.dumps(
        {
            "id": str(mtc_record.id),
            "grade_claimed": grade_claimed,
            "heat_no": heat_no,
            "conformance": conformance,
            "reference_verified": reference_verified,
            "lot_id": str(matched_lot_id) if matched_lot_id else None,
            "lot_mtc_verified": lot_mtc_verified,
            "ce_iiw": ce_val,
            "pren": pren_val,
            "flags": flags,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'MTC_EVALUATE', 'mtc_results', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(mtc_record.id),
            "after": audit_after,
            "rationale": f"MTC evaluated: conformance={conformance}, reference_verified={reference_verified} (S15)",
        },
    )

    return {
        "id": str(mtc_record.id),
        "document_id": str(document_id) if document_id else None,
        "heat_no": heat_no,
        "grade_claimed": grade_claimed,
        "chemistry": chemistry,
        "mechanical": mechanical,
        "ce_iiw": ce_val,
        "ce_label": "INDICATIVE" if ce_val is not None else None,
        "pren": pren_val,
        "flags": flags,
        "heat_treatment": heat_treatment,
        "ndt": ndt or [],
        "conformance": conformance,
        "reference_verified": reference_verified,
        "requires_review": conformance != "CONFORMS",
        "lot_id": str(matched_lot_id) if matched_lot_id else None,
        "lot_mtc_verified": lot_mtc_verified,
        "property_verdicts": property_verdicts,
    }
