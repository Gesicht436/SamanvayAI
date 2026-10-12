"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  listTransfers,
  advanceTransferGate,
  getForwardIndents,
  createTenderPool,
  getTenderPools,
  getTenderPack,
} from "@/lib/api";
import {
  TransferOrderItem,
  ForwardIndentItem,
  TenderPoolItem,
  TenderPackResponse,
} from "@/types";
import {
  Truck,
  Layers,
  ArrowRightLeft,
  Building2,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Plus,
  ShieldCheck,
  TrendingDown,
  X,
  AlertCircle,
  FileSpreadsheet,
} from "lucide-react";

export default function ProcurementHubPage() {
  const { user, selectedOrg } = useAuth();
  const [activeTab, setActiveTab] = useState<"stream-a" | "stream-b">("stream-a");

  // Stream A states
  const [transfers, setTransfers] = useState<{ incoming: TransferOrderItem[]; outgoing: TransferOrderItem[] }>({
    incoming: [],
    outgoing: [],
  });
  const [loadingTransfers, setLoadingTransfers] = useState(false);
  const [reviewModalTransfer, setReviewModalTransfer] = useState<TransferOrderItem | null>(null);
  const [gateAction, setGateAction] = useState("TECHNICAL_REVIEW");
  const [gateRationale, setGateRationale] = useState("");
  const [gateMtc, setGateMtc] = useState(true);
  const [gatePmi, setGatePmi] = useState(false);
  const [gateFeedback, setGateFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  // Stream B states
  const [indents, setIndents] = useState<ForwardIndentItem[]>([]);
  const [pools, setPools] = useState<TenderPoolItem[]>([]);
  const [selectedIndentIds, setSelectedIndentIds] = useState<string[]>([]);
  const [tenderPackData, setTenderPackData] = useState<TenderPackResponse | null>(null);
  const [poolingFeedback, setPoolingFeedback] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoadingTransfers(true);
      const trf = await listTransfers();
      setTransfers(trf);
      setLoadingTransfers(false);

      const ind = await getForwardIndents();
      setIndents(ind);

      const pl = await getTenderPools();
      setPools(pl);
    }
    load();
  }, [selectedOrg]);

  async function handleGateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewModalTransfer) return;
    setGateFeedback(null);

    const res = await advanceTransferGate(
      reviewModalTransfer.id,
      {
        action: gateAction,
        rationale: gateRationale || "Workflow progression by steward",
        mtc_uploaded: gateMtc,
        pmi_done: gatePmi,
      },
      user
    );

    if (res.success) {
      setGateFeedback({ type: "success", msg: res.message });
      const updated = await listTransfers();
      setTransfers(updated);
      setTimeout(() => {
        setReviewModalTransfer(null);
        setGateFeedback(null);
        setGateRationale("");
      }, 1500);
    } else {
      setGateFeedback({ type: "error", msg: res.message });
    }
  }

  async function handleCreatePool() {
    if (selectedIndentIds.length === 0) return;
    setPoolingFeedback("Aggregating indents into joint tender pool...");
    const res = await createTenderPool({
      indent_ids: selectedIndentIds,
      mou_ref: `MOU-INTER-CPSE-${selectedOrg?.code || "OIL"}-2026`,
    });
    setPoolingFeedback(res.message);
    setSelectedIndentIds([]);
    const updatedPools = await getTenderPools();
    setPools(updatedPools);
    const updatedIndents = await getForwardIndents();
    setIndents(updatedIndents);
  }

  async function handleViewTenderPack(poolId: string) {
    const pack = await getTenderPack(poolId);
    setTenderPackData(pack);
  }

  function downloadFile(content: string, filename: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 mb-2">
            <Truck className="w-3.5 h-3.5" />
            Procurement Optimization (Section 8.1 & 13.0)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Inter-CPSE Surplus Transfer & Joint Demand Pooling Hub
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
            Stream A redeploys idle surplus inventory across CPSE plants to avoid fresh capital outlay. Stream B pools forward procurement requisitions for common Golden Masters to unlock volume discount curves.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono flex items-center gap-2 text-slate-700 dark:text-slate-300 shadow-sm">
            <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Active Org: <strong className="text-emerald-700 dark:text-emerald-300">{selectedOrg?.code || "OIL-1"}</strong></span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4">
        <button
          onClick={() => setActiveTab("stream-a")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "stream-a"
              ? "text-emerald-700 dark:text-emerald-400 border-emerald-600 dark:border-emerald-400"
              : "text-slate-500 dark:text-slate-400 border-transparent hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <ArrowRightLeft className="w-4 h-4" />
          <span>Stream A: Surplus Redeployment Transfers</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-transparent">
            {transfers.incoming.length + transfers.outgoing.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("stream-b")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "stream-b"
              ? "text-emerald-700 dark:text-emerald-400 border-emerald-600 dark:border-emerald-400"
              : "text-slate-500 dark:text-slate-400 border-transparent hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Stream B: Forward Demand Pooling & Tender Packs</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-transparent">
            {pools.length} Pools
          </span>
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: STREAM A SURPLUS TRANSFERS */}
      {/* ========================================================= */}
      {activeTab === "stream-a" && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">Active Requisitions</div>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 font-mono mt-1">
                {transfers.incoming.length + transfers.outgoing.length}
              </div>
              <div className="text-[11px] text-emerald-700 dark:text-emerald-400 mt-1 flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3 h-3" />
                Inter-CPSE Dual Governance
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">Avoided Purchase Cost</div>
              <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 font-mono mt-1">
                ₹{((transfers.incoming.reduce((acc, t) => acc + t.avoided_purchase_cost, 0) + transfers.outgoing.reduce((acc, t) => acc + t.avoided_purchase_cost, 0))).toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Avoided Fresh Market Buy</div>
            </div>

            <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">Net Financial Benefit</div>
              <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-400 font-mono mt-1">
                ₹{((transfers.incoming.reduce((acc, t) => acc + t.net_benefit, 0) + transfers.outgoing.reduce((acc, t) => acc + t.net_benefit, 0))).toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Net of Freight & Inspection</div>
            </div>
          </div>

          {/* Transfers Table */}
          <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-transparent">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Inter-CPSE Transfer Requisitions</h2>
              </div>
              <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                Maker-Checker Verified
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/60 font-mono text-slate-500 dark:text-slate-400 text-[11px]">
                    <th className="py-3 px-4">REQUISITION</th>
                    <th className="py-3 px-4">ITEM DESCRIPTOR</th>
                    <th className="py-3 px-4">ORGANISATIONS</th>
                    <th className="py-3 px-4">QUANTITY</th>
                    <th className="py-3 px-4">AVOIDED COST</th>
                    <th className="py-3 px-4">NET BENEFIT</th>
                    <th className="py-3 px-4">GATE STATUS</th>
                    <th className="py-3 px-4 text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                  {[...transfers.incoming, ...transfers.outgoing].map((trf) => (
                    <tr key={trf.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-4 font-mono">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">{trf.id}</div>
                        <div className="text-[10px] text-slate-400 dark:text-slate-500">{trf.created_at?.slice(0, 10)}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100">{trf.descriptor}</div>
                        <div className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400">{trf.golden_code}</div>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-[11px]">
                        <div>From: <strong className="text-slate-800 dark:text-slate-200">{trf.from_org}</strong></div>
                        <div className="text-slate-500 dark:text-slate-400">To: <strong className="text-slate-800 dark:text-slate-200">{trf.to_org}</strong></div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-medium text-slate-800 dark:text-slate-200">
                        {trf.qty} EA
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-800 dark:text-slate-200">
                        ₹{trf.avoided_purchase_cost.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-emerald-700 dark:text-emerald-400 font-semibold">
                        ₹{trf.net_benefit.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                          trf.state === "APPROVED"
                            ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/50"
                            : trf.state === "TECHNICAL_REVIEW"
                            ? "bg-blue-50 dark:bg-blue-950 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-500/50"
                            : trf.state === "COMMERCIAL_REVIEW"
                            ? "bg-purple-50 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-500/50"
                            : "bg-amber-50 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/50"
                        }`}>
                          {trf.state}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => setReviewModalTransfer(trf)}
                          className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-mono transition-all border border-slate-200 dark:border-transparent shadow-2xs"
                        >
                          Review Gate
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: STREAM B FORWARD DEMAND POOLING */}
      {/* ========================================================= */}
      {activeTab === "stream-b" && (
        <div className="space-y-8">
          {/* Section 1: Forward Indents Selection */}
          <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800/80 rounded-2xl overflow-hidden shadow-xs">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Open Forward Indents by CPSE Plants</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">Select open indents for the same Golden Master to pool forward capital demand.</p>
              </div>

              <button
                type="button"
                disabled={selectedIndentIds.length < 1}
                onClick={handleCreatePool}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold font-mono flex items-center gap-1.5 transition-all ${
                  selectedIndentIds.length >= 1
                    ? "bg-emerald-600 hover:bg-emerald-500 text-slate-950 shadow-md shadow-emerald-900/20"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed"
                }`}
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Pool Selected Indents ({selectedIndentIds.length})</span>
              </button>
            </div>

            {poolingFeedback && (
              <div className="px-6 py-2 bg-emerald-50 dark:bg-emerald-950/60 border-b border-emerald-200 dark:border-emerald-800/40 text-xs text-emerald-800 dark:text-emerald-300 font-mono">
                {poolingFeedback}
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/60 font-mono text-slate-500 dark:text-slate-400 text-[11px]">
                    <th className="py-3 px-4 w-10">SELECT</th>
                    <th className="py-3 px-4">INDENT ID</th>
                    <th className="py-3 px-4">CPSE & PLANT</th>
                    <th className="py-3 px-4">ITEM SPECIFICATION</th>
                    <th className="py-3 px-4">QUANTITY</th>
                    <th className="py-3 px-4">TARGET DELIVERY</th>
                    <th className="py-3 px-4">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                  {indents.map((ind) => (
                    <tr key={ind.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-4">
                        <input
                          type="checkbox"
                          disabled={ind.status === "POOLED"}
                          checked={selectedIndentIds.includes(ind.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedIndentIds([...selectedIndentIds, ind.id]);
                            } else {
                              setSelectedIndentIds(selectedIndentIds.filter((id) => id !== ind.id));
                            }
                          }}
                          className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-emerald-500 focus:ring-0"
                        />
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-900 dark:text-slate-200">
                        {ind.id}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{ind.org_name || ind.org_id}</div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">{ind.plant || "Store"}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100">{ind.descriptor}</div>
                        <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">{ind.golden_code}</div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-medium text-slate-900 dark:text-slate-200">
                        {ind.qty} {ind.uom}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-600 dark:text-slate-300">
                        {ind.need_by}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                          ind.status === "POOLED"
                            ? "bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-500/50"
                            : "bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/50"
                        }`}>
                          {ind.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 2: Joint Tender Pools & Tender Packs */}
          <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800/80 rounded-2xl overflow-hidden shadow-xs">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Aggregated Joint Tender Pools</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">Consolidated buyer volume unlocking bulk pooling discount curves.</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/60 font-mono text-slate-500 dark:text-slate-400 text-[11px]">
                    <th className="py-3 px-4">POOL ID & MOU REF</th>
                    <th className="py-3 px-4">LEAD BUYER</th>
                    <th className="py-3 px-4">POOLED SPECIFICATION</th>
                    <th className="py-3 px-4">COMBINED VOLUME</th>
                    <th className="py-3 px-4">BASELINE INR</th>
                    <th className="py-3 px-4">POOLED INR</th>
                    <th className="py-3 px-4">EST. SAVINGS</th>
                    <th className="py-3 px-4 text-right">TENDER PACK</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                  {pools.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-4 font-mono">
                        <div className="font-semibold text-slate-900 dark:text-slate-200">{p.id}</div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-500">{p.mou_ref}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{p.lead_org_name || p.lead_org}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100">{p.descriptor}</div>
                        <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">{p.golden_code}</div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        {p.total_qty.toLocaleString()} {p.canonical_uom}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-500 dark:text-slate-400">
                        ₹{p.estimated_baseline_cost.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-900 dark:text-slate-200">
                        ₹{p.estimated_pooled_cost.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                        ₹{p.estimated_savings.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => handleViewTenderPack(p.id)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs font-mono transition-all flex items-center gap-1.5 ml-auto shadow-sm"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>Tender Pack</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Review Gate Modal */}
      {reviewModalTransfer && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 dark:bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl relative">
            <button onClick={() => setReviewModalTransfer(null)} className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
              <X className="w-5 h-5" />
            </button>

            <div>
              <div className="text-xs font-mono text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-1">
                Maker-Checker Gate Progression
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">{reviewModalTransfer.id}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{reviewModalTransfer.descriptor}</p>
            </div>

            <form onSubmit={handleGateSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Target Workflow State</label>
                <select
                  value={gateAction}
                  onChange={(e) => setGateAction(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="TECHNICAL_REVIEW">Technical Review (MTC / PMI / Specs)</option>
                  <option value="COMMERCIAL_REVIEW">Commercial Review (Book Value / Settlement)</option>
                  <option value="APPROVED">Approve Transfer Order (Checker Role Required)</option>
                  <option value="DISPATCHED">Mark Dispatched</option>
                  <option value="COMPLETED">Mark Completed</option>
                  <option value="REJECTED">Reject Requisition</option>
                </select>
              </div>

              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={gateMtc}
                    onChange={(e) => setGateMtc(e.target.checked)}
                    className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-emerald-500 focus:ring-0"
                  />
                  <span>MTC EN 10204 3.1 Uploaded</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={gatePmi}
                    onChange={(e) => setGatePmi(e.target.checked)}
                    className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-emerald-500 focus:ring-0"
                  />
                  <span>PMI Chemical Test Verified</span>
                </label>
              </div>

              <div>
                <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Steward Engineering Rationale</label>
                <textarea
                  value={gateRationale}
                  onChange={(e) => setGateRationale(e.target.value)}
                  placeholder="Justification for gate progression..."
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-200 focus:outline-none focus:border-emerald-500 h-20 resize-none"
                  required
                />
              </div>

              {gateFeedback && (
                <div className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                  gateFeedback.type === "success" 
                    ? "bg-emerald-50 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800" 
                    : "bg-red-50 dark:bg-red-950/80 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800"
                }`}>
                  {gateFeedback.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                  <span>{gateFeedback.msg}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setReviewModalTransfer(null)}
                  className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs shadow-md shadow-emerald-900/20"
                >
                  Advance Gate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tender Pack View Modal */}
      {tenderPackData && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 dark:bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button onClick={() => setTenderPackData(null)} className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
              <X className="w-5 h-5" />
            </button>

            <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
              <div className="text-xs font-mono text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-1">
                Structured Tender Pack (Section 13.0)
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">{tenderPackData.tender_pack.title}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                Tender Ref: {tenderPackData.tender_pack.tender_id} • Lead Buyer: {tenderPackData.tender_pack.lead_buyer_name}
              </p>
            </div>

            {/* Consignee Allocation */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono uppercase text-slate-600 dark:text-slate-400 font-semibold">Consignee Distribution Table</h4>
              <div className="bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800/80 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 dark:bg-slate-900/80 font-mono text-slate-600 dark:text-slate-400 text-[10px]">
                    <tr>
                      <th className="p-2.5">CONSIGNEE CPSE</th>
                      <th className="p-2.5">PLANT SITE</th>
                      <th className="p-2.5">ALLOCATED QUANTITY</th>
                      <th className="p-2.5">TARGET DATE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800/50 text-slate-700 dark:text-slate-300">
                    {tenderPackData.tender_pack.consignee_distribution.map((c, idx) => (
                      <tr key={idx}>
                        <td className="p-2.5 font-semibold text-slate-900 dark:text-slate-200">{c.org_name}</td>
                        <td className="p-2.5 text-slate-500 dark:text-slate-400">{c.delivery_site}</td>
                        <td className="p-2.5 font-mono text-emerald-600 dark:text-emerald-400 font-bold">{c.allocated_qty} {c.uom}</td>
                        <td className="p-2.5 font-mono text-slate-600 dark:text-slate-300">{c.need_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Statutory Checklists */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono uppercase text-slate-600 dark:text-slate-400 font-semibold">Technical Compliance & Make-in-India Requirements</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {tenderPackData.tender_pack.technical_compliance_checklist.map((chk, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-slate-200">{chk.standard}</div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{chk.clause}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => downloadFile(JSON.stringify(tenderPackData.tender_pack, null, 2), `${tenderPackData.tender_pack.tender_id}.json`, "application/json")}
                className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON Pack</span>
              </button>

              <button
                type="button"
                onClick={() => downloadFile(tenderPackData.csv_export, `${tenderPackData.tender_pack.tender_id}_boq.csv`, "text/csv")}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-emerald-900/20"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Export BoQ (CSV)</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
