"use client";

import React from "react";
import { CandidateMaster } from "@/types";
import { TierBadge, VerdictBadge, RoleBadge } from "@/components/common/Badge";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
  ArrowRight,
  FileText,
} from "lucide-react";

interface DiffInspectorProps {
  candidate: CandidateMaster;
  rawText?: string;
  onBack?: () => void;
  onProposeTask?: (candidate: CandidateMaster) => void;
}

export function DiffInspector({
  candidate,
  rawText,
  onBack,
  onProposeTask,
}: DiffInspectorProps) {
  const hasHardMismatch = candidate.verdicts.some(
    (v) => v.role === "HARD" && v.verdict === "MISMATCH"
  );
  const hasMissingRequired = candidate.verdicts.some(
    (v) => (v.role === "HARD" || v.role === "REQUIRED") && v.verdict === "MISSING"
  );
  const isAllExact = candidate.verdicts.every(
    (v) => v.role === "SOFT" || v.verdict === "EXACT"
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-6 shadow-xl">
      {/* Screen Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              Diff Inspector
              <span className="text-xs font-mono font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                Explains the decision
              </span>
            </h2>
            <TierBadge tier={candidate.tier} />
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic attribute comparator verdict matrix. Evaluates physical safety lattices and invariants S1–S15.
          </p>
        </div>

        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="text-xs px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            ← Back to Candidates
          </button>
        )}
      </div>

      {/* Target Golden Master Overview */}
      <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2 font-mono">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>Target Golden Master Code</span>
          <span className="text-slate-200">Similarity Probability: {(candidate.prob * 100).toFixed(1)}%</span>
        </div>
        <div className="text-emerald-400 font-bold text-sm">
          {candidate.golden_code}
        </div>
        <div className="text-xs text-slate-300">
          {candidate.descriptor}
        </div>
        {rawText && (
          <div className="text-xs text-slate-400 pt-2 border-t border-slate-800 flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            <span>Raw Query: <strong className="text-slate-200">{rawText}</strong></span>
          </div>
        )}
      </div>

      {/* Decision Explanation / Safety Banners */}
      {hasHardMismatch && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-200 flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <strong className="font-semibold text-rose-300 block">
              SAFETY REFUSAL: Hard Attribute Mismatch Detected (Tier 3)
            </strong>
            <p className="text-rose-200/90 leading-relaxed">
              One or more HARD physical attributes mismatch the canonical master. Safety Invariants S1 and S4 strictly block Tier 1 auto-harmonization to prevent catastrophic physical mis-specification in hazardous operating environments.
            </p>
          </div>
        </div>
      )}

      {!hasHardMismatch && hasMissingRequired && (
        <div className="p-4 rounded-lg bg-amber-950/60 border border-amber-500/40 text-amber-200 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <strong className="font-semibold text-amber-300 block">
              SAFETY ROUTING: Required Attribute Gap (Tier 2 Steward Review)
            </strong>
            <p className="text-amber-200/90 leading-relaxed">
              Required attributes are unspecified on the raw item. Per Safety Invariant S1, this item is routed to the human stewardship queue for technical datasheet review.
            </p>
          </div>
        </div>
      )}

      {isAllExact && candidate.tier === 1 && (
        <div className="p-4 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <strong className="font-semibold text-emerald-300 block">
              SPECIFICATION COMPLIANT: All Hard & Required Attributes Match (Tier 1)
            </strong>
            <p className="text-emerald-200/90 leading-relaxed">
              Deterministic comparator verified 100% equivalence across critical dimensions, electrical ratings, and safety parameters.
            </p>
          </div>
        </div>
      )}

      {/* Attribute Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 uppercase text-[11px] bg-slate-950/50">
              <th className="py-2.5 px-3">Attribute</th>
              <th className="py-2.5 px-3">Role</th>
              <th className="py-2.5 px-3">Raw Item Extracted</th>
              <th className="py-2.5 px-3 text-center">→</th>
              <th className="py-2.5 px-3">Golden Master</th>
              <th className="py-2.5 px-3">Verdict</th>
              <th className="py-2.5 px-3">Engineering Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {candidate.verdicts.map((v) => (
              <tr
                key={v.attr}
                className={`hover:bg-slate-800/40 transition-colors ${
                  v.verdict === "MISMATCH"
                    ? "bg-rose-950/20"
                    : v.verdict === "MISSING"
                    ? "bg-amber-950/15"
                    : ""
                }`}
              >
                <td className="py-3 px-3 font-semibold text-slate-200">
                  {v.attr}
                </td>
                <td className="py-3 px-3">
                  <RoleBadge role={v.role} />
                </td>
                <td className="py-3 px-3">
                  {v.raw !== null ? (
                    <span className="text-slate-100 font-semibold bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      {String(v.raw)}
                    </span>
                  ) : (
                    <span className="text-amber-400/80 italic font-normal">
                      [Missing]
                    </span>
                  )}
                </td>
                <td className="py-3 px-3 text-center text-slate-600">
                  <ArrowRight className="w-3.5 h-3.5 inline" />
                </td>
                <td className="py-3 px-3">
                  {v.golden !== null ? (
                    <span className="text-slate-100 font-semibold bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      {String(v.golden)}
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">—</span>
                  )}
                </td>
                <td className="py-3 px-3">
                  <VerdictBadge verdict={v.verdict} />
                </td>
                <td className="py-3 px-3 text-slate-400 font-sans text-xs">
                  {v.note || "Deterministic evaluation"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer Info & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-800">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Info className="w-4 h-4 text-slate-500" />
          <span>The attribute diff matrix remains the authoritative explanation of the decision.</span>
        </div>

        {onProposeTask && (
          <button
            type="button"
            onClick={() => onProposeTask(candidate)}
            className="px-4 py-2 rounded-md text-xs font-semibold bg-emerald-600 text-slate-950 hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-950/40"
          >
            Propose Stewardship Task for this Match
          </button>
        )}
      </div>
    </div>
  );
}
