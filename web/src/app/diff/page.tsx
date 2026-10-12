"use client";

import React, { useState } from "react";
import { DiffInspector } from "@/components/diff/DiffInspector";
import { DEMO_MATCH_RESPONSES } from "@/lib/api";
import { GitCompare } from "lucide-react";

export default function DiffPage() {
  const valveCandidates = DEMO_MATCH_RESPONSES.valve.candidates;
  const motorCandidates = DEMO_MATCH_RESPONSES.motor.candidates;

  const allPresets = [
    {
      title: "Case 1: Valve Missing Required Trim & Bonnet (Tier 2)",
      description: "Missing required attributes route directly to human stewardship queue per S1.",
      candidate: valveCandidates[0],
      rawText: DEMO_MATCH_RESPONSES.valve.clean_text,
    },
    {
      title: "Case 2: Valve Hard Pressure Rating Mismatch CL150 vs CL300 (Tier 3)",
      description: "Hard attribute mismatch triggers strict safety refusal per S1 and S4.",
      candidate: valveCandidates[1],
      rawText: DEMO_MATCH_RESPONSES.valve.clean_text,
    },
    {
      title: "Case 3: Motor Ex Directional Upgrade IIC >= IIB (Tier 2)",
      description: "Directional safety lattice: Gas Group IIC supersedes IIB.",
      candidate: motorCandidates[1],
      rawText: DEMO_MATCH_RESPONSES.motor.clean_text,
    },
    {
      title: "Case 4: Motor Ex Flameproof Full Exact Match (Tier 1)",
      description: "100% equivalence on power, poles, mounting, and hazardous ratings.",
      candidate: motorCandidates[0],
      rawText: DEMO_MATCH_RESPONSES.motor.clean_text,
    },
  ];

  const [activePresetIndex, setActivePresetIndex] = useState(0);
  const activePreset = allPresets[activePresetIndex];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2.5">
          <GitCompare className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
          Diff Inspector & Safety Verdict Matrix
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
          Visual attribute-by-attribute comparator comparing raw requisition specs against national golden master records. Displays exact physical lattices, missing attribute gaps, and invariant safety refusals.
        </p>
      </div>

      {/* Preset Case Switcher */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs">
        <label className="text-xs font-mono uppercase text-slate-500 dark:text-slate-400 tracking-wider block font-semibold">
          Select Engineering Comparison Scenario:
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {allPresets.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setActivePresetIndex(idx)}
              className={`p-3 text-left rounded-lg border transition-all text-xs font-mono ${
                activePresetIndex === idx
                  ? "bg-emerald-50 dark:bg-slate-800 border-emerald-500 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              <div className="font-semibold truncate">{preset.title.split(":")[0]}</div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                {preset.title.split(":")[1]?.trim() || preset.title}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Active Diff Inspector */}
      <DiffInspector
        candidate={activePreset.candidate}
        rawText={activePreset.rawText}
      />
    </div>
  );
}
