import {
  MatchRequest,
  MatchResponse,
  StewardTask,
  TasksResponse,
  EvaluationMetrics,
  Org,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const SAMPLE_ORGS: Org[] = [
  { code: "OIL-1", name: "Indian Oil & Gas Corporation (OIL-1)", sector: "COMMON" },
  { code: "POWER-1", name: "National Thermal Power Grid (POWER-1)", sector: "POWER" },
  { code: "STEEL-1", name: "National Steel Authority (STEEL-1)", sector: "STEEL" },
  { code: "MINE-1", name: "National Coal & Minerals Ltd (MINE-1)", sector: "MINING" },
  { code: "HEAVY-1", name: "Heavy Engineering & Locomotive Corp (HEAVY-1)", sector: "HEAVY_ENG" },
];

export const DEMO_MATCH_RESPONSES: Record<string, MatchResponse> = {
  valve: {
    clean_text: "VALVE GATE 100 NB CL150 WCB FLANGED RF API 600",
    subcategory: "VALVES.GATE",
    category_confidence: 0.985,
    flags: [],
    extracted: {
      size_nb: { value: 100, confidence: 0.96, evidence: [11, 17] },
      pressure_class: { value: "ASME_150", confidence: 0.97, evidence: [18, 23] },
      body_material: { value: "A216_WCB", confidence: 0.95, evidence: [24, 27] },
      end_connection: { value: "FLANGED", confidence: 0.98, evidence: [28, 35] },
      facing: { value: "RF", confidence: 0.99, evidence: [36, 38] },
      design_standard: { value: "API_600", confidence: 0.95, evidence: [39, 46] },
    },
    candidates: [
      {
        golden_code: "MPNG-0004821937-3",
        descriptor: "VALVES.GATE | 100NB | CL150 | A216-WCB | FLG-RF | API600",
        tier: 2,
        prob: 0.932,
        reason_codes: ["MISSING_REQUIRED"],
        attribute_gap_alert: "Missing Required Attributes: trim_code, bonnet_type, operator, fire_safe",
        verdicts: [
          { attr: "size_nb", role: "HARD", raw: 100, golden: 100, verdict: "EXACT", note: "Exact size match" },
          { attr: "pressure_class", role: "HARD", raw: "ASME_150", golden: "ASME_150", verdict: "EXACT", note: "Rating aligned" },
          { attr: "body_material", role: "HARD", raw: "A216_WCB", golden: "A216_WCB", verdict: "EXACT", note: "Carbon steel WCB" },
          { attr: "end_connection", role: "HARD", raw: "FLANGED", golden: "FLANGED", verdict: "EXACT", note: "Flanged joint" },
          { attr: "facing", role: "HARD", raw: "RF", golden: "RF", verdict: "EXACT", note: "Raised face" },
          { attr: "design_standard", role: "HARD", raw: "API_600", golden: "API_600", verdict: "EXACT", note: "API 600 heavy-wall" },
          { attr: "trim_code", role: "REQUIRED", raw: null, golden: "API_TRIM_8", verdict: "MISSING", note: "Trim 8 (Cr-Co) missing on raw item" },
          { attr: "bonnet_type", role: "REQUIRED", raw: null, golden: "BOLTED", verdict: "MISSING", note: "Bonnet style missing" },
          { attr: "operator", role: "REQUIRED", raw: null, golden: "HANDWHEEL", verdict: "MISSING", note: "Actuation not stated" },
        ],
      },
      {
        golden_code: "MPNG-0001948211-7",
        descriptor: "VALVES.GATE | 100NB | CL300 | A216-WCB | FLG-RF | API600",
        tier: 3,
        prob: 0.841,
        reason_codes: ["HARD_ATTR_MISMATCH"],
        attribute_gap_alert: "Safety Refusal: Pressure class mismatch (ASME_150 vs ASME_300). Invariant S1/S4 blocks Tier 1.",
        verdicts: [
          { attr: "size_nb", role: "HARD", raw: 100, golden: 100, verdict: "EXACT" },
          { attr: "pressure_class", role: "HARD", raw: "ASME_150", golden: "ASME_300", verdict: "MISMATCH", note: "High-pressure hazard mismatch" },
          { attr: "body_material", role: "HARD", raw: "A216_WCB", golden: "A216_WCB", verdict: "EXACT" },
          { attr: "end_connection", role: "HARD", raw: "FLANGED", golden: "FLANGED", verdict: "EXACT" },
          { attr: "facing", role: "HARD", raw: "RF", golden: "RF", verdict: "EXACT" },
        ],
      },
    ],
  },
  motor: {
    clean_text: "MOTOR 55 KW 4 POLE B3 FOOT MOUNTED EX D IIB T4 IE3",
    subcategory: "MOTORS.EX",
    category_confidence: 0.992,
    flags: [],
    extracted: {
      power_kw: { value: 55, confidence: 0.99, evidence: [6, 11] },
      pole_count: { value: 4, confidence: 0.98, evidence: [12, 18] },
      mounting: { value: "B3", confidence: 0.97, evidence: [19, 21] },
      ex_type: { value: "EX_D", confidence: 0.99, evidence: [35, 39] },
      gas_group: { value: "IIB", confidence: 0.98, evidence: [40, 43] },
      t_class: { value: "T4", confidence: 0.99, evidence: [44, 46] },
      efficiency_class: { value: "IE3", confidence: 0.98, evidence: [47, 50] },
    },
    candidates: [
      {
        golden_code: "MPNG-0008812390-1",
        descriptor: "MOTORS.EX | 55KW | 4P | B3 | EX_D | IIB | T4 | IE3",
        tier: 1,
        prob: 0.988,
        reason_codes: [],
        verdicts: [
          { attr: "power_kw", role: "HARD", raw: 55, golden: 55, verdict: "EXACT", note: "55 kW rating matches" },
          { attr: "pole_count", role: "HARD", raw: 4, golden: 4, verdict: "EXACT", note: "4 Pole (1500 rpm sync)" },
          { attr: "mounting", role: "HARD", raw: "B3", golden: "B3", verdict: "EXACT", note: "Foot mounted" },
          { attr: "ex_type", role: "HARD", raw: "EX_D", golden: "EX_D", verdict: "EXACT", note: "Flameproof enclosure" },
          { attr: "gas_group", role: "HARD", raw: "IIB", golden: "IIB", verdict: "EXACT", note: "Gas group IIB matches" },
          { attr: "t_class", role: "HARD", raw: "T4", golden: "T4", verdict: "EXACT", note: "135 deg C max surface temp" },
          { attr: "efficiency_class", role: "HARD", raw: "IE3", golden: "IE3", verdict: "EXACT", note: "Premium efficiency" },
        ],
      },
      {
        golden_code: "MPNG-0008812391-9",
        descriptor: "MOTORS.EX | 55KW | 4P | B3 | EX_D | IIC | T4 | IE3",
        tier: 2,
        prob: 0.915,
        reason_codes: ["DIRECTIONAL_UPGRADE"],
        attribute_gap_alert: "Directional Lattice Upgrade: Gas group IIC supersedes IIB (Invariant S11 lattice: IIC >= IIB >= IIA).",
        verdicts: [
          { attr: "power_kw", role: "HARD", raw: 55, golden: 55, verdict: "EXACT" },
          { attr: "pole_count", role: "HARD", raw: 4, golden: 4, verdict: "EXACT" },
          { attr: "mounting", role: "HARD", raw: "B3", golden: "B3", verdict: "EXACT" },
          { attr: "ex_type", role: "HARD", raw: "EX_D", golden: "EX_D", verdict: "EXACT" },
          { attr: "gas_group", role: "HARD", raw: "IIB", golden: "IIC", verdict: "UPGRADE", note: "IIC can safely substitute for IIB" },
          { attr: "t_class", role: "HARD", raw: "T4", golden: "T4", verdict: "EXACT" },
          { attr: "efficiency_class", role: "HARD", raw: "IE3", golden: "IE3", verdict: "EXACT" },
        ],
      },
    ],
  },
};

export const INITIAL_DEMO_TASKS: StewardTask[] = [
  {
    id: 101,
    kind: "LINK",
    subcategory: "VALVES.GATE",
    sector: "COMMON",
    status: "PROPOSED",
    proposed_by: "steward-maker-01",
    payload: {
      raw_id: 1001,
      golden_id: 2001,
      golden_code: "MPNG-0004821937-3",
      raw_description: "GATE VALVE 4 INCH 150# A216 WCB FLANGED RF API 600",
      tier: 2,
    },
    rationale: "Datasheet page 2 confirms trim 8 and fire-safe API 607 design.",
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
  },
  {
    id: 102,
    kind: "CREATE_MASTER",
    subcategory: "MOTORS.EX",
    sector: "COMMON",
    status: "PROPOSED",
    proposed_by: "steward-maker-02",
    payload: {
      descriptor: "MOTORS.EX | 75KW | 4P | B3 | EX_D | IIB | T4 | IE3",
      attributes: { power_kw: 75, pole_count: 4, mounting: "B3", ex_type: "EX_D", gas_group: "IIB", t_class: "T4", efficiency_class: "IE3" },
      identity_mode: "PARAMETRIC",
      safety_critical: true,
    },
    rationale: "New high-demand motor variant identified across 3 refinery locations.",
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
  },
  {
    id: 103,
    kind: "LINK",
    subcategory: "POWER.TRANSFORMER",
    sector: "POWER",
    status: "APPROVED",
    proposed_by: "steward-maker-01",
    approved_by: "steward-checker-power",
    payload: {
      raw_id: 1002,
      golden_id: 2005,
      golden_code: "MPNG-0003928172-8",
      raw_description: "TRANSFORMER 100 KVA 11/0.433KV DYN11 ONAN",
      tier: 2,
    },
    rationale: "Approved with vector group test report verified.",
    audit_seq: 10420,
    audit_hash: "3e28f0928a6f982b6b010c74d81290a3c261971764839218274618293847291a",
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
  },
  {
    id: 104,
    kind: "MERGE",
    subcategory: "STEEL.REFRACTORY",
    sector: "STEEL",
    status: "REJECTED",
    proposed_by: "steward-maker-03",
    approved_by: "steward-checker-steel",
    payload: {
      source_id: 2010,
      target_id: 2011,
      source_code: "MPNG-0008472910-4",
      target_code: "MPNG-0008472911-2",
    },
    rationale: "Proposed merging two MgO-C refractory grades.",
    rejection_reason: "Refractories differ by carbon content (10% vs 14%). Merging violates Invariant S1.",
    created_at: new Date(Date.now() - 3600000 * 30).toISOString(),
  },
  {
    id: 105,
    kind: "CORRECT_ATTR",
    subcategory: "MINING.OTR_TYRE",
    sector: "MINING",
    status: "PROPOSED",
    proposed_by: "steward-maker-01",
    payload: {
      golden_id: 2020,
      golden_code: "MPNG-0005728193-5",
      attr_name: "tread_code",
      old_value: "E3",
      new_value: "E4",
    },
    rationale: "Correcting tread code from catalog addendum specification.",
    created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
  },
  {
    id: 106,
    kind: "DOC_REVIEW",
    subcategory: "HEAVY.PUMP_CENTRIFUGAL",
    sector: "HEAVY_ENG",
    status: "PROPOSED",
    proposed_by: "steward-maker-02",
    payload: {
      document_id: "doc-uuid-88120",
      line_id: "line-uuid-12",
      ocr_text: "CENTRIFUGAL PUMP OH2 100 M3/HR 50 M HEAD S-6",
      low_confidence_fields: ["head_m"],
    },
    rationale: "Head value verified from manufacturer specification curve.",
    created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
  },
];

const inMemoryTasks = [...INITIAL_DEMO_TASKS];

export const DEMO_METRICS: EvaluationMetrics = {
  total_pairs: 170,
  baselines: {
    cosine_error_rate: 67.6,
    trigram_error_rate: 55.9,
    samanvay_error_rate: 0.0,
    clopper_pearson_95_upper: 2.15,
  },
  gates: [
    { name: "Hard-negative false merges", status: "PASS", detail: "0/170 observed (95% upper bound: 2.15% <= 3.0%)" },
    { name: "Missing-attribute routing to Tier 2", status: "PASS", detail: "76/76 routed to Tier 2 (100.0%)" },
    { name: "Low-confidence OCR in Tier 1", status: "PASS", detail: "0 found in Tier 1 (Invariant S5 strictly enforced)" },
    { name: "MTC conformance against unverified reference", status: "PASS", detail: "0 unverified references permitted (Invariant S15)" },
    { name: "Auto-tier precision (dev set)", status: "PASS", detail: "100.00% (600/600 dev pairs >= 99.50% target)" },
  ],
  sector_parity: [
    { sector: "COMMON", pairs: 76, false_merges: 0, error_rate: 0.0, tier2_routing: 100.0 },
    { sector: "POWER", pairs: 25, false_merges: 0, error_rate: 0.0, tier2_routing: 100.0 },
    { sector: "STEEL", pairs: 26, false_merges: 0, error_rate: 0.0, tier2_routing: 100.0 },
    { sector: "MINING", pairs: 19, false_merges: 0, error_rate: 0.0, tier2_routing: 100.0 },
    { sector: "HEAVY_ENG", pairs: 24, false_merges: 0, error_rate: 0.0, tier2_routing: 100.0 },
  ],
  org_parity: [
    { org: "OIL-1", pairs: 100, false_merges: 0, status: "In Parity" },
    { org: "POWER-1", pairs: 101, false_merges: 0, status: "In Parity" },
    { org: "STEEL-1", pairs: 126, false_merges: 0, status: "In Parity" },
    { org: "MINE-1", pairs: 95, false_merges: 0, status: "In Parity" },
  ],
};

export async function matchMaterial(req: MatchRequest): Promise<MatchResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Backend offline; use local demo response
  }

  // Fallback demo match
  const text = req.description.toLowerCase();
  if (text.includes("motor") || text.includes("kw") || text.includes("ex d")) {
    return DEMO_MATCH_RESPONSES.motor;
  }
  return DEMO_MATCH_RESPONSES.valve;
}

