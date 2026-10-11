"""Pressure class parser (worked example of a Python extractor). Standard library only.

Rules: ASME classes and PN are different systems; a bare '300 PSI' is not a class;
unknown numbers give None + NON_STANDARD_RATING; two systems or two numbers give
None + EXTRACTION_CONFLICT. Evidence spans index into the raw text.
"""
import re
from extract_base import ExtractedValue, none_with

CLASSES_FLANGED = {150, 300, 600, 900, 1500, 2500}
CLASSES_FORGED = {800}
CLASSES_FITTING = {2000, 3000, 6000, 9000}
VALID_CLASSES = CLASSES_FLANGED | CLASSES_FORGED | CLASSES_FITTING
PN_VALID = {2.5, 6, 10, 16, 25, 40, 63, 100, 160, 250, 320, 400}
PRESSURE_CATEGORIES = {"VALVES", "PIPES", "FLANGES", "FITTINGS"}

RE_CLASS_PREFIX = re.compile(r'(?<![A-Z0-9])(?:CLASS|CLS|CL|RATING|ANSI|ASA)\s*[-.:#]?\s*(?P<c>\d{3,4})(?!\d)')
RE_CLASS_SUFFIX = re.compile(r'(?<!\d)(?P<c>\d{3,4})\s*(?:#|LBS?|LBF)(?![A-Z0-9])')
RE_HASH_PREFIX = re.compile(r'(?<![A-Z0-9])#\s*(?P<c>\d{3,4})(?!\d)')
RE_PN = re.compile(r'(?<![A-Z0-9])PN\s*[-.:]?\s*(?P<pn>\d{1,3}(?:\.5)?)(?!\d)')
RE_SLASH = re.compile(r'(?:CLASS|CLS|CL|RATING)\s*[-.:#]?\s*\d{3,4}\s*/\s*\d{3,4}')


def extract_pressure_class(text: str, category: str) -> ExtractedValue:
    if category not in PRESSURE_CATEGORIES or not text:
        return ExtractedValue()
    t = text.upper()
    if RE_SLASH.search(t):
        return none_with("EXTRACTION_CONFLICT")

    found = []  # (system, number, span)
    for rx in (RE_CLASS_PREFIX, RE_CLASS_SUFFIX, RE_HASH_PREFIX):
        for m in rx.finditer(t):
            found.append(("ASME_CLASS", int(m.group("c")), m.span("c")))
    for m in RE_PN.finditer(t):
        found.append(("PN", float(m.group("pn")), m.span("pn")))

    if not found:
        return ExtractedValue()
    distinct = {(s, n) for s, n, _ in found}
    if len(distinct) > 1:
        return none_with("EXTRACTION_CONFLICT")

    system, num, span = found[0]
    if system == "ASME_CLASS":
        if num not in VALID_CLASSES:
            return none_with("NON_STANDARD_RATING", span)
        return ExtractedValue(f"ASME_{num}", 0.95, "rule", span)
    if num not in PN_VALID:
        return none_with("NON_STANDARD_RATING", span)
    shown = int(num) if num == int(num) else num
    return ExtractedValue(f"PN_{shown}", 0.95, "rule", span)
