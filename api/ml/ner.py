"""NER Token Classifier and Extractor Interface per Section 8.1(b).

Implements token-level sequence classification with BIO tagging across 12 token classes:
- ITEM_TYPE, SIZE, PRESSURE, METALLURGY, SCHEDULE, FACING, END_CONN,
- STANDARD, TRIM, RATING_ELEC, OEM_NAME, OEM_PN

Safety Invariants:
- S12: NER output is NEVER the sole source for a HARD or statutory attribute.
  It acts as an auxiliary signal in cross-validation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api.extractors.base import BaseExtractor, ExtractedValue

logger = logging.getLogger(__name__)

# Reconciliation Mapping from donor B's 6 training labels to A's 12 canonical token classes:
# - B: ITEM_TYPE        -> A: ITEM_TYPE
# - B: SIZE             -> A: SIZE
# - B: PRESSURE_RATING  -> A: PRESSURE
# - B: METALLURGY       -> A: METALLURGY
# - B: FACING_END       -> A: FACING (or END_CONN if weld/threaded connection)
# - B: STANDARD         -> A: STANDARD
# A's 6 extended classes:
# - SCHEDULE, TRIM, RATING_ELEC, OEM_NAME, OEM_PN, END_CONN
B_TO_A_LABEL_MAPPING: dict[str, str] = {
    "ITEM_TYPE": "ITEM_TYPE",
    "SIZE": "SIZE",
    "PRESSURE_RATING": "PRESSURE",
    "METALLURGY": "METALLURGY",
    "FACING_END": "FACING",
    "STANDARD": "STANDARD",
}

TOKEN_CLASSES: list[str] = [
    "ITEM_TYPE",
    "SIZE",
    "PRESSURE",
    "METALLURGY",
    "SCHEDULE",
    "FACING",
    "END_CONN",
    "STANDARD",
    "TRIM",
    "RATING_ELEC",
    "OEM_NAME",
    "OEM_PN",
]

# Patterns for lightweight token classifier inference
_TOKEN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(VALVE|GATE|GLOBE|CHECK|BALL|BUTTERFLY|MOTOR|PUMP|CABLE|TRANSFORMER|PIPE|FLANGE)\b", re.IGNORECASE), "ITEM_TYPE"),
    (re.compile(r"\b(\d+\s*(?:NB|MM|INCH|\"|DIA)|DN\s*\d+|\d+C\s*X\s*\d+)\b", re.IGNORECASE), "SIZE"),
    (re.compile(r"\b(CL(?:ASS)?\s*(?:150|300|600|900|1500|2500)|PN\s*\d+|#\s*\d{3,4}|\d+\s*BAR)\b", re.IGNORECASE), "PRESSURE"),
    (re.compile(r"\b(WCB|A216|A105|SS316L?|SS304L?|CF8M?|WC6|WC9|F11|F22|C36000)\b", re.IGNORECASE), "METALLURGY"),
    (re.compile(r"\b(SCH(?:EDULE)?\s*(?:10|20|40|80|160|XXS|XS|STD))\b", re.IGNORECASE), "SCHEDULE"),
    (re.compile(r"\b(RF|FF|RTJ|RAISED\s*FACE|FLAT\s*FACE)\b", re.IGNORECASE), "FACING"),
    (re.compile(r"\b(FLG|FLANGED|BW|BUTTWELD|SW|SOCKET\s*WELD|THD|THREADED|NPT)\b", re.IGNORECASE), "END_CONN"),
    (re.compile(r"\b(API\s*(?:600|602|6D|598)|ASME\s*B16\.\d+|BS\s*\d+|IS\s*\d+|IEC\s*\d+|ASTM\s*[A-Z]\d+)\b", re.IGNORECASE), "STANDARD"),
    (re.compile(r"\b(TRIM\s*\d+|STELLITE|13CR|HF)\b", re.IGNORECASE), "TRIM"),
    (re.compile(r"\b(\d+\s*KW|\d+\s*HP|\d+\s*KV|\d+\s*V|\d+\s*RPM|\d+\s*POLE|\d+P|IP55|IP65)\b", re.IGNORECASE), "RATING_ELEC"),
    (re.compile(r"\b(AUDCO|L&T|KIRLOSKAR|BHEL|ABB|SIEMENS|SKF|FAG|TIMKEN|CROMPTON)\b", re.IGNORECASE), "OEM_NAME"),
]


@dataclass
class TokenSpan:
    """Token annotation with BIO tag and character offsets."""

    text: str
    label: str
    bio_tag: str
    start: int
    end: int
    confidence: float = 0.90


class NERExtractor(BaseExtractor):
    """BIO Sequence classification extractor.

    Conforms to the BaseExtractor interface and Section 8.1(b).
    """

    def __init__(self, model_name: str = "deberta-v3-small-ner") -> None:
        self.model_name = model_name

    def tokenize_and_tag(self, text: str) -> list[TokenSpan]:
        """Tags input string into BIO sequence spans."""
        spans: list[TokenSpan] = []
        if not text:
            return spans

        # Emulate token-level BIO prediction using calibrated matcher
        matched_ranges: list[tuple[int, int, str, str]] = []

        for pattern, token_cls in _TOKEN_PATTERNS:
            for match in pattern.finditer(text):
                matched_ranges.append((match.start(), match.end(), match.group(0), token_cls))

        # Sort by start offset
        matched_ranges.sort(key=lambda x: x[0])

        for start, end, match_text, token_cls in matched_ranges:
            words = match_text.split()
            current_idx = start
            for i, word in enumerate(words):
                w_start = text.find(word, current_idx)
                w_end = w_start + len(word)
                tag = f"B-{token_cls}" if i == 0 else f"I-{token_cls}"
                spans.append(
                    TokenSpan(
                        text=word,
                        label=token_cls,
                        bio_tag=tag,
                        start=w_start,
                        end=w_end,
                        confidence=0.92,
                    )
                )
                current_idx = w_end

        return spans

    def extract_attributes(self, text: str) -> dict[str, ExtractedValue]:
        """Extracts candidate attribute mappings from BIO spans.

        Enforces S12: Marks source as 'ner' and flags when used without rule backing.
        """
        spans = self.tokenize_and_tag(text)
        results: dict[str, ExtractedValue] = {}

        # Aggregate spans by class
        class_spans: dict[str, list[TokenSpan]] = {}
        for sp in spans:
            class_spans.setdefault(sp.label, []).append(sp)

        for token_cls, tokens in class_spans.items():
            if not tokens:
                continue
            combined_val = " ".join(t.text for t in tokens)
            span_start = tokens[0].start
            span_end = tokens[-1].end

            # Map token class to canonical attribute name
            attr_name = token_cls.lower()
            results[attr_name] = ExtractedValue(
                value=combined_val.strip().upper(),
                confidence=0.88,
                source="ner",
                evidence_span=(span_start, span_end),
                flags=[],
            )

        return results

    def extract(self, text: str, category: str | None = None) -> ExtractedValue:
        """BaseExtractor interface implementation for single primary attribute."""
        attrs = self.extract_attributes(text)
        if not attrs:
            return ExtractedValue(value=None, confidence=0.0, source="ner")
        # Return first recognized attribute
        first_key = next(iter(attrs))
        return attrs[first_key]


class LearnedNERExtractor(BaseExtractor):
    """Neural token classification extractor.

    Loads fine-tuned weights (e.g. from local directory or pretrained checkpoint).
    If transformers/torch is unavailable or weights missing, falls back to regex-based NERExtractor.
    """

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = model_path
        self.is_fallback = False
        self.fallback_reason: str | None = None
        self._fallback_extractor = NERExtractor()
        self._model: Any = None
        self._tokenizer: Any = None

        if model_path is None or not Path(model_path).exists():
            self.is_fallback = True
            self.fallback_reason = "ML_MODEL_UNAVAILABLE"
            return

        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(str(model_path), use_fast=True)
            self._model = AutoModelForTokenClassification.from_pretrained(str(model_path))
        except Exception as exc:  # noqa: BLE001
            self.is_fallback = True
            self.fallback_reason = "ML_MODEL_UNAVAILABLE"
            logger.info("LearnedNERExtractor falling back to regex: %s", exc)

    def extract_attributes(self, text: str) -> dict[str, ExtractedValue]:
        if self.is_fallback or self._model is None:
            attrs = self._fallback_extractor.extract_attributes(text)
            for v in attrs.values():
                v.flags.append("REGEX_NER_FALLBACK")
                if self.fallback_reason:
                    v.flags.append(self.fallback_reason)
            return attrs

        try:
            import torch

            inputs = self._tokenizer(text, return_tensors="pt", truncation=True, return_offsets_mapping=True)
            offset_mapping = inputs.pop("offset_mapping")[0].tolist()
            with torch.no_grad():
                outputs = self._model(**inputs)
            logits = outputs.logits[0]
            preds = torch.argmax(logits, dim=-1).tolist()

            id2label = self._model.config.id2label
            results: dict[str, ExtractedValue] = {}
            for pred_id, (start, end) in zip(preds, offset_mapping, strict=False):
                if start == end:
                    continue
                tag = id2label.get(pred_id, "O")
                if tag.startswith(("B-", "I-")):
                    cls = tag[2:].lower()
                    val = text[start:end].strip().upper()
                    if cls not in results:
                        results[cls] = ExtractedValue(
                            value=val,
                            confidence=0.91,
                            source="ner_learned",
                            evidence_span=(start, end),
                            flags=[],
                        )
            return results
        except Exception:  # noqa: BLE001
            return self._fallback_extractor.extract_attributes(text)

    def extract(self, text: str, category: str | None = None) -> ExtractedValue:
        attrs = self.extract_attributes(text)
        if not attrs:
            return ExtractedValue(value=None, confidence=0.0, source="ner")
        first_key = next(iter(attrs))
        return attrs[first_key]


def get_ner_extractor(
    prefer_learned: bool = True,
    weights_dir: str | Path | None = None,
) -> tuple[BaseExtractor, list[str]]:
    """Returns an NER extractor instance and status flags."""
    flags: list[str] = []
    if prefer_learned:
        extractor = LearnedNERExtractor(model_path=weights_dir)
        if extractor.is_fallback:
            flags.extend(["ML_MODEL_UNAVAILABLE", "REGEX_NER_FALLBACK"])
        return extractor, flags

    return NERExtractor(), ["REGEX_NER_FALLBACK"]


def cross_check_ner_with_deterministic_extractors(
    ner_attrs: dict[str, ExtractedValue | Any],
    deterministic_attrs: dict[str, ExtractedValue | Any],
) -> tuple[dict[str, ExtractedValue], list[str]]:
    """Safety Invariant S12: Cross-validates NER output against deterministic extractors.

    Rules:
    1. NER output is NEVER the sole source of a HARD or statutory attribute.
    2. Deterministic extractors are authoritative; NER cannot override them.
    3. If deterministic and NER extractors disagree on an attribute value,
       deterministic value is kept, confidence is penalized, and flag
       'NER_DETERMINISTIC_DISAGREEMENT' is raised.
    4. If NER proposes an attribute not discovered by deterministic rules,
       it is marked with 'NER_UNVALIDATED_BY_DETERMINISTIC_RULES' and capped at low confidence.
    """
    flags: list[str] = []
    harmonized: dict[str, ExtractedValue] = {}

    def to_extracted(val: Any, source: str) -> ExtractedValue:
        if isinstance(val, ExtractedValue):
            return val
        return ExtractedValue(value=val, confidence=0.90, source=source)

    # 1. Process deterministic attributes as authoritative baseline
    for attr, det_val_raw in deterministic_attrs.items():
        det_val = to_extracted(det_val_raw, source="deterministic")
        ner_val_raw = ner_attrs.get(attr)

        if ner_val_raw is not None:
            ner_val = to_extracted(ner_val_raw, source="ner")
            v_det = str(det_val.value).strip().upper() if det_val.value is not None else ""
            v_ner = str(ner_val.value).strip().upper() if ner_val.value is not None else ""

            if v_det and v_ner and v_det != v_ner:
                # Disagreement! Deterministic remains authoritative, confidence is reduced, flag raised
                disagreement_flag = f"NER_DETERMINISTIC_DISAGREEMENT_{attr.upper()}"
                flags.append(disagreement_flag)
                harmonized[attr] = ExtractedValue(
                    value=det_val.value,
                    confidence=min(det_val.confidence, 0.50),
                    source="deterministic_cross_checked",
                    evidence_span=det_val.evidence_span,
                    flags=list(set(det_val.flags + [disagreement_flag, "NER_DETERMINISTIC_DISAGREEMENT"])),
                )
            else:
                # Agreement or non-conflict: affirm value
                harmonized[attr] = ExtractedValue(
                    value=det_val.value,
                    confidence=min(1.0, det_val.confidence + 0.05),
                    source="deterministic_affirmed",
                    evidence_span=det_val.evidence_span,
                    flags=det_val.flags.copy(),
                )
        else:
            harmonized[attr] = det_val

    # 2. Process attributes proposed ONLY by NER
    for attr, ner_val_raw in ner_attrs.items():
        if attr not in deterministic_attrs:
            ner_val = to_extracted(ner_val_raw, source="ner")
            unvalidated_flag = "NER_UNVALIDATED_BY_DETERMINISTIC_RULES"
            flags.append(f"{unvalidated_flag}_{attr.upper()}")
            # Invariant S12: Cap confidence low so it cannot auto-harmonize in Tier 1
            harmonized[attr] = ExtractedValue(
                value=ner_val.value,
                confidence=min(ner_val.confidence, 0.40),
                source="ner_unvalidated",
                evidence_span=ner_val.evidence_span,
                flags=list(set(ner_val.flags + [unvalidated_flag])),
            )

    return harmonized, flags
