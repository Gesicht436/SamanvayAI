export type UserRole = "VIEWER" | "MAKER" | "CHECKER" | "ADMIN";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  org_code?: string;
  domains: string[];
}

export interface Org {
  code: string;
  name: string;
  sector: string;
}

export interface ExtractedAttribute {
  value: string | number | boolean | null;
  confidence: number;
  evidence?: [number, number] | null;
}

export type VerdictStatus = "EXACT" | "MISSING" | "MISMATCH" | "UPGRADE";
export type AttributeRole = "HARD" | "REQUIRED" | "SOFT";

export interface AttributeVerdict {
  attr: string;
  role: AttributeRole;
  raw: string | number | boolean | null;
  golden: string | number | boolean | null;
  verdict: VerdictStatus;
  note?: string;
}

export interface CandidateMaster {
  golden_code: string;
  descriptor: string;
  tier: 1 | 2 | 3;
  prob: number;
  reason_codes: string[];
  verdicts: AttributeVerdict[];
  attribute_gap_alert?: string;
}

export interface MatchResponse {
  clean_text: string;
  subcategory: string;
  category_confidence: number;
  flags: string[];
  extracted: Record<string, ExtractedAttribute>;
  candidates: CandidateMaster[];
}

export interface MatchRequest {
  description: string;
  category_hint?: string | null;
  top_k?: number;
}

export type TaskKind =
  | "LINK"
  | "CREATE_MASTER"
  | "MERGE"
  | "SPLIT"
  | "CORRECT_ATTR"
  | "DOC_REVIEW";

export type TaskStatus = "PROPOSED" | "APPROVED" | "REJECTED";

export interface StewardTask {
  id: number;
  kind: TaskKind;
  subcategory: string;
  sector: string;
  status: TaskStatus;
  proposed_by: string;
  approved_by?: string | null;
  payload: Record<string, unknown>;
  rationale?: string | null;
  rejection_reason?: string | null;
  audit_seq?: number;
  audit_hash?: string;
  created_at: string;
}

export interface TasksResponse {
  items: StewardTask[];
  total: number;
  page: number;
  size: number;
}

export interface EvaluationMetrics {
  total_pairs: number;
  baselines: {
    cosine_error_rate: number;
    trigram_error_rate: number;
    samanvay_error_rate: number;
    clopper_pearson_95_upper: number;
  };
  gates: {
    name: string;
    status: "PASS" | "FAIL";
    detail: string;
  }[];
  sector_parity: {
    sector: string;
    pairs: number;
    false_merges: number;
    error_rate: number;
    tier2_routing: number;
  }[];
  org_parity: {
    org: string;
    pairs: number;
    false_merges: number;
    status: string;
  }[];
}

export interface CatalogHealthSummary {
  catalog_completeness: number;
  classified_share: number;
  uncertain_items_count: number;
  extraction_flag_rates: Record<string, number>;
  duplicate_rate: number;
  top_missing_attributes: Record<string, { attribute: string; missing_pct: number }[]>;
  statutory_missing_count: number;
}

export interface ClusterSavingsItem {
  cluster_id: number;
  domain: string;
  subcategory: string;
  description: string;
  annual_spend_inr: number;
  table_pct: number;
  table_pct_display: string;
  low_savings: number;
  base_savings: number;
  high_savings: number;
}

export interface DashboardSummary {
  org_id: string;
  queue_by_domain: Record<string, number>;
  tier_distribution: Record<string, number>;
  harmonization: {
    raw_items_before: number;
    golden_masters_after: number;
    compression_ratio: number;
  };
  catalog_health: CatalogHealthSummary;
  ocr_readiness: {
    ready: boolean;
    primary_engine: string;
    fallback_engine: string;
  };
  audit_integrity: {
    status: string;
    verified_records: number;
    head_hash: string | null;
  };
  clusters?: ClusterSavingsItem[];
}

export interface OemProposalItem {
  id: number;
  batch_id: string;
  raw_part_number: string;
  norm_part_number: string;
  effective_part_number: string;
  superseded_from?: string | null;
  drawing_no?: string | null;
  parent_equipment_model?: string | null;
  raw_description: string;
  subcategory?: string | null;
  evidence_spans: Record<string, [number, number]>;
  status: "PROPOSED" | "ACCEPTED" | "REJECTED" | "APPROVED";
  golden_id?: string | null;
}

export interface OemBatchData {
  batch_id: string;
  oem_name: string;
  filename: string;
  total_rows: number;
  superseded_count: number;
  status: string;
  proposals: OemProposalItem[];
}

export interface StockLotItem {
  lot_id: string;
  golden_code?: string | null;
  descriptor?: string | null;
  plant?: string | null;
  batch_no?: string | null;
  mfg_date?: string | null;
  expiry_date?: string | null;
  remaining_days?: number | null;
  risk: "GREEN" | "AMBER" | "RED" | "EXPIRED" | "UNKNOWN";
  basis: string;
  qty_remaining?: number | null;
  uom?: string | null;
  stream_a_eligible: boolean;
  reason?: string | null;
  near_expiry_path: boolean;
}

export interface DocLineData {
  line_id: string;
  raw_text: string;
  ocr_conf?: number | null;
  fields: Record<string, unknown>;
  flags: string[];
}

export interface MtcEvaluationData {
  id: string;
  grade_claimed: string;
  heat_no?: string | null;
  chemistry: Record<string, number>;
  ce_iiw?: number | null;
  pren?: number | null;
  conformance: "CONFORMS" | "FAILS" | "INCOMPLETE" | "UNVERIFIED_REFERENCE" | "REQUIRES_REVIEW";
  reference_verified: boolean;
  flags: string[];
  property_verdicts: {
    property: string;
    kind: string;
    found: number;
    min_required?: number | null;
    max_allowed?: number | null;
    unit?: string | null;
    verdict: "PASS" | "FAIL";
  }[];
}
