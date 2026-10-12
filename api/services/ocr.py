"""Optical Character Recognition and digital document intake provider protocol.

Enforces Section 10.0, 10.1:
- OCRProvider protocol with FakeOCRProvider, PyMuPDFProvider, PaddleOCRProvider, EasyOCRProvider, HybridOCRProvider.
- Real per-block confidences aggregated per line and page.
- Low-confidence OCR threshold enforcement for HARD attributes (Invariant S5).
- Scanned page rasterization at 300 DPI with denoising (median filter) and deskewing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from statistics import median
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


def _detect_filetype(file_bytes: bytes, filename: str | None = None, content_type: str | None = None) -> str:
    """Detects document or image filetype from magic bytes or extension."""
    if file_bytes.startswith(b"%PDF"):
        return "pdf"
    if file_bytes.startswith(b"\x89PNG"):
        return "png"
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if file_bytes.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("pdf", "png", "jpg", "jpeg", "tif", "tiff"):
            return "jpeg" if ext in ("jpg", "jpeg") else ("tiff" if ext in ("tif", "tiff") else ext)
    if content_type:
        ct = content_type.lower()
        if "pdf" in ct:
            return "pdf"
        if "png" in ct:
            return "png"
        if "jpeg" in ct or "jpg" in ct:
            return "jpeg"
        if "tiff" in ct:
            return "tiff"
    return "pdf"


def _box_vertical_bounds(block: dict[str, Any]) -> tuple[float, float]:
    box = block.get("box")
    if isinstance(box, (list, tuple)):
        if len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
            return float(box[1]), float(box[3])
        points = [
            point
            for point in box
            if isinstance(point, (list, tuple))
            and len(point) >= 2
            and isinstance(point[1], (int, float))
        ]
        if points:
            ys = [float(point[1]) for point in points]
            return min(ys), max(ys)

    y = float(block.get("y", 0))
    return y, y


def _reading_order(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group blocks with overlapping vertical boxes into rows, then order each row left-to-right."""
    if not blocks:
        return []
    positioned = []
    for block in blocks:
        top, bottom = _box_vertical_bounds(block)
        positioned.append((top, bottom, float(block.get("x", 0)), block))
    positioned.sort(key=lambda item: ((item[0] + item[1]) / 2, item[2]))

    lines: list[list[tuple[float, float, float, dict[str, Any]]]] = []
    for item in positioned:
        top, bottom, _, _ = item
        matching_line = next(
            (
                line
                for line in lines
                if (
                    min(bottom, max(entry[1] for entry in line))
                    - max(top, min(entry[0] for entry in line))
                )
                >= 0.5
                * min(
                    bottom - top,
                    max(entry[1] for entry in line) - min(entry[0] for entry in line),
                )
                and bottom > top
                and max(entry[1] for entry in line) > min(entry[0] for entry in line)
            ),
            None,
        )
        if matching_line is None:
            lines.append([item])
        else:
            matching_line.append(item)

    lines.sort(key=lambda line: median((item[0] + item[1]) / 2 for item in line))
    return [
        item[3]
        for line in lines
        for item in sorted(line, key=lambda entry: entry[2])
    ]


def _normalize_bbox(box: Any, width: float, height: float) -> list[float]:
    """Converts pixel bounding boxes (quad or xyxy) to normalized [0, 1] [x0, y0, x1, y1]."""
    w = max(float(width), 1.0)
    h = max(float(height), 1.0)
    if isinstance(box, (list, tuple)):
        if len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
            x0, y0, x1, y1 = [float(v) for v in box]
            return [
                round(max(0.0, min(1.0, min(x0, x1) / w)), 4),
                round(max(0.0, min(1.0, min(y0, y1) / h)), 4),
                round(max(0.0, min(1.0, max(x0, x1) / w)), 4),
                round(max(0.0, min(1.0, max(y0, y1) / h)), 4),
            ]
        points = [
            pt
            for pt in box
            if isinstance(pt, (list, tuple))
            and len(pt) >= 2
            and isinstance(pt[0], (int, float))
            and isinstance(pt[1], (int, float))
        ]
        if points:
            xs = [float(pt[0]) for pt in points]
            ys = [float(pt[1]) for pt in points]
            return [
                round(max(0.0, min(1.0, min(xs) / w)), 4),
                round(max(0.0, min(1.0, min(ys) / h)), 4),
                round(max(0.0, min(1.0, max(xs) / w)), 4),
                round(max(0.0, min(1.0, max(ys) / h)), 4),
            ]
    return [0.05, 0.05, 0.95, 0.95]


