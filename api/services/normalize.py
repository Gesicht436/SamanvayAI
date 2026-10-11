"""Text Normalization Engine for Material Descriptions.

Conforms to specsheet.md Section 4.2 and Section 18.3:
1. NFKC normalization; maps quote variants (″ ” “ '' -> ", ′ ’ -> ').
2. Uppercase Latin; leaves Indic scripts intact.
3. Transliterates Indic trade terms using per-language dictionaries.
   Unknown Indic tokens stay and trigger UNKNOWN_INDIC_TOKENS flag.
   Mixed Latin + Indic text triggers MIXED_SCRIPT flag.
4. Expands abbreviations only inside a candidate category.
   Unknown category: no expansion of ambiguous tokens.
   Fasteners STD expands only when followed by a bolt size.
5. Preserves # " ' / - + . and X between numbers.
   Preserves Indic combining marks.
6. Returns (clean_text, tokens, language, flags).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from api.services.script_detector import detect_scripts

# Paths
DICTIONARIES_DIR = Path(__file__).resolve().parent.parent.parent / "dictionaries"
ABBREVIATIONS_FILE = DICTIONARIES_DIR / "abbreviations.json"
INDIC_DIR = DICTIONARIES_DIR / "indic"

# Bolt size pattern for FASTENERS: e.g. M12, M16, M16X50, 1/2", 1/2, 5/8", 1", 20MM
BOLT_SIZE_RE = re.compile(
    r"^(?:M\d+(?:\.\d+)?(?:[X\*]\d+(?:\.\d+)?)?|\d+(?:/\d+)?(?:\"|INCH|MM)?(?:[X\*]\d+(?:\"|INCH|MM)?)?)$",
    re.IGNORECASE,
)

# Cross-sector collision tokens that must never be naively expanded (Section 18.3)
COLLISION_TOKENS = {
    "ROLL",
    "BELT",
    "ST",
    "EP",
    "T22",
    "T91",
    "T11",
    "TUBE",
    "I",
    "R",
    "FC",
}


@dataclass
class NormalizationResult:
    """Normalized text with tokens, primary language, and safety flags."""

    clean_text: str
    tokens: list[str]
    language: str
    flags: list[str] = field(default_factory=list)


class NormalizerDictionaries:
    """Loads and caches normalization dictionaries from disk."""

    def __init__(self) -> None:
        self.category_gated: dict[str, dict[str, str]] = {}
        self.general: dict[str, str] = {}
        self.indic_maps: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if ABBREVIATIONS_FILE.exists():
            with open(ABBREVIATIONS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                self.category_gated = {
                    cat.upper(): {k.upper(): v.upper() for k, v in terms.items()}
                    for cat, terms in data.get("category_gated", {}).items()
                }
                self.general = {
                    k.upper(): v.upper()
                    for k, v in data.get("general", {}).items()
                    if k.upper() not in COLLISION_TOKENS
                }

        if INDIC_DIR.exists():
            for json_file in INDIC_DIR.glob("*.json"):
                lang = json_file.stem.lower()
                with open(json_file, encoding="utf-8") as f:
                    terms = json.load(f)
                    self.indic_maps[lang] = {k.strip(): v.strip().upper() for k, v in terms.items()}


_DICTS: NormalizerDictionaries | None = None


def get_dictionaries() -> NormalizerDictionaries:
    """Get or initialize singleton dictionaries."""
    global _DICTS
    if _DICTS is None:
        _DICTS = NormalizerDictionaries()
    return _DICTS


def map_quotes(text: str) -> str:
    """Standardize Unicode quotation marks, primes, and apostrophes.

    Double quotes: ″ (U+2033), ” (U+201D), “ (U+201C), ʺ (U+02BA), '' -> "
    Single quotes: ′ (U+2032), ’ (U+2019), ‘ (U+2018), ʹ (U+02B9) -> '
    """
    text = text.replace("''", '"')
    text = (
        text.replace("\u2033", '"')
        .replace("\u201d", '"')
        .replace("\u201c", '"')
        .replace("\u02ba", '"')
        .replace("\u02b9\u02b9", '"')
    )
    text = text.replace("\u2032", "'").replace("\u2019", "'").replace("\u2018", "'").replace("\u02b9", "'")
    return text


def contains_indic_chars(token: str) -> bool:
    """Check if token contains any Indic characters."""
    for ch in token:
        cp = ord(ch)
        for start, end, _ in {
            "Devanagari": (0x0900, 0x097F, "hi"),
            "Bengali": (0x0980, 0x09FF, "bn"),
            "Gurmukhi": (0x0A00, 0x0A7F, "pa"),
            "Gujarati": (0x0A80, 0x0AFF, "gu"),
            "Odia": (0x0B00, 0x0B7F, "or"),
            "Tamil": (0x0B80, 0x0BFF, "ta"),
            "Telugu": (0x0C00, 0x0C7F, "te"),
            "Kannada": (0x0C80, 0x0CFF, "kn"),
            "Malayalam": (0x0D00, 0x0D7F, "ml"),
        }.values():
            if start <= cp <= end:
                return True
    return False


def tokenize_preserving_special(text: str) -> list[str]:
    """Tokenize string while preserving punctuation, dimensions, and Indic text.

    Tokens split by whitespace. Punctuation attached to words is kept if valid
    (#, ", ', /, -, +, ., X).
    """
    raw_tokens = text.split()
    tokens: list[str] = []
    for t in raw_tokens:
        clean = t.strip()
        if clean:
            tokens.append(clean)
    return tokens


def normalize_text(text: str, category: str | None = None) -> NormalizationResult:
    """Normalize material description string.

    Args:
        text: Raw description input.
        category: Candidate material family/category (e.g. 'VALVES', 'PIPES', 'MOTORS').

    Returns:
        NormalizationResult containing clean_text, tokens, language, and flags.
    """
    if not text or not text.strip():
        return NormalizationResult(clean_text="", tokens=[], language="en", flags=[])

    flags: list[str] = []

    # 1. NFKC normalization and quote standardization
    norm = map_quotes(text)
    norm = unicodedata.normalize("NFKC", norm)
    norm = map_quotes(norm)

    # 2. Detect script & language
    script_info = detect_scripts(norm)
    language = script_info.primary_language
    if "MIXED_SCRIPT" in script_info.flags:
        flags.append("MIXED_SCRIPT")

    # 3. Uppercase Latin characters while leaving Indic scripts intact
    # Python str.upper() does this cleanly without modifying Indic code points
    norm = norm.upper()

    # 4. Standardize dimension multiplier 'x' between numbers: e.g. 50 x 50 x 6 -> 50X50X6
    dim_pat = re.compile(r"(\d+)(?:\s+[xX]\s*|\s*[xX]\s+)(\d+)")
    while dim_pat.search(norm):
        norm = dim_pat.sub(r"\1X\2", norm, count=1)

    # 5. Tokenize
    raw_tokens = tokenize_preserving_special(norm)

    dicts = get_dictionaries()
    out_tokens: list[str] = []
    cat_upper = category.upper() if category else None

    # Track unknown Indic tokens
    has_unknown_indic = False

    # 6. Process tokens (Indic transliteration + Abbreviation expansion)
    n_tokens = len(raw_tokens)
    idx = 0
    while idx < n_tokens:
        tok = raw_tokens[idx]

        # Check for Indic transliteration
        if contains_indic_chars(tok):
            translated = None
            # Check specific language map first
            if language in dicts.indic_maps and tok in dicts.indic_maps[language]:
                translated = dicts.indic_maps[language][tok]
            else:
                # Search across all Indic maps
                for lang_dict in dicts.indic_maps.values():
                    if tok in lang_dict:
                        translated = lang_dict[tok]
                        break

            if translated:
                out_tokens.append(translated)
            else:
                out_tokens.append(tok)
                has_unknown_indic = True
            idx += 1
            continue

        # Check category-gated abbreviation expansion
        expanded = None

        if cat_upper and cat_upper in dicts.category_gated:
            cat_abbrevs = dicts.category_gated[cat_upper]

            if tok in cat_abbrevs:
                # Special rule for FASTENERS: STD only expands to STUD when followed by bolt size
                if cat_upper == "FASTENERS" and tok == "STD":
                    next_tok = raw_tokens[idx + 1] if idx + 1 < n_tokens else None
                    if next_tok and BOLT_SIZE_RE.match(next_tok):
                        expanded = "STUD"
                    else:
                        flags.append("AMBIGUOUS_ABBREVIATION")
                        expanded = tok  # Do not expand
                else:
                    expanded = cat_abbrevs[tok]

        # Check general abbreviations if not expanded and not a collision token
        if expanded is None and tok in dicts.general:
            expanded = dicts.general[tok]

        out_tokens.append(expanded if expanded is not None else tok)
        idx += 1

    if has_unknown_indic:
        flags.append("UNKNOWN_INDIC_TOKENS")

    # 7. Collapse whitespace and format clean_text
    clean_text = " ".join(out_tokens)
    # Deduplicate flags while preserving order
    unique_flags = list(dict.fromkeys(flags))

    return NormalizationResult(
        clean_text=clean_text,
        tokens=out_tokens,
        language=language,
        flags=unique_flags,
    )
