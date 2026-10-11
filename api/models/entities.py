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
