import React from "react";
import { VerdictStatus, AttributeRole, TaskStatus } from "@/types";
import { CheckCircle2, AlertTriangle, XCircle, ShieldAlert, ShieldCheck, ArrowUpRight } from "lucide-react";

export function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  if (tier === 1) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 dark:bg-emerald-400 animate-pulse" />
        Tier 1: Auto-Harmonized
      </span>
    );
  }
  if (tier === 2) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 dark:bg-amber-400" />
        Tier 2: Steward Review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 dark:bg-rose-500/15 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30">
      <span className="w-1.5 h-1.5 rounded-full bg-rose-600 dark:bg-rose-400" />
      Tier 3: Refused (Mismatch)
    </span>
  );
}

export function VerdictBadge({ verdict }: { verdict: VerdictStatus }) {
  switch (verdict) {
    case "EXACT":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> EXACT
        </span>
      );
    case "UPGRADE":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
          <ArrowUpRight className="w-3 h-3 text-amber-600 dark:text-amber-400" /> UPGRADE
        </span>
      );
    case "MISSING":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
          <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" /> MISSING
        </span>
      );
    case "MISMATCH":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30">
          <XCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" /> MISMATCH
        </span>
      );
  }
}

export function RoleBadge({ role }: { role: AttributeRole }) {
  switch (role) {
    case "HARD":
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-red-100 dark:bg-red-950/70 text-red-800 dark:text-red-300 border border-red-300 dark:border-red-500/30">
          HARD
        </span>
      );
    case "REQUIRED":
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
          REQUIRED
        </span>
      );
    case "SOFT":
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
          SOFT
        </span>
      );
  }
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  switch (status) {
    case "PROPOSED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
          PROPOSED
        </span>
      );
    case "APPROVED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
          APPROVED
        </span>
      );
    case "REJECTED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30">
          REJECTED
        </span>
      );
  }
}
