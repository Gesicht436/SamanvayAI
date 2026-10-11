"""Optical Character Recognition and digital document intake provider protocol.

Enforces Section 10.0, 10.1:
- OCRProvider protocol with FakeOCRProvider (CI/replay) and PyMuPDFProvider (digital PDF text layer).
- Low-confidence OCR threshold enforcement for HARD attributes (Invariant S5).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None

from api.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class OCRLine:
    """A single recognized line or table item from a document page."""

    page: int
    raw_text: str
    bbox: list[float] = field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])
    ocr_engine: str = "fake"
    raster_dpi: int = 300
    ocr_conf: float = 1.000
    fields: dict[str, Any] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


@dataclass
class OCRPageResult:
    """Recognition result for a single page."""

    page_number: int
    lines: list[OCRLine]
    mean_confidence: float = 1.000


@dataclass
class OCRDocumentResult:
    """Full document extraction result."""

    file_hash: str
    pages: list[OCRPageResult]
    doc_type_hint: str | None = None


class OCRProvider(Protocol):
    """Protocol for document text and layout recognition."""

    def extract_document(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> OCRDocumentResult:
        """Extract text and structured lines from document bytes."""
        ...


class FakeOCRProvider:
    """Deterministic OCR provider for CI, testing, and fixture replay.

    Can parse plain text, JSON sidecars, or synthesize lines from raw text.
    """

    def __init__(self, default_conf: float = 0.985):
        self.default_conf = default_conf

    def extract_document(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> OCRDocumentResult:
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check if the bytes are a UTF-8 JSON sidecar payload
        try:
            payload_str = file_bytes.decode("utf-8")
            if payload_str.strip().startswith("{") and payload_str.strip().endswith("}"):
                data = json.loads(payload_str)
                if "lines" in data or "pages" in data:
                    doc_type_hint = data.get("doc_type")
                    pages_out: list[OCRPageResult] = []

                    if "pages" in data:
                        for p_idx, p_data in enumerate(data["pages"], start=1):
                            lines_out = [
                                OCRLine(
                                    page=p_idx,
                                    raw_text=line.get("raw_text", ""),
                                    bbox=line.get("bbox", [0.0, 0.0, 1.0, 1.0]),
                                    ocr_engine="fake",
                                    raster_dpi=line.get("raster_dpi", 300),
                                    ocr_conf=float(line.get("ocr_conf", self.default_conf)),
                                    fields=line.get("fields", {}),
                                    flags=line.get("flags", []),
                                )
                                for line in p_data.get("lines", [])
                            ]
                            conf = (
                                sum(l.ocr_conf for l in lines_out) / len(lines_out) if lines_out else self.default_conf
                            )
                            pages_out.append(OCRPageResult(page_number=p_idx, lines=lines_out, mean_confidence=conf))
                    else:
                        lines_out = [
                            OCRLine(
                                page=line.get("page", 1),
                                raw_text=line.get("raw_text", ""),
                                bbox=line.get("bbox", [0.0, 0.0, 1.0, 1.0]),
                                ocr_engine="fake",
                                raster_dpi=line.get("raster_dpi", 300),
                                ocr_conf=float(line.get("ocr_conf", self.default_conf)),
                                fields=line.get("fields", {}),
                                flags=line.get("flags", []),
                            )
                            for line in data.get("lines", [])
                        ]
                        conf = sum(l.ocr_conf for l in lines_out) / len(lines_out) if lines_out else self.default_conf
                        pages_out.append(OCRPageResult(page_number=1, lines=lines_out, mean_confidence=conf))

                    return OCRDocumentResult(file_hash=file_hash, pages=pages_out, doc_type_hint=doc_type_hint)

            # Plain text fallback
            raw_lines = [line.strip() for line in payload_str.splitlines() if line.strip()]
            ocr_lines = [
                OCRLine(
                    page=1,
                    raw_text=line,
                    bbox=[0.05, float(i) * 0.05, 0.95, float(i) * 0.05 + 0.04],
                    ocr_engine="fake_text",
                    ocr_conf=self.default_conf,
                )
                for i, line in enumerate(raw_lines)
            ]
            return OCRDocumentResult(
                file_hash=file_hash,
                pages=[OCRPageResult(page_number=1, lines=ocr_lines, mean_confidence=self.default_conf)],
                doc_type_hint=None,
            )
        except UnicodeDecodeError:
            # Binary PDF/Image payload in fake provider
            return OCRDocumentResult(
                file_hash=file_hash,
                pages=[
                    OCRPageResult(
                        page_number=1,
                        lines=[
                            OCRLine(
                                page=1,
                                raw_text="BINARY DOCUMENT CONTENT",
                                bbox=[0.1, 0.1, 0.9, 0.2],
                                ocr_engine="fake_binary",
                                ocr_conf=self.default_conf,
                            )
                        ],
                        mean_confidence=self.default_conf,
                    )
                ],
                doc_type_hint=None,
            )


class PyMuPDFProvider:
    """PDF text layer extractor using PyMuPDF (fitz).

    Extracts digital text and layout coordinates directly from PDF streams.
    """

    def extract_document(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> OCRDocumentResult:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        if not fitz:
            logger.warning("PyMuPDF not installed, falling back to FakeOCRProvider")
            return FakeOCRProvider().extract_document(file_bytes, filename, content_type)

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:  # noqa: BLE001 - fallback gracefully on any corrupt or unparseable binary stream
            logger.warning("Could not open PDF with PyMuPDF: %s. Falling back to FakeOCRProvider.", exc)
            return FakeOCRProvider().extract_document(file_bytes, filename, content_type)

        pages_out: list[OCRPageResult] = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            width = rect.width or 1.0
            height = rect.height or 1.0

            blocks = page.get_text("blocks")
            lines_out: list[OCRLine] = []

            for b in blocks:
                # b format: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5 and b[4].strip():
                    x0, y0, x1, y1, text_content = b[0], b[1], b[2], b[3], b[4]
                    norm_bbox = [
                        round(float(x0) / width, 4),
                        round(float(y0) / height, 4),
                        round(float(x1) / width, 4),
                        round(float(y1) / height, 4),
                    ]
                    lines_out.append(
                        OCRLine(
                            page=page_idx + 1,
                            raw_text=text_content.strip(),
                            bbox=norm_bbox,
                            ocr_engine="pymupdf",
                            raster_dpi=300,
                            ocr_conf=1.000,
                        )
                    )

            conf = 1.000 if lines_out else 0.000
            pages_out.append(OCRPageResult(page_number=page_idx + 1, lines=lines_out, mean_confidence=conf))

        doc.close()
        return OCRDocumentResult(file_hash=file_hash, pages=pages_out, doc_type_hint=None)


def get_ocr_provider(provider_name: str | None = None) -> OCRProvider:
    """Returns the configured OCR provider instance."""
    settings = get_settings()
    name = (provider_name or settings.ocr_provider).lower()
    if name == "pymupdf":
        return PyMuPDFProvider()
    return FakeOCRProvider()


def enforce_ocr_confidence_on_attributes(
    extracted_attrs: dict[str, Any],
    attribute_specs: dict[str, str],
    ocr_conf: float,
    threshold: float = 0.70,
) -> tuple[dict[str, Any], list[str]]:
    """Enforces Safety Invariant S5.

    Invariant S5: Low-confidence OCR on HARD attributes becomes None with
    flag LOW_OCR_CONFIDENCE.

    Parameters:
        extracted_attrs: Extracted attribute dictionary {attr_name: ExtractedValue | dict | primitive}
        attribute_specs: Mapping of attribute name to role ('HARD', 'REQUIRED', 'SOFT', etc.)
        ocr_conf: Confidence of the OCR line / document source
        threshold: Minimum acceptable confidence threshold (default 0.70 from settings)

    Returns:
        (sanitized_attrs, flags)
    """
    sanitized = dict(extracted_attrs)
    flags: list[str] = []

    if ocr_conf is not None and ocr_conf < threshold:
        low_hard_found = False
        for attr_name, role in attribute_specs.items():
            if role == "HARD" and attr_name in sanitized and sanitized[attr_name] is not None:
                # Value must be blanked to None
                val = sanitized[attr_name]
                if isinstance(val, dict):
                    sanitized[attr_name] = {
                        **val,
                        "value": None,
                        "flags": list(val.get("flags", [])) + ["LOW_OCR_CONFIDENCE"],
                    }
                else:
                    sanitized[attr_name] = None
                low_hard_found = True

        if low_hard_found:
            flags.append("LOW_OCR_CONFIDENCE")

    return sanitized, flags
