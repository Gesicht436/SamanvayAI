"""Test suite for Document intake, OCR pipeline, and pre-procurement check.

Enforces Section 10.0, 10.1:
- OCRProvider protocol (FakeOCRProvider and PyMuPDFProvider).
- Safety Invariant S5: Low-confidence OCR on HARD attributes becomes None with flag LOW_OCR_CONFIDENCE.
- Safety Invariant S10: A duplicate document warns or blocks; it never merges silently.
- Pre-procurement check: tests existing golden masters without creating entities.
- Endpoints: POST /docs, POST /docs/paste, GET /docs/{id}, GET /docs/{id}/lines, POST /docs/precheck.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.entities import Document
from api.security.jwt_auth import create_access_token
from api.services.docs import check_document_duplicate, normalize_invoice_key
from api.services.ocr import (
    FakeOCRProvider,
    enforce_ocr_confidence_on_attributes,
)

client = TestClient(app)


def test_normalize_invoice_key():
    """Verify invoice_key normalization."""
    k = normalize_invoice_key("27AAACB2026M1Z1", "INV-2026/089", "2026-10-01")
    assert k == "27AAACB2026M1Z1|INV-2026/089|2026-10-01"

    # None if missing any component
    assert normalize_invoice_key(None, "INV-1", "2026-10-01") is None
    assert normalize_invoice_key("GSTIN", None, "2026-10-01") is None
    assert normalize_invoice_key("GSTIN", "INV-1", None) is None


def test_fake_ocr_provider_text_and_json():
    """Verify FakeOCRProvider deterministic parsing."""
    provider = FakeOCRProvider(default_conf=0.95)

    # 1. Plain text extraction
    text_bytes = b"VALVE GATE 100 NB CL150 WCB\nFLANGED RF API 600"
    res = provider.extract_document(text_bytes)
    assert len(res.pages) == 1
    assert len(res.pages[0].lines) == 2
    assert res.pages[0].lines[0].raw_text == "VALVE GATE 100 NB CL150 WCB"
    assert res.pages[0].lines[0].ocr_conf == 0.95

    # 2. Sidecar JSON extraction
    json_bytes = b'{"doc_type": "PO_GRN", "lines": [{"raw_text": "PUMP CENTRIFUGAL 50 M3/HR", "ocr_conf": 0.99}]}'
    res_json = provider.extract_document(json_bytes)
    assert res_json.doc_type_hint == "PO_GRN"
    assert len(res_json.pages[0].lines) == 1
    assert res_json.pages[0].lines[0].ocr_conf == 0.99


def test_invariant_s5_low_ocr_confidence_on_hard_attributes():
    """Invariant S5: Low-confidence OCR on HARD attributes becomes None with LOW_OCR_CONFIDENCE."""
    attribute_specs = {
        "size_nb": "HARD",
        "pressure_class": "HARD",
        "body_material": "HARD",
        "description_notes": "SOFT",
    }
    extracted_attrs = {
        "size_nb": {"value": 100, "confidence": 0.95},
        "pressure_class": {"value": "ASME_150", "confidence": 0.90},
        "body_material": "A216_WCB",
        "description_notes": "Urgent site delivery",
    }

    # Case A: High confidence (0.92 >= 0.70 threshold) -> preserved
    sanitized_high, flags_high = enforce_ocr_confidence_on_attributes(
        extracted_attrs=extracted_attrs,
        attribute_specs=attribute_specs,
        ocr_conf=0.92,
        threshold=0.70,
    )
    assert sanitized_high["size_nb"]["value"] == 100
    assert sanitized_high["body_material"] == "A216_WCB"
    assert "LOW_OCR_CONFIDENCE" not in flags_high

    # Case B: Low confidence (0.55 < 0.70 threshold) -> HARD values become None with flag
    sanitized_low, flags_low = enforce_ocr_confidence_on_attributes(
        extracted_attrs=extracted_attrs,
        attribute_specs=attribute_specs,
        ocr_conf=0.55,
        threshold=0.70,
    )
    assert sanitized_low["size_nb"]["value"] is None
    assert "LOW_OCR_CONFIDENCE" in sanitized_low["size_nb"]["flags"]
    assert sanitized_low["pressure_class"]["value"] is None
    assert sanitized_low["body_material"] is None
    # SOFT attributes remain intact
    assert sanitized_low["description_notes"] == "Urgent site delivery"
    assert "LOW_OCR_CONFIDENCE" in flags_low


@pytest.mark.asyncio
async def test_invariant_s10_duplicate_document_blocks_or_warns(db_session):
    """Invariant S10: A duplicate document warns or blocks; it never merges silently."""
    org_id = "OIL-1"

    # Insert an existing document
    existing_doc = Document(
        org_id=org_id,
        doc_type="INVOICE",
        capture_channel="UPLOAD",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_path="./data/storage/dummy",
        pages=1,
        vendor_gstin="27AAACB2026M1Z1",
        invoice_no="INV-2026-001",
        invoice_key="27AAACB2026M1Z1|INV-2026-001|2026-10-01",
        status="PARSED",
    )
    db_session.add(existing_doc)
    await db_session.flush()

    # 1. Exact file_hash duplicate
    is_dup_hash, doc_dup, reason_hash = await check_document_duplicate(
        db_session, org_id, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", None
    )
    assert is_dup_hash is True
    assert doc_dup.id == existing_doc.id
    assert "Identical file hash" in reason_hash

    # 2. Duplicate invoice_key with different file_hash
    is_dup_inv, doc_inv, reason_inv = await check_document_duplicate(
        db_session, org_id, "different_hash_123456", "27AAACB2026M1Z1|INV-2026-001|2026-10-01"
    )
    assert is_dup_inv is True
    assert doc_inv.id == existing_doc.id
    assert "Duplicate invoice key" in reason_inv

    # 3. Clean non-duplicate
    is_dup_clean, _, _ = await check_document_duplicate(
        db_session, org_id, "fresh_unique_hash_999", "27AAACB2026M1Z1|INV-2026-999|2026-10-01"
    )
    assert is_dup_clean is False


def test_docs_api_upload_and_duplicate_block():
    """Verify POST /docs blocks duplicates under S10 with 409 Conflict."""
    token = create_access_token("user-s10", "OIL-1", "MAKER")
    headers = {"Authorization": f"Bearer {token}"}

    import uuid

    suffix = uuid.uuid4().hex[:8]
    file_content = f"PO 4500019283 - LINE 1: GATE VALVE 100NB CL150 {suffix}".encode()
    inv_no = f"PO-{suffix}"

    # First upload succeeds
    resp1 = client.post(
        "/docs",
        data={
            "doc_type": "PO_GRN",
            "capture_channel": "UPLOAD",
            "vendor_gstin": "07AAACB2026P1Z1",
            "invoice_no": inv_no,
            "invoice_date": "2026-10-10",
        },
        files={"file": ("po.txt", file_content, "text/plain")},
        headers=headers,
    )
    assert resp1.status_code == 200
    doc_data = resp1.json()
    assert doc_data["status"] == "PARSED"
    doc_id = doc_data["id"]

    # Retrieve lines
    resp_lines = client.get(f"/docs/{doc_id}/lines", headers=headers)
    assert resp_lines.status_code == 200
    lines_data = resp_lines.json()
    assert len(lines_data["lines"]) >= 1

    # Second identical upload must FAIL with 409 Conflict (S10)
    resp2 = client.post(
        "/docs",
        data={
            "doc_type": "PO_GRN",
            "capture_channel": "UPLOAD",
            "vendor_gstin": "07AAACB2026P1Z1",
            "invoice_no": inv_no,
            "invoice_date": "2026-10-10",
        },
        files={"file": ("po.txt", file_content, "text/plain")},
        headers=headers,
    )
    assert resp2.status_code == 409
    err = resp2.json()["detail"]
    assert err["code"] == "DUPLICATE_DOCUMENT"
    assert "never merge silently" in err["message"]


def test_docs_paste_channel():
    """Verify POST /docs/paste tags lines with PASTED_TEXT."""
    token = create_access_token("user-paste", "STEEL-1", "MAKER")
    headers = {"Authorization": f"Bearer {token}"}

    import uuid

    suffix = uuid.uuid4().hex[:8]

    resp = client.post(
        "/docs/paste",
        json={
            "pasted_text": f"BALL VALVE 50 NB CL300 A105 FLG RF\nMOTOR 55KW 4P B3 {suffix}",
            "doc_type": "INVOICE",
            "vendor_gstin": "24AAACB2026L1Z1",
            "invoice_no": f"INV-PASTE-{suffix}",
            "invoice_date": "2026-10-11",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capture_channel"] == "PASTE"
    assert data["status"] == "PARSED"

    # Verify lines
    lines_resp = client.get(f"/docs/{data['id']}/lines", headers=headers)
    assert lines_resp.status_code == 200
    lines = lines_resp.json()["lines"]
    assert len(lines) == 2
    assert lines[0]["ocr_engine"] == "pasted_text"


def test_precheck_endpoint():
    """Verify POST /docs/precheck returns candidate matches without persisting items."""
    token = create_access_token("user-precheck", "POWER-1", "PROCUREMENT")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/docs/precheck",
        json={
            "description": "VLV GT 100 NB CL150 WCB FLG RF API600",
            "category_hint": "VALVES.GATE",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subcategory"] == "VALVES.GATE"
    assert "extracted" in data
    assert "candidates" in data


def test_docs_promote_line_endpoint():
    """Verify POST /docs/{id}/lines/{line_id}/promote creates raw_item with audit log."""
    import uuid

    token = create_access_token("user-promote", "OIL-1", "MAKER")
    headers = {"Authorization": f"Bearer {token}"}

    suffix = uuid.uuid4().hex[:8]

    # Ingest paste document with a line item
    doc_resp = client.post(
        "/docs/paste",
        json={
            "pasted_text": f"GATE VALVE 100 NB CL150 WCB RF {suffix}",
            "doc_type": "PO_GRN",
            "invoice_no": f"PO-PROMOTE-{suffix}",
            "invoice_date": "2026-10-11",
        },
        headers=headers,
    )
    assert doc_resp.status_code == 200
    doc_id = doc_resp.json()["id"]

    # Get line
    lines_resp = client.get(f"/docs/{doc_id}/lines", headers=headers)
    assert lines_resp.status_code == 200
    line_id = lines_resp.json()["lines"][0]["line_id"]

    # Promote line
    promote_resp = client.post(f"/docs/{doc_id}/lines/{line_id}/promote", headers=headers)
    assert promote_resp.status_code == 200
    promote_data = promote_resp.json()
    assert promote_data["status"] == "PROMOTED"
    assert promote_data["raw_item_id"]
    assert promote_data["subcategory"] == "VALVES.GATE"


def test_pymupdf_scanned_page_300dpi_rasterization():
    """Verify Section 10.1: scanned pages without text layer rasterize at 300 DPI and flag SCANNED_RASTER_300DPI."""
    import pymupdf as fitz

    from api.services.ocr import PyMuPDFProvider

    # Create empty PDF page without digital text layer (simulating a pure scan)
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    provider = PyMuPDFProvider()
    res = provider.extract_document(pdf_bytes, filename="scanned_test.pdf")

    assert len(res.pages) == 1
    page = res.pages[0]
    assert len(page.lines) == 1
    line = page.lines[0]
    assert line.ocr_engine == "pymupdf_raster"
    assert line.raster_dpi == 300
    assert "SCANNED_RASTER_300DPI" in line.flags
    assert "LOW_OCR_CONFIDENCE" in line.flags
    assert page.mean_confidence < 0.85  # Gated to Tier 2 / review


def test_median_filter_and_deskew():
    """Verify Section 10.1 3x3 median filtering and row-projection deskew estimation."""
    from api.services.ocr import (
        apply_median_filter_3x3,
        estimate_row_projection_deskew_angle,
        get_ocr_provider,
    )

    # 1. Median filter removes isolated speckle noise
    grid = [
        [0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],  # Single noise pixel at (1, 2)
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    filtered = apply_median_filter_3x3(grid)
    assert filtered[1][2] == 0  # Denoised to 0

    # 2. Deskew angle on horizontal row projection
    h_grid = [[1 if r in (2, 5, 8) else 0 for _ in range(20)] for r in range(12)]
    angle = estimate_row_projection_deskew_angle(h_grid)
    assert abs(angle) <= 1.0

    # 3. Provider factory
    neural_prov = get_ocr_provider("neural")
    assert neural_prov is not None


def test_ocr_provider_factory_distinct_providers():
    """Verify provider names mean what they say and do not alias tesseract."""
    from api.services.ocr import (
        EasyOCRProvider,
        FakeOCRProvider,
        HybridOCRProvider,
        LocalNeuralOCRProvider,
        PaddleOCRProvider,
        PyMuPDFProvider,
        get_ocr_provider,
    )

    paddle_p = get_ocr_provider("paddleocr")
    assert isinstance(paddle_p, PaddleOCRProvider)

    easy_p = get_ocr_provider("easyocr")
    assert isinstance(easy_p, EasyOCRProvider)

    hybrid_p = get_ocr_provider("hybrid")
    assert isinstance(hybrid_p, HybridOCRProvider)

    tess_p = get_ocr_provider("tesseract")
    assert isinstance(tess_p, LocalNeuralOCRProvider)

    pymupdf_p = get_ocr_provider("pymupdf")
    assert isinstance(pymupdf_p, PyMuPDFProvider)

    fake_p = get_ocr_provider("fake")
    assert isinstance(fake_p, FakeOCRProvider)


def test_paddleocr_provider_mock_replay_and_reading_order():
    """Verify PaddleOCRProvider with mocked engine produces real scores and reading-order."""
    from unittest.mock import MagicMock

    import pymupdf as fitz

    from api.services.ocr import PaddleOCREngine, PaddleOCRProvider

    mock_engine = MagicMock(spec=PaddleOCREngine)
    mock_engine.available = True
    # Row 2 (y=150) and Row 1 (y=50) out of order; reading order sorts Row 1 then Row 2
    mock_engine.extract.return_value = [
        {"text": "VALVE GATE 100 NB", "score": 0.965, "box": [[10, 50], [200, 50], [200, 80], [10, 80]], "x": 10, "y": 50},
        {"text": "CL150 WCB", "score": 0.942, "box": [[220, 50], [350, 50], [350, 80], [220, 80]], "x": 220, "y": 50},
        {"text": "HEAT NO: H12345", "score": 0.988, "box": [[10, 150], [250, 150], [250, 180], [10, 180]], "x": 10, "y": 150},
    ]

    doc = fitz.open()
    doc.new_page()  # Blank scanned raster page
    pdf_bytes = doc.tobytes()
    doc.close()

    provider = PaddleOCRProvider(engine=mock_engine)
    res = provider.extract_document(pdf_bytes, filename="test_scan.pdf")

    assert len(res.pages) == 1
    page = res.pages[0]
    assert len(page.lines) == 3
    assert page.lines[0].raw_text == "VALVE GATE 100 NB"
    assert page.lines[0].ocr_conf == 0.965
    assert page.lines[0].ocr_engine == "paddleocr"
    assert page.lines[0].raster_dpi == 300
    assert page.lines[1].raw_text == "CL150 WCB"
    assert page.lines[1].ocr_conf == 0.942
    assert page.lines[2].raw_text == "HEAT NO: H12345"
    assert page.lines[2].ocr_conf == 0.988
    assert abs(page.mean_confidence - ((0.965 + 0.942 + 0.988) / 3)) < 1e-4


def test_easyocr_provider_mock_replay():
    """Verify EasyOCRProvider with mocked engine produces real scores and normalized boxes."""
    from unittest.mock import MagicMock

    import pymupdf as fitz

    from api.services.ocr import EasyOCREngine, EasyOCRProvider

    mock_engine = MagicMock(spec=EasyOCREngine)
    mock_engine.available = True
    mock_engine.extract.return_value = [
        {"text": "PIPE SEAMLESS 2 INCH", "score": 0.912, "box": [50, 100, 300, 140], "x": 50, "y": 100},
    ]

    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    provider = EasyOCRProvider(engine=mock_engine)
    res = provider.extract_document(pdf_bytes, filename="test_easy.pdf")

    assert len(res.pages) == 1
    page = res.pages[0]
    assert len(page.lines) == 1
    line = page.lines[0]
    assert line.raw_text == "PIPE SEAMLESS 2 INCH"
    assert line.ocr_conf == 0.912
    assert line.ocr_engine == "easyocr"
    assert line.raster_dpi == 300


def test_hybrid_ocr_per_page_fallback():
    """Verify HybridOCRProvider tries PaddleOCR first and falls back to EasyOCR per-page."""
    from unittest.mock import MagicMock

    import pymupdf as fitz

    from api.services.ocr import EasyOCREngine, HybridOCRProvider, PaddleOCREngine

    paddle_mock = MagicMock(spec=PaddleOCREngine)
    paddle_mock.available = True
    # Page 1 succeeds on paddle; page 2 raises error to trigger easyocr fallback
    paddle_mock.extract.side_effect = [
        [{"text": "PAGE 1 FROM PADDLE", "score": 0.95, "box": [10, 10, 100, 30], "x": 10, "y": 10}],
        RuntimeError("PaddleOCR page 2 unreadable"),
    ]

    easy_mock = MagicMock(spec=EasyOCREngine)
    easy_mock.available = True
    easy_mock.extract.return_value = [
        {"text": "PAGE 2 FROM EASYOCR", "score": 0.88, "box": [10, 10, 100, 30], "x": 10, "y": 10}
    ]

    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    provider = HybridOCRProvider(paddle_engine=paddle_mock, easy_engine=easy_mock)
    res = provider.extract_document(pdf_bytes, filename="test_hybrid.pdf")

    assert len(res.pages) == 2
    assert res.pages[0].lines[0].ocr_engine == "paddleocr"
    assert res.pages[0].lines[0].raw_text == "PAGE 1 FROM PADDLE"
    assert res.pages[1].lines[0].ocr_engine == "easyocr"
    assert res.pages[1].lines[0].raw_text == "PAGE 2 FROM EASYOCR"


def test_ocr_graceful_fallback_without_ml_extra():
    """Verify PaddleOCRProvider and EasyOCRProvider fall back with visible flag when ml extra is missing."""
    import pymupdf as fitz

    from api.services.ocr import EasyOCREngine, EasyOCRProvider, PaddleOCREngine, PaddleOCRProvider

    paddle_engine = PaddleOCREngine()
    paddle_engine.available = False  # Simulate absence of paddleocr
    provider_p = PaddleOCRProvider(engine=paddle_engine)

    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    res = provider_p.extract_document(pdf_bytes, filename="scan.pdf")
    assert len(res.pages) == 1
    line = res.pages[0].lines[0]
    assert line.ocr_conf == 0.0
    assert "ML_MODEL_UNAVAILABLE" in line.flags
    assert "LOW_OCR_CONFIDENCE" in line.flags
    assert res.pages[0].mean_confidence == 0.0

    easy_engine = EasyOCREngine()
    easy_engine.available = False
    provider_e = EasyOCRProvider(engine=easy_engine)
    res_e = provider_e.extract_document(pdf_bytes, filename="scan.pdf")
    line_e = res_e.pages[0].lines[0]
    assert line_e.ocr_conf == 0.0
    assert "ML_MODEL_UNAVAILABLE" in line_e.flags


def test_invariant_s5_real_ocr_confidence_gates_to_tier2():
    """Verify S5: Real low OCR confidence from engine blanks HARD attributes and enforces Tier 2."""
    from api.extractors.registry import default_registry
    from api.services.comparator import compare_items
    from api.services.ocr import enforce_ocr_confidence_on_attributes
    from api.services.tiering import Tier, assign_tier

    default_registry.load_packs("packs")

    attr_specs = {
        "size_nb": "HARD",
        "pressure_class": "HARD",
        "body_material": "HARD",
        "end_connection": "HARD",
        "facing": "HARD",
        "design_standard": "HARD",
    }
    extracted = {
        "size_nb": {"value": 100, "confidence": 0.95},
        "pressure_class": {"value": "ASME_150", "confidence": 0.90},
        "body_material": {"value": "A216_WCB", "confidence": 0.85},
        "end_connection": "FLANGED",
        "facing": "RF",
        "design_standard": "API_600",
    }

    # Low OCR confidence measured from engine = 0.52 (< 0.70 threshold)
    sanitized, flags = enforce_ocr_confidence_on_attributes(extracted, attr_specs, ocr_conf=0.52, threshold=0.70)
    assert sanitized["size_nb"]["value"] is None
    assert "LOW_OCR_CONFIDENCE" in flags

    # Run through comparison against golden candidate
    comp_result = compare_items(
        req_attrs=sanitized,
        cand_attrs={
            "size_nb": 100,
            "pressure_class": "ASME_150",
            "body_material": "A216_WCB",
            "end_connection": "FLANGED",
            "facing": "RF",
            "design_standard": "API_600",
        },
        subcategory="VALVES.GATE",
    )
    assert comp_result.has_missing_hard is True
    assert comp_result.has_hard_mismatch is False

    # Tiering must route to Tier 2 (TWO_REVIEW), never Tier 1
    tier_res = assign_tier(
        comparison=comp_result,
        extraction_flags=flags,
        ocr_confidence_low=True,
    )
    assert tier_res.tier == Tier.TWO_REVIEW





