"""Unicode script and language detection for material descriptions.

Detects Indic scripts (Devanagari, Tamil, Bengali, Gujarati, Telugu, Kannada,
Malayalam, Odia, Gurmukhi) and Latin script. Flags mixed-script text.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# Unicode script ranges
SCRIPT_RANGES: dict[str, tuple[int, int, str]] = {
    "Devanagari": (0x0900, 0x097F, "hi"),
    "Bengali": (0x0980, 0x09FF, "bn"),
    "Gurmukhi": (0x0A00, 0x0A7F, "pa"),
    "Gujarati": (0x0A80, 0x0AFF, "gu"),
    "Odia": (0x0B00, 0x0B7F, "or"),
    "Tamil": (0x0B80, 0x0BFF, "ta"),
    "Telugu": (0x0C00, 0x0C7F, "te"),
    "Kannada": (0x0C80, 0x0CFF, "kn"),
    "Malayalam": (0x0D00, 0x0D7F, "ml"),
}

INDIC_SCRIPTS = set(SCRIPT_RANGES.keys())


@dataclass
class ScriptDetectionResult:
    """Result of script and language analysis on a text string."""

    primary_script: str
    primary_language: str
    script_counts: dict[str, int] = field(default_factory=dict)
    is_mixed_script: bool = False
    flags: list[str] = field(default_factory=list)


def get_char_script(char: str) -> tuple[str, str] | None:
    """Identify the script and language code of a single character.

    Returns (script_name, lang_code) or None if character is non-alphabetic/punctuation/digit.
    """
    cp = ord(char)
    # Check Indic ranges
    for script_name, (start, end, lang_code) in SCRIPT_RANGES.items():
        if start <= cp <= end:
            return script_name, lang_code

    # Check Latin: ASCII letters and Latin extended
    if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A) or (0x00C0 <= cp <= 0x024F):
        return "Latin", "en"

    return None


def detect_scripts(text: str) -> ScriptDetectionResult:
    """Detect scripts and primary language in a given text.

    Flags MIXED_SCRIPT if both Latin and any Indic script are present.
    """
    if not text:
        return ScriptDetectionResult(
            primary_script="Latin",
            primary_language="en",
            script_counts={},
            is_mixed_script=False,
            flags=[],
        )

    # Normalize to NFC before character analysis
    norm_text = unicodedata.normalize("NFC", text)
    counts: dict[str, int] = {}
    lang_for_script: dict[str, str] = {"Latin": "en"}
    has_latin = False
    has_indic = False

    for char in norm_text:
        match = get_char_script(char)
        if match:
            script_name, lang_code = match
            counts[script_name] = counts.get(script_name, 0) + 1
            lang_for_script[script_name] = lang_code
            if script_name == "Latin":
                has_latin = True
            elif script_name in INDIC_SCRIPTS:
                has_indic = True

    if not counts:
        return ScriptDetectionResult(
            primary_script="Latin",
            primary_language="en",
            script_counts={},
            is_mixed_script=False,
            flags=[],
        )

    # Determine primary script by highest frequency
    primary_script = max(counts.items(), key=lambda kv: kv[1])[0]
    primary_language = lang_for_script.get(primary_script, "en")

    is_mixed = has_latin and has_indic
    flags: list[str] = []
    if is_mixed:
        flags.append("MIXED_SCRIPT")

    return ScriptDetectionResult(
        primary_script=primary_script,
        primary_language=primary_language,
        script_counts=counts,
        is_mixed_script=is_mixed,
        flags=flags,
    )