def apply_median_filter_3x3(grid: list[list[int]]) -> list[list[int]]:
    """Applies a 3x3 median filter for speckle de-noising per Section 10.1."""
    if not grid or not grid[0]:
        return grid
    h = len(grid)
    w = len(grid[0])
    out = [[grid[r][c] for c in range(w)] for r in range(h)]

    for r in range(1, h - 1):
        for c in range(1, w - 1):
            neighbors = [
                grid[r - 1][c - 1], grid[r - 1][c], grid[r - 1][c + 1],
                grid[r][c - 1],     grid[r][c],     grid[r][c + 1],
                grid[r + 1][c - 1], grid[r + 1][c], grid[r + 1][c + 1],
            ]
            neighbors.sort()
            out[r][c] = neighbors[4]  # Median element of 9
    return out


def estimate_row_projection_deskew_angle(grid: list[list[int]]) -> float:
    """Estimates skew angle using horizontal row projection variance per Section 10.1."""
    if not grid or not grid[0]:
        return 0.0

    best_angle = 0.0
    best_variance = -1.0
    h = len(grid)
    w = len(grid[0])

    for angle_deg in [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]:
        import math
        tan_theta = math.tan(math.radians(angle_deg))
        row_sums = [0] * h
        for r in range(h):
            for c in range(w):
                if grid[r][c] > 0:
                    target_r = int(r + c * tan_theta)
                    if 0 <= target_r < h:
                        row_sums[target_r] += 1

        mean_val = sum(row_sums) / float(h)
        variance = sum((x - mean_val) ** 2 for x in row_sums) / float(h)
        if variance > best_variance:
            best_variance = variance
            best_angle = angle_deg

    return best_angle


def preprocess_scanned_image(image: Any) -> tuple[Any, list[str]]:
    """Fast full-page preprocessing using Pillow / numpy (median filter, deskew, contrast).

    If Pillow/numpy are not installed, returns original image with visible flag.
    """
    flags: list[str] = []
    try:
        import numpy as np
        from PIL import Image, ImageFilter, ImageOps

        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(image)
        elif isinstance(image, (bytes, bytearray)):
            import io
            pil_img = Image.open(io.BytesIO(image))
        elif hasattr(image, "convert"):
            pil_img = image
        else:
            return image, ["PREPROCESSING_UNSUPPORTED_TYPE"]

        # 1. Median filter (3x3)
        denoised = pil_img.filter(ImageFilter.MedianFilter(size=3))

        # 2. Deskew estimation via row projection variance on thumbnail
        grayscale = denoised.convert("L")
        thumb = grayscale.copy()
        thumb.thumbnail((1000, 1000))
        pixels = np.asarray(thumb)

        best_angle = 0.0
        if np.any(pixels < 180):
            angles = np.linspace(-5.0, 5.0, 11)
            best_score = -1.0
            for angle in angles:
                rotated = thumb.rotate(float(angle), resample=Image.Resampling.NEAREST, fillcolor=255)
                row_ink = np.count_nonzero(np.asarray(rotated) < 180, axis=1)
                score = float(np.var(row_ink))
                if score > best_score:
                    best_score = score
                    best_angle = float(angle)

        deskewed = denoised.rotate(
            best_angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=(255, 255, 255) if denoised.mode in ("RGB", "RGBA") else 255,
        )

        # 3. Contrast enhancement
        contrasted = ImageOps.autocontrast(deskewed.convert("L"))
        result = np.asarray(contrasted.convert("RGB"))
        flags.append("PREPROCESSED_DENOISE_DESKEW_CONTRAST")
        return result, flags
    except ImportError:
        flags.append("PREPROCESSING_SKIPPED_NO_PILLOW")
        return image, flags
    except Exception as exc:  # noqa: BLE001
        logger.warning("Preprocessing encountered issue: %s", exc)
        flags.append("PREPROCESSING_ERROR")
        return image, flags


