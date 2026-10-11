"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { getStockLots } from "@/lib/api";
import { StockLotItem } from "@/types";
import {
  Boxes,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Building2,
  Calendar,
  Layers,
  Search,
  Filter,
} from "lucide-react";

export default function LotsLifeMonitorPage() {
  const { selectedOrg } = useAuth();
  const [lots, setLots] = useState<StockLotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [plantFilter, setPlantFilter] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      const res = await getStockLots({
        risk: riskFilter,
        plant: plantFilter || undefined,
      });
      setLots(res);
      setLoading(false);
    }
    load();
  }, [riskFilter, plantFilter, selectedOrg]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-2">
            <Boxes className="w-3.5 h-3.5" />
            Stock Lots & Shelf-Life Monitor (Section 11.0, 15.1)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            Lot-Level Physical Life & FEFO Disposition Ladder
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Tracks age, remaining usage, and expiration across CPSE plants. Enforces Invariant $S8$ (adding usage never increases remaining life) and blocks expired lots from Stream A pooling.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono flex items-center gap-2 text-slate-300">
            <Building2 className="w-4 h-4 text-emerald-400" />
            <span>Active Plant Context: <strong className="text-emerald-300">{selectedOrg?.code || "OIL-1"}</strong></span>
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Risk Filter:</span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Risk States</option>
              <option value="GREEN">GREEN (Normal)</option>
              <option value="AMBER">AMBER (Warning)</option>
              <option value="RED">RED (Critical/Expired)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Filter by plant name..."
            value={plantFilter}
            onChange={(e) => setPlantFilter(e.target.value)}
            className="w-full sm:w-64 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>

      {/* Lots Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-md">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/40">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            Tracked Stock Lots ({lots.length} active lots)
          </h2>
          <span className="text-xs font-mono text-slate-400">
            Real-time multi-basis tracking
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">
            Loading stock lots...
          </div>
        ) : lots.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-slate-500">
            No stock lots match the selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider bg-slate-950/20">
                  <th className="py-3 px-4">Lot ID & Batch</th>
                  <th className="py-3 px-4">Plant & Location</th>
                  <th className="py-3 px-4">Golden Descriptor</th>
                  <th className="py-3 px-4">Qty Remaining</th>
                  <th className="py-3 px-4">Basis & Expiry</th>
                  <th className="py-3 px-4 text-center">Risk State</th>
                  <th className="py-3 px-4">Stream A Pooling</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {lots.map((lot) => {
                  const isRed = lot.risk === "RED" || lot.risk === "EXPIRED";
                  const isAmber = lot.risk === "AMBER";
                  const isGreen = lot.risk === "GREEN";

                  return (
                    <tr key={lot.lot_id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-100">{lot.lot_id}</div>
                        <div className="text-[11px] text-slate-400">{lot.batch_no || "N/A"}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-sans font-medium text-slate-200">{lot.plant || "Unknown"}</span>
                      </td>
                      <td className="py-3 px-4 max-w-xs">
                        <div className="font-bold text-emerald-400">{lot.golden_code || "UNLINKED"}</div>
                        <div className="text-[11px] text-slate-400 truncate">{lot.descriptor || "No descriptor"}</div>
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-100">
                        {lot.qty_remaining !== null && lot.qty_remaining !== undefined ? `${lot.qty_remaining} ${lot.uom || "EA"}` : "N/A"}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-slate-300 font-semibold">{lot.basis}</div>
                        <div className="text-[11px] text-slate-400">
                          {lot.expiry_date ? `Exp: ${lot.expiry_date}` : "No fixed expiry"}
                        </div>
                        {lot.remaining_days !== null && lot.remaining_days !== undefined && (
                          <div className={`text-[10px] font-bold ${
                            lot.remaining_days < 0 ? "text-red-400" : lot.remaining_days < 90 ? "text-amber-400" : "text-emerald-400"
                          }`}>
                            {lot.remaining_days < 0 ? `${Math.abs(lot.remaining_days)}d overdue` : `${lot.remaining_days}d remaining`}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold inline-flex items-center gap-1 border ${
                          isRed
                            ? "bg-red-950/60 border-red-500/40 text-red-400"
                            : isAmber
                            ? "bg-amber-950/60 border-amber-500/40 text-amber-400"
                            : "bg-emerald-950/60 border-emerald-500/40 text-emerald-400"
                        }`}>
                          {isRed && <XCircle className="w-3 h-3" />}
                          {isAmber && <AlertTriangle className="w-3 h-3" />}
                          {isGreen && <CheckCircle2 className="w-3 h-3" />}
                          {lot.risk}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-col gap-0.5">
                          <span className={`font-bold ${lot.stream_a_eligible ? "text-emerald-400" : "text-red-400"}`}>
                            {lot.stream_a_eligible ? "Eligible" : "Blocked"}
                          </span>
                          <span className="text-[10px] text-slate-400 font-sans max-w-xs truncate">
                            {lot.reason || (lot.stream_a_eligible ? "Normal condition" : "Safety invariant refusal")}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* FEFO Disposition Ladder Explain Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 font-mono text-xs space-y-3">
        <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Clock className="w-4 h-4 text-emerald-400" />
          FEFO Disposition Ladder Hierarchy
        </h3>
        <p className="text-slate-400 leading-relaxed font-sans">
          To prevent capital write-offs in Indian CPSE stores, inventory is automatically prioritized:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-emerald-400 block">Step 1: Stream A Inter-CPSE Transfer</strong>
            <p className="text-[11px] text-slate-400 font-sans">Eligible green lots transferred to CPSEs with immediate project requisitions.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-amber-400 block">Step 2: Stream B Plant Internal Priority</strong>
            <p className="text-[11px] text-slate-400 font-sans">Amber lots near expiration routed to maintenance workorders at the origin plant.</p>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <strong className="text-red-400 block">Step 3: Segregation / Quarantine</strong>
            <p className="text-[11px] text-slate-400 font-sans">Red lots automatically blocked from issue; scrap or vendor re-validation requested.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
