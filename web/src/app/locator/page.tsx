"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { searchSpareLocator, requestStreamATransfer } from "@/lib/api";
import { SpareLocatorItem } from "@/types";
import {
  Compass,
  Search,
  MapPin,
  Building2,
  ShieldCheck,
  EyeOff,
  ArrowRight,
  TrendingDown,
  Truck,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";

export default function SpareLocatorPage() {
  const { selectedOrg } = useAuth();
  const [query, setQuery] = useState("");
  const [maxDistance, setMaxDistance] = useState<number | undefined>(undefined);
  const [selectedPlant, setSelectedPlant] = useState("PLANT-MATHURA");
  const [results, setResults] = useState<SpareLocatorItem[]>([]);
  const [loading, setLoading] = useState(false);

  // Transfer Request Modal state
  const [transferModalItem, setTransferModalItem] = useState<SpareLocatorItem | null>(null);
  const [reqQty, setReqQty] = useState(5.0);
  const [reqBasis, setReqBasis] = useState("BOOK_VALUE");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const res = await searchSpareLocator({
        query: query || undefined,
        plant: selectedPlant,
        max_distance_km: maxDistance,
      });
      setResults(res);
      setLoading(false);
    }
    load();
  }, [query, maxDistance, selectedPlant, selectedOrg]);

  async function handleTransferSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!transferModalItem) return;
    setSubmitting(true);
    setFeedback(null);

    const res = await requestStreamATransfer({
      lot_id: transferModalItem.lot_id,
      requested_qty: reqQty,
      to_plant: selectedPlant,
      basis: reqBasis,
      agreed_price: 1800.0,
      recipient_market_price: 3600.0,
    });

    setSubmitting(false);
    if (res.success) {
      setFeedback({ type: "success", msg: res.message });
      setTimeout(() => {
        setTransferModalItem(null);
        setFeedback(null);
      }, 2000);
    } else {
      setFeedback({ type: "error", msg: res.message });
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 mb-2">
            <Compass className="w-3.5 h-3.5" />
            Inter-CPSE Spare Locator (Section 12.0 & 13.2)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Geographic Spare Inventory & Surplus Locator
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
            Locates critical spares across CPSE plants using Haversine great-circle distance matrix with 1.25x road transit estimates. Enforces Section 9.3 privacy disclosure masking: partner CPSE identities and exact quantities remain masked until transfer approval.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono flex items-center gap-2 text-slate-700 dark:text-slate-300 shadow-sm">
            <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Active Org: <strong className="text-emerald-700 dark:text-emerald-300">{selectedOrg?.code || "OIL-1"}</strong></span>
          </div>
        </div>
      </div>

      {/* Search & Location Filters */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 bg-white dark:bg-slate-900/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="md:col-span-6 relative">
          <label className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5 block">Search Master or Descriptor</label>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400 dark:text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. GATE VALVE 100 NB, SEAMLESS PIPE, BEARING..."
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        <div className="md:col-span-3">
          <label className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5 block">Origin Plant Base</label>
          <select
            value={selectedPlant}
            onChange={(e) => setSelectedPlant(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-slate-200 focus:outline-none focus:border-emerald-500"
          >
            <option value="PLANT-MATHURA">PLANT-MATHURA (Mathura, UP)</option>
            <option value="PLANT-GUWAHATI">PLANT-GUWAHATI (Guwahati, AS)</option>
            <option value="PLANT-KORBA">PLANT-KORBA (Korba, CG)</option>
            <option value="PLANT-RAMAGUNDAM">PLANT-RAMAGUNDAM (Ramagundam, TS)</option>
            <option value="PLANT-BHILAI">PLANT-BHILAI (Bhilai, CG)</option>
            <option value="PLANT-ROURKELA">PLANT-ROURKELA (Rourkela, OD)</option>
            <option value="PLANT-DHANBAD">PLANT-DHANBAD (Dhanbad, JH)</option>
            <option value="PLANT-RANCHI">PLANT-RANCHI (Ranchi, JH)</option>
          </select>
        </div>

        <div className="md:col-span-3">
          <label className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5 block">Distance Radius</label>
          <div className="flex gap-1.5">
            {[
              { label: "All India", val: undefined },
              { label: "500 km", val: 500 },
              { label: "1000 km", val: 1000 },
            ].map((btn, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setMaxDistance(btn.val)}
                className={`flex-1 text-xs py-2 rounded-lg font-mono border transition-all ${
                  maxDistance === btn.val
                    ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/50 shadow-2xs"
                    : "bg-slate-50 dark:bg-slate-950 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-transparent">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Discovered Spare Holdings</h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-transparent">
              {results.length} Locations
            </span>
          </div>

          <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              S6 Verified Green Lots
            </span>
            <span className="flex items-center gap-1.5">
              <EyeOff className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              Section 9.3 Masked Identity
            </span>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-500 text-sm font-mono">Searching inter-CPSE plant registry...</div>
        ) : results.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm font-mono">
            No matching spares found within selected distance radius.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/60 font-mono text-slate-500 dark:text-slate-400 text-[11px]">
                  <th className="py-3 px-4">ITEM DESCRIPTOR & CODE</th>
                  <th className="py-3 px-4">LOCATION CITY</th>
                  <th className="py-3 px-4">TRANSIT DISTANCE</th>
                  <th className="py-3 px-4">STOCK BUCKET</th>
                  <th className="py-3 px-4">DISCLOSURE STATUS</th>
                  <th className="py-3 px-4 text-right">STREAM A ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                {results.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 dark:text-slate-100 text-sm">{item.descriptor}</div>
                      <div className="font-mono text-[11px] text-emerald-700 dark:text-emerald-400 flex items-center gap-2 mt-0.5">
                        <span>{item.golden_code}</span>
                        <span className="text-slate-400 dark:text-slate-500">•</span>
                        <span className="text-slate-600 dark:text-slate-400">{item.canonical_uom}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-slate-800 dark:text-slate-200 font-medium flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        {item.city}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {item.plant_code || "External Store"}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-slate-800 dark:text-slate-200">
                        {item.air_distance_km === 0 ? (
                          <span className="text-emerald-700 dark:text-emerald-400 font-bold">Local Store</span>
                        ) : (
                          `${item.air_distance_km} km (Air)`
                        )}
                      </div>
                      {item.road_distance_km > 0 && (
                        <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                          <Truck className="w-3 h-3" />
                          Est. Road: {item.road_distance_km} km
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className={`inline-flex px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${
                        item.quantity_bucket.startsWith("HIGH")
                          ? "bg-purple-50 dark:bg-purple-950/70 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-600/40"
                          : item.quantity_bucket.startsWith("MEDIUM")
                          ? "bg-blue-50 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-600/40"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700"
                      }`}>
                        {item.quantity_bucket}
                      </span>
                      {item.exact_qty !== null && item.exact_qty !== undefined && (
                        <div className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400 mt-0.5">
                          Exact: {item.exact_qty} {item.canonical_uom}
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      {item.is_own_inventory ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 dark:text-emerald-400 font-mono">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          Internal Inventory
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 dark:text-amber-300 font-mono">
                          <EyeOff className="w-3.5 h-3.5" />
                          Partner Masked
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      {item.can_request_transfer ? (
                        <button
                          type="button"
                          onClick={() => setTransferModalItem(item)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white dark:text-slate-950 font-semibold text-xs transition-all flex items-center gap-1.5 ml-auto shadow-md"
                        >
                          <span>Request Transfer</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      ) : (
                        <span className="text-slate-400 dark:text-slate-500 font-mono text-[11px]">Own Store</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Request Transfer Modal */}
      {transferModalItem && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl relative font-mono text-xs">
            <button
              onClick={() => setTransferModalItem(null)}
              className="absolute right-4 top-4 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            >
              <X className="w-5 h-5" />
            </button>

            <div>
              <div className="text-xs font-mono text-emerald-700 dark:text-emerald-400 uppercase tracking-wider mb-1 font-semibold">
                Stream A Surplus Redeployment Requisition
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-sans">
                {transferModalItem.descriptor}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                {transferModalItem.golden_code} • Source Location: {transferModalItem.city}
              </p>
            </div>

            <form onSubmit={handleTransferSubmit} className="space-y-4 font-mono text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Requested Quantity ({transferModalItem.canonical_uom})</label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={reqQty}
                    onChange={(e) => setReqQty(parseFloat(e.target.value) || 1)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-slate-200 focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Transfer Pricing Basis</label>
                  <select
                    value={reqBasis}
                    onChange={(e) => setReqBasis(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="BOOK_VALUE">Book Value (Surplus Basis)</option>
                    <option value="LAST_PURCHASE_PRICE">Last Purchase Price</option>
                    <option value="AGREED">Agreed Mutual Settlement</option>
                  </select>
                </div>
              </div>

              {/* Economic Benefit Preview */}
              <div className="bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 space-y-2">
                <div className="text-xs font-mono font-medium text-slate-700 dark:text-slate-300 flex items-center justify-between">
                  <span>Economic Value Model (Section 13.0):</span>
                  <span className="text-emerald-700 dark:text-emerald-400 font-bold">Avoided Fresh Purchase</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-slate-200 dark:border-slate-800/60 font-mono text-xs">
                  <div>
                    <div className="text-slate-500 text-[10px]">Avoided Cost</div>
                    <div className="text-slate-900 dark:text-slate-200 font-semibold mt-0.5">₹{(reqQty * 3600).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-[10px]">Transfer + Logistics</div>
                    <div className="text-amber-700 dark:text-amber-400 font-semibold mt-0.5">₹{(reqQty * 1800 + 4500).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-[10px]">Net Benefit</div>
                    <div className="text-emerald-700 dark:text-emerald-400 font-bold mt-0.5">₹{(reqQty * 1800 - 4500).toLocaleString()}</div>
                  </div>
                </div>
              </div>

              {feedback && (
                <div className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                  feedback.type === "success" ? "bg-emerald-50 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800" : "bg-red-50 dark:bg-red-950/80 text-red-800 dark:text-red-300 border border-red-300 dark:border-red-800"
                }`}>
                  {feedback.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" /> : <AlertCircle className="w-4 h-4 shrink-0 text-red-600 dark:text-red-400" />}
                  <span>{feedback.msg}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setTransferModalItem(null)}
                  className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-transparent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white dark:text-slate-950 font-semibold text-xs shadow-md flex items-center gap-1.5"
                >
                  {submitting ? "Submitting Requisition..." : "Submit Stream A Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
