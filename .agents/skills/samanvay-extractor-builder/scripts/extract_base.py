"""Base types and a TOML lexicon engine for attribute extraction. Standard library only."""
import re
import tomllib
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExtractedValue:
    value: Any = None
    confidence: float = 0.0
    source: str = "rule"
    evidence: Optional[tuple] = None          # (start, end) offsets into the RAW text
    flags: list = field(default_factory=list)


def none_with(flag: str, evidence=None) -> ExtractedValue:
    """The only correct response to a conflict or invalid value: None plus a flag."""
    return ExtractedValue(value=None, confidence=0.0, evidence=evidence, flags=[flag])


def load_lexicon(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _synonym_regex(syn: str) -> re.Pattern:
    body = r"\s+".join(re.escape(p) for p in syn.upper().split())
    return re.compile(r"(?<![A-Z0-9])" + body + r"(?![A-Z0-9])")


class LexiconExtractor:
    """Matches canonical values by synonym on token boundaries (longest synonym wins)."""

    def __init__(self, spec: dict):
        self.attribute = spec["attribute"]
        self.categories = set(spec.get("categories", []))
        pairs = []
        for canon, body in spec["values"].items():
            for syn in body.get("synonyms", []):
                pairs.append((len(syn), canon, _synonym_regex(syn)))
        pairs.sort(key=lambda x: -x[0])
        self._pairs = pairs

    def extract(self, text: str, category: Optional[str] = None) -> ExtractedValue:
        if self.categories and category not in self.categories:
            return ExtractedValue()
        raw = text or ""
        upper = raw.upper()
        taken = []        # spans already claimed by a longer synonym
        hits = {}         # canon -> first span
        for _, canon, rx in self._pairs:
            for m in rx.finditer(upper):
                s, e = m.span()
                if any(s < te and ts < e for ts, te in taken):
                    continue
                taken.append((s, e))
                hits.setdefault(canon, (s, e))
        if not hits:
            return ExtractedValue()
        if len(hits) > 1:
            return none_with("EXTRACTION_CONFLICT")
        canon, span = next(iter(hits.items()))
        return ExtractedValue(value=canon, confidence=0.95, evidence=span)
