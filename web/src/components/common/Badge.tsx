import React from "react";
import { VerdictStatus, AttributeRole, TaskStatus } from "@/types";

export function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  if (tier === 1) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        Tier 1: Auto-Harmonized
      </span>
    );
  }
  if (tier === 2) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        Tier 2: Steward Review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
      <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
      Tier 3: Refused (Mismatch)
    </span>
  );
}

export function VerdictBadge({ verdict }: { verdict: VerdictStatus }) {
  switch (verdict) {
    case "EXACT":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
          EXACT
        </span>
      );
    case "UPGRADE":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-sky-950/60 text-sky-300 border border-sky-500/30">
          UPGRADE
        </span>
      );
    case "MISSING":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-950/60 text-amber-300 border border-amber-500/30">
          MISSING
        </span>
      );
    case "MISMATCH":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-950/60 text-rose-300 border border-rose-500/30">
          MISMATCH
        </span>
      );
  }
}

export function RoleBadge({ role }: { role: AttributeRole }) {
  switch (role) {
    case "HARD":
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-red-950/70 text-red-400 border border-red-500/30">
          HARD
        </span>
      );
    case "REQUIRED":
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-950/70 text-amber-400 border border-amber-500/30">
          REQUIRED
        </span>
      );
    case "SOFT":
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
          SOFT
        </span>
      );
  }
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  switch (status) {
    case "PROPOSED":
      return (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-500/30">
          PROPOSED
        </span>
      );
    case "APPROVED":
      return (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
          APPROVED
        </span>
      );
    case "REJECTED":
      return (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-rose-950/60 text-rose-300 border border-rose-500/30">
          REJECTED
        </span>
      );
  }
}
