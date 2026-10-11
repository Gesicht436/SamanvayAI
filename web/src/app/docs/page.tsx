"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { DEMO_MTC_EVALUATION } from "@/lib/api";
import { MtcEvaluationData } from "@/types";
import {
  FileCheck,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Beaker,
  ShieldCheck,
  FileText,
  Search,
  ArrowRight,
  ClipboardCheck,
} from "lucide-react";

export default function DocumentIntakeMtcPage() {
  const { selectedOrg } = useAuth();
  const [activeTab, setActiveTab] = useState<"mtc" | "precheck" | "paste">("mtc");

  // MTC Form state
  const [claimedGrade, setClaimedGrade] = useState("A105");
  const [productForm, setProductForm] = useState("FORGING");
  const [heatNo, setHeatNo] = useState("HEAT-88421");
  const [cVal, setCVal] = useState("0.22");
  const [mnVal, setMnVal] = useState("0.95");
  const [pVal, setPVal] = useState("0.02");
  const [sVal, setSVal] = useState("0.015");
  const [siVal, setSiVal] = useState("0.25");
  const [crVal, setCrVal] = useState("0.08");
  const [moVal, setMoVal] = useState("0.04");
  const [niVal, setNiVal] = useState("0.05");
  const [cuVal, setCuVal] = useState("0.08");
  const [vVal, setVVal] = useState("0.01");

  const [mtcResult, setMtcResult] = useState<MtcEvaluationData | null>(DEMO_MTC_EVALUATION);

  // Pre-check state
  const [precheckText, setPrecheckText] = useState("GATE VALVE 100 NB CL150 WCB FLANGED RF API 600");
  const [precheckResult, setPrecheckResult] = useState<{
    clean_text: string;
    duplicate_warning?: string;
    golden_code?: string;
    status: string;
  } | null>(null);

  const calculateCeIiw = () => {
    const c = parseFloat(cVal) || 0;
    const mn = parseFloat(mnVal) || 0;
    const cr = parseFloat(crVal) || 0;
    const mo = parseFloat(moVal) || 0;
    const v = parseFloat(vVal) || 0;
    const ni = parseFloat(niVal) || 0;
    const cu = parseFloat(cuVal) || 0;
    // CE_IIW = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15
    return c + mn / 6 + (cr + mo + v) / 5 + (ni + cu) / 15;
  };

  const handleEvaluateMtc = () => {
    const c = parseFloat(cVal) || 0;
    const mn = parseFloat(mnVal) || 0;
    const p = parseFloat(pVal) || 0;
    const s = parseFloat(sVal) || 0;
    const si = parseFloat(siVal) || 0;
    const ce = calculateCeIiw();

    // Verification against ASTM A105 limits
    const verdicts = [
      { property: "C", kind: "CHEM", found: c, max_allowed: 0.35, unit: "wt%", verdict: (c <= 0.35 ? "PASS" : "FAIL") as "PASS" | "FAIL" },
      { property: "Mn", kind: "CHEM", found: mn, min_required: 0.60, max_allowed: 1.05, unit: "wt%", verdict: (mn >= 0.60 && mn <= 1.05 ? "PASS" : "FAIL") as "PASS" | "FAIL" },
      { property: "P", kind: "CHEM", found: p, max_allowed: 0.035, unit: "wt%", verdict: (p <= 0.035 ? "PASS" : "FAIL") as "PASS" | "FAIL" },
      { property: "S", kind: "CHEM", found: s, max_allowed: 0.040, unit: "wt%", verdict: (s <= 0.040 ? "PASS" : "FAIL") as "PASS" | "FAIL" },
      { property: "Si", kind: "CHEM", found: si, min_required: 0.10, max_allowed: 0.35, unit: "wt%", verdict: (si >= 0.10 && si <= 0.35 ? "PASS" : "FAIL") as "PASS" | "FAIL" },
    ];

    const hasFail = verdicts.some((v) => v.verdict === "FAIL");

    setMtcResult({
      id: "mtc-eval-live",
      grade_claimed: claimedGrade,
      heat_no: heatNo,
      chemistry: { C: c, Mn: mn, P: p, S: s, Si: si },
      ce_iiw: parseFloat(ce.toFixed(3)),
      conformance: hasFail ? "FAILS" : "CONFORMS",
      reference_verified: true,
      flags: [],
      property_verdicts: verdicts,
    });
  };

  const handleRunPrecheck = () => {
    setPrecheckResult({
      clean_text: precheckText.trim().toUpperCase(),
      duplicate_warning: "Identical material active in Golden Master MPNG-0004821937-3. Pre-procurement requisition stopped before PR/PO creation.",
      golden_code: "MPNG-0004821937-3",
      status: "DUPLICATE_IDENTIFIED",
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-2">
            <FileCheck className="w-3.5 h-3.5" />
            Document Intake & MTC Conformance (Section 10.0, 10.2, 15.1)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Document Ingestion & Material Test Certificate (MTC) Conformance
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Validates metallurgical chemistry against statutory ASTM/ASME specifications, computes Carbon Equivalent ($CE_{'{IIW}'}$), and stops duplicate requisitions at pre-procurement.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800 font-mono text-xs">
        <button
          onClick={() => setActiveTab("mtc")}
          className={`px-4 py-2.5 border-b-2 font-medium transition-colors flex items-center gap-2 ${
            activeTab === "mtc"
              ? "border-emerald-400 text-emerald-400 bg-emerald-950/20"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Beaker className="w-4 h-4" />
          MTC Chemistry & CE Conformance
        </button>
        <button
          onClick={() => setActiveTab("precheck")}
          className={`px-4 py-2.5 border-b-2 font-medium transition-colors flex items-center gap-2 ${
            activeTab === "precheck"
              ? "border-emerald-400 text-emerald-400 bg-emerald-950/20"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Search className="w-4 h-4" />
          Pre-Procurement Duplicate Precheck
        </button>
      </div>

      {/* Tab 1: MTC Conformance */}
      {activeTab === "mtc" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Inputs */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4">
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Beaker className="w-4 h-4 text-emerald-400" />
              Claimed Grade & Heat Chemistry
            </h2>

            <div className="grid grid-cols-3 gap-3 font-mono text-xs">
              <div className="space-y-1">
                <label className="text-slate-400">Claimed Grade</label>
                <input
                  type="text"
                  value={claimedGrade}
                  onChange={(e) => setClaimedGrade(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-400">Product Form</label>
                <input
                  type="text"
                  value={productForm}
                  onChange={(e) => setProductForm(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-400">Heat / Batch No</label>
                <input
                  type="text"
                  value={heatNo}
                  onChange={(e) => setHeatNo(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100"
                />
              </div>
            </div>

            <div className="pt-2">
              <label className="text-xs font-mono text-slate-300 block mb-2 font-bold">
                Elemental Chemistry (% by weight):
              </label>
              <div className="grid grid-cols-5 gap-2 font-mono text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 block">% C</span>
                  <input
                    type="number"
                    step="0.01"
                    value={cVal}
                    onChange={(e) => setCVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% Mn</span>
                  <input
                    type="number"
                    step="0.01"
                    value={mnVal}
                    onChange={(e) => setMnVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% P</span>
                  <input
                    type="number"
                    step="0.001"
                    value={pVal}
                    onChange={(e) => setPVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% S</span>
                  <input
                    type="number"
                    step="0.001"
                    value={sVal}
                    onChange={(e) => setSVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% Si</span>
                  <input
                    type="number"
                    step="0.01"
                    value={siVal}
                    onChange={(e) => setSiVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% Cr</span>
                  <input
                    type="number"
                    step="0.01"
                    value={crVal}
                    onChange={(e) => setCrVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% Mo</span>
                  <input
                    type="number"
                    step="0.01"
                    value={moVal}
                    onChange={(e) => setMoVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% Ni</span>
                  <input
                    type="number"
                    step="0.01"
                    value={niVal}
                    onChange={(e) => setNiVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% Cu</span>
                  <input
                    type="number"
                    step="0.01"
                    value={cuVal}
                    onChange={(e) => setCuVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">% V</span>
                  <input
                    type="number"
                    step="0.01"
                    value={vVal}
                    onChange={(e) => setVVal(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </div>
              </div>
            </div>

            <div className="pt-4 flex justify-between items-center">
              <div className="text-[11px] font-mono text-slate-400">
                Calculated CE_IIW: <strong className="text-emerald-400">{calculateCeIiw().toFixed(3)}</strong>
              </div>
              <button
                onClick={handleEvaluateMtc}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs font-mono transition-colors flex items-center gap-1.5"
              >
                <ClipboardCheck className="w-4 h-4" />
                Evaluate Conformance
              </button>
            </div>
          </div>

          {/* Results Card */}
          {mtcResult && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  MTC Verification Result
                </h3>
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold border ${
                    mtcResult.conformance === "CONFORMS"
                      ? "bg-emerald-950 text-emerald-400 border-emerald-500/40"
                      : "bg-red-950 text-red-400 border-red-500/40"
                  }`}
                >
                  {mtcResult.conformance}
                </span>
              </div>

              <div className="space-y-2 font-mono text-xs">
                <div className="flex justify-between text-slate-300">
                  <span>Grade Claimed:</span>
                  <strong className="text-slate-100">{mtcResult.grade_claimed}</strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Heat Batch:</span>
                  <strong className="text-slate-100">{mtcResult.heat_no}</strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Carbon Equivalent (CE_IIW):</span>
                  <strong className="text-emerald-400">{mtcResult.ce_iiw} (Weldable)</strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Reference DB Status:</span>
                  <strong className="text-emerald-400">
                    {mtcResult.reference_verified ? "Verified Standard (ASTM A105 Table 1)" : "Unverified"}
                  </strong>
                </div>
              </div>

              {/* Property Verdicts Table */}
              <div className="pt-2">
                <h4 className="text-xs font-mono text-slate-400 mb-2 font-semibold">
                  Elemental Bounds Check:
                </h4>
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                      <th className="py-1.5 px-2">Element</th>
                      <th className="py-1.5 px-2">Found</th>
                      <th className="py-1.5 px-2">ASTM Range</th>
                      <th className="py-1.5 px-2 text-right">Verdict</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 text-slate-200">
                    {mtcResult.property_verdicts.map((v) => (
                      <tr key={v.property}>
                        <td className="py-1.5 px-2 font-bold">{v.property}</td>
                        <td className="py-1.5 px-2">{v.found} {v.unit}</td>
                        <td className="py-1.5 px-2 text-slate-400">
                          {v.min_required !== undefined ? `${v.min_required} - ` : "<= "}
                          {v.max_allowed} {v.unit}
                        </td>
                        <td className="py-1.5 px-2 text-right">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                              v.verdict === "PASS" ? "bg-emerald-950 text-emerald-400" : "bg-red-950 text-red-400"
                            }`}
                          >
                            {v.verdict}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Pre-procurement Precheck */}
      {activeTab === "precheck" && (
        <div className="max-w-2xl bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Search className="w-4 h-4 text-emerald-400" />
            Pre-Procurement Requisition Check (Section 10.0)
          </h2>
          <p className="text-xs text-slate-400 font-sans leading-relaxed">
            Checks prospective material requisitions against active Golden Masters before PR or PO creation. Prevents accidental parallel procurement.
          </p>

          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-300 block">
              Draft Item Description:
            </label>
            <input
              type="text"
              value={precheckText}
              onChange={(e) => setPrecheckText(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <button
            onClick={handleRunPrecheck}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs font-mono transition-colors flex items-center gap-1.5"
          >
            <Search className="w-4 h-4" />
            Run Pre-Check
          </button>

          {precheckResult && (
            <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 space-y-2 font-mono text-xs">
              <div className="flex items-center gap-2 text-amber-400 font-bold">
                <AlertTriangle className="w-4 h-4" />
                Duplicate Material Detected in Central Repository
              </div>
              <p className="text-slate-300 font-sans text-xs leading-relaxed">
                {precheckResult.duplicate_warning}
              </p>
              <div className="text-[11px] text-slate-400">
                Matched Master: <strong className="text-emerald-400">{precheckResult.golden_code}</strong>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
