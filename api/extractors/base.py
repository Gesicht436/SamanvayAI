"""Base data structures and interface definitions for attribute extraction.

Follows standard library first principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedValue:
    """Represents a single extracted attribute value with provenance and confidence."""

    value: Any = None
    confidence: float = 0.0
    source: str = "rule"
    evidence_span: tuple[int, int] | None = None  # (start, end) offsets into RAW text
    flags: list[str] = field(default_factory=list)
    evidence: tuple[int, int] | None = None  # Alias for compatibility

    def __post_init__(self) -> None:
        """Keep evidence and evidence_span synchronized."""
        if self.evidence_span is None and self.evidence is not None:
            self.evidence_span = self.evidence
        elif self.evidence is None and self.evidence_span is not None:
            self.evidence = self.evidence_span

    def is_valid(self) -> bool:
        """Returns True if a non-null canonical value was identified without conflicts."""
        return self.value is not None and len(self.flags) == 0


def none_with(flag: str, evidence_span: tuple[int, int] | None = None) -> ExtractedValue:
    """The safe response to a conflict, ambiguous token, or invalid rating.

    Returns None value plus an explicit safety flag.
    Never guess or guess partially when an extraction is ambiguous or invalid.
    """
    return ExtractedValue(value=None, confidence=0.0, evidence_span=evidence_span, flags=[flag])


class BaseExtractor(ABC):
    """Abstract base class for all attribute extractors."""

    @abstractmethod
    def extract(self, text: str, category: str | None = None) -> ExtractedValue:
        """Extract a canonical value and evidence span from text.

        Args:
            text: Raw input text.
            category: Optional subcategory or major category for gating.

        Returns:
            ExtractedValue containing canonical value, confidence, evidence span, and flags.
        """
        raise NotImplementedError