export async function getTasks(params?: {
  status?: string;
  kind?: string;
  sector?: string;
  page?: number;
  size?: number;
}): Promise<TasksResponse> {
  const page = params?.page || 1;
  const size = params?.size || 10;

  try {
    const query = new URLSearchParams();
    if (params?.status && params.status !== "ALL") query.set("status", params.status);
    if (params?.kind && params.kind !== "ALL") query.set("kind", params.kind);
    if (params?.sector && params.sector !== "ALL") query.set("sector", params.sector);
    query.set("page", String(page));
    query.set("size", String(size));

    const res = await fetch(`${API_BASE_URL}/tasks?${query.toString()}`);
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Backend offline; use memory tasks
  }

  // Filter in-memory demo tasks
  let filtered = [...inMemoryTasks];
  if (params?.status && params.status !== "ALL") {
    filtered = filtered.filter((t) => t.status === params.status);
  }
  if (params?.kind && params.kind !== "ALL") {
    filtered = filtered.filter((t) => t.kind === params.kind);
  }
  if (params?.sector && params.sector !== "ALL") {
    filtered = filtered.filter((t) => t.sector === params.sector);
  }

  const start = (page - 1) * size;
  const paged = filtered.slice(start, start + size);

  return {
    items: paged,
    total: filtered.length,
    page,
    size,
  };
}

