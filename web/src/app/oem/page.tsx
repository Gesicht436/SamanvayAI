"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  DEMO_OEM_BATCH,
  getOemProposals,
  reviewOemProposal,
  approveOemBatch,
  uploadOemCatalogue,
} from "@/lib/api";
import { OemProposalItem, OemBatchData } from "@/types";
import {
  Factory,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  FileSpreadsheet,
  Check,
  RotateCcw,
} from "lucide-react";

export default function OemOnboardingPage() {
  const { user } = useAuth();
  const [batch, setBatch] = useState<OemBatchData>(DEMO_OEM_BATCH);
  const [proposals, setProposals] = useState<OemProposalItem[]>(DEMO_OEM_BATCH.proposals);
  const [rationale, setRationale] = useState("OEM Sulzer pump spare manual cross-referenced and verified.");
  const [statusMessage, setStatusMessage] = useState<{ text: string; error?: boolean } | null>(null);
  const [isApproving, setIsApproving] = useState(false);

  const handleReview = async (id: number, action: "ACCEPT" | "REJECT") => {
    setStatusMessage(null);
    const res = await reviewOemProposal(id, action, user);
    if (!res.success) {
      setStatusMessage({ text: res.message, error: true });
      return;
    }
    setProposals((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: action === "ACCEPT" ? "ACCEPTED" : "REJECTED" } : p))
    );
    setStatusMessage({ text: res.message });
  };

  const handleApprove = async () => {
    setStatusMessage(null);
    setIsApproving(true);
    const res = await approveOemBatch(batch.batch_id, rationale, user);
    setIsApproving(false);
    if (!res.success) {
      setStatusMessage({ text: res.message, error: true });
      return;
    }
    setBatch((prev) => ({ ...prev, status: "COMPLETED" }));
    setProposals((prev) => prev.map((p) => ({ ...p, status: "APPROVED" })));
    setStatusMessage({ text: res.message });
  };

  const handleResetDemo = () => {
    setBatch({ ...DEMO_OEM_BATCH, status: "PENDING_REVIEW" });
    setProposals(DEMO_OEM_BATCH.proposals.map((p, idx) => ({ ...p, status: idx === 1 ? "ACCEPTED" : "PROPOSED" })));
    setStatusMessage({ text: "Reset demo batch." });
  };

  const canApprove = user.role === "CHECKER" || user.role === "ADMIN";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 mb-2">
            <Factory className="w-3.5 h-3.5" />
            OEM Catalogue Onboarding Wizard (Section 20.2)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Bulk OEM Spares Ingestion & Supersession Mapping
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Automates OEM part normalization, detects supersession chains, generates draft masters under <code>OEM_PN</code> mode, and enforces Maker-Checker dual governance.
          </p>
        </div>

        <button
          onClick={handleResetDemo}
          className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-800 text-xs font-mono text-slate-700 dark:text-slate-300 flex items-center gap-1.5 self-start sm:self-auto transition-colors shadow-2xs"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset Demo
        </button>
      </div>

      {/* Batch Header Card */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4 font-mono text-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <span className="text-base font-bold text-slate-900 dark:text-slate-100">{batch.filename}</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              batch.status === "COMPLETED"
                ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30"
                : "bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30"
            }`}>
              {batch.status}
            </span>
          </div>
          <div className="text-slate-500 dark:text-slate-400 text-[11px] font-sans">
            OEM Manufacturer: <strong className="text-slate-800 dark:text-slate-200">{batch.oem_name}</strong> | Batch ID: <code>{batch.batch_id}</code>
          </div>
        </div>

        <div className="flex items-center gap-4 text-slate-700 dark:text-slate-300">
          <div>
            <span className="text-slate-400 dark:text-slate-500 block text-[10px]">TOTAL ITEMS</span>
            <span className="text-base font-bold text-slate-900 dark:text-slate-100">{batch.total_rows}</span>
          </div>
          <div>
            <span className="text-slate-400 dark:text-slate-500 block text-[10px]">SUPERSEDED DETECTED</span>
            <span className="text-base font-bold text-amber-600 dark:text-amber-400">{batch.superseded_count}</span>
          </div>
        </div>
      </div>

      {/* Feedback Alert */}
      {statusMessage && (
        <div
          className={`p-4 rounded-xl text-xs font-mono flex items-center gap-2 border ${
            statusMessage.error
              ? "bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-500/40 text-red-800 dark:text-red-300"
              : "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-500/40 text-emerald-800 dark:text-emerald-300"
          }`}
        >
          {statusMessage.error ? <AlertTriangle className="w-4 h-4 shrink-0" /> : <CheckCircle2 className="w-4 h-4 shrink-0" />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Proposals Table */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50/80 dark:bg-slate-950/40">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Proposed Catalogue Items (Draft Masters)
          </h2>
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
            {proposals.length} item proposals
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-wider bg-slate-50/50 dark:bg-slate-950/20">
                <th className="py-3 px-4">Raw Part No</th>
                <th className="py-3 px-4">Normalized</th>
                <th className="py-3 px-4">Effective PN (Supersession)</th>
                <th className="py-3 px-4">Description & Spans</th>
                <th className="py-3 px-4">Subcategory</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Maker Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-200">
              {proposals.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-100">{p.raw_part_number}</td>
                  <td className="py-3 px-4 text-slate-500 dark:text-slate-400">{p.norm_part_number}</td>
                  <td className="py-3 px-4">
                    <div className="flex flex-col gap-1">
                      <span className="font-bold text-emerald-600 dark:text-emerald-400">{p.effective_part_number}</span>
                      {p.superseded_from && (
                        <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.2 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30 w-fit">
                          Supersedes: {p.superseded_from}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 max-w-sm">
                    <div className="font-sans text-slate-700 dark:text-slate-300 text-[11px] leading-relaxed">
                      {p.raw_description}
                    </div>
                    {p.evidence_spans && Object.keys(p.evidence_spans).length > 0 && (
                      <div className="mt-1 flex gap-1.5 text-[10px] text-slate-400 dark:text-slate-500">
                        {Object.entries(p.evidence_spans).map(([key, span]) => (
                          <span key={key} className="px-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            {key}: [{span[0]}, {span[1]}]
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {p.subcategory || "COMMON"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        p.status === "APPROVED"
                          ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/40"
                          : p.status === "ACCEPTED"
                          ? "bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-500/40"
                          : p.status === "REJECTED"
                          ? "bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-500/40"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    {p.status !== "APPROVED" && (
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleReview(p.id, "ACCEPT")}
                          disabled={user.role !== "MAKER" && user.role !== "ADMIN"}
                          title={user.role !== "MAKER" && user.role !== "ADMIN" ? "Only Makers can review" : "Accept draft proposal"}
                          className="px-2.5 py-1 rounded bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-500/40 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 disabled:opacity-40 transition-colors text-[11px] font-sans font-medium flex items-center gap-1 shadow-2xs"
                        >
                          <Check className="w-3 h-3" />
                          Accept
                        </button>
                        <button
                          onClick={() => handleReview(p.id, "REJECT")}
                          disabled={user.role !== "MAKER" && user.role !== "ADMIN"}
                          title={user.role !== "MAKER" && user.role !== "ADMIN" ? "Only Makers can review" : "Reject draft proposal"}
                          className="px-2.5 py-1 rounded bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-500/40 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/60 disabled:opacity-40 transition-colors text-[11px] font-sans font-medium flex items-center gap-1 shadow-2xs"
                        >
                          <XCircle className="w-3 h-3" />
                          Reject
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Maker-Checker Approval Section */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-xs">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Checker Dual-Governance Approval Gate
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enforces Maker != Checker rule and requires appropriate domain authorization tags before publishing active Golden Masters.
            </p>
          </div>
          <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
            Current User: <strong className="text-emerald-600 dark:text-emerald-400">{user.name}</strong> ({user.role})
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-mono text-slate-700 dark:text-slate-300 block">
            Verification & Approval Rationale:
          </label>
          <input
            type="text"
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            disabled={batch.status === "COMPLETED"}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
          />
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            {!canApprove && (
              <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1 font-semibold">
                <AlertTriangle className="w-3.5 h-3.5" />
                Switch user role to CHECKER or ADMIN to execute final batch publication.
              </span>
            )}
            {canApprove && batch.status !== "COMPLETED" && (
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Authorized. Ready to publish Golden Masters with transactional audit logging.
              </span>
            )}
          </div>

          <button
            onClick={handleApprove}
            disabled={!canApprove || batch.status === "COMPLETED" || isApproving}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:text-slate-400 dark:disabled:text-slate-500 text-slate-950 font-bold text-xs font-mono transition-colors flex items-center gap-2 self-end shadow-xs"
          >
            <CheckCircle2 className="w-4 h-4" />
            {batch.status === "COMPLETED" ? "Batch Completed" : "Approve & Publish Batch"}
          </button>
        </div>
      </div>
    </div>
  );
}
