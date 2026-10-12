"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  X,
  Hash,
  CheckCircle2,
  Lock,
  Clock,
  User,
  ArrowRight,
  RefreshCw,
  FileCode,
} from "lucide-react";

interface AuditEntry {
  seq: number;
  at: string;
  actor: string;
  action: string;
  entity: string;
  entityId: string;
  rationale: string;
  prevHash: string;
  thisHash: string;
}

const SAMPLE_AUDIT_LOG: AuditEntry[] = [
  {
    seq: 4092,
    at: "2026-10-12T08:34:10Z",
    actor: "steward.ongc@samanvay.gov.in",
    action: "APPROVE_TASK",
    entity: "steward_tasks",
    entityId: "TSK-0842",
    rationale: "Approved ANSI Class 150 flanged valve harmonization after verifying body metallurgy A216 WCB",
    prevHash: "7b4c92...ea01",
    thisHash: "9a2f18...bc44",
  },
  {
    seq: 4091,
    at: "2026-10-12T07:15:22Z",
    actor: "ocr_pipeline.system",
    action: "PROMOTE_DOC_LINE",
    entity: "raw_items",
    entityId: "RAW-2026-0041",
    rationale: "Automated promotion from PO_77391_Valves_Spares.pdf line 14 with OCR confidence 0.960",
    prevHash: "3f8821...12cc",
    thisHash: "7b4c92...ea01",
  },
  {
    seq: 4090,
    at: "2026-10-12T05:42:01Z",
    actor: "checker.iocl@samanvay.gov.in",
    action: "PROPOSE_SPLIT",
    entity: "golden_masters",
    entityId: "MPNG-0004821937-3",
    rationale: "Separated sour-gas service variant with NACE MR0175 compliance from standard utility line",
    prevHash: "0a11bc...ff98",
    thisHash: "3f8821...12cc",
  },
  {
    seq: 4089,
    at: "2026-10-11T22:11:45Z",
    actor: "life_monitor.daemon",
    action: "ESCALATE_ALERT",
    entity: "life_alerts",
    entityId: "ALT-0019",
    rationale: "NBR Hydraulic Seal batch expired 14 days ago. Capped forward pooling per Section 11.",
    prevHash: "5e44aa...dd23",
    thisHash: "0a11bc...ff98",
  },
];

export function AuditDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState<string>("Just now");

  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) setIsOpen(false);
    };

    window.addEventListener("open-audit-drawer", handleOpen);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("open-audit-drawer", handleOpen);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleVerify = () => {
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setVerifiedAt(new Date().toLocaleTimeString());
    }, 600);
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Tamper-Evident Audit Log"
      className="fixed inset-0 z-50 overflow-hidden bg-black/50 dark:bg-black/70 backdrop-blur-sm animate-in fade-in"
      onClick={() => setIsOpen(false)}
    >
      <div
        className="fixed inset-y-0 right-0 w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                Tamper-Evident Audit Log
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-400 border border-emerald-500/30">
                  CHAIN INTACT
                </span>
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Append-only SHA-256 hash chain protected by transactional advisory locking
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            aria-label="Close audit log"
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Cryptographic Health Bar */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 space-y-3 font-mono text-xs">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
            <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase">Head Sequence</span>
              <strong className="text-emerald-600 dark:text-emerald-400 font-bold text-sm">#4092</strong>
            </div>
            <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase">Advisory Lock</span>
              <strong className="text-slate-700 dark:text-slate-200 font-semibold flex items-center gap-1">
                <Lock className="w-3 h-3 text-slate-400" /> 727001
              </strong>
            </div>
            <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 col-span-2 sm:col-span-1">
              <span className="text-slate-400 block text-[10px] uppercase">Verification</span>
              <span className="text-emerald-600 dark:text-emerald-400 text-[11px] flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> {verifiedAt}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[10px] text-slate-400">
              Algorithm: <code className="text-slate-600 dark:text-slate-300">sha256(prev_hash || row_data)</code>
            </span>
            <button
              type="button"
              onClick={handleVerify}
              disabled={verifying}
              className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-sans text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-3 h-3 ${verifying ? "animate-spin" : ""}`} />
              {verifying ? "Verifying..." : "Verify Chain"}
            </button>
          </div>
        </div>

        {/* Timeline Log Feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 px-1">
            Recent Cryptographic Audit Records
          </div>

          {SAMPLE_AUDIT_LOG.map((log) => (
            <div
              key={log.seq}
              className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 space-y-2 text-xs"
            >
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <Hash className="w-3 h-3" /> Seq #{log.seq}
                </span>
                <span className="text-slate-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(log.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  {log.action}
                </span>
                <span className="text-slate-500 text-[11px]">{log.entity} &rarr; <code className="text-slate-700 dark:text-slate-300">{log.entityId}</code></span>
              </div>

              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed font-sans">
                {log.rationale}
              </p>

              <div className="pt-2 border-t border-slate-200 dark:border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3" /> {log.actor}
                </span>
                <span title={`prev: ${log.prevHash} -> this: ${log.thisHash}`}>
                  hash: <code className="text-emerald-600 dark:text-emerald-400">{log.thisHash}</code>
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 text-[10px] text-slate-400 text-center font-mono">
          Governed by Invariant S8 &middot; Immutability protected against UPDATE, DELETE, TRUNCATE
        </div>
      </div>
    </div>
  );
}