class PaddleOCREngine:
    """PaddleOCR adapter handling 2.x and 3.x structures."""

    def __init__(self) -> None:
        self.available = False
        self._engine: Any = None
        self._init_error: str | None = None
        try:
            import os
            os.environ.setdefault("FLAGS_use_mkldnn", "0")
            import paddle
            paddle.set_flags({"FLAGS_use_mkldnn": False, "FLAGS_enable_pir_api": False})
            from paddleocr import PaddleOCR
            try:
                self._engine = PaddleOCR(
                    lang="en",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                    enable_mkldnn=False,
                    enable_hpi=False,
                )
            except TypeError:
                self._engine = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    show_log=False,
                    enable_mkldnn=False,
                    ir_optim=False,
                )
            self.available = True
        except Exception as exc:  # noqa: BLE001
            self._init_error = str(exc)
            self.available = False

    def extract(self, image: Any) -> list[dict[str, Any]]:
        if not self.available or self._engine is None:
            raise RuntimeError(f"PaddleOCR is unavailable: {self._init_error}")
        try:
            result = (
                self._engine.predict(image)
                if hasattr(self._engine, "predict")
                else self._engine.ocr(image, cls=True)
            )
        except Exception as exc:
            raise RuntimeError(f"PaddleOCR extraction failed: {exc}") from exc

        blocks: list[dict[str, Any]] = []
        for item in result or []:
            data = item.json if hasattr(item, "json") else item
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:  # noqa: BLE001
                    data = {}
            if isinstance(data, dict) and "res" in data:
                data = data["res"]
            texts = data.get("rec_texts", []) if isinstance(data, dict) else []
            scores = data.get("rec_scores", []) if isinstance(data, dict) else []
            boxes = data.get("rec_boxes", []) if isinstance(data, dict) else []
            if texts:
                for index, text in enumerate(texts):
                    score = float(scores[index]) if index < len(scores) else 1.0
                    if score >= 0.4:
                        box = boxes[index] if index < len(boxes) else [0, 0, 0, 0]
                        box = box.tolist() if hasattr(box, "tolist") else list(box)
                        x0 = box[0] if len(box) > 0 else 0
                        y0 = box[1] if len(box) > 1 else 0
                        blocks.append({"text": str(text), "score": score, "box": box, "x": x0, "y": y0})
                continue

            for line in item or []:
                if not line or len(line) < 2:
                    continue
                box, value = line
                text, score = value
                if float(score) < 0.4:
                    continue
                if isinstance(box, (list, tuple)) and box and isinstance(box[0], (list, tuple)):
                    x0 = min(point[0] for point in box)
                    y0 = min(point[1] for point in box)
                else:
                    x0, y0 = 0, 0
                blocks.append({"text": str(text), "score": float(score), "box": box, "x": x0, "y": y0})

        return _reading_order(blocks)


class EasyOCREngine:
    """EasyOCR adapter."""

    def __init__(self) -> None:
        self.available = False
        self._engine: Any = None
        self._init_error: str | None = None
        try:
            from importlib import import_module
            easyocr = import_module("easyocr")
            self._engine = easyocr.Reader(["en"], gpu=False)
            self.available = True
        except Exception as exc:  # noqa: BLE001
            self._init_error = str(exc)
            self.available = False

    def extract(self, image: Any) -> list[dict[str, Any]]:
        if not self.available or self._engine is None:
            raise RuntimeError(f"EasyOCR is unavailable: {self._init_error}")
        try:
            results = self._engine.readtext(image, detail=1)
        except Exception as exc:
            raise RuntimeError(f"EasyOCR extraction failed: {exc}") from exc

        blocks: list[dict[str, Any]] = []
        for box, text, score in results:
            confidence = float(score)
            if confidence < 0.4:
                continue
            if isinstance(box, (list, tuple)) and box and isinstance(box[0], (list, tuple)):
                x0 = min(point[0] for point in box)
                y0 = min(point[1] for point in box)
            else:
                x0, y0 = 0, 0
            blocks.append({
                "text": str(text),
                "score": confidence,
                "box": box,
                "x": x0,
                "y": y0,
            })
        return _reading_order(blocks)


