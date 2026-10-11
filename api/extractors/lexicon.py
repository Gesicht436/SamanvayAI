"""Lexicon extractor engine supporting TOML and YAML dictionaries.

Implements token-boundary regex matching with longest-synonym precedence,
conflict detection, category gating, and raw-text character span indexing.
"""

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

from api.extractors.base import BaseExtractor, ExtractedValue, none_with


def load_lexicon_data(path_or_dict: str | Path | dict) -> dict[str, Any]:
    """Loads a lexicon definition from a TOML/YAML file path or dict."""
    if isinstance(path_or_dict, dict):
        return path_or_dict

    path = Path(path_or_dict)
    if not path.exists():
        raise FileNotFoundError(f"Lexicon file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".toml":
        with open(path, "rb") as f:
            return tomllib.load(f)
    elif suffix in (".yaml", ".yml"):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data or {}
    else:
        # Default try tomllib, then yaml
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, ValueError):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}


def _synonym_regex(syn: str) -> re.Pattern:
    """Builds a token-boundary regex pattern for a multi-word synonym."""
    tokens = syn.upper().split()
    body = r"\s+".join(re.escape(token) for token in tokens)
    return re.compile(r"(?<![A-Z0-9])" + body + r"(?![A-Z0-9])")


class LexiconExtractor(BaseExtractor):
    """Matches canonical values by synonym on token boundaries.

    Guarantees:
    - Longest synonym match wins.
    - Category gating blocks irrelevant searches.
    - Multiple distinct canonical values in one string return EXTRACTION_CONFLICT.
    - Evidence spans reference the raw input text.
    """

    def __init__(self, spec_or_path: dict | str | Path):
        spec = load_lexicon_data(spec_or_path)
        self.attribute: str = spec["attribute"]
        self.categories: set[str] = {c.upper() for c in spec.get("categories", [])}

        pairs = []
        values_dict = spec.get("values", {})
        for canon, body in values_dict.items():
            synonyms = body.get("synonyms", []) if isinstance(body, dict) else []
            for syn in synonyms:
                clean_syn = str(syn).strip()
                if clean_syn:
                    pairs.append((len(clean_syn), str(canon), _synonym_regex(clean_syn)))

        # Sort descending by synonym length so longest synonym claims tokens first
        pairs.sort(key=lambda x: -x[0])
        self._pairs = pairs

    def extract(self, text: str, category: str | None = None) -> ExtractedValue:
        """Extract canonical value from text under category gate."""
        if not text:
            return ExtractedValue()

        # Category gating
        if self.categories and category:
            cat_upper = category.upper()
            major_cat = cat_upper.split(".")[0]
            if cat_upper not in self.categories and major_cat not in self.categories:
                return ExtractedValue()

        raw = text
        upper = raw.upper()
        taken_spans: list[tuple[int, int]] = []
        hits: dict[str, tuple[int, int]] = {}

        for _, canon, rx in self._pairs:
            for match in rx.finditer(upper):
                s, e = match.span()
                # Check overlap with any span already claimed by a longer synonym
                if any(s < te and ts < e for ts, te in taken_spans):
                    continue
                taken_spans.append((s, e))
                if canon not in hits:
                    hits[canon] = (s, e)

        if not hits:
            return ExtractedValue()

        # If two different canonical values were identified, return EXTRACTION_CONFLICT
        if len(hits) > 1:
            return none_with("EXTRACTION_CONFLICT")

        canon, span = next(iter(hits.items()))
        return ExtractedValue(value=canon, confidence=0.95, source="rule", evidence_span=span)
