"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { getDashboardSummary } from "@/lib/api";
import { DashboardSummary } from "@/types";
import {
  BarChart3,
  TrendingDown,
  Layers,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  Building2,
  FileCheck2,
  IndianRupee,
  Activity,
  ArrowUpRight,
} from "lucide-react";

export default function DashboardPage() {
  const { selectedOrg } = useAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const res = await getDashboardSummary(selectedOrg?.code);
      setData(res);
      setLoading(false);
    }
    load();
  }, [selectedOrg]);

  if (loading || !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center font-mono text-slate-400">
        Loading Executive Dashboard & Catalog Health Scorecard...
      </div>
    );
  }

  const { catalog_health, harmonization, queue_by_domain, tier_distribution, audit_integrity, ocr_readiness, clusters } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-2">
            <Activity className="w-3.5 h-3.5" />
            CPSE Master Health & Savings Monitor (Section 15.2, 19.1, 20.1)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Executive Catalog Health & Inter-CPSE Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time catalog completeness, queue depth by domain, directional harmonization, and procurement savings scenarios.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono flex items-center gap-2 text-slate-300">
            <Building2 className="w-4 h-4 text-emerald-400" />
            <span>Tenant: <strong className="text-emerald-300">{selectedOrg?.code || data.org_id}</strong></span>
          </div>
          <div className={`px-3 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-1.5 ${
            audit_integrity.status === "OK"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-red-950/40 border-red-500/40 text-red-300"
          }`}>
            <ShieldCheck className="w-4 h-4" />
            <span>Audit Chain: <strong>{audit_integrity.status}</strong> ({audit_integrity.verified_records} txns)</span>
          </div>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        {/* Catalog Completeness */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs text-slate-400 font-sans flex items-center justify-between">
            <span>Item Completeness</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
              HARD=2, REQ=1
            </span>
          </div>
          <div className="text-3xl font-bold text-slate-100 mt-2">
            {catalog_health.catalog_completeness.toFixed(1)}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1.5 flex items-center gap-1">
            <span>Classified: </span>
            <strong className="text-emerald-400">{catalog_health.classified_share.toFixed(1)}%</strong>
            <span className="text-slate-500">({catalog_health.uncertain_items_count} uncertain)</span>
          </div>
        </div>

        {/* Harmonization Compression */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs text-slate-400 font-sans flex items-center justify-between">
            <span>Harmonization Ratio</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-500/30">
              Deduplication
            </span>
          </div>
          <div className="text-3xl font-bold text-slate-100 mt-2">
            {harmonization.compression_ratio.toFixed(2)}x
          </div>
          <div className="text-[11px] text-slate-400 mt-1.5">
            <span className="text-slate-300 font-semibold">{harmonization.raw_items_before}</span> raw &rarr;{" "}
            <span className="text-emerald-400 font-semibold">{harmonization.golden_masters_after}</span> golden
          </div>
        </div>

        {/* Duplicate Rate */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs text-slate-400 font-sans flex items-center justify-between">
            <span>Duplicate Rate</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-500/30">
              Pre-procurement
            </span>
          </div>
          <div className="text-3xl font-bold text-slate-100 mt-2">
            {catalog_health.duplicate_rate.toFixed(1)}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1.5">
            Duplicate requests stopped before RFQ
          </div>
        </div>

        {/* OCR Engine Status */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs text-slate-400 font-sans flex items-center justify-between">
            <span>OCR Intake Engine</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
              ocr_readiness.ready
                ? "bg-emerald-950 text-emerald-400 border-emerald-500/30"
                : "bg-red-950 text-red-400 border-red-500/30"
            }`}>
              {ocr_readiness.ready ? "READY" : "DEGRADED"}
            </span>
          </div>
          <div className="text-xl font-bold text-slate-100 mt-2 truncate">
            {ocr_readiness.primary_engine}
          </div>
          <div className="text-[11px] text-slate-400 mt-1.5">
            Fallback: {ocr_readiness.fallback_engine}
          </div>
        </div>
      </div>

      {/* Middle Grid: Queue Depth & Tier Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Review Queue Depth by Domain */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Stewardship Queue Depth by Domain
            </h3>
            <span className="text-xs font-mono text-slate-400">Total Open: {Object.values(queue_by_domain).reduce((a, b) => a + b, 0)}</span>
          </div>
          <div className="space-y-3 font-mono text-xs">
            {Object.entries(queue_by_domain).map(([domain, count]) => {
              const max = 10;
              const pct = Math.min(100, Math.round((count / max) * 100));
              return (
                <div key={domain} className="space-y-1">
                  <div className="flex justify-between text-slate-300">
                    <span>{domain}</span>
                    <span className="font-bold text-slate-100">{count} tasks</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.max(8, pct)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Tier Distribution Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              Match Candidate Tier Breakdown
            </h3>
            <span className="text-xs font-mono text-slate-400">Invariants S1–S14</span>
          </div>
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/20 flex justify-between items-center">
              <div>
                <strong className="text-emerald-400 block">Tier 1 — Exact Physical Identity</strong>
                <span className="text-[11px] text-slate-400 font-sans">Automatic substitution permitted (100% precision)</span>
              </div>
              <div className="text-xl font-bold text-emerald-300">{tier_distribution["1"] || 0}</div>
            </div>

            <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/20 flex justify-between items-center">
              <div>
                <strong className="text-amber-400 block">Tier 2 — Directional Upgrade / Missing Spec</strong>
                <span className="text-[11px] text-slate-400 font-sans">Requires domain-steward concurrence</span>
              </div>
              <div className="text-xl font-bold text-amber-300">{tier_distribution["2"] || 0}</div>
            </div>

            <div className="p-3 rounded-lg bg-red-950/30 border border-red-500/20 flex justify-between items-center">
              <div>
                <strong className="text-red-400 block">Tier 3 — HARD Mismatch / Safety Refusal</strong>
                <span className="text-[11px] text-slate-400 font-sans">Substitution strictly prohibited</span>
              </div>
              <div className="text-xl font-bold text-red-300">{tier_distribution["3"] || 0}</div>
            </div>
          </div>
        </div>

        {/* Top Missing Attributes Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Top Missing Attributes (Catalog Gap)
            </h3>
            <span className="text-xs font-mono text-amber-400">
              Statutory Missing: {catalog_health.statutory_missing_count}
            </span>
          </div>
          <div className="space-y-4 font-mono text-xs">
            {Object.entries(catalog_health.top_missing_attributes).map(([subcat, attrs]) => (
              <div key={subcat} className="space-y-1.5 border-b border-slate-800 pb-3 last:border-b-0 last:pb-0">
                <div className="text-slate-300 font-semibold flex items-center justify-between">
                  <span>{subcat}</span>
                  <span className="text-[10px] text-slate-500">{attrs.length} gaps</span>
                </div>
                <div className="space-y-1">
                  {attrs.map((item) => (
                    <div key={item.attribute} className="flex justify-between text-slate-400 text-[11px]">
                      <span>&bull; {item.attribute}</span>
                      <span className="text-amber-400 font-bold">{item.missing_pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Section 19.2: Inter-CPSE Spend Pooling & Financial Savings Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-mono font-medium text-emerald-400 mb-1">
              <IndianRupee className="w-3.5 h-3.5" />
              Section 19.2 Scenario-Based Financial Calculations
            </div>
            <h2 className="text-lg font-bold text-slate-100">
              Standardized Material Clusters & Inter-CPSE Savings Scenarios
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Reflects pure mathematical calculations: Low (0.5x), Base (1.0x), High (1.25x capped at 25%).
            </p>
          </div>
          <div className="text-xs font-mono text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            14 Validated Clusters
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                <th className="py-2.5 px-3">Cluster ID</th>
                <th className="py-2.5 px-3">Domain</th>
                <th className="py-2.5 px-3">Description</th>
                <th className="py-2.5 px-3 text-right">Spend (INR)</th>
                <th className="py-2.5 px-3 text-center">Table %</th>
                <th className="py-2.5 px-3 text-right text-slate-300">Low (0.5x)</th>
                <th className="py-2.5 px-3 text-right text-emerald-300 font-bold">Base (1.0x)</th>
                <th className="py-2.5 px-3 text-right text-slate-300">High (1.25x)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {clusters?.map((c) => (
                <tr key={c.cluster_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 px-3 font-bold text-slate-300">#{c.cluster_id}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                      {c.domain}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-sans text-slate-100 font-medium max-w-xs truncate">
                    {c.description}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-300">
                    ₹{c.annual_spend_inr.toLocaleString("en-IN")}
                  </td>
                  <td className="py-2.5 px-3 text-center font-bold text-emerald-400">
                    {c.table_pct_display}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-400">
                    ₹{c.low_savings.toLocaleString("en-IN")}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                    ₹{c.base_savings.toLocaleString("en-IN")}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-400">
                    ₹{c.high_savings.toLocaleString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              {clusters && (
                <tr className="border-t-2 border-slate-700 font-bold text-slate-100 text-xs bg-slate-950/50">
                  <td colSpan={3} className="py-3 px-3 uppercase">Total Portfolio (14 Clusters)</td>
                  <td className="py-3 px-3 text-right">
                    ₹{clusters.reduce((sum, c) => sum + c.annual_spend_inr, 0).toLocaleString("en-IN")}
                  </td>
                  <td className="py-3 px-3 text-center text-emerald-400">&mdash;</td>
                  <td className="py-3 px-3 text-right text-slate-300">
                    ₹{clusters.reduce((sum, c) => sum + c.low_savings, 0).toLocaleString("en-IN")}
                  </td>
                  <td className="py-3 px-3 text-right text-emerald-300 text-sm">
                    ₹{clusters.reduce((sum, c) => sum + c.base_savings, 0).toLocaleString("en-IN")}
                  </td>
                  <td className="py-3 px-3 text-right text-slate-300">
                    ₹{clusters.reduce((sum, c) => sum + c.high_savings, 0).toLocaleString("en-IN")}
                  </td>
                </tr>
              )}
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
