"use client";

import React, { useState, useMemo } from "react";
import { useAuth } from "@/lib/auth-context";
import { FacetedFilterDrawer, FacetGroup } from "@/components/common/FacetedFilterDrawer";
import { DensityToggle, TableDensity, getDensityRowClasses } from "@/components/common/DensityToggle";
import {
  BookOpen,
  Search,
  CheckCircle2,
  Clock,
  Layers,
  Building2,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  AlertOctagon,
  Tag,
  Hash,
  SlidersHorizontal,
} from "lucide-react";

interface GoldenMasterRecord {
  golden_code: string;
  descriptor: string;
  sector: string;
  subcategory: string;
  status: "ACTIVE" | "DRAFT" | "DEPRECATED";
  attributes: Record<string, string | number>;
  aliases: string[];
  where_used: { cpse: string; plant: string; raw_count: number }[];
  created_at: string;
}

const SAMPLE_MASTERS: GoldenMasterRecord[] = [
  {
    golden_code: "MPNG-0004821937-3",
    descriptor: "VALVES.GATE | 100NB | CL150 | A216-WCB | FLG-RF",
    sector: "COMMON",
    subcategory: "VALVES.GATE",
    status: "ACTIVE",
    attributes: {
      size_nb: 100,
      pressure_class: 150,
      material_grade: "A216 WCB",
      end_connection: "FLANGED",
      facing: "RF",
      industry_standard: "API 600",
    },
    aliases: ["GATE VLV 100 NB 150#", "VALVE GATE FLGD RF 4 INCH 150 LB WCB"],
    where_used: [
      { cpse: "OIL-1", plant: "Koyali Refinery", raw_count: 14 },
      { cpse: "OIL-2", plant: "Panipat Refinery", raw_count: 8 },
      { cpse: "POWER-1", plant: "Ramagundam STPS", raw_count: 5 },
    ],
    created_at: "2025-11-10",
  },
  {
    golden_code: "MPNG-0005728193-5",
    descriptor: "HEAVY.BEARING | 22220 EK/C3 | SPHERICAL ROLLER",
    sector: "HEAVY_ENG",
    subcategory: "BEARINGS.SPHERICAL",
    status: "ACTIVE",
    attributes: {
      bearing_type: "SPHERICAL ROLLER",
      bore_code: "22220",
      taper_bore: "EK",
      clearance: "C3",
    },
    aliases: ["22220EK/C3", "BEARING SPHERICAL ROLLER 22220"],
    where_used: [
      { cpse: "HEAVY-1", plant: "Ranchi Heavy Machine Bldg", raw_count: 6 },
      { cpse: "STEEL-1", plant: "Bhilai Steel Plant", raw_count: 12 },
    ],
    created_at: "2025-12-01",
  },
  {
    golden_code: "MPNG-0003928172-8",
    descriptor: "GASKETS.SPIRAL | 100NB | CL150 | 316-GRAPHITE",
    sector: "COMMON",
    subcategory: "GASKETS.SPIRAL",
    status: "ACTIVE",
    attributes: {
      size_nb: 100,
      pressure_class: 150,
      winding_material: "SS 316",
      filler_material: "FLEXIBLE GRAPHITE",
    },
    aliases: ["SPWD GSKT 100 NB 150#", "GASKET SPIRAL WOUND 4 INCH CL150"],
    where_used: [
      { cpse: "POWER-1", plant: "Ramagundam STPS", raw_count: 22 },
      { cpse: "OIL-1", plant: "Koyali Refinery", raw_count: 18 },
    ],
    created_at: "2026-01-15",
  },
  {
    golden_code: "MPNG-0008472910-4",
    descriptor: "POWER.TRANSFORMER | 100KVA | 11/0.433KV",
    sector: "POWER",
    subcategory: "TRANSFORMERS.DISTRIBUTION",
    status: "ACTIVE",
    attributes: {
      rating_kva: 100,
      primary_voltage_kv: 11.0,
      secondary_voltage_kv: 0.433,
      cooling: "ONAN",
    },
    aliases: ["DIST TX 100 KVA 11KV", "TRANSFORMER 100KVA 11/.433KV"],
    where_used: [
      { cpse: "POWER-1", plant: "Singrauli STPS", raw_count: 3 },
      { cpse: "STEEL-1", plant: "Bhilai Steel Plant", raw_count: 2 },
    ],
    created_at: "2026-02-20",
  },
  {
    golden_code: "MPNG-0009182741-2",
    descriptor: "VALVES.BALL | 50NB | CL300 | A105 | FLG-RF",
    sector: "COMMON",
    subcategory: "VALVES.BALL",
    status: "DRAFT",
    attributes: {
      size_nb: 50,
      pressure_class: 300,
      material_grade: "A105",
      end_connection: "FLANGED",
      facing: "RF",
    },
    aliases: ["BALL VALVE 50 NB 300#"],
    where_used: [
      { cpse: "OIL-1", plant: "Koyali Refinery", raw_count: 4 },
    ],
    created_at: "2026-03-01",
  },
];

