"use client";

import React, { useState } from "react";
import { ExtractedAttribute } from "@/types";
import { Tag, Sparkles } from "lucide-react";

interface ExtractedCardProps {
  cleanText: string;
  subcategory: string;
  categoryConfidence: number;
  flags: string[];
  extracted: Record<string, ExtractedAttribute>;
}

export function ExtractedCard({
  cleanText,
  subcategory,
  categoryConfidence,
  flags,
  extracted,
}: ExtractedCardProps) {
  const [hoveredSpan, setHoveredSpan] = useState<[number, number] | null>(null);

  const tokens = cleanText.split(/\s+/).filter(Boolean);

  // Helper to render text with highlighted evidence span
  const renderHighlightedText = () => {
    if (!hoveredSpan) return cleanText;
    const [start, end] = hoveredSpan;
    if (start >= cleanText.length || end <= start) return cleanText;

    const before = cleanText.substring(0, start);
    const highlight = cleanText.substring(start, end);
    const after = cleanText.substring(end);

    return (
      <>
        <span>{before}</span>
        <mark className="bg-emerald-500/25 text-emerald-950 dark:text-emerald-200 border-b-2 border-emerald-500 px-0.5 rounded font-bold">
          {highlight}
        </mark>
        <span>{after}</span>
      </>
    );
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      {/* Header and Classification */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-50 dark:bg-slate-800 border border-emerald-200 dark:border-slate-700 shadow-2xs">
            <Tag className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span className="text-xs font-mono font-semibold text-emerald-800 dark:text-emerald-300">
              {subcategory}
            </span>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            Confidence:{" "}
            <strong className="text-slate-800 dark:text-slate-200">
              {(categoryConfidence * 100).toFixed(1)}%
            </strong>
          </span>
        </div>

        {flags.length > 0 ? (
          <div className="flex items-center gap-1.5">
            {flags.map((f) => (
              <span
                key={f}
                className="px-2 py-0.5 rounded text-[11px] font-mono bg-rose-50 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-500/30"
              >
                FLAG: {f}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-[11px] font-mono text-emerald-700 dark:text-emerald-400/80 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            Clean Normalization
          </span>
        )}
      </div>

      {/* Normalized Text and Token Stream */}
      <div>
        <label className="text-xs font-mono uppercase text-slate-500 dark:text-slate-400 tracking-wider block mb-1">
          Normalized Text & Evidence Tracing
        </label>
        <div className="p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 text-sm font-mono text-slate-800 dark:text-slate-200 leading-relaxed shadow-inner">
          {renderHighlightedText()}
        </div>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {tokens.map((tok, i) => (
            <span
              key={i}
              className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700/60"
            >
              {tok}
            </span>
          ))}
        </div>
      </div>

      {/* Extracted Attributes Grid */}
      <div>
        <label className="text-xs font-mono uppercase text-slate-500 dark:text-slate-400 tracking-wider block mb-2">
          Extracted Technical Attributes ({Object.keys(extracted).length})
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {Object.entries(extracted).map(([key, attr]) => (
            <div
              key={key}
              onMouseEnter={() => {
                if (attr.evidence) setHoveredSpan(attr.evidence);
              }}
              onMouseLeave={() => setHoveredSpan(null)}
              className="p-3 rounded-lg bg-slate-50/70 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800/80 hover:border-emerald-500/50 dark:hover:border-emerald-500/40 transition-colors cursor-pointer group shadow-2xs"
            >
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-600 dark:text-slate-400 group-hover:text-emerald-700 dark:group-hover:text-emerald-400 transition-colors font-medium">
                  {key}
                </span>
                <span className="text-[10px] text-slate-500">
                  {(attr.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono mt-1 truncate">
                {String(attr.value ?? "—")}
              </div>
              {attr.evidence && (
                <div className="text-[10px] text-slate-500 font-mono mt-1">
                  Span: [{attr.evidence[0]}, {attr.evidence[1]}]
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
