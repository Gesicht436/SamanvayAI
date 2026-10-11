"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  Search,
  GitCompare,
  ListTodo,
  ShieldCheck,
  Building2,
  ArrowRight,
  Lock,
  BarChart3,
  Factory,
  Boxes,
  FileCheck,
} from "lucide-react";

export default function HomePage() {
  const { selectedOrg } = useAuth();

  const featureCards = [
    {
      title: "Executive Dashboard & Health Scorecard",
      description: "Real-time catalog completeness, queue depth by domain, directional harmonization, and 14 cluster savings scenario table.",
      href: "/dashboard",
      icon: BarChart3,
      tag: "Module 10",
      badge: "Live KPI",
    },
    {
      title: "Material Standardizer",
      description: "Extract physical and statutory attributes with evidence spans from legacy descriptions. Retrieve ranked golden masters.",
      href: "/standardizer",
      icon: Search,
      tag: "Module 1 & 6",
      badge: "P0 Core",
    },
    {
      title: "Diff Inspector",
      description: "Explain harmonization decisions with side-by-side attribute matrices: EXACT (green), MISSING/UPGRADE (amber), MISMATCH (red).",
      href: "/diff",
      icon: GitCompare,
      tag: "Module 3",
      badge: "Explainable",
    },
    {
      title: "Stewardship Governance",
      description: "Maker-Checker task management. Enforces domain tags, Maker != Checker rules, and transactional SHA-256 audit logs.",
      href: "/queue",
      icon: ListTodo,
      tag: "Module 7",
      badge: "Governance",
    },
    {
      title: "OEM Catalogue Onboarding Wizard",
      description: "Bulk spares ingestion with part number normalization, supersession detection (OLD->NEW), and Maker-Checker approval.",
      href: "/oem",
      icon: Factory,
      tag: "Module 10",
      badge: "Supersession",
    },
    {
      title: "Stock Lots & Life Monitor",
      description: "Tracks physical shelf-life and usage across CPSE plants. Enforces Invariant S8 and ordered FEFO disposition ladder.",
      href: "/lots",
      icon: Boxes,
      tag: "Module 5",
      badge: "FEFO Ladder",
    },
    {
      title: "Document Intake & MTC Conformance",
      description: "Validates metallurgical test reports against ASTM/ASME standards, computes CE_IIW, and stops pre-procurement duplicates.",
      href: "/docs",
      icon: FileCheck,
      tag: "Module 4",
      badge: "Metallurgy S15",
    },
    {
      title: "Evaluation Gate & Parity",
      description: "3 Baselines side-by-side: Cosine (67.6% err) vs Trigram (55.9% err) vs Samanvay (0.0% err). Exact Clopper-Pearson bounds.",
      href: "/eval",
      icon: ShieldCheck,
      tag: "Module 8",
      badge: "Release Gate",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-8 sm:p-10 relative overflow-hidden">
        <div className="max-w-3xl space-y-4 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            National CPSE Material Standardization Architecture
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight leading-tight">
            Deterministic Material Harmonization for Indian Public Enterprises
          </h1>

          <p className="text-sm text-slate-300 leading-relaxed">
            Eliminates multi-crore duplicate inventories across Oil & Gas, Power, Steel, Mining, and Heavy Engineering. Governed by 15 immutable safety invariants ($S1$–$S15$) to prevent catastrophic plant substitutions.
          </p>

          {/* Org context indicator */}
          <div className="pt-2">
            {selectedOrg ? (
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-slate-800/80 border border-slate-700 text-xs font-mono text-slate-200">
                <Building2 className="w-4 h-4 text-emerald-400" />
                Active Enterprise: <strong className="text-emerald-300">{selectedOrg.name}</strong> ({selectedOrg.code})
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-amber-950/40 border border-amber-500/40 text-xs font-mono text-amber-300">
                <Building2 className="w-4 h-4 text-amber-400" />
                No CPSE selected. Use the header dropdown to switch active organisation context.
              </div>
            )}
          </div>
        </div>

        {/* Decorative background grid */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
      </div>

      {/* Core Platform Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-500">Supported Families</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">21 Families</div>
          <div className="text-[11px] text-emerald-400 mt-1">5 Domain Packs</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-500">Safety Invariants</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">S1 to S15</div>
          <div className="text-[11px] text-emerald-400 mt-1">Directional Lattices</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-500">Adversarial False Merges</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">0.0% (0 / 170)</div>
          <div className="text-[11px] text-slate-400 mt-1">vs 67.6% Cosine</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-500">Audit Verification</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">SHA-256 Chain</div>
          <div className="text-[11px] text-emerald-400 mt-1">Maker-Checker Gated</div>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {featureCards.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.href}
              href={card.href}
              className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-emerald-500/50 hover:bg-slate-800/50 transition-all group shadow-md"
            >
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center border border-slate-700 group-hover:border-emerald-500/40 group-hover:bg-emerald-950/40 transition-colors">
                  <Icon className="w-5 h-5 text-emerald-400" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    {card.tag}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                    {card.badge}
                  </span>
                </div>
              </div>

              <h2 className="text-base font-bold text-slate-100 mt-4 group-hover:text-emerald-300 transition-colors flex items-center justify-between">
                {card.title}
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
              </h2>

              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                {card.description}
              </p>
            </Link>
          );
        })}
      </div>

      {/* Architecture & Neutrality Notice */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-lg p-5 text-xs text-slate-400 flex items-start gap-4">
        <Lock className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-slate-300 font-semibold block">
            Federated Multi-Enterprise Privacy & Integrity
          </strong>
          <p className="leading-relaxed">
            Row-Level Security (RLS) ensures CPSEs cannot observe competing internal procurement pricing or proprietary stock locations without bilateral agreement. All state changes append immutable cryptographic entries to the central hash chain.
          </p>
        </div>
      </div>
    </div>
  );
}
