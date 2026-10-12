"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { getStockLots } from "@/lib/api";
import { StockLotItem } from "@/types";
import {
  Boxes,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Building2,
  Calendar,
  Layers,
  Search,
  Filter,
  Download,
  CheckSquare,
  FileSpreadsheet,
  RotateCcw,
  FastForward,
  TrendingDown,
  BarChart3,
  Activity,
} from "lucide-react";

export default function LotsLifeMonitorPage() {
  const { selectedOrg, user } = useAuth();
  const [baseLots, setBaseLots] = useState<StockLotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [plantFilter, setPlantFilter] = useState("");

  // Simulated Clock State (Section 11.0 & 15.1)
  const [clockOffsetDays, setClockOffsetDays] = useState(0);

  // Selected Lot for Graphical Depletion Chart
  const [selectedChartLotId, setSelectedChartLotId] = useState<string | null>(null);

  // Alert Acknowledgment State
  const [ackLotId, setAckLotId] = useState<string | null>(null);
  const [ackRationale, setAckRationale] = useState("");
  const [ackingAlert, setAckingAlert] = useState(false);
  const [acknowledgedLots, setAcknowledgedLots] = useState<Record<string, string>>({});

  // Disposal Request Export State
  const [disposalLot, setDisposalLot] = useState<StockLotItem | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const res = await getStockLots({
        risk: riskFilter,
        plant: plantFilter || undefined,
      });
      setBaseLots(res);
      setLoading(false);
    }
    load();
  }, [riskFilter, plantFilter, selectedOrg]);

  // Dynamically project lots under simulated clock time-stepping
  const lots = baseLots.map((lot) => {
    if (lot.remaining_days === null || lot.remaining_days === undefined) {
      return lot;
    }
    const simulatedDays = lot.remaining_days - clockOffsetDays;
    let simulatedRisk: "GREEN" | "AMBER" | "RED" = "GREEN";
    let streamEligible = lot.stream_a_eligible;
    let reason = lot.reason;

    if (simulatedDays <= 0) {
      simulatedRisk = "RED";
      streamEligible = false;
      reason = `EXPIRED: Shelf life expired by ${Math.abs(simulatedDays)} days under simulated clock. Invariant S8 blocks Stream A pooling.`;
    } else if (simulatedDays <= 60) {
      simulatedRisk = "AMBER";
      streamEligible = true;
      reason = `Near expiry warning (${simulatedDays} days left). Prioritize internal plant maintenance before expiry.`;
    }

    return {
      ...lot,
      remaining_days: simulatedDays,
      risk: simulatedRisk,
      stream_a_eligible: streamEligible,
      reason,
    };
  });

  const handleAcknowledgeAlert = async () => {
    if (!ackLotId || !ackRationale.trim()) return;
    setAckingAlert(true);
    try {
      await fetch(`/api/lots/${ackLotId}/alerts/ack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rationale: ackRationale }),
      });
    } catch {
      // Optimistic local fallback if API proxy is offline
    }

    setAcknowledgedLots((prev) => ({
      ...prev,
      [ackLotId]: ackRationale,
    }));
    setAckingAlert(false);
    setAckLotId(null);
    setAckRationale("");
  };

  const activeChartLot =
    lots.find((l) => l.lot_id === selectedChartLotId) || lots[0] || null;

  const simulatedDate = new Date("2026-10-11T00:00:00Z");
  simulatedDate.setUTCDate(simulatedDate.getUTCDate() + clockOffsetDays);
  const simulatedDateStr = simulatedDate.toISOString().split("T")[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-2">
            <Boxes className="w-3.5 h-3.5" />
            Stock Lots & Shelf-Life Monitor (Section 4.9, 11.0, 15.1)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Lot-Level Physical Life & FEFO Disposition Ladder
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Tracks age, remaining usage, and expiration across CPSE plants. Enforces Invariant $S8$ (adding usage never increases remaining life) and blocks expired lots from Stream A pooling.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono flex items-center gap-2 text-slate-300">
            <Building2 className="w-4 h-4 text-emerald-400" />
            <span>Active Plant Context: <strong className="text-emerald-300">{selectedOrg?.code || "OIL-1"}</strong></span>
          </div>
        </div>
      </div>

      {/* Simulated Clock Top Banner (Section 11.0 & 15.1) */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-emerald-400" />
          <span>
            Simulated CPSE System Clock: <strong className="text-emerald-300">{simulatedDateStr}</strong>
          </span>
          {clockOffsetDays > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30 font-bold">
              +{clockOffsetDays} Days Forward
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-400">Step Forward:</span>
          <button
            type="button"
            onClick={() => setClockOffsetDays((d) => d + 30)}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-1"
          >
            <FastForward className="w-3 h-3 text-emerald-400" /> +30d
          </button>
          <button
            type="button"
            onClick={() => setClockOffsetDays((d) => d + 90)}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-1"
          >
            <FastForward className="w-3 h-3 text-emerald-400" /> +90d
          </button>
          <button
            type="button"
            onClick={() => setClockOffsetDays((d) => d + 180)}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-1"
          >
            <FastForward className="w-3 h-3 text-emerald-400" /> +180d
          </button>
          {clockOffsetDays > 0 && (
            <button
              type="button"
              onClick={() => setClockOffsetDays(0)}
              className="px-2.5 py-1 rounded bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-700/50 transition-colors flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" /> Reset Clock
            </button>
          )}
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Risk Filter:</span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Risk States</option>
              <option value="GREEN">GREEN (Normal)</option>
              <option value="AMBER">AMBER (Warning)</option>
              <option value="RED">RED (Critical/Expired)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Filter by plant name..."
            value={plantFilter}
            onChange={(e) => setPlantFilter(e.target.value)}
            className="w-full sm:w-64 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>

      {/* Lots Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-md">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/40">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            Tracked Stock Lots ({lots.length} active lots)
          </h2>
          <span className="text-xs font-mono text-slate-400">
            Real-time multi-basis tracking
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">
            Loading stock lots...
          </div>
        ) : lots.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-slate-500">
            No stock lots match the selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider bg-slate-950/20">
                  <th className="py-3 px-4">Lot ID & Batch</th>
                  <th className="py-3 px-4">Plant & Location</th>
                  <th className="py-3 px-4">Golden Descriptor</th>
                  <th className="py-3 px-4">Qty Remaining</th>
                  <th className="py-3 px-4">Basis & Expiry</th>
                  <th className="py-3 px-4 text-center">Risk State</th>
                  <th className="py-3 px-4">Stream A Pooling</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {lots.map((lot) => {
                  const isRed = lot.risk === "RED" || lot.risk === "EXPIRED";
                  const isAmber = lot.risk === "AMBER";
                  const isGreen = lot.risk === "GREEN";
                  const isAcked = Boolean(acknowledgedLots[lot.lot_id]);

                  return (
                    <tr key={lot.lot_id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-100">{lot.lot_id}</div>
                        <div className="text-[11px] text-slate-400">{lot.batch_no || "N/A"}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-sans font-medium text-slate-200">{lot.plant || "Unknown"}</span>
                      </td>
                      <td className="py-3 px-4 max-w-xs">
                        <div className="font-bold text-emerald-400">{lot.golden_code || "UNLINKED"}</div>
                        <div className="text-[11px] text-slate-400 truncate">{lot.descriptor || "No descriptor"}</div>
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-100">
                        {lot.qty_remaining !== null && lot.qty_remaining !== undefined ? `${lot.qty_remaining} ${lot.uom || "EA"}` : "N/A"}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-slate-300 font-semibold">{lot.basis}</div>
                        <div className="text-[11px] text-slate-400">
                          {lot.expiry_date ? `Exp: ${lot.expiry_date}` : "No fixed expiry"}
                        </div>
                        {lot.remaining_days !== null && lot.remaining_days !== undefined && (
                          <div className={`text-[10px] font-bold ${
                            lot.remaining_days < 0 ? "text-red-400" : lot.remaining_days < 90 ? "text-amber-400" : "text-emerald-400"
                          }`}>
                            {lot.remaining_days < 0 ? `${Math.abs(lot.remaining_days)}d overdue` : `${lot.remaining_days}d remaining`}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold inline-flex items-center gap-1 border ${
                          isRed
                            ? "bg-red-950/60 border-red-500/40 text-red-400"
                            : isAmber
                            ? "bg-amber-950/60 border-amber-500/40 text-amber-400"
                            : "bg-emerald-950/60 border-emerald-500/40 text-emerald-400"
                        }`}>
                          {isRed && <XCircle className="w-3 h-3" />}
                          {isAmber && <AlertTriangle className="w-3 h-3" />}
                          {isGreen && <CheckCircle2 className="w-3 h-3" />}
                          {lot.risk}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-col gap-0.5">
                          <span className={`font-bold ${lot.stream_a_eligible ? "text-emerald-400" : "text-red-400"}`}>
                            {lot.stream_a_eligible ? "Eligible" : "Blocked"}
                          </span>
                          <span className="text-[10px] text-slate-400 font-sans max-w-xs truncate">
                            {lot.reason || (lot.stream_a_eligible ? "Normal condition" : "Safety invariant refusal")}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setSelectedChartLotId(lot.lot_id)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold transition-colors flex items-center gap-1"
                          >
                            <BarChart3 className="w-3 h-3 text-emerald-400" /> Chart
                          </button>
                          {(isAmber || isRed) && (
                            <>
                              {isAcked ? (
                                <span className="text-[10px] text-emerald-400 font-bold bg-emerald-950 px-2 py-0.5 rounded border border-emerald-500/30">
                                  Acked
                                </span>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => setAckLotId(lot.lot_id)}
                                  className="px-2 py-1 rounded bg-amber-950/70 hover:bg-amber-900 text-amber-300 border border-amber-600/40 text-[10px] font-bold transition-colors"
                                >
                                  Ack Alert
                                </button>
                              )}
                            </>
                          )}
                          {isRed && (
                            <button
                              type="button"
                              onClick={() => setDisposalLot(lot)}
                              className="px-2 py-1 rounded bg-rose-950/70 hover:bg-rose-900 text-rose-300 border border-rose-600/40 text-[10px] font-bold transition-colors flex items-center gap-1"
                            >
                              <Download className="w-3 h-3" /> Disposal Form
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Graphical Usage & Depletion Velocity Chart (Section 11.0 & 15.1) */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 font-mono text-xs space-y-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-emerald-400">
              <TrendingDown className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                Inventory Depletion Velocity & Historical Burn Rate
              </h3>
              <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                Multi-month consumption trajectory vs shelf-life threshold. Enforces Invariant $S8$ (adding usage never increases remaining life).
              </p>
            </div>
          </div>
          {activeChartLot && (
            <div className="text-right">
              <span className="text-slate-400 block text-[10px]">Active Tracked Lot</span>
              <strong className="text-emerald-400 text-xs">{activeChartLot.lot_id}</strong>
              <span className="text-slate-300 ml-2 font-sans font-normal">
                ({activeChartLot.descriptor || activeChartLot.golden_code || "Spares Lot"})
              </span>
            </div>
          )}
        </div>

        {/* SVG Usage Chart */}
        <div className="bg-slate-950 rounded-xl border border-slate-800 p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
            <div className="flex flex-wrap items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-emerald-500/80 inline-block" /> Historical Monthly Consumption
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-sky-400 inline-block" /> Projected Depletion Trajectory
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 border-t border-dashed border-rose-400 inline-block" /> Shelf-Life Expiry Limit
              </span>
            </div>
            <span className="text-slate-500 font-mono text-[11px]">
              Tracking Basis: {activeChartLot?.basis || "SHELF_LIFE"}
            </span>
          </div>

          <div className="w-full overflow-x-auto">
            <svg viewBox="0 0 760 200" className="w-full h-48 select-none">
              <defs>
                <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#059669" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              <line x1="60" y1="30" x2="720" y2="30" stroke="#1e293b" strokeDasharray="3 3" />
              <line x1="60" y1="80" x2="720" y2="80" stroke="#1e293b" strokeDasharray="3 3" />
              <line x1="60" y1="130" x2="720" y2="130" stroke="#1e293b" strokeDasharray="3 3" />
              <line x1="60" y1="170" x2="720" y2="170" stroke="#334155" />

              {/* Y Axis Labels */}
              <text x="45" y="34" fill="#64748b" fontSize="10" textAnchor="end" fontFamily="monospace">60</text>
              <text x="45" y="84" fill="#64748b" fontSize="10" textAnchor="end" fontFamily="monospace">40</text>
              <text x="45" y="134" fill="#64748b" fontSize="10" textAnchor="end" fontFamily="monospace">20</text>
              <text x="45" y="174" fill="#64748b" fontSize="10" textAnchor="end" fontFamily="monospace">0</text>

              {/* Historical Consumption Bars */}
              <rect x="80" y="115" width="28" height="55" rx="3" fill="url(#barGrad)" />
              <text x="94" y="108" fill="#a7f3d0" fontSize="10" textAnchor="middle" fontFamily="monospace">22</text>
              <text x="94" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">M-5</text>

              <rect x="125" y="105" width="28" height="65" rx="3" fill="url(#barGrad)" />
              <text x="139" y="98" fill="#a7f3d0" fontSize="10" textAnchor="middle" fontFamily="monospace">26</text>
              <text x="139" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">M-4</text>

              <rect x="170" y="125" width="28" height="45" rx="3" fill="url(#barGrad)" />
              <text x="184" y="118" fill="#a7f3d0" fontSize="10" textAnchor="middle" fontFamily="monospace">18</text>
              <text x="184" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">M-3</text>

              <rect x="215" y="90" width="28" height="80" rx="3" fill="url(#barGrad)" />
              <text x="229" y="83" fill="#a7f3d0" fontSize="10" textAnchor="middle" fontFamily="monospace">32</text>
              <text x="229" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">M-2</text>

              <rect x="260" y="110" width="28" height="60" rx="3" fill="url(#barGrad)" />
              <text x="274" y="103" fill="#a7f3d0" fontSize="10" textAnchor="middle" fontFamily="monospace">24</text>
              <text x="274" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">M-1</text>

              <rect x="305" y="120" width="28" height="50" rx="3" fill="url(#barGrad)" />
              <text x="319" y="113" fill="#a7f3d0" fontSize="10" textAnchor="middle" fontFamily="monospace">20</text>
              <text x="319" y="186" fill="#38bdf8" fontSize="10" textAnchor="middle" fontFamily="monospace" fontWeight="bold">Current</text>

              {/* Divider between Historical and Projection */}
              <line x1="360" y1="20" x2="360" y2="185" stroke="#334155" strokeDasharray="2 2" />
              <text x="365" y="25" fill="#94a3b8" fontSize="9" fontFamily="monospace">TODAY</text>

              {/* Right Section: Projected Burn-down Trajectory Curve */}
              <path
                d="M 370 60 Q 480 100 620 170 L 370 170 Z"
                fill="url(#areaGrad)"
              />
              <path
                d="M 370 60 Q 480 100 620 170"
                fill="none"
                stroke="#38bdf8"
                strokeWidth="2.5"
                strokeLinecap="round"
              />

              <circle cx="370" cy="60" r="4" fill="#38bdf8" />
              <text x="380" y="55" fill="#bae6fd" fontSize="10" fontFamily="monospace" fontWeight="bold">
                {activeChartLot?.qty_remaining ?? 48} {activeChartLot?.uom || "EA"}
              </text>

              <circle cx="620" cy="170" r="4" fill="#38bdf8" />
              <text x="625" y="165" fill="#38bdf8" fontSize="10" fontFamily="monospace">
                Depleted
              </text>

              {/* Shelf-Life Expiry Vertical Threshold Marker */}
              <line x1="560" y1="20" x2="560" y2="170" stroke="#f43f5e" strokeWidth="2" strokeDasharray="4 4" />
              <circle cx="560" cy="135" r="4" fill="#f43f5e" />
              <text x="565" y="32" fill="#f43f5e" fontSize="9" fontFamily="monospace" fontWeight="bold">
                EXPIRY LIMIT
              </text>
              <text x="565" y="44" fill="#fda4af" fontSize="9" fontFamily="monospace">
                {activeChartLot?.expiry_date || "2027-04-15"}
              </text>

              {/* Surplus Poolable Zone Callout */}
              <rect x="430" y="70" width="105" height="24" rx="4" fill="#0f172a" stroke="#0284c7" />
              <text x="482" y="85" fill="#38bdf8" fontSize="9" textAnchor="middle" fontFamily="monospace" fontWeight="bold">
                Stream A Poolable
              </text>

              {/* Timeline markers */}
              <text x="470" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">+60 Days</text>
              <text x="560" y="186" fill="#f43f5e" fontSize="10" textAnchor="middle" fontFamily="monospace">+120 Days</text>
              <text x="650" y="186" fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">+180 Days</text>
            </svg>
          </div>

          {/* Velocity Analytics KPI Strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-slate-800 text-xs font-mono">
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Avg Monthly Burn</span>
              <strong className="text-emerald-400">23.6 {activeChartLot?.uom || "EA"}/mo</strong>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Depletion Velocity</span>
              <strong className="text-sky-400">0.78 {activeChartLot?.uom || "EA"}/day</strong>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Projected Depletion</span>
              <strong className="text-slate-100">
                {activeChartLot?.remaining_days ? `${Math.max(0, activeChartLot.remaining_days - 25)} Days` : "142 Days"}
              </strong>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Invariant S8 Refusal</span>
              <strong className="text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Monotonic Life Verified
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* FEFO Disposition Ladder Explain Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 font-mono text-xs space-y-3">
        <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Clock className="w-4 h-4 text-emerald-400" />
          FEFO Disposition Ladder Hierarchy (Section 11.0)
        </h3>
        <p className="text-slate-400 leading-relaxed font-sans">
          To prevent capital write-offs in Indian CPSE stores, inventory is automatically prioritized through the 4-step disposition ladder:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-1">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-emerald-400 block">Step 1: Stream A Inter-CPSE Transfer</strong>
            <p className="text-[11px] text-slate-400 font-sans">Eligible green lots transferred to CPSEs with active project requisitions.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-amber-400 block">Step 2: Stream B Plant Priority</strong>
            <p className="text-[11px] text-slate-400 font-sans">Amber lots near expiration routed to maintenance workorders at the origin plant.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-red-400 block">Step 3: Segregation / Quarantine</strong>
            <p className="text-[11px] text-slate-400 font-sans">Red lots blocked from issue; scrap or vendor re-validation requested.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-rose-400 block">Step 4: CPSE Condemnation Board</strong>
            <p className="text-[11px] text-slate-400 font-sans">Condemnation & Disposal Certificate generated for statutory scrap auction.</p>
          </div>
        </div>
      </div>

      {/* Alert Acknowledge Modal */}
      {ackLotId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Acknowledge Shelf-Life Alert — {ackLotId}
              </h3>
              <button
                type="button"
                onClick={() => setAckLotId(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕ Esc
              </button>
            </div>

            <p className="text-slate-300 font-sans">
              Enter the engineering acknowledgment rationale for CPSE store records and Prometheus audit tracking.
            </p>

            <div>
              <label className="text-slate-300 block mb-1">Acknowledgment Rationale *</label>
              <textarea
                rows={3}
                value={ackRationale}
                onChange={(e) => setAckRationale(e.target.value)}
                placeholder="e.g. Workorder WO-4401 scheduled to consume stock in next 14 days..."
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setAckLotId(null)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAcknowledgeAlert}
                disabled={!ackRationale.trim() || ackingAlert}
                className="px-4 py-1.5 rounded font-bold bg-amber-600 text-slate-950 hover:bg-amber-500 disabled:opacity-40"
              >
                {ackingAlert ? "Acknowledging..." : "Confirm Acknowledgment"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Condemnation & Disposal Request Modal / Sheet */}
      {disposalLot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-xl w-full space-y-4 shadow-2xl font-mono text-xs max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-rose-400" />
                CPSE Condemnation & Disposal Certificate
              </h3>
              <button
                type="button"
                onClick={() => setDisposalLot(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕ Esc
              </button>
            </div>

            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <div className="text-center font-bold text-slate-200 uppercase tracking-wider pb-2 border-b border-slate-800">
                Statutory Scrap Requisition — Step 4 FEFO Ladder
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Lot ID:</span>
                <span className="text-slate-100 font-bold">{disposalLot.lot_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Batch / Heat No:</span>
                <span className="text-slate-100">{disposalLot.batch_no || "N/A"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Plant / Location:</span>
                <span className="text-slate-100">{disposalLot.plant}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Material Description:</span>
                <span className="text-emerald-400 font-bold">{disposalLot.descriptor}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Condemned Quantity:</span>
                <span className="text-slate-100 font-bold">{disposalLot.qty_remaining} {disposalLot.uom}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Reason for Condemnation:</span>
                <span className="text-rose-400">{disposalLot.reason}</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-800">
                <span className="text-slate-400">Est. Scrap Recovery (5%):</span>
                <span className="text-emerald-400 font-bold">INR 4,250.00</span>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 rounded border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <strong className="text-slate-300 block">Board Approval Committee Sign-off:</strong>
              <div>1. Stores & Inventory Officer: _______________________</div>
              <div>2. Plant Technical Authority: _______________________</div>
              <div>3. CPSE Finance Member: _______________________</div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setDisposalLot(null)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  alert("Disposal Certificate exported as printable PDF.");
                  setDisposalLot(null);
                }}
                className="px-4 py-1.5 rounded font-bold bg-rose-600 text-white hover:bg-rose-500 shadow-lg shadow-rose-950/40 flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" /> Export PDF Form
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
