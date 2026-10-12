"use client";

import React, { useState } from "react";
import { MatchResponse, CandidateMaster } from "@/types";
import { matchMaterial } from "@/lib/api";
import { ExtractedCard } from "@/components/standardizer/ExtractedCard";
import { CandidateCard } from "@/components/standardizer/CandidateCard";
import { DiffInspector } from "@/components/diff/DiffInspector";
import { Search, Loader2, PlayCircle, Sparkles } from "lucide-react";

const SAMPLE_QUERIES = [
  { label: "Gate Valve 100NB Cl150", query: "VLV GT 100 NB CL150 WCB FLG RF API600" },
  { label: "Motor 55kW Ex d IIB", query: "MOTOR 55 KW 4 POLE B3 FOOT MOUNTED EX D IIB T4 IE3" },
  { label: "Distribution Transformer", query: "TRANSFORMER 100 KVA 11/0.433 KV DYN11 ONAN CU" },
  { label: "OTR Tyre 27.00R49", query: "OTR TYRE 27.00R49 E4 TL DUMP TRUCK" },
];

export default function StandardizerPage() {
  const [description, setDescription] = useState(SAMPLE_QUERIES[0].query);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateMaster | null>(null);

  const handleMatch = async (textToMatch?: string) => {
    const text = textToMatch ?? description;
    if (!text.trim()) return;
    setLoading(true);
    setSelectedCandidate(null);
    try {
      const res = await matchMaterial({ description: text, top_k: 3 });
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Intro */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2.5">
          <Search className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
          Material Standardizer & Match Engine
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
          Enter unstructured, noisy, or multilingual legacy plant descriptions. The system normalizes text, extracts physical and statutory attributes with evidence spans, and retrieves ranked candidate masters under Safety Invariants S1–S15.
        </p>
      </div>

      {/* Input Box and Sample Chips */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
        <div>
          <label className="text-xs font-mono uppercase text-slate-700 dark:text-slate-300 block mb-2 font-semibold">
            Raw Material Description (ERP / Requisition Line)
          </label>
          <div className="flex flex-col sm:flex-row gap-3">
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. VLV GT 100 NB CL150 WCB FLG RF API600..."
              className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-3 text-sm font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <button
              type="button"
              onClick={() => handleMatch()}
              disabled={loading}
              className="px-6 py-2 rounded-lg font-semibold text-xs bg-emerald-600 text-white dark:text-slate-950 hover:bg-emerald-500 transition-colors flex items-center gap-2 shrink-0 self-stretch justify-center shadow-md disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Matching...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Standardize & Match
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Sample Queries */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200 dark:border-slate-800/60">
          <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
            <PlayCircle className="w-3.5 h-3.5" /> Quick Samples:
          </span>
          {SAMPLE_QUERIES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setDescription(sample.query);
                handleMatch(sample.query);
              }}
              className="text-xs font-mono px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white border border-slate-300 dark:border-slate-700/60 transition-colors shadow-2xs"
            >
              {sample.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results View */}
      {result && (
        <div className="space-y-6">
          {/* Extracted Attributes and Tokens */}
          <ExtractedCard
            cleanText={result.clean_text}
            subcategory={result.subcategory}
            categoryConfidence={result.category_confidence}
            flags={result.flags}
            extracted={result.extracted}
          />

          {/* Diff Inspector Modal / In-Place View */}
          {selectedCandidate ? (
            <DiffInspector
              candidate={selectedCandidate}
              rawText={result.clean_text}
              onBack={() => setSelectedCandidate(null)}
            />
          ) : (
            /* Ranked Candidates List */
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase font-mono tracking-wider">
                  Ranked Golden Master Candidates ({result.candidates.length})
                </h3>
                <span className="text-xs text-slate-500 font-mono">
                  Gated by Directional Safety Comparator
                </span>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {result.candidates.map((cand) => (
                  <CandidateCard
                    key={cand.golden_code}
                    candidate={cand}
                    onInspectDiff={(candidate) => setSelectedCandidate(candidate)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
