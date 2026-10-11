"""SQLAlchemy ORM models corresponding to the Section 9.2 schema."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from api.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    gstin = Column(Text, nullable=True)
    headquarters = Column(Text, nullable=True)
    segment = Column(ARRAY(Text), server_default="{}", nullable=False)
    profile = Column(JSONB, server_default="{}", nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=True)
    subject = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=True)
    domains = Column(ARRAY(Text), server_default="{}", nullable=False)
    role = Column(Text, nullable=False)
    active = Column(Boolean, server_default="true", nullable=False)


class AttributeSpec(Base):
    __tablename__ = "attribute_specs"

    subcategory = Column(Text, primary_key=True)
    attr = Column(Text, primary_key=True)
    role = Column(Text, nullable=False)  # HARD, REQUIRED, SOFT, DIRECTIONAL
    condition_expr = Column(Text, nullable=True)
    order_def = Column(JSONB, nullable=True)
    statutory = Column(Boolean, server_default="false", nullable=False)


class SubcategorySpec(Base):
    __tablename__ = "subcategory_specs"

    subcategory = Column(Text, primary_key=True)
    segment = Column(ARRAY(Text), server_default="{}", nullable=False)
    identity_mode = Column(Text, server_default="PARAMETRIC", nullable=False)
    safety_critical = Column(Boolean, server_default="false", nullable=False)
    expiry_required = Column(Boolean, server_default="false", nullable=False)
    pooling_class = Column(Text, nullable=True)
    depth = Column(Text, nullable=True)


class GoldenMaster(Base):
    __tablename__ = "golden_masters"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code = Column(Text, unique=True, nullable=False)
    descriptor = Column(Text, nullable=False)
    status = Column(Text, server_default="DRAFT", nullable=False)
    merged_into = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=True)
    major_category = Column(Text, nullable=False)
    subcategory = Column(Text, nullable=False)
    block_key = Column(Text, nullable=False)
    identity_mode = Column(Text, server_default="PARAMETRIC", nullable=False)
    segment = Column(ARRAY(Text), server_default="{}", nullable=False)
    attributes = Column(JSONB, server_default="{}", nullable=False)
    is_proprietary = Column(Boolean, server_default="false", nullable=False)
    oem_name_norm = Column(Text, nullable=True)
    oem_part_number_norm = Column(Text, nullable=True)
    canonical_text = Column(Text, nullable=False)
    canonical_uom = Column(Text, nullable=False)
    unspsc_code = Column(Text, nullable=True)
    gem_category_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))


class GoldenAlias(Base):
    __tablename__ = "golden_aliases"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=False)
    alias_type = Column(Text, nullable=False)
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=True)
    value_raw = Column(Text, nullable=False)
    value_norm = Column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("alias_type", "org_id", "value_norm", name="uq_golden_alias"),)


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_norm = Column(Text, unique=True, nullable=False)
    names_seen = Column(ARRAY(Text), nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    doc_type = Column(Text, nullable=False)
    capture_channel = Column(Text, server_default="UPLOAD", nullable=False)
    file_hash = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    pages = Column(Integer, nullable=True)
    vendor_gstin = Column(Text, nullable=True)
    invoice_no = Column(Text, nullable=True)
    invoice_date = Column(Date, nullable=True)
    invoice_key = Column(Text, nullable=True)
    status = Column(Text, server_default="UPLOADED", nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (UniqueConstraint("org_id", "file_hash", name="uq_document_org_hash"),)


class DocLine(Base):
    __tablename__ = "doc_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    page = Column(Integer, nullable=True)
    bbox = Column(JSONB, nullable=True)
    raw_text = Column(Text, nullable=False)
    ocr_engine = Column(Text, nullable=True)
    raster_dpi = Column(Integer, nullable=True)
    ocr_conf = Column(Numeric(4, 3), nullable=True)
    fields = Column(JSONB, server_default="{}", nullable=False)
    raw_item_id = Column(UUID(as_uuid=True), nullable=True)


class RawItem(Base):
    __tablename__ = "raw_items"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    source_type = Column(Text, server_default="LEGACY_MASTER", nullable=False)
    doc_line_id = Column(UUID(as_uuid=True), ForeignKey("doc_lines.id"), nullable=True)
    ocr_conf = Column(Numeric(4, 3), nullable=True)
    source_file_hash = Column(Text, nullable=True)
    source_row = Column(Integer, nullable=True)
    raw_payload = Column(JSONB, nullable=False)
    item_code = Column(Text, nullable=True)
    raw_description = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    original_uom = Column(Text, nullable=True)
    original_qty = Column(Numeric(14, 3), nullable=True)
    canonical_uom = Column(Text, nullable=True)
    canonical_qty = Column(Numeric(14, 3), nullable=True)
    unit_price_inr = Column(Numeric(14, 2), nullable=True)
    plant = Column(Text, nullable=True)
    last_movement_date = Column(Date, nullable=True)
    criticality = Column(Text, nullable=True)
    min_stock = Column(Numeric, nullable=True)
    max_stock = Column(Numeric, nullable=True)
    item_condition = Column(Text, server_default="NEW_UNUSED", nullable=False)
    has_mtc = Column(Boolean, server_default="false", nullable=False)
    category = Column(Text, nullable=True)
    subcategory = Column(Text, nullable=True)
    block_key = Column(Text, nullable=True)
    extracted = Column(JSONB, server_default="{}", nullable=False)
    extraction_flags = Column(ARRAY(Text), server_default="{}", nullable=False)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=True)
    tier = Column(Integer, nullable=True)
    match_prob = Column(Numeric(5, 4), nullable=True)
    status = Column(Text, server_default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (UniqueConstraint("org_id", "item_code", "source_file_hash", name="uq_raw_item_source"),)


class MatchCandidate(Base):
    __tablename__ = "match_candidates"

    raw_id = Column(UUID(as_uuid=True), ForeignKey("raw_items.id"), primary_key=True)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), primary_key=True)
    verdicts = Column(JSONB, nullable=False)
    features = Column(JSONB, nullable=False)
    prob = Column(Numeric(5, 4), nullable=True)
    tier = Column(Integer, nullable=True)


class StewardTask(Base):
    __tablename__ = "steward_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_id = Column(UUID(as_uuid=True), ForeignKey("raw_items.id"), nullable=True)
    kind = Column(Text, nullable=False)  # LINK, CREATE_MASTER, MERGE, SPLIT, CORRECT_ATTR, DOC_REVIEW
    payload = Column(JSONB, nullable=False)
    reason_codes = Column(ARRAY(Text), nullable=True)
    maker = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    checker = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    state = Column(Text, server_default="OPEN", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    decided_at = Column(DateTime(timezone=True), nullable=True)


class FeedbackExample(Base):
    __tablename__ = "feedback_examples"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_id = Column(UUID(as_uuid=True), nullable=True)
    golden_id = Column(UUID(as_uuid=True), nullable=True)
    label = Column(Boolean, nullable=False)
    features = Column(JSONB, nullable=True)
    steward = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class AuditLog(Base):
    __tablename__ = "audit_log"

    seq = Column(BigInteger, primary_key=True, autoincrement=True)
    at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    actor = Column(UUID(as_uuid=True), nullable=True)
    action = Column(Text, nullable=False)
    entity = Column(Text, nullable=False)
    entity_id = Column(Text, nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    rationale = Column(Text, nullable=True)
    prev_hash = Column(Text, nullable=False)
    this_hash = Column(Text, nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    kind = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    state = Column(Text, server_default="QUEUED", nullable=False)
    attempts = Column(Integer, server_default="0", nullable=False)
    run_after = Column(DateTime(timezone=True), server_default=text("now()"))
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class ProcurementLine(Base):
    __tablename__ = "procurement_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=True)
    doc_line_id = Column(UUID(as_uuid=True), ForeignKey("doc_lines.id"), nullable=True)
    qty = Column(Numeric(14, 3), nullable=True)
    uom = Column(Text, nullable=True)
    unit_price_inr = Column(Numeric(14, 2), nullable=True)
    vendor = Column(Text, nullable=True)
    po_no = Column(Text, nullable=True)
    grn_no = Column(Text, nullable=True)
    received_on = Column(Date, nullable=True)


class StockLot(Base):
    __tablename__ = "stock_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=True)
    procurement_line_id = Column(UUID(as_uuid=True), ForeignKey("procurement_lines.id"), nullable=True)
    plant = Column(Text, nullable=True)
    qty_remaining = Column(Numeric(14, 3), nullable=True)
    batch_no = Column(Text, nullable=True)
    mfg_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("stock_lots.id"), nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(14, 3), nullable=False)
    unit = Column(Text, nullable=False)


class LifePolicy(Base):
    __tablename__ = "life_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope_type = Column(Text, nullable=False)  # GOLDEN, CLASS
    scope_value = Column(Text, nullable=False)
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=True)
    basis = Column(Text, nullable=False)  # SHELF_LIFE_DAYS, USAGE_COUNT, USAGE_HOURS
    limit_value = Column(Numeric, nullable=False)
    unit = Column(Text, nullable=True)
    source = Column(Text, nullable=True)


class LifeAlert(Base):
    __tablename__ = "life_alerts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("stock_lots.id"), nullable=False)
    kind = Column(Text, nullable=True)
    risk = Column(Text, nullable=True)
    projected_date = Column(Date, nullable=True)
    recipient_role = Column(Text, nullable=True)
    dedupe_key = Column(Text, unique=True, nullable=True)
    state = Column(Text, server_default="OPEN", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    acked_at = Column(DateTime(timezone=True), nullable=True)


class CertRecord(Base):
    __tablename__ = "cert_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("stock_lots.id"), nullable=True)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=True)
    cert_type = Column(Text, nullable=False)
    cert_no = Column(Text, nullable=True)
    issuer = Column(Text, nullable=True)
    valid_to = Column(Date, nullable=True)
    file_hash = Column(Text, nullable=True)
    verified = Column(Boolean, server_default="false", nullable=False)


class GradeReference(Base):
    __tablename__ = "grade_reference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grade = Column(Text, nullable=False)
    product_form = Column(Text, nullable=False)
    property = Column(Text, nullable=False)
    kind = Column(Text, nullable=False)  # CHEM, MECH
    min_value = Column(Numeric, nullable=True)
    max_value = Column(Numeric, nullable=True)
    unit = Column(Text, nullable=True)
    condition = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    verified = Column(Boolean, server_default="false", nullable=False)

    __table_args__ = (UniqueConstraint("grade", "product_form", "property", name="uq_grade_reference_property"),)


class MtcResult(Base):
    __tablename__ = "mtc_results"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    cert_id = Column(UUID(as_uuid=True), ForeignKey("cert_records.id"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("stock_lots.id"), nullable=True)
    heat_no = Column(Text, nullable=True)
    grade_claimed = Column(Text, nullable=True)
    chemistry = Column(JSONB, server_default="{}", nullable=False)
    mechanical = Column(JSONB, server_default="{}", nullable=False)
    ce_iiw = Column(Numeric(5, 3), nullable=True)
    pren = Column(Numeric(5, 1), nullable=True)
    heat_treatment = Column(Text, nullable=True)
    ndt = Column(JSONB, server_default="[]", nullable=False)
    flags = Column(ARRAY(Text), server_default="{}", nullable=False)
    conformance = Column(Text, nullable=True)  # CONFORMS, FAILS, INCOMPLETE, UNVERIFIED_REFERENCE, REQUIRES_REVIEW
    reference_verified = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class OemPartSupersession(Base):
    __tablename__ = "oem_part_supersessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    manufacturer = Column(Text, nullable=False)
    old_pn = Column(Text, nullable=False)
    new_pn = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (UniqueConstraint("manufacturer", "old_pn", name="uq_oem_supersession_mfr_old_pn"),)


class OemCatalogueBatch(Base):
    __tablename__ = "oem_catalogue_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    oem_name = Column(Text, nullable=False)
    filename = Column(Text, nullable=False)
    file_hash = Column(Text, nullable=False)
    total_rows = Column(Integer, server_default="0", nullable=False)
    status = Column(Text, server_default="UPLOADED", nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    summary = Column(JSONB, server_default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class OemProposal(Base):
    __tablename__ = "oem_proposals"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("oem_catalogue_batches.id"), nullable=False)
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    oem_name = Column(Text, nullable=False)
    raw_part_number = Column(Text, nullable=False)
    norm_part_number = Column(Text, nullable=False)
    effective_part_number = Column(Text, nullable=False)
    superseded_from = Column(Text, nullable=True)
    drawing_no = Column(Text, nullable=True)
    parent_equipment_model = Column(Text, nullable=True)
    raw_description = Column(Text, nullable=False)
    subcategory = Column(Text, nullable=True)
    evidence_spans = Column(JSONB, server_default="{}", nullable=False)
    status = Column(Text, server_default="PROPOSED", nullable=False)  # PROPOSED, ACCEPTED, REJECTED, APPROVED
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=True)
    task_id = Column(BigInteger, ForeignKey("steward_tasks.id"), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class ForwardIndent(Base):
    __tablename__ = "forward_indents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    org_id = Column(Text, ForeignKey("organizations.id"), nullable=False)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=False)
    qty = Column(Numeric(14, 3), nullable=False)
    uom = Column(Text, nullable=False)
    budget_unit_cost = Column(Numeric(14, 2), nullable=True)
    need_by = Column(Date, nullable=False)
    delivery_site = Column(Text, nullable=True)
    plant = Column(Text, nullable=True)
    status = Column(Text, server_default="OPEN", nullable=False)  # OPEN, POOLED, ORDERED, CANCELLED
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class TenderPool(Base):
    __tablename__ = "tender_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    lead_org = Column(Text, ForeignKey("organizations.id"), nullable=False)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=False)
    status = Column(Text, server_default="DRAFT", nullable=False)  # DRAFT, POOLED, TENDERED, AWARDED, CANCELLED
    mou_ref = Column(Text, nullable=True)
    total_qty = Column(Numeric(14, 3), server_default="0", nullable=False)
    canonical_uom = Column(Text, nullable=True)
    estimated_baseline_cost = Column(Numeric(14, 2), server_default="0", nullable=False)
    estimated_pooled_cost = Column(Numeric(14, 2), server_default="0", nullable=False)
    estimated_savings = Column(Numeric(14, 2), server_default="0", nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))


class TenderPoolLine(Base):
    __tablename__ = "tender_pool_lines"

    pool_id = Column(UUID(as_uuid=True), ForeignKey("tender_pools.id", ondelete="CASCADE"), primary_key=True)
    indent_id = Column(UUID(as_uuid=True), ForeignKey("forward_indents.id", ondelete="CASCADE"), primary_key=True)


class TransferOrder(Base):
    __tablename__ = "transfer_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    from_org = Column(Text, ForeignKey("organizations.id"), nullable=False)
    to_org = Column(Text, ForeignKey("organizations.id"), nullable=False)
    from_plant = Column(Text, nullable=True)
    to_plant = Column(Text, nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("stock_lots.id"), nullable=False)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id"), nullable=False)
    qty = Column(Numeric(14, 3), nullable=False)
    basis = Column(Text, server_default="BOOK_VALUE", nullable=False)  # BOOK_VALUE, LAST_PURCHASE_PRICE, AGREED
    unit_price = Column(Numeric(14, 2), nullable=True)
    avoided_purchase_cost = Column(Numeric(14, 2), nullable=True)
    transfer_cost = Column(Numeric(14, 2), nullable=True)
    net_benefit = Column(Numeric(14, 2), nullable=True)
    mtc_uploaded = Column(Boolean, server_default="false", nullable=False)
    pmi_done = Column(Boolean, server_default="false", nullable=False)
    shelf_life_ok = Column(Boolean, server_default="true", nullable=False)
    state = Column(Text, server_default="REQUESTED", nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))


class GoldenSubvector(Base):
    __tablename__ = "golden_subvectors"

    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_masters.id", ondelete="CASCADE"), primary_key=True)
    domain = Column(Text, primary_key=True)  # 'dim', 'met', 'pt', 'std'
    text_repr = Column(Text, nullable=False, server_default="")
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