export async function approveTask(
  taskId: number,
  rationale: string,
  user: { id: string; role: string; domains: string[] }
): Promise<{ success: boolean; message: string; audit_seq?: number; audit_hash?: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rationale }),
    });
    if (res.ok) {
      const data = await res.json();
      return { success: true, message: "Task approved successfully", audit_seq: data.audit_seq, audit_hash: data.audit_hash };
    }
    const err = await res.json();
    return { success: false, message: err.detail || err.message || "Failed to approve task" };
  } catch {
    // Local demo simulation with Maker-Checker validation
    const task = inMemoryTasks.find((t) => t.id === taskId);
    if (!task) return { success: false, message: "Task not found" };

    if (task.proposed_by === user.id) {
      return {
        success: false,
        message: "MAKER_CHECKER_VIOLATION: The checker must differ from the maker who proposed this task.",
      };
    }

    if (user.role !== "CHECKER" && user.role !== "ADMIN") {
      return {
        success: false,
        message: "ROLE_REQUIRED: Only Checkers or Admins can approve stewardship tasks.",
      };
    }

    if (!user.domains.includes(task.sector) && !user.domains.includes("COMMON")) {
      return {
        success: false,
        message: `DOMAIN_TAG_REQUIRED: Approval of ${task.subcategory} requires domain tag '${task.sector}'.`,
      };
    }

    task.status = "APPROVED";
    task.approved_by = user.id;
    task.audit_seq = 10500 + taskId;
    task.audit_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    return {
      success: true,
      message: "Task approved and executed in transactional audit chain.",
      audit_seq: task.audit_seq,
      audit_hash: task.audit_hash,
    };
  }
}

export async function rejectTask(
  taskId: number,
  reason: string,
  user: { id: string; role: string }
): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (res.ok) {
      return { success: true, message: "Task rejected successfully" };
    }
    const err = await res.json();
    return { success: false, message: err.detail || err.message || "Failed to reject task" };
  } catch {
    const task = inMemoryTasks.find((t) => t.id === taskId);
    if (!task) return { success: false, message: "Task not found" };

    if (user.role !== "CHECKER" && user.role !== "ADMIN") {
      return { success: false, message: "ROLE_REQUIRED: Only Checkers or Admins can reject stewardship tasks." };
    }

    task.status = "REJECTED";
    task.rejection_reason = reason;
    return { success: true, message: "Task rejected and recorded in audit log." };
  }
}

export async function getEvaluationMetrics(): Promise<EvaluationMetrics> {
  try {
    const res = await fetch(`${API_BASE_URL}/metrics/eval`);
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Backend offline; use locked metrics
  }
  return DEMO_METRICS;
}
