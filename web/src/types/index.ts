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