class PaddleOCRProvider:
    """PaddleOCR provider with rasterization, reading order, and graceful fallback."""

    def __init__(self, engine: PaddleOCREngine | None = None, fallback_engine: OCRProvider | None = None):
        self.engine = engine or PaddleOCREngine()
        self.fallback = fallback_engine

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

        filetype = _detect_filetype(file_bytes, filename, content_type)
        try:
            doc = fitz.open(stream=file_bytes, filetype=filetype)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not open stream: %s. Falling back to FakeOCRProvider.", exc)
            return FakeOCRProvider().extract_document(file_bytes, filename, content_type)

        pages_out: list[OCRPageResult] = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            width = rect.width or 1.0
            height = rect.height or 1.0

            words = page.get_text("words")
            lines_out: list[OCRLine] = []

            if words:
                blocks = page.get_text("blocks")
                for b in blocks:
                    if len(b) >= 5 and b[4].strip():
                        x0, y0, x1, y1, text_content = b[0], b[1], b[2], b[3], b[4]
                        norm_bbox = _normalize_bbox([x0, y0, x1, y1], width, height)
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
            else:
                pix = page.get_pixmap(dpi=300)
                if self.engine.available:
                    try:
                        import numpy as np
                        img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    except ImportError:
                        img_arr = pix.samples

                    prep_img, prep_flags = preprocess_scanned_image(img_arr)
                    try:
                        blocks = self.engine.extract(prep_img)
                        for blk in blocks:
                            score = float(blk.get("score", 1.0))
                            lines_out.append(
                                OCRLine(
                                    page=page_idx + 1,
                                    raw_text=str(blk.get("text", "")).strip(),
                                    bbox=_normalize_bbox(blk.get("box"), pix.width, pix.height),
                                    ocr_engine="paddleocr",
                                    raster_dpi=300,
                                    ocr_conf=round(score, 4),
                                    flags=["SCANNED_RASTER_300DPI"] + prep_flags + (["LOW_OCR_CONFIDENCE"] if score < 0.70 else []),
                                )
                            )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("PaddleOCR runtime error: %s", exc)
                        if self.fallback:
                            fb_doc = self.fallback.extract_document(file_bytes, filename, content_type)
                            if page_idx < len(fb_doc.pages):
                                lines_out.extend(fb_doc.pages[page_idx].lines)
                else:
                    if self.fallback:
                        fb_doc = self.fallback.extract_document(file_bytes, filename, content_type)
                        if page_idx < len(fb_doc.pages):
                            lines_out.extend(fb_doc.pages[page_idx].lines)
                    else:
                        lines_out.append(
                            OCRLine(
                                page=page_idx + 1,
                                raw_text=f"[SCANNED_RASTER_PAGE_{page_idx + 1}_PADDLEOCR_UNAVAILABLE]",
                                bbox=[0.05, 0.05, 0.95, 0.95],
                                ocr_engine="paddleocr_unavailable",
                                raster_dpi=300,
                                ocr_conf=0.000,
                                flags=["SCANNED_RASTER_300DPI", "LOW_OCR_CONFIDENCE", "ML_MODEL_UNAVAILABLE", "OCR_PROVIDER_UNAVAILABLE"],
                            )
                        )

            conf = sum(l.ocr_conf for l in lines_out) / len(lines_out) if lines_out else 0.0
            pages_out.append(OCRPageResult(page_number=page_idx + 1, lines=lines_out, mean_confidence=conf))

        doc.close()
        return OCRDocumentResult(file_hash=file_hash, pages=pages_out, doc_type_hint=None)


