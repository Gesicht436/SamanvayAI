"use client";

import React from "react";
import { ShieldAlert, AlertTriangle, ShieldCheck, Info } from "lucide-react";

export type SafetyVerdictType = "HARD_MISMATCH" | "MISSING_REQUIRED" | "DIRECTIONAL_UPGRADE" | "EXACT_HARMONIZED";

interface SafetyBannerProps {
  type: SafetyVerdictType;
  title?: string;
  description?: string;
  invariants?: string[];
  className?: string;
}

export function SafetyBanner({
  type,
  title,
  description,
  invariants = [],
  className = "",
}: SafetyBannerProps) {
  if (type === "HARD_MISMATCH") {
    return (
      <div
        role="alert"
        className={`p-4 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-500/40 text-rose-900 dark:text-rose-200 flex items-start gap-3.5 shadow-sm transition-colors ${className}`}
      >
        <ShieldAlert className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="font-bold text-rose-800 dark:text-rose-300">
              {title || "SAFETY REFUSAL: Hard Physical Mismatch Detected (Tier 3)"}
            </strong>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-200/80 dark:bg-rose-900/60 text-rose-900 dark:text-rose-300 border border-rose-300 dark:border-rose-700/60 font-bold">
              {invariants.length > 0 ? invariants.join(", ") : "Invariants S1, S4"}
            </span>
          </div>
          <p className="text-rose-800/90 dark:text-rose-200/90 leading-relaxed font-sans">
            {description ||
              "One or more HARD physical attributes (e.g. pressure class, flange metallurgy, voltage, or explosion-proof rating) mismatch the canonical golden master. Tier 1 auto-harmonization is strictly blocked to eliminate catastrophic physical failure in hazardous environments."}
          </p>
        </div>
      </div>
    );
  }

  if (type === "MISSING_REQUIRED") {
    return (
      <div
        role="alert"
        className={`p-4 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-500/40 text-amber-900 dark:text-amber-200 flex items-start gap-3.5 shadow-sm transition-colors ${className}`}
      >
        <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="font-bold text-amber-800 dark:text-amber-300">
              {title || "STEWARDSHIP REQUIRED: Missing Required Physical Parameters (Tier 2)"}
            </strong>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-200/80 dark:bg-amber-900/60 text-amber-900 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60 font-bold">
              {invariants.length > 0 ? invariants.join(", ") : "Invariant S1"}
            </span>
          </div>
          <p className="text-amber-800/90 dark:text-amber-200/90 leading-relaxed font-sans">
            {description ||
              "Requisition text is missing one or more required physical parameters. Per Safety Invariant S1, incomplete specifications are routed directly to human stewardship and cannot be auto-merged."}
          </p>
        </div>
      </div>
    );
  }

  if (type === "DIRECTIONAL_UPGRADE") {
    return (
      <div
        role="alert"
        className={`p-4 rounded-xl bg-sky-50 dark:bg-sky-950/60 border border-sky-300 dark:border-sky-500/40 text-sky-900 dark:text-sky-200 flex items-start gap-3.5 shadow-sm transition-colors ${className}`}
      >
        <Info className="w-5 h-5 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="font-bold text-sky-800 dark:text-sky-300">
              {title || "DIRECTIONAL UPGRADE: Conservative Safety Supersession (Tier 2)"}
            </strong>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-200/80 dark:bg-sky-900/60 text-sky-900 dark:text-sky-300 border border-sky-300 dark:border-sky-700/60 font-bold">
              {invariants.length > 0 ? invariants.join(", ") : "Invariant S3"}
            </span>
          </div>
          <p className="text-sky-800/90 dark:text-sky-200/90 leading-relaxed font-sans">
            {description ||
              "Candidate record has higher safety rating (e.g. Class 300 replacing Class 150, or Gas Group IIC superseding IIB). Allowed only as a directional upgrade requiring human engineer sign-off."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={`p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-500/40 text-emerald-900 dark:text-emerald-200 flex items-start gap-3.5 shadow-sm transition-colors ${className}`}
    >
      <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
      <div className="text-xs space-y-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="font-bold text-emerald-800 dark:text-emerald-300">
            {title || "DETERMINISTIC CONFORMANCE: Exact Physical Identity Verified (Tier 1)"}
          </strong>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-200/80 dark:bg-emerald-900/60 text-emerald-900 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60 font-bold">
            Verhoeff Verified &middot; S1 Compliant
          </span>
        </div>
        <p className="text-emerald-800/90 dark:text-emerald-200/90 leading-relaxed font-sans">
          {description ||
            "100% parameter equivalence established across all required engineering dimensions with verified Verhoeff check digit. Safe for automated inter-CPSE catalog linkage."}
        </p>
      </div>
    </div>
  );
}