export default function MasterCataloguePage() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [density, setDensity] = useState<TableDensity>("standard");
  const [selectedMaster, setSelectedMaster] = useState<GoldenMasterRecord | null>(SAMPLE_MASTERS[0]);

  // Faceted Filters State (AWS Console pattern)
  const [selectedFacets, setSelectedFacets] = useState<Record<string, string[]>>({
    sector: [],
    status: [],
  });

  // Lifecycle confirmation state
  const [lifecycleModal, setLifecycleModal] = useState<{
    master: GoldenMasterRecord;
    targetStatus: "ACTIVE" | "DEPRECATED";
  } | null>(null);
  const [lifecycleRationale, setLifecycleRationale] = useState("");
  const [mastersList, setMastersList] = useState<GoldenMasterRecord[]>(SAMPLE_MASTERS);

  // Merge and Split stewardship action states
  const [mergeModal, setMergeModal] = useState<GoldenMasterRecord | null>(null);
  const [mergeTargetCode, setMergeTargetCode] = useState("");
  const [mergeRationale, setMergeRationale] = useState("");
  const [splitModal, setSplitModal] = useState<GoldenMasterRecord | null>(null);
  const [splitNewDescriptor, setSplitNewDescriptor] = useState("");
  const [splitRationale, setSplitRationale] = useState("");
  const [stewardshipNotice, setStewardshipNotice] = useState<string | null>(null);

  // Build facet groups with live counts
  const facetGroups: FacetGroup[] = useMemo(() => {
    const sectorCounts: Record<string, number> = {};
    const statusCounts: Record<string, number> = {};

    mastersList.forEach((m) => {
      sectorCounts[m.sector] = (sectorCounts[m.sector] || 0) + 1;
      statusCounts[m.status] = (statusCounts[m.status] || 0) + 1;
    });

    return [
      {
        id: "sector",
        name: "Sector Pack",
        options: Object.entries(sectorCounts).map(([k, v]) => ({
          id: k,
          label: k,
          count: v,
        })),
      },
      {
        id: "status",
        name: "Lifecycle Status",
        options: Object.entries(statusCounts).map(([k, v]) => ({
          id: k,
          label: k,
          count: v,
        })),
      },
    ];
  }, [mastersList]);

  const handleFacetChange = (groupId: string, optionId: string) => {
    setSelectedFacets((prev) => {
      const current = prev[groupId] || [];
      const updated = current.includes(optionId)
        ? current.filter((id) => id !== optionId)
        : [...current, optionId];
      return { ...prev, [groupId]: updated };
    });
  };

  const handleResetFacets = () => {
    setSelectedFacets({ sector: [], status: [] });
  };

  const filteredMasters = useMemo(() => {
    return mastersList.filter((m) => {
      const q = search.toLowerCase().trim();
      const matchesSearch =
        !q ||
        m.golden_code.toLowerCase().includes(q) ||
        m.descriptor.toLowerCase().includes(q) ||
        m.subcategory.toLowerCase().includes(q);

      const matchesSector =
        (selectedFacets.sector?.length ?? 0) === 0 ||
        selectedFacets.sector.includes(m.sector);

      const matchesStatus =
        (selectedFacets.status?.length ?? 0) === 0 ||
        selectedFacets.status.includes(m.status);

      return matchesSearch && matchesSector && matchesStatus;
    });
  }, [mastersList, search, selectedFacets]);

  const handleApplyLifecycleChange = () => {
    if (!lifecycleModal || !lifecycleRationale.trim()) return;
    setMastersList((prev) =>
      prev.map((item) =>
        item.golden_code === lifecycleModal.master.golden_code
          ? { ...item, status: lifecycleModal.targetStatus }
          : item
      )
    );
    if (selectedMaster?.golden_code === lifecycleModal.master.golden_code) {
      setSelectedMaster((prev) => (prev ? { ...prev, status: lifecycleModal.targetStatus } : null));
    }
    setLifecycleModal(null);
    setLifecycleRationale("");
  };

  const handleProposeMerge = () => {
    if (!mergeModal || !mergeTargetCode.trim() || !mergeRationale.trim()) return;
    setStewardshipNotice(
      `Stewardship Task Submitted: Propose MERGE ${mergeModal.golden_code} into ${mergeTargetCode}. Awaiting Checker domain sign-off.`
    );
    setMergeModal(null);
    setMergeTargetCode("");
    setMergeRationale("");
  };

  const handleProposeSplit = () => {
    if (!splitModal || !splitNewDescriptor.trim() || !splitRationale.trim()) return;
    setStewardshipNotice(
      `Stewardship Task Submitted: Propose SPLIT of ${splitModal.golden_code} into variant '${splitNewDescriptor}'. Awaiting Checker domain sign-off.`
    );
    setSplitModal(null);
    setSplitNewDescriptor("");
    setSplitRationale("");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30 mb-2">
            <BookOpen className="w-3.5 h-3.5" />
            Master Golden Catalogue Browser (Section 8.0, 9.1, 15.1)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Central Golden Master Repository & Verhoeff Codes
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Authoritative national material catalog. Enforces Verhoeff MPNG-17 check digit codes, canonical attribute keys, lifecycle stewardship, and cross-CPSE where-used linkage.
          </p>
        </div>

        {/* Density Toggle */}
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400 hidden sm:inline">Density:</span>
          <DensityToggle density={density} onChange={setDensity} />
        </div>
      </div>

      {/* Stewardship Notice Banner */}
      {stewardshipNotice && (
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-500/40 text-emerald-900 dark:text-emerald-300 font-mono text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{stewardshipNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setStewardshipNotice(null)}
            className="text-slate-500 hover:text-slate-900 dark:hover:text-white px-2 py-0.5"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Layout: Left Faceted Filters + Right Content */}
      <div className="flex flex-col md:flex-row gap-6 items-start">
        {/* Amazon/AWS-Style Faceted Filter Drawer */}
        <FacetedFilterDrawer
          groups={facetGroups}
          selectedFacets={selectedFacets}
          onChange={handleFacetChange}
          onReset={handleResetFacets}
        />

        {/* Core Catalog Area */}
        <div className="flex-1 w-full space-y-6">
          {/* Search Bar & Quick Sector Filter */}
          <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl p-3 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <Search className="w-4 h-4 text-slate-400 shrink-0" />
                <input
                  type="text"
                  placeholder="Search by Verhoeff MPNG code, descriptor, or subcategory..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-transparent text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none font-mono"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch("")}
                    className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    ✕
                  </button>
                )}
              </div>

              <select
                aria-label="Sector Filter"
                value={selectedFacets.sector.length === 1 ? selectedFacets.sector[0] : "ALL"}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedFacets((prev) => ({
                    ...prev,
                    sector: val === "ALL" ? [] : [val],
                  }));
                }}
                className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs font-mono text-slate-700 dark:text-slate-300 focus:outline-none shrink-0"
              >
                <option value="ALL">ALL SECTORS</option>
                <option value="POWER">POWER</option>
                <option value="STEEL">STEEL</option>
                <option value="MINING">MINING</option>
                <option value="HEAVY_ENG">HEAVY_ENG</option>
                <option value="COMMON">COMMON</option>
              </select>
            </div>
          </div>

          {/* Master List & Master Detail Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Masters List */}
            <div className="lg:col-span-5 space-y-3">
              <div className="text-xs font-mono text-slate-500 dark:text-slate-400 flex justify-between items-center px-1">
                <span>Matching Masters ({filteredMasters.length})</span>
                <span className="text-emerald-600 dark:text-emerald-400">Verhoeff Validated</span>
              </div>

              <div className="space-y-2.5 max-h-[650px] overflow-y-auto pr-1">
                {filteredMasters.length === 0 ? (
                  <div className="p-12 text-center bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-400">
                    No golden masters match selected criteria.
                  </div>
                ) : (
                  filteredMasters.map((master) => {
                    const isSelected = selectedMaster?.golden_code === master.golden_code;
                    const rowClass = getDensityRowClasses(density);

                    return (
                      <div
                        key={master.golden_code}
                        onClick={() => setSelectedMaster(master)}
                        className={`rounded-xl border cursor-pointer transition-all ${rowClass} ${
                          isSelected
                            ? "bg-emerald-50/70 dark:bg-slate-900 border-emerald-500 shadow-sm"
                            : "bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900/60"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">
                            {master.golden_code}
                          </span>
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                              master.status === "ACTIVE"
                                ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30"
                                : master.status === "DRAFT"
                                ? "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/30"
                                : "bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-500/30"
                            }`}
                          >
                            {master.status}
                          </span>
                        </div>

                        <div className="mt-1.5 font-mono font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                          {master.descriptor}
                        </div>

                        <div className="mt-1.5 flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 pt-1.5 border-t border-slate-100 dark:border-slate-800/60">
                          <span>{master.subcategory}</span>
                          <span className="text-slate-400">{master.sector}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Master Detail View */}
            <div className="lg:col-span-7">
              {selectedMaster ? (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6 shadow-sm">
                  {/* Header */}
                  <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-mono">
                          {selectedMaster.golden_code}
                        </h2>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                            selectedMaster.status === "ACTIVE"
                              ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30"
                              : selectedMaster.status === "DRAFT"
                              ? "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/30"
                              : "bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-500/30"
                          }`}
                        >
                          {selectedMaster.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 dark:text-slate-300 font-mono mt-1 font-semibold">
                        {selectedMaster.descriptor}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setMergeModal(selectedMaster);
                          const other = mastersList.find((m) => m.golden_code !== selectedMaster.golden_code);
                          setMergeTargetCode(other ? other.golden_code : "");
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-purple-100 dark:bg-purple-950/70 hover:bg-purple-200 dark:hover:bg-purple-900 text-purple-900 dark:text-purple-300 border border-purple-300 dark:border-purple-700/50 transition-colors"
                      >
                        Propose Merge
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setSplitModal(selectedMaster);
                          setSplitNewDescriptor(`${selectedMaster.descriptor} - VARIANT`);
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-sky-100 dark:bg-sky-950/70 hover:bg-sky-200 dark:hover:bg-sky-900 text-sky-900 dark:text-sky-300 border border-sky-300 dark:border-sky-700/50 transition-colors"
                      >
                        Propose Split
                      </button>

                      {selectedMaster.status === "DRAFT" && (
                        <button
                          type="button"
                          onClick={() =>
                            setLifecycleModal({ master: selectedMaster, targetStatus: "ACTIVE" })
                          }
                          className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm"
                        >
                          Promote to ACTIVE
                        </button>
                      )}
                      {selectedMaster.status === "ACTIVE" && (
                        <button
                          type="button"
                          onClick={() =>
                            setLifecycleModal({ master: selectedMaster, targetStatus: "DEPRECATED" })
                          }
                          className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-rose-100 dark:bg-rose-950/70 hover:bg-rose-200 dark:hover:bg-rose-900 text-rose-900 dark:text-rose-300 border border-rose-300 dark:border-rose-700/50 transition-colors"
                        >
                          Deprecate Master
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Canonical Physical Attributes */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                      <Tag className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      Canonical Physical Attributes
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 font-mono text-xs">
                      {Object.entries(selectedMaster.attributes).map(([k, v]) => (
                        <div key={k} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                          <span className="text-[10px] text-slate-500 block uppercase">{k}</span>
                          <strong className="text-slate-900 dark:text-slate-100">{String(v)}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Known Aliases */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                      <Hash className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      Known Enterprise Aliases
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedMaster.aliases.map((alias) => (
                        <span
                          key={alias}
                          className="px-2.5 py-1 rounded bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 text-xs font-mono"
                        >
                          {alias}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Where-Used Across CPSE Plants */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      Where-Used Across CPSE Plants
                    </h3>
                    <div className="space-y-2">
                      {selectedMaster.where_used.map((u) => (
                        <div
                          key={u.plant}
                          className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-mono"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-emerald-700 dark:text-emerald-400">{u.cpse}</span>
                            <span className="text-slate-700 dark:text-slate-300 font-sans">{u.plant}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-800 text-[11px]">
                            {u.raw_count} linked items
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center bg-white dark:bg-slate-900/40 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-400">
                  Select a golden master from the list to view specifications and where-used links.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Lifecycle Modal */}
      {lifecycleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                Change Master Status &rarr; {lifecycleModal.targetStatus}
              </h3>
              <button
                type="button"
                onClick={() => setLifecycleModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
              >
                ✕ Esc
              </button>
            </div>

            <p className="text-slate-600 dark:text-slate-300 font-sans">
              Changing lifecycle status of Golden Master <strong>{lifecycleModal.master.golden_code}</strong> requires formal engineering rationale for the tamper-evident audit log.
            </p>

            <div>
              <label className="text-slate-700 dark:text-slate-300 block mb-1 font-semibold">Engineering Rationale *</label>
              <textarea
                rows={3}
                value={lifecycleRationale}
                onChange={(e) => setLifecycleRationale(e.target.value)}
                placeholder="e.g. Master verified across multiple refinery specifications; ready for production active harmonization..."
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-2 text-slate-900 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setLifecycleModal(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplyLifecycleChange}
                disabled={!lifecycleRationale.trim()}
                className="px-4 py-1.5 rounded-lg font-bold bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40"
              >
                Confirm Status Change
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Modal */}
      {mergeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                Propose Golden Master Merge
              </h3>
              <button
                type="button"
                onClick={() => setMergeModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
              >
                ✕ Esc
              </button>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 dark:text-slate-400">Source Golden Master:</span>
              <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200">
                <strong className="text-purple-700 dark:text-purple-400">{mergeModal.golden_code}</strong>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{mergeModal.descriptor}</div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-slate-700 dark:text-slate-300 block font-semibold">Target Golden Master Code *</label>
              <select
                value={mergeTargetCode}
                onChange={(e) => setMergeTargetCode(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                {mastersList
                  .filter((m) => m.golden_code !== mergeModal.golden_code)
                  .map((m) => (
                    <option key={m.golden_code} value={m.golden_code}>
                      {m.golden_code} — {m.descriptor}
                    </option>
                  ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-slate-700 dark:text-slate-300 block font-semibold">Engineering Rationale & Justification *</label>
              <textarea
                rows={3}
                value={mergeRationale}
                onChange={(e) => setMergeRationale(e.target.value)}
                placeholder="e.g. Dimensions, metallurgy, and ASME standards are physically identical; legacy duplicate entry across CPSE stores..."
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500 font-sans"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setMergeModal(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleProposeMerge}
                disabled={!mergeTargetCode.trim() || !mergeRationale.trim()}
                className="px-4 py-1.5 rounded-lg font-bold bg-purple-600 text-white hover:bg-purple-500 disabled:opacity-40"
              >
                Submit Merge Proposal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Modal */}
      {splitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                Propose Golden Master Split
              </h3>
              <button
                type="button"
                onClick={() => setSplitModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
              >
                ✕ Esc
              </button>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 dark:text-slate-400">Source Golden Master:</span>
              <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200">
                <strong className="text-sky-700 dark:text-sky-400">{splitModal.golden_code}</strong>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{splitModal.descriptor}</div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-slate-700 dark:text-slate-300 block font-semibold">New Variant Canonical Descriptor *</label>
              <input
                type="text"
                value={splitNewDescriptor}
                onChange={(e) => setSplitNewDescriptor(e.target.value)}
                placeholder="e.g. VALVES.GATE | 100NB | CL300 | A216-WCB | FLG-RF"
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-700 dark:text-slate-300 block font-semibold">Engineering Rationale & Justification *</label>
              <textarea
                rows={3}
                value={splitRationale}
                onChange={(e) => setSplitRationale(e.target.value)}
                placeholder="e.g. Discovered distinct pressure class variants previously lumped together; splitting into distinct Verhoeff MPNG masters..."
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500 font-sans"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setSplitModal(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleProposeSplit}
                disabled={!splitNewDescriptor.trim() || !splitRationale.trim()}
                className="px-4 py-1.5 rounded-lg font-bold bg-sky-600 text-white hover:bg-sky-500 disabled:opacity-40"
              >
                Submit Split Proposal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