class EasyOCRProvider:
    """EasyOCR provider with rasterization, reading order, and graceful fallback."""

    def __init__(self, engine: EasyOCREngine | None = None, fallback_engine: OCRProvider | None = None):
        self.engine = engine or EasyOCREngine()
        self.fallback = fallback_engine

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

        filetype = _detect_filetype(file_bytes, filename, content_type)
        try:
            doc = fitz.open(stream=file_bytes, filetype=filetype)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not open stream: %s. Falling back to FakeOCRProvider.", exc)
            return FakeOCRProvider().extract_document(file_bytes, filename, content_type)

        pages_out: list[OCRPageResult] = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            width = rect.width or 1.0
            height = rect.height or 1.0

            words = page.get_text("words")
            lines_out: list[OCRLine] = []

            if words:
                blocks = page.get_text("blocks")
                for b in blocks:
                    if len(b) >= 5 and b[4].strip():
                        x0, y0, x1, y1, text_content = b[0], b[1], b[2], b[3], b[4]
                        norm_bbox = _normalize_bbox([x0, y0, x1, y1], width, height)
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
            else:
                pix = page.get_pixmap(dpi=300)
                if self.engine.available:
                    try:
                        import numpy as np
                        img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    except ImportError:
                        img_arr = pix.samples

                    prep_img, prep_flags = preprocess_scanned_image(img_arr)
                    try:
                        blocks = self.engine.extract(prep_img)
                        for blk in blocks:
                            score = float(blk.get("score", 1.0))
                            lines_out.append(
                                OCRLine(
                                    page=page_idx + 1,
                                    raw_text=str(blk.get("text", "")).strip(),
                                    bbox=_normalize_bbox(blk.get("box"), pix.width, pix.height),
                                    ocr_engine="easyocr",
                                    raster_dpi=300,
                                    ocr_conf=round(score, 4),
                                    flags=["SCANNED_RASTER_300DPI"] + prep_flags + (["LOW_OCR_CONFIDENCE"] if score < 0.70 else []),
                                )
                            )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("EasyOCR runtime error: %s", exc)
                        if self.fallback:
                            fb_doc = self.fallback.extract_document(file_bytes, filename, content_type)
                            if page_idx < len(fb_doc.pages):
                                lines_out.extend(fb_doc.pages[page_idx].lines)
                else:
                    if self.fallback:
                        fb_doc = self.fallback.extract_document(file_bytes, filename, content_type)
                        if page_idx < len(fb_doc.pages):
                            lines_out.extend(fb_doc.pages[page_idx].lines)
                    else:
                        lines_out.append(
                            OCRLine(
                                page=page_idx + 1,
                                raw_text=f"[SCANNED_RASTER_PAGE_{page_idx + 1}_EASYOCR_UNAVAILABLE]",
                                bbox=[0.05, 0.05, 0.95, 0.95],
                                ocr_engine="easyocr_unavailable",
                                raster_dpi=300,
                                ocr_conf=0.000,
                                flags=["SCANNED_RASTER_300DPI", "LOW_OCR_CONFIDENCE", "ML_MODEL_UNAVAILABLE", "OCR_PROVIDER_UNAVAILABLE"],
                            )
                        )

            conf = sum(l.ocr_conf for l in lines_out) / len(lines_out) if lines_out else 0.0
            pages_out.append(OCRPageResult(page_number=page_idx + 1, lines=lines_out, mean_confidence=conf))

        doc.close()
        return OCRDocumentResult(file_hash=file_hash, pages=pages_out, doc_type_hint=None)


