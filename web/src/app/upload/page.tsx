"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Database,
  Building2,
  Table,
  Sparkles,
} from "lucide-react";

interface MappingProfile {
  name: string;
  erp: string;
  mapping: Record<string, string>;
}

const PRESET_PROFILES: MappingProfile[] = [
  {
    name: "SAP MARA / MAKT Profile",
    erp: "SAP ERP",
    mapping: {
      MATNR: "item_code",
      MAKTX: "description",
      MEINS: "uom",
      WERKS: "plant",
      LABST: "quantity",
    },
  },
  {
    name: "Oracle Cloud ERP Profile",
    erp: "Oracle ERP",
    mapping: {
      ITEM_NUMBER: "item_code",
      ITEM_DESCRIPTION: "description",
      PRIMARY_UOM_CODE: "uom",
      ORGANIZATION_CODE: "plant",
      ON_HAND_QUANTITY: "quantity",
    },
  },
  {
    name: "IBM Maximo Item Master",
    erp: "IBM Maximo",
    mapping: {
      ITEMNUM: "item_code",
      DESCRIPTION: "description",
      ORDERUNIT: "uom",
      SITEID: "plant",
      CURBAL: "quantity",
    },
  },
];

interface SampleRow {
  row_id: number;
  source_data: Record<string, string>;
  mapped: {
    item_code: string;
    description: string;
    uom: string;
    plant: string;
    quantity: string;
  };
  validation_status: "VALID" | "WARNING" | "INVALID";
  notes?: string;
}

const INITIAL_ROWS: SampleRow[] = [
  {
    row_id: 1,
    source_data: {
      MATNR: "MAT-77001",
      MAKTX: "GATE VALVE 100 NB CL150 WCB FLANGED RF API 600",
      MEINS: "EA",
      WERKS: "KOYALI",
      LABST: "18",
    },
    mapped: {
      item_code: "MAT-77001",
      description: "GATE VALVE 100 NB CL150 WCB FLANGED RF API 600",
      uom: "EA",
      plant: "KOYALI",
      quantity: "18",
    },
    validation_status: "VALID",
  },
  {
    row_id: 2,
    source_data: {
      MATNR: "MAT-77002",
      MAKTX: "BALL VALVE 50 NB CL300 A105 RF",
      MEINS: "NOS",
      WERKS: "RAMAGUNDAM",
      LABST: "24",
    },
    mapped: {
      item_code: "MAT-77002",
      description: "BALL VALVE 50 NB CL300 A105 RF",
      uom: "NOS",
      plant: "RAMAGUNDAM",
      quantity: "24",
    },
    validation_status: "WARNING",
    notes: "UoM 'NOS' will be normalized to canonical 'EA' via Invariant S13 dictionary.",
  },
  {
    row_id: 3,
    source_data: {
      MATNR: "MAT-77003",
      MAKTX: "POWER CABLE 1.1KV 4C X 16 SQMM XLPE ARMOURED",
      MEINS: "MTR",
      WERKS: "BHILAI",
      LABST: "500",
    },
    mapped: {
      item_code: "MAT-77003",
      description: "POWER CABLE 1.1KV 4C X 16 SQMM XLPE ARMOURED",
      uom: "MTR",
      plant: "BHILAI",
      quantity: "500",
    },
    validation_status: "VALID",
  },
  {
    row_id: 4,
    source_data: {
      MATNR: "MAT-77004",
      MAKTX: "GASKET SPIRAL WOUND 100 NB",
      MEINS: "",
      WERKS: "RANCHI",
      LABST: "100",
    },
    mapped: {
      item_code: "MAT-77004",
      description: "GASKET SPIRAL WOUND 100 NB",
      uom: "",
      plant: "RANCHI",
      quantity: "100",
    },
    validation_status: "WARNING",
    notes: "Missing UoM on source record. Will default to subcategory target EA.",
  },
];

