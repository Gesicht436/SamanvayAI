import React from "react";
import { AlertTriangle } from "lucide-react";

export function DemoBanner() {
  return (
    <div
      role="banner"
      className="bg-amber-950/80 border-b border-amber-500/30 text-amber-200 px-4 py-1.5 text-xs font-mono flex items-center justify-between"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
        <span>
          <strong className="text-amber-300 font-semibold uppercase tracking-wider">
            SYNTHETIC DEMO DATA:
          </strong>{" "}
          Demonstration environment running 14 synthetic clusters across 21 material families. No proprietary CPSE data is exposed.
        </span>
      </div>
      <span className="hidden sm:inline-block text-amber-400/80 text-[11px] bg-amber-900/40 px-2 py-0.5 rounded border border-amber-600/30">
        Invariants S1–S15 Active
      </span>
    </div>
  );
}
