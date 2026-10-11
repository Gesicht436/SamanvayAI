"""Ingestion Service for Tabular Material Masters (CSV & XLSX).

Conforms to specsheet.md Section 4.1:
- CSV/XLSX parsed via per-organisation mapping profiles.
- Store the original row verbatim (raw_payload JSONB), file hash, and row number.
- Never drop a row silently; report errors per row.
- Detect encoding and language per row via Unicode script ranges.
- Idempotent on file hash.
- Integrates text normalization and canonical UoM conversion.
- Transactional audit log integration.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

import openpyxl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.normalize import normalize_text
from api.services.script_detector import detect_scripts
from api.services.uom import convert_to_canonical

# Default column name aliases (normalized to lowercase alphanumeric)
DEFAULT_COLUMN_ALIASES: dict[str, list[str]] = {
    "item_code": [
        "itemcode",
        "materialcode",
        "materialno",
        "materialnumber",
        "itemno",
        "partno",
        "partnumber",
        "code",
        "material",
    ],
    "description": [
        "description",
        "materialdescription",
        "itemdescription",
        "desc",
        "shorttext",
        "itemdesc",
        "matdesc",
    ],
    "long_text": [
        "longtext",
        "potext",
        "specification",
        "spec",
        "specs",
        "extendeddescription",
        "technicalspecs",
    ],
    "uom": [
        "uom",
        "unit",
        "unitofmeasure",
        "baseuom",
        "bun",
        "measureunit",
        "orderunit",
    ],
    "qty": [
        "qty",
        "quantity",
        "stockqty",
        "inventory",
        "stock",
        "currentstock",
        "availableqty",
    ],
    "unit_price": [
        "unitprice",
        "unitpriceinr",
        "price",
        "rate",
        "unitrate",
        "cost",
        "lastpurchaseprice",
    ],
    "plant": [
        "plant",
        "plantcode",
        "location",
        "site",
        "works",
        "warehouse",
    ],
    "last_movement_date": [
        "lastmovementdate",
        "movementdate",
        "lastissuedate",
        "lastreceiptdate",
        "movementdt",
    ],
    "criticality": [
        "criticality",
        "ved",
        "vitalessentialdesirable",
        "abcanalysis",
    ],
    "min_stock": [
        "minstock",
        "safetystock",
        "min",
        "reorderlevel",
        "rol",
    ],
    "max_stock": [
        "maxstock",
        "max",
        "maxlevel",
    ],
    "manufacturer": [
        "manufacturer",
        "mfr",
        "make",
        "oem",
        "brand",
        "vendor",
    ],
    "mpn": [
        "mpn",
        "partnumber",
        "modelnumber",
        "modelno",
        "oempn",
    ],
    "category": [
        "category",
        "materialgroup",
        "matkl",
        "family",
        "subfamily",
        "commodity",
    ],
}


def _norm_col(col_name: str) -> str:
    """Normalize column header for alias matching."""
    return "".join(c for c in col_name.lower() if c.isalnum())


@dataclass
class IngestedRow:
    """Single row ingested from tabular source."""

    row_number: int
    raw_payload: dict[str, Any]
    item_code: str | None
    raw_description: str
    clean_text: str
    language: str
    original_uom: str | None
    original_qty: float | None
    canonical_uom: str | None
    canonical_qty: float | None
    unit_price_inr: float | None
    plant: str | None
    last_movement_date: date | None
    criticality: str | None
    min_stock: float | None
    max_stock: float | None
    category: str | None
    flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ParsedTabularData:
    """Structured result of parsing tabular master data."""

    filename: str
    file_hash: str
    total_rows: int
    valid_rows: int
    error_rows: int
    rows: list[IngestedRow]
    errors: list[str] = field(default_factory=list)


def build_column_mapping(
    headers: list[str], profile_mapping: dict[str, str] | None = None
) -> dict[str, str]:
    """Map standard fields to specific column names present in the file."""
    mapping: dict[str, str] = {}
    norm_headers = {_norm_col(h): h for h in headers if h}

    # If profile provides exact mappings, apply them first
    if profile_mapping:
        for standard_field, source_col in profile_mapping.items():
            if source_col in headers:
                mapping[standard_field] = source_col
            elif _norm_col(source_col) in norm_headers:
                mapping[standard_field] = norm_headers[_norm_col(source_col)]

    # For standard fields not yet mapped, use default aliases
    for standard_field, aliases in DEFAULT_COLUMN_ALIASES.items():
        if standard_field in mapping:
            continue
        for alias in aliases:
            if alias in norm_headers:
                mapping[standard_field] = norm_headers[alias]
                break

    return mapping


def _parse_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_date(val: Any) -> date | None:
    if val is None or val == "":
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    val_str = str(val).strip()
    # Try ISO YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_csv_bytes(file_bytes: bytes) -> list[dict[str, Any]]:
    """Decode and parse CSV content trying UTF-8-sig, UTF-8, and Latin-1."""
    text_content = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text_content = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text_content is None:
        raise ValueError("Unable to decode CSV file with supported encodings (UTF-8, Latin-1).")

    f = io.StringIO(text_content)
    reader = csv.DictReader(f)
    return [row for row in reader]


def parse_xlsx_bytes(file_bytes: bytes) -> list[dict[str, Any]]:
    """Parse XLSX content using openpyxl."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheet = wb.active or wb.worksheets[0]
    rows_iter = sheet.iter_rows(values_only=True)

    header_row = next(rows_iter, None)
    if not header_row:
        return []

    headers = [str(cell).strip() if cell is not None else f"col_{i}" for i, cell in enumerate(header_row)]
    data: list[dict[str, Any]] = []

    for row_vals in rows_iter:
        if not any(v is not None and str(v).strip() != "" for v in row_vals):
            continue  # Skip entirely empty rows
        row_dict = {
            headers[i]: row_vals[i] if i < len(row_vals) else None
            for i in range(len(headers))
        }
        data.append(row_dict)

    return data