class HybridOCRProvider:
    """Hybrid OCR provider with per-page PaddleOCR primary and EasyOCR fallback."""

    def __init__(
        self,
        paddle_engine: PaddleOCREngine | None = None,
        easy_engine: EasyOCREngine | None = None,
        fallback_engine: OCRProvider | None = None,
    ):
        self.paddle_engine = paddle_engine or PaddleOCREngine()
        self.easy_engine = easy_engine or EasyOCREngine()
        self.fallback = fallback_engine

    def extract_document(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> OCRDocumentResult:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        if not fitz:
            return FakeOCRProvider().extract_document(file_bytes, filename, content_type)

        filetype = _detect_filetype(file_bytes, filename, content_type)
        try:
            doc = fitz.open(stream=file_bytes, filetype=filetype)
        except Exception:  # noqa: BLE001
            return FakeOCRProvider().extract_document(file_bytes, filename, content_type)

        pages_out: list[OCRPageResult] = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            width = rect.width or 1.0
            height = rect.height or 1.0

            words = page.get_text("words")
            lines_out: list[OCRLine] = []

            if words:
                blocks = page.get_text("blocks")
                for b in blocks:
                    if len(b) >= 5 and b[4].strip():
                        x0, y0, x1, y1, text_content = b[0], b[1], b[2], b[3], b[4]
                        norm_bbox = _normalize_bbox([x0, y0, x1, y1], width, height)
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
            else:
                pix = page.get_pixmap(dpi=300)
                try:
                    import numpy as np
                    img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                except ImportError:
                    img_arr = pix.samples

                prep_img, prep_flags = preprocess_scanned_image(img_arr)
                page_extracted = False

                # 1. Try PaddleOCR primary
                if self.paddle_engine.available:
                    try:
                        blocks = self.paddle_engine.extract(prep_img)
                        if blocks:
                            for blk in blocks:
                                score = float(blk.get("score", 1.0))
                                lines_out.append(
                                    OCRLine(
                                        page=page_idx + 1,
                                        raw_text=str(blk.get("text", "")).strip(),
                                        bbox=_normalize_bbox(blk.get("box"), pix.width, pix.height),
                                        ocr_engine="paddleocr",
                                        raster_dpi=300,
                                        ocr_conf=round(score, 4),
                                        flags=["SCANNED_RASTER_300DPI"] + prep_flags + (["LOW_OCR_CONFIDENCE"] if score < 0.70 else []),
                                    )
                                )
                            page_extracted = True
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("PaddleOCR failed on page %d: %s. Falling back to EasyOCR.", page_idx + 1, exc)

                # 2. Try EasyOCR fallback on page
                if not page_extracted and self.easy_engine.available:
                    try:
                        blocks = self.easy_engine.extract(prep_img)
                        if blocks:
                            for blk in blocks:
                                score = float(blk.get("score", 1.0))
                                lines_out.append(
                                    OCRLine(
                                        page=page_idx + 1,
                                        raw_text=str(blk.get("text", "")).strip(),
                                        bbox=_normalize_bbox(blk.get("box"), pix.width, pix.height),
                                        ocr_engine="easyocr",
                                        raster_dpi=300,
                                        ocr_conf=round(score, 4),
                                        flags=["SCANNED_RASTER_300DPI"] + prep_flags + (["LOW_OCR_CONFIDENCE"] if score < 0.70 else []),
                                    )
                                )
                            page_extracted = True
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("EasyOCR fallback failed on page %d: %s", page_idx + 1, exc)

                # 3. Graceful fallback if neither engine worked
                if not page_extracted:
                    if self.fallback:
                        fb_doc = self.fallback.extract_document(file_bytes, filename, content_type)
                        if page_idx < len(fb_doc.pages):
                            lines_out.extend(fb_doc.pages[page_idx].lines)
                    else:
                        lines_out.append(
                            OCRLine(
                                page=page_idx + 1,
                                raw_text=f"[SCANNED_RASTER_PAGE_{page_idx + 1}_ML_UNAVAILABLE]",
                                bbox=[0.05, 0.05, 0.95, 0.95],
                                ocr_engine="hybrid_ocr_unavailable",
                                raster_dpi=300,
                                ocr_conf=0.000,
                                flags=["SCANNED_RASTER_300DPI", "LOW_OCR_CONFIDENCE", "ML_MODEL_UNAVAILABLE", "OCR_PROVIDER_UNAVAILABLE"],
                            )
                        )

            conf = sum(l.ocr_conf for l in lines_out) / len(lines_out) if lines_out else 0.0
            pages_out.append(OCRPageResult(page_number=page_idx + 1, lines=lines_out, mean_confidence=conf))

        doc.close()
        return OCRDocumentResult(file_hash=file_hash, pages=pages_out, doc_type_hint=None)


class PyMuPDFProvider:
    """PDF text layer extractor using PyMuPDF (fitz).

    Extracts digital text and layout coordinates directly from PDF streams.
    When a page has no digital text layer (scanned page) or is an image (PNG, JPEG, TIFF),
    it rasterizes the page at 300 DPI, flags SCANNED_RASTER_300DPI, and calibrates confidence
    to enforce Section 10.1 confidence gating without inventing arbitrary high constants.
    """

    def __init__(self, ocr_delegate: OCRProvider | None = None):
        self.ocr_delegate = ocr_delegate

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

        filetype = _detect_filetype(file_bytes, filename, content_type)
        try:
            doc = fitz.open(stream=file_bytes, filetype=filetype)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not open %s with PyMuPDF: %s. Falling back to FakeOCRProvider.", filetype, exc)
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

            if not lines_out:
                # Scanned image or raster page without text layer:
                # Rasterize at 300 DPI per Section 10.1
                pix = page.get_pixmap(dpi=300)
                if self.ocr_delegate:
                    del_doc = self.ocr_delegate.extract_document(file_bytes, filename, content_type)
                    if page_idx < len(del_doc.pages):
                        lines_out = del_doc.pages[page_idx].lines
                        conf = del_doc.pages[page_idx].mean_confidence
                    else:
                        conf = 0.0
                else:
                    ocr_text = ""
                    try:
                        ocr_text = page.get_text("text")
                    except Exception:  # noqa: BLE001
                        ocr_text = ""

                    raw_text_val = (
                        ocr_text.strip()
                        if ocr_text.strip()
                        else f"[SCANNED_RASTER_PAGE_{page_idx + 1}_{pix.width}X{pix.height}]"
                    )
                    lines_out.append(
                        OCRLine(
                            page=page_idx + 1,
                            raw_text=raw_text_val,
                            bbox=[0.05, 0.05, 0.95, 0.95],
                            ocr_engine="pymupdf_raster",
                            raster_dpi=300,
                            ocr_conf=0.000,
                            flags=["SCANNED_RASTER_300DPI", "LOW_OCR_CONFIDENCE", "NO_DIGITAL_TEXT_LAYER"],
                        )
                    )
                    conf = 0.000
            else:
                conf = sum(l.ocr_conf for l in lines_out) / len(lines_out)

            pages_out.append(OCRPageResult(page_number=page_idx + 1, lines=lines_out, mean_confidence=conf))

        doc.close()
        return OCRDocumentResult(file_hash=file_hash, pages=pages_out, doc_type_hint=None)


class LocalNeuralOCRProvider:
    """Local Tesseract OCR engine with 300 DPI rasterization and real word/line confidence parsing."""

    def __init__(self, fallback_engine: OCRProvider | None = None):
        self.fallback = fallback_engine or PyMuPDFProvider()

    def extract_document(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> OCRDocumentResult:
        import shutil
        import subprocess

        tess_bin = shutil.which("tesseract")
        if tess_bin:
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir) / (filename or "document.pdf")
                tmp_path.write_bytes(file_bytes)
                try:
                    # Request TSV output for genuine per-word/line confidence measurements
                    res = subprocess.run(
                        [tess_bin, str(tmp_path), "stdout", "--dpi", "300", "tsv"],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        check=False,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        file_hash = hashlib.sha256(file_bytes).hexdigest()
                        lines_by_key: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
                        tsv_lines = res.stdout.splitlines()
                        for row in tsv_lines[1:]:
                            parts = row.split("\t")
                            if len(parts) >= 12:
                                _level, page_num, block_num, _par_num, line_num, _word_num = parts[:6]
                                left, top, width, height, conf_str, text_val = parts[6:12]
                                if text_val.strip() and float(conf_str) >= 0:
                                    key = (int(page_num), int(block_num), int(line_num))
                                    lines_by_key.setdefault(key, []).append({
                                        "text": text_val.strip(),
                                        "conf": float(conf_str) / 100.0,
                                        "left": float(left),
                                        "top": float(top),
                                        "right": float(left) + float(width),
                                        "bottom": float(top) + float(height),
                                    })

                        if lines_by_key:
                            ocr_lines: list[OCRLine] = []
                            for (p_num, _, _), words in lines_by_key.items():
                                line_text = " ".join(w["text"] for w in words)
                                line_conf = sum(w["conf"] for w in words) / len(words)
                                ocr_lines.append(
                                    OCRLine(
                                        page=p_num,
                                        raw_text=line_text,
                                        bbox=[0.05, 0.05, 0.95, 0.95],
                                        ocr_engine="tesseract_tsv",
                                        raster_dpi=300,
                                        ocr_conf=round(line_conf, 4),
                                        flags=["LOW_OCR_CONFIDENCE"] if line_conf < 0.70 else [],
                                    )
                                )
                            mean_c = sum(l.ocr_conf for l in ocr_lines) / len(ocr_lines) if ocr_lines else 0.0
                            return OCRDocumentResult(
                                file_hash=file_hash,
                                pages=[OCRPageResult(page_number=1, lines=ocr_lines, mean_confidence=mean_c)],
                                doc_type_hint=None,
                            )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Local tesseract execution encountered issue: %s. Falling back.", exc)

        return self.fallback.extract_document(file_bytes, filename, content_type)


def get_ocr_provider(provider_name: str | None = None) -> OCRProvider:
    """Returns the configured OCR provider instance."""
    settings = get_settings()
    name = (provider_name or settings.ocr_provider).lower()
    if name == "paddleocr":
        return PaddleOCRProvider()
    if name == "easyocr":
        return EasyOCRProvider()
    if name in ("hybrid", "fallback"):
        return HybridOCRProvider()
    if name in ("tesseract", "neural"):
        return LocalNeuralOCRProvider()
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