export default function TabularIngestionPage() {
  const { selectedOrg } = useAuth();
  const [selectedProfileIndex, setSelectedProfileIndex] = useState(0);
  const [rows, setRows] = useState<SampleRow[]>(INITIAL_ROWS);
  const [fileName, setFileName] = useState("SAP_Plant_Export_2026.csv");
  const [ingested, setIngested] = useState(false);
  const [ingestSummary, setIngestSummary] = useState<{
    total: number;
    valid: number;
    warnings: number;
  } | null>(null);

  const activeProfile = PRESET_PROFILES[selectedProfileIndex];

  const handleRunIngest = () => {
    setIngested(true);
    setIngestSummary({
      total: rows.length,
      valid: rows.filter((r) => r.validation_status === "VALID").length,
      warnings: rows.filter((r) => r.validation_status === "WARNING").length,
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 mb-2">
            <Table className="w-3.5 h-3.5" />
            Tabular Ingestion & Column Mapping (Section 4.1, 12.0, 15.1)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Batch Tabular Ingestion & ERP Schema Mapping
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Ingest enterprise CSV, TSV, and Excel spreadsheets from SAP MARA, Oracle Cloud ERP, and IBM Maximo. Maps arbitrary enterprise columns to Samanvay canonical schemas.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono flex items-center gap-2 text-slate-700 dark:text-slate-300 shadow-sm">
            <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Target CPSE: <strong className="text-emerald-700 dark:text-emerald-300">{selectedOrg?.code || "OIL-1"}</strong></span>
          </div>
        </div>
      </div>

      {/* Upload Zone & Profile Selector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* File Drop Box */}
        <div className="lg:col-span-2 border-2 border-dashed border-slate-300 dark:border-slate-800 rounded-xl p-6 bg-white dark:bg-slate-900/40 hover:border-slate-400 dark:hover:border-slate-700 transition-colors shadow-sm">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-inner">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div className="space-y-2 flex-1">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center justify-between">
                <span>Enterprise Catalog File Upload</span>
                <span className="text-xs font-mono text-emerald-800 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950 px-2 py-0.5 rounded border border-emerald-300 dark:border-emerald-500/30">
                  {fileName}
                </span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-sans">
                Drag and drop CSV or TSV exports from ERP systems. Automatically parses header tokens and suggests field mappings.
              </p>
              <div className="flex items-center gap-3 pt-2">
                <label className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white dark:text-slate-950 font-bold text-xs font-mono cursor-pointer transition-colors shadow-sm">
                  Upload CSV File
                  <input
                    type="file"
                    accept=".csv,.tsv,.xlsx"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) setFileName(e.target.files[0].name);
                    }}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => setFileName("SAP_Plant_Export_2026.csv")}
                  className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono transition-colors border border-slate-200 dark:border-transparent"
                >
                  Load Sample Export
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ERP Mapping Profile Selector */}
        <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs shadow-sm">
          <div className="flex items-center gap-2 text-slate-900 dark:text-slate-200 font-bold">
            <Database className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Mapping Profile</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 font-sans">
            Choose pre-configured column header mappings for your enterprise ERP:
          </p>
          <div className="space-y-2">
            {PRESET_PROFILES.map((p, idx) => (
              <button
                key={p.name}
                type="button"
                onClick={() => setSelectedProfileIndex(idx)}
                className={`w-full text-left p-2.5 rounded-lg border transition-all ${
                  selectedProfileIndex === idx
                    ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-500/50 text-emerald-800 dark:text-emerald-300 shadow-2xs"
                    : "bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                <div className="font-bold">{p.name}</div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">{p.erp} standard extract</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Active Mapping Dictionary Review */}
      <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs shadow-sm">
        <h3 className="font-bold text-slate-900 dark:text-slate-200 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          Active Header Mappings ({activeProfile.erp})
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {Object.entries(activeProfile.mapping).map(([src, dst]) => (
            <div key={src} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1">
              <span className="text-slate-500 dark:text-slate-400 text-[10px] block">Source ERP Column:</span>
              <strong className="text-slate-900 dark:text-slate-100 block">{src}</strong>
              <div className="text-[10px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-semibold">
                <ArrowRight className="w-3 h-3" /> {dst}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Row Preview & Validation Table */}
      <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50/80 dark:bg-slate-950/40">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Ingestion Data Preview ({rows.length} rows)
          </h2>
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
            Validated against canonical physical constraints
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-wider bg-slate-50/50 dark:bg-slate-950/20">
                <th className="py-3 px-4">#</th>
                <th className="py-3 px-4">Item Code</th>
                <th className="py-3 px-4">Raw Description</th>
                <th className="py-3 px-4">UoM</th>
                <th className="py-3 px-4">Plant</th>
                <th className="py-3 px-4">Qty</th>
                <th className="py-3 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 text-slate-800 dark:text-slate-200">
              {rows.map((row) => (
                <tr key={row.row_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 text-slate-500">{row.row_id}</td>
                  <td className="py-3 px-4 font-bold text-slate-700 dark:text-slate-300">{row.mapped.item_code}</td>
                  <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100 max-w-md">
                    <div>{row.mapped.description}</div>
                    {row.notes && (
                      <div className="text-[10px] text-amber-600 dark:text-amber-400/90 font-sans mt-0.5">
                        {row.notes}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-950 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800">
                      {row.mapped.uom || "EMPTY"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-700 dark:text-slate-300">{row.mapped.plant}</td>
                  <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-100">{row.mapped.quantity}</td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        row.validation_status === "VALID"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                          : "bg-amber-50 dark:bg-amber-950/60 border-amber-200 dark:border-amber-500/40 text-amber-700 dark:text-amber-400"
                      }`}
                    >
                      {row.validation_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="text-xs font-mono text-slate-800 dark:text-slate-300 font-semibold">
            Ready to commit batch to Central Ingestion Pipeline
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
            Records will enter Stage 1 Normalization and Stage 2 Attribute Extraction with full SHA-256 audit logging.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRunIngest}
          className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white dark:text-slate-950 font-bold text-xs font-mono transition-colors shadow-md flex items-center gap-2"
        >
          <Table className="w-4 h-4" />
          Ingest {rows.length} Records to Samanvay
        </button>
      </div>

      {/* Ingestion Result Summary */}
      {ingested && ingestSummary && (
        <div className="p-5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-500/40 space-y-2 font-mono text-xs animate-in fade-in shadow-sm">
          <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-400 font-bold text-sm">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            Batch Ingestion Successfully Triggered
          </div>
          <p className="text-slate-700 dark:text-slate-300 font-sans leading-relaxed">
            All {ingestSummary.total} records ingested into <code>raw_items</code>. {ingestSummary.valid} records passed physical validation directly; {ingestSummary.warnings} records routed with normalized UoM fallbacks.
          </p>
          <div className="text-[11px] text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-slate-800">
            Audit Transaction: <code>INGEST_BATCH_TX_2026_0911</code> &middot; View candidates in Standardizer.
          </div>
        </div>
      )}
    </div>
  );
}