def parse_tabular_bytes(
    file_bytes: bytes,
    filename: str,
    org_profile: dict[str, Any] | None = None,
) -> ParsedTabularData:
    """Parse CSV or XLSX bytes and perform normalization and UoM processing."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    is_xlsx = filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls")

    if is_xlsx:
        raw_rows = parse_xlsx_bytes(file_bytes)
    else:
        raw_rows = parse_csv_bytes(file_bytes)

    if not raw_rows:
        return ParsedTabularData(
            filename=filename,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            error_rows=0,
            rows=[],
            errors=["File contains no data rows."],
        )

    headers = list(raw_rows[0].keys())
    profile_mapping = (org_profile or {}).get("column_mapping")
    col_map = build_column_mapping(headers, profile_mapping)

    parsed_rows: list[IngestedRow] = []
    error_count = 0

    for idx, raw_dict in enumerate(raw_rows, start=1):
        row_errors: list[str] = []
        row_flags: list[str] = []

        # Extract values according to mapped columns
        item_code_val = raw_dict.get(col_map.get("item_code", ""))
        desc_val = raw_dict.get(col_map.get("description", ""))
        uom_val = raw_dict.get(col_map.get("uom", ""))
        qty_val = raw_dict.get(col_map.get("qty", ""))
        price_val = raw_dict.get(col_map.get("unit_price", ""))
        plant_val = raw_dict.get(col_map.get("plant", ""))
        movement_val = raw_dict.get(col_map.get("last_movement_date", ""))
        crit_val = raw_dict.get(col_map.get("criticality", ""))
        min_stock_val = raw_dict.get(col_map.get("min_stock", ""))
        max_stock_val = raw_dict.get(col_map.get("max_stock", ""))
        category_val = raw_dict.get(col_map.get("category", ""))

        item_code = str(item_code_val).strip() if item_code_val is not None else None
        raw_desc = str(desc_val).strip() if desc_val is not None else ""
        raw_uom = str(uom_val).strip() if uom_val is not None else None
        orig_qty = _parse_float(qty_val)
        unit_price = _parse_float(price_val)
        plant = str(plant_val).strip() if plant_val is not None else None
        last_move_dt = _parse_date(movement_val)
        criticality = str(crit_val).strip().upper() if crit_val is not None else None
        min_stock = _parse_float(min_stock_val)
        max_stock = _parse_float(max_stock_val)
        category = str(category_val).strip().upper() if category_val is not None else None

        if not raw_desc:
            row_errors.append("MISSING_DESCRIPTION")

        # 1. Detect language / script
        script_info = detect_scripts(raw_desc)
        language = script_info.primary_language

        # 2. Text Normalization
        norm_res = normalize_text(raw_desc, category=category)
        clean_text = norm_res.clean_text
        row_flags.extend(norm_res.flags)

        # 3. Canonical UoM Conversion
        canonical_uom = None
        canonical_qty = None
        if orig_qty is not None and raw_uom:
            uom_res = convert_to_canonical(
                orig_qty,
                raw_uom,
                category=category,
                attributes={"designation": clean_text},
            )
            canonical_uom = uom_res.canonical_uom
            canonical_qty = uom_res.canonical_qty
            row_flags.extend(uom_res.flags)
        elif raw_uom:
            canonical_uom = raw_uom

        if row_errors:
            error_count += 1

        parsed_rows.append(
            IngestedRow(
                row_number=idx,
                raw_payload=raw_dict,
                item_code=item_code,
                raw_description=raw_desc,
                clean_text=clean_text,
                language=language,
                original_uom=raw_uom,
                original_qty=orig_qty,
                canonical_uom=canonical_uom,
                canonical_qty=canonical_qty,
                unit_price_inr=unit_price,
                plant=plant,
                last_movement_date=last_move_dt,
                criticality=criticality,
                min_stock=min_stock,
                max_stock=max_stock,
                category=category,
                flags=list(dict.fromkeys(row_flags)),
                errors=row_errors,
            )
        )

    valid_count = len(parsed_rows) - error_count

    return ParsedTabularData(
        filename=filename,
        file_hash=file_hash,
        total_rows=len(parsed_rows),
        valid_rows=valid_count,
        error_rows=error_count,
        rows=parsed_rows,
        errors=[],
    )


@dataclass
class IngestionResult:
    """Result of full ingestion into PostgreSQL database."""

    document_id: UUID
    file_hash: str
    status: str
    is_duplicate: bool
    total_rows: int
    inserted_rows: int
    error_rows: int
    message: str


async def ingest_tabular_document(
    db: AsyncSession,
    org_id: str,
    file_bytes: bytes,
    filename: str,
    org_profile: dict[str, Any] | None = None,
    uploaded_by: UUID | None = None,
    doc_type: str = "LEGACY_MASTER",
) -> IngestionResult:
    """Ingest a CSV/XLSX file with idempotency on file hash, persistence, and audit logging."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # 1. Idempotency Check: check if file_hash already processed for this org
    existing_doc_res = await db.execute(
        text("SELECT id, status FROM documents WHERE org_id = :org_id AND file_hash = :hash"),
        {"org_id": org_id, "hash": file_hash},
    )
    existing_doc = existing_doc_res.fetchone()
    if existing_doc:
        # File already exists: return idempotent response
        rows_res = await db.execute(
            text("SELECT COUNT(*) FROM raw_items WHERE org_id = :org_id AND source_file_hash = :hash"),
            {"org_id": org_id, "hash": file_hash},
        )
        row_count = rows_res.scalar() or 0
        return IngestionResult(
            document_id=existing_doc.id,
            file_hash=file_hash,
            status=existing_doc.status,
            is_duplicate=True,
            total_rows=row_count,
            inserted_rows=0,
            error_rows=0,
            message="Document already ingested with identical file hash (idempotent skip).",
        )

    # 2. Parse file
    parsed = parse_tabular_bytes(file_bytes, filename, org_profile=org_profile)

    # 3. Create document record
    doc_id = uuid4()
    await db.execute(
        text(
            "INSERT INTO documents (id, org_id, doc_type, capture_channel, file_hash, storage_path, pages, status, uploaded_by) "
            "VALUES (:id, :org_id, :doc_type, 'UPLOAD', :file_hash, :storage_path, 1, 'PROCESSED', :uploaded_by)"
        ),
        {
            "id": doc_id,
            "org_id": org_id,
            "doc_type": doc_type,
            "file_hash": file_hash,
            "storage_path": filename,
            "uploaded_by": uploaded_by,
        },
    )

    # 4. Insert raw items
    inserted_count = 0
    import json

    for row in parsed.rows:
        raw_id = uuid4()
        raw_payload_json = json.dumps(row.raw_payload)

        await db.execute(
            text(
                "INSERT INTO raw_items ("
                "  id, org_id, source_type, source_file_hash, source_row, raw_payload, "
                "  item_code, raw_description, clean_text, language, original_uom, original_qty, "
                "  canonical_uom, canonical_qty, unit_price_inr, plant, last_movement_date, "
                "  criticality, min_stock, max_stock, category, extraction_flags, status"
                ") VALUES ("
                "  :id, :org_id, :source_type, :source_file_hash, :source_row, CAST(:raw_payload AS jsonb), "
                "  :item_code, :raw_description, :clean_text, :language, :original_uom, :original_qty, "
                "  :canonical_uom, :canonical_qty, :unit_price_inr, :plant, :last_movement_date, "
                "  :criticality, :min_stock, :max_stock, :category, :extraction_flags, 'PENDING'"
                ")"
            ),
            {
                "id": raw_id,
                "org_id": org_id,
                "source_type": doc_type,
                "source_file_hash": file_hash,
                "source_row": row.row_number,
                "raw_payload": raw_payload_json,
                "item_code": row.item_code,
                "raw_description": row.raw_description,
                "clean_text": row.clean_text,
                "language": row.language,
                "original_uom": row.original_uom,
                "original_qty": row.original_qty,
                "canonical_uom": row.canonical_uom,
                "canonical_qty": row.canonical_qty,
                "unit_price_inr": row.unit_price_inr,
                "plant": row.plant,
                "last_movement_date": row.last_movement_date,
                "criticality": row.criticality,
                "min_stock": row.min_stock,
                "max_stock": row.max_stock,
                "category": row.category,
                "extraction_flags": row.flags,
            },
        )
        inserted_count += 1

    # 5. Write to transactional audit_log (Invariant S6)
    audit_after = json.dumps({
        "filename": filename,
        "file_hash": file_hash,
        "total_rows": parsed.total_rows,
        "valid_rows": parsed.valid_rows,
        "error_rows": parsed.error_rows,
    })

    await db.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'INGEST_DOCUMENT', 'documents', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": uploaded_by,
            "entity_id": str(doc_id),
            "after": audit_after,
            "rationale": f"Legacy master ingestion of {filename} ({parsed.valid_rows} items)",
        },
    )

    return IngestionResult(
        document_id=doc_id,
        file_hash=file_hash,
        status="PROCESSED",
        is_duplicate=False,
        total_rows=parsed.total_rows,
        inserted_rows=inserted_count,
        error_rows=parsed.error_rows,
        message=f"Successfully ingested {inserted_count} rows from {filename}.",
    )
