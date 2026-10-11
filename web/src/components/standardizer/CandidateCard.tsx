"use client";

import React from "react";
import { CandidateMaster } from "@/types";
import { TierBadge } from "@/components/common/Badge";
import { useAuth } from "@/lib/auth-context";
import { GitCompare, PlusCircle, AlertCircle } from "lucide-react";

interface CandidateCardProps {
  candidate: CandidateMaster;
  onInspectDiff: (candidate: CandidateMaster) => void;
  onProposeLink?: (candidate: CandidateMaster) => void;
}

export function CandidateCard({
  candidate,
  onInspectDiff,
  onProposeLink,
}: CandidateCardProps) {
  const { user } = useAuth();
  const canPropose = user.role === "MAKER" || user.role === "ADMIN";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-3 hover:border-slate-700 transition-colors">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded border border-emerald-500/30">
            {candidate.golden_code}
          </span>
          <TierBadge tier={candidate.tier} />
        </div>
        <div className="text-xs font-mono text-slate-400">
          Match Prob:{" "}
          <strong className="text-slate-200">
            {(candidate.prob * 100).toFixed(1)}%
          </strong>
        </div>
      </div>

      <div className="text-sm font-mono text-slate-200 bg-slate-950 p-2.5 rounded border border-slate-800/80">
        {candidate.descriptor}
      </div>

      {candidate.attribute_gap_alert && (
        <div
          className={`flex items-start gap-2 p-2.5 rounded text-xs font-mono ${
            candidate.tier === 3
              ? "bg-rose-950/50 text-rose-300 border border-rose-500/30"
              : "bg-amber-950/50 text-amber-300 border border-amber-500/30"
          }`}
        >
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{candidate.attribute_gap_alert}</span>
        </div>
      )}

      {candidate.reason_codes.length > 0 && (
        <div className="flex flex-wrap gap-1.5 items-center">
          <span className="text-[10px] font-mono text-slate-500 uppercase">
            Reason Codes:
          </span>
          {candidate.reason_codes.map((code) => (
            <span
              key={code}
              className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
            >
              {code}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-slate-800">
        <button
          type="button"
          onClick={() => onInspectDiff(candidate)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 text-slate-200 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
        >
          <GitCompare className="w-3.5 h-3.5 text-emerald-400" />
          Inspect Diff Matrix
        </button>

        {canPropose && onProposeLink && (
          <button
            type="button"
            onClick={() => onProposeLink(candidate)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5 text-emerald-400" />
            Propose Link Task
          </button>
        )}
      </div>
    </div>
  );
}
