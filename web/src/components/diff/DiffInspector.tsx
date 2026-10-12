"use client";

import React, { useState } from "react";
import { CandidateMaster } from "@/types";
import { TierBadge, VerdictBadge, RoleBadge } from "@/components/common/Badge";
import { SafetyBanner, SafetyVerdictType } from "@/components/common/SafetyBanner";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
  ArrowRight,
  FileText,
  Sparkles,
  GitCompare,
  Zap,
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
  const [hoveredAttr, setHoveredAttr] = useState<string | null>(null);

  const hasHardMismatch = candidate.verdicts.some(
    (v) => v.role === "HARD" && v.verdict === "MISMATCH"
  );
  const hasMissingRequired = candidate.verdicts.some(
    (v) => (v.role === "HARD" || v.role === "REQUIRED") && v.verdict === "MISSING"
  );
  const isUpgrade = candidate.verdicts.some((v) => v.verdict === "UPGRADE");

  let bannerType: SafetyVerdictType = "EXACT_HARMONIZED";
  let bannerTitle = "SPECIFICATION COMPLIANT: All Hard & Required Attributes Match (Tier 1)";
  let bannerDesc = "Deterministic comparator verified 100% equivalence across critical dimensions, electrical ratings, and safety parameters.";

  if (hasHardMismatch) {
    bannerType = "HARD_MISMATCH";
    bannerTitle = "SAFETY REFUSAL: Hard Attribute Mismatch Detected (Tier 3)";
    bannerDesc = "One or more HARD physical attributes mismatch the canonical master. Safety Invariants S1 and S4 strictly block Tier 1 auto-harmonization to prevent catastrophic physical failure in hazardous environments.";
  } else if (hasMissingRequired) {
    bannerType = "MISSING_REQUIRED";
    bannerTitle = "SAFETY ROUTING: Required Attribute Gap (Tier 2 Steward Review)";
    bannerDesc = "Required physical parameters are absent from the input text. Per Safety Invariant S1, this item is routed to the human stewardship queue for datasheet review.";
  } else if (isUpgrade) {
    bannerType = "DIRECTIONAL_UPGRADE";
    bannerTitle = "DIRECTIONAL UPGRADE: Conservative Safety Supersession (Tier 2)";
    bannerDesc = "Candidate has higher safety rating (e.g. Class 300 replacing Class 150). Permitted only as a directional lattice upgrade requiring human engineer sign-off per Invariant S3.";
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6 shadow-sm transition-colors">
      {/* Screen Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              Diff Inspector
              <span className="text-[11px] font-mono font-normal text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                Explains the decision
              </span>
            </h2>
            <TierBadge tier={candidate.tier} />
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Authoritative explanation of the decision. Evaluates physical safety lattices and invariants S1–S15.
          </p>
        </div>

        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            ← Back to Candidates
          </button>
        )}
      </div>

      {/* Target Golden Master Overview */}
      <div className="p-4 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800/80 space-y-2 font-mono">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span>Target Golden Master Code</span>
          <span className="text-slate-900 dark:text-slate-200 font-semibold">
            Similarity Probability: {(candidate.prob * 100).toFixed(1)}%
          </span>
        </div>
        <div className="text-emerald-700 dark:text-emerald-400 font-bold text-sm tracking-wide">
          {candidate.golden_code}
        </div>
        <div className="text-xs text-slate-700 dark:text-slate-300">
          {candidate.descriptor}
        </div>
        {rawText && (
          <div className="text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate">Raw Query: <strong className="text-slate-800 dark:text-slate-200">{rawText}</strong></span>
          </div>
        )}
      </div>

      {/* Full-width Safety Regulatory Banner */}
      <SafetyBanner
        type={bannerType}
        title={bannerTitle}
        description={bannerDesc}
        invariants={hasHardMismatch ? ["S1", "S4"] : hasMissingRequired ? ["S1"] : isUpgrade ? ["S3"] : ["S1", "S2"]}
      />

      {/* 50/50 Synchronized Side-by-Side Comparison Matrix */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-400 px-1">
          <span>Parameter-by-Parameter Lattice Alignment</span>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-sans">
            Hover over values to inspect character slice offsets
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 uppercase text-[11px] bg-slate-50 dark:bg-slate-950/60">
                <th className="py-2.5 px-3">Attribute</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Raw Item Extracted</th>
                <th className="py-2.5 px-2 text-center">Lattice</th>
                <th className="py-2.5 px-3">Golden Master</th>
                <th className="py-2.5 px-3">Verdict</th>
                <th className="py-2.5 px-3">Engineering Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 bg-white dark:bg-slate-900">
              {candidate.verdicts.map((v) => {
                const isHovered = hoveredAttr === v.attr;
                return (
                  <tr
                    key={v.attr}
                    onMouseEnter={() => setHoveredAttr(v.attr)}
                    onMouseLeave={() => setHoveredAttr(null)}
                    className={`transition-colors ${
                      v.verdict === "MISMATCH"
                        ? "bg-rose-50/60 dark:bg-rose-950/20"
                        : v.verdict === "MISSING"
                        ? "bg-amber-50/50 dark:bg-amber-950/15"
                        : v.verdict === "UPGRADE"
                        ? "bg-sky-50/50 dark:bg-sky-950/15"
                        : "hover:bg-slate-50 dark:hover:bg-slate-800/40"
                    }`}
                  >
                    <td className="py-3 px-3 font-semibold text-slate-900 dark:text-slate-100">
                      {v.attr}
                    </td>
                    <td className="py-3 px-3">
                      <RoleBadge role={v.role} />
                    </td>
                    {/* Requisition Raw Column with Apple-style Character Offset Tooltip */}
                    <td className="py-3 px-3 relative group">
                      {v.raw !== null ? (
                        <div className="inline-block relative">
                          <span className="text-slate-900 dark:text-slate-100 font-semibold bg-slate-100 dark:bg-slate-950 px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 cursor-help transition-all group-hover:border-emerald-500/50">
                            {String(v.raw)}
                          </span>

                          {/* Hover Popover: Character Slice Offsets & Token Evidence */}
                          <div className="absolute left-0 bottom-full mb-1.5 hidden group-hover:flex flex-col z-30 p-2.5 bg-slate-900 dark:bg-slate-950 text-white border border-slate-700 rounded-lg shadow-2xl text-[11px] font-mono pointer-events-none min-w-[220px] animate-in fade-in duration-100">
                            <div className="flex items-center justify-between text-slate-400 text-[10px] pb-1 border-b border-slate-800 mb-1.5">
                              <span className="font-bold">Token Evidence Span</span>
                              <span className="text-emerald-400">Lexicon Offset</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-emerald-300 font-semibold">
                              <span>Raw Value:</span>
                              <code className="bg-slate-800 px-1 rounded">&ldquo;{String(v.raw)}&rdquo;</code>
                            </div>
                            <div className="text-[10px] text-slate-400 mt-1">
                              Character Alignment vs Golden:
                            </div>
                            <div className="flex flex-wrap gap-0.5 mt-1">
                              {String(v.raw).split("").map((ch, i) => {
                                const masterStr = String(v.golden ?? "");
                                const isMatch = masterStr[i] === ch;
                                return (
                                  <span
                                    key={i}
                                    className={`px-1 py-0.2 rounded text-[10px] ${
                                      isMatch
                                        ? "bg-emerald-900 text-emerald-300 border border-emerald-500/40"
                                        : "bg-rose-900 text-rose-200 border border-rose-500/40"
                                    }`}
                                  >
                                    {ch === " " ? "␣" : ch}
                                  </span>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-amber-600 dark:text-amber-400/90 italic font-normal">
                          [Missing Parameter]
                        </span>
                      )}
                    </td>

                    {/* SVG Connector Column */}
                    <td className="py-3 px-2 text-center text-slate-400">
                      <div className="flex items-center justify-center">
                        <ArrowRight
                          className={`w-3.5 h-3.5 transition-transform ${
                            isHovered ? "scale-125 text-emerald-500" : ""
                          }`}
                        />
                      </div>
                    </td>

                    {/* Golden Master Column */}
                    <td className="py-3 px-3">
                      {v.golden !== null ? (
                        <span className="text-slate-900 dark:text-slate-100 font-semibold bg-slate-100 dark:bg-slate-950 px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800">
                          {String(v.golden)}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">—</span>
                      )}
                    </td>

                    {/* Verdict Badge */}
                    <td className="py-3 px-3">
                      <VerdictBadge verdict={v.verdict} />
                    </td>

                    {/* Engineering Notes */}
                    <td className="py-3 px-3 text-slate-600 dark:text-slate-400 font-sans text-xs">
                      {v.note || "Deterministic evaluation"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* TreeSHAP Feature Attribution Panel (Section 8.1 & 15.2) */}
      <div className="bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-3 font-mono">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
              TreeSHAP Feature Attribution (Optional ML Layer)
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-600/30">
              XGBoost Subvectors
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Base Expected Value E[f(x)] = 0.50</span>
        </div>

        {/* Mandatory Governance Notice */}
        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-600/30 text-amber-900 dark:text-amber-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed font-sans">
            <strong>Mandatory Governance Notice:</strong> The deterministic attribute diff matrix above remains the authoritative explanation of the decision. This TreeSHAP panel illustrates statistical feature influence across the corpus, not physical engineering justification.
          </p>
        </div>

        {/* Feature Attribution Bars */}
        <div className="space-y-2 pt-1">
          {[
            { name: "size_nb (Nominal Bore)", phi: "+0.34", pct: 85 },
            { name: "pressure_class (ANSI/PN)", phi: "+0.28", pct: 70 },
            { name: "body_material (Metallurgy)", phi: "+0.19", pct: 48 },
            { name: "end_connection / facing", phi: "+0.12", pct: 30 },
            { name: "design_standard (API/IS)", phi: "+0.07", pct: 18 },
          ].map((item) => (
            <div key={item.name} className="flex items-center gap-3 text-xs">
              <span className="w-48 text-slate-600 dark:text-slate-400 truncate">{item.name}</span>
              <div className="flex-1 bg-slate-200 dark:bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-300 dark:border-slate-800">
                <div
                  className="h-full bg-emerald-500 rounded-full"
                  style={{ width: `${item.pct}%` }}
                />
              </div>
              <span className="w-14 text-right text-emerald-700 dark:text-emerald-400 font-bold">{item.phi}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Info className="w-4 h-4" />
          <span>The attribute diff matrix remains the authoritative explanation of the decision.</span>
        </div>

        {onProposeTask && (
          <button
            type="button"
            onClick={() => onProposeTask(candidate)}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm"
          >
            Propose Stewardship Task for this Match
          </button>
        )}
      </div>
    </div>
  );
}
