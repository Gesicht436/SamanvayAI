"use client";

import React, { useState } from "react";
import {
  Filter,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  CheckSquare,
  Square,
  Layers,
  ShieldAlert,
  SlidersHorizontal,
  X,
} from "lucide-react";

export interface FacetGroup {
  id: string;
  name: string;
  options: {
    id: string;
    label: string;
    count: number;
  }[];
}

interface FacetedFilterDrawerProps {
  groups: FacetGroup[];
  selectedFacets: Record<string, string[]>;
  onChange: (groupId: string, optionId: string) => void;
  onReset: () => void;
  className?: string;
}

export function FacetedFilterDrawer({
  groups,
  selectedFacets,
  onChange,
  onReset,
  className = "",
}: FacetedFilterDrawerProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const toggleGroup = (id: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const totalActiveFilters = Object.values(selectedFacets).reduce(
    (acc, arr) => acc + arr.length,
    0
  );

  const content = (
    <div className="space-y-4 text-xs font-sans">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span className="font-bold text-slate-900 dark:text-slate-100 uppercase font-mono tracking-wider text-[11px]">
            Faceted Filters
          </span>
          {totalActiveFilters > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 font-mono text-[10px] font-bold">
              {totalActiveFilters}
            </span>
          )}
        </div>
        {totalActiveFilters > 0 && (
          <button
            type="button"
            onClick={onReset}
            className="text-[11px] font-mono text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 flex items-center gap-1 transition-colors"
          >
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        )}
      </div>

      {/* Facet Groups */}
      <div className="space-y-3">
        {groups.map((group) => {
          const isCollapsed = collapsedGroups[group.id];
          const activeForGroup = selectedFacets[group.id] || [];

          return (
            <div
              key={group.id}
              className="border-b border-slate-100 dark:border-slate-800/60 pb-3 last:border-0"
            >
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className="w-full flex items-center justify-between py-1 text-slate-800 dark:text-slate-200 font-semibold hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
              >
                <span>{group.name}</span>
                {isCollapsed ? (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                )}
              </button>

              {!isCollapsed && (
                <div className="mt-2 space-y-1.5 pl-1">
                  {group.options.map((opt) => {
                    const isSelected = activeForGroup.includes(opt.id);
                    return (
                      <label
                        key={opt.id}
                        className="flex items-center justify-between gap-2 py-1 px-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800/50 cursor-pointer select-none transition-colors group"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => onChange(group.id, opt.id)}
                            className="w-3.5 h-3.5 rounded border-slate-300 dark:border-slate-700 text-emerald-600 focus:ring-emerald-500 bg-transparent"
                          />
                          <span
                            className={`truncate ${
                              isSelected
                                ? "text-slate-900 dark:text-slate-100 font-semibold"
                                : "text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200"
                            }`}
                          >
                            {opt.label}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 shrink-0">
                          ({opt.count})
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sticky Panel */}
      <div
        className={`hidden md:block w-64 shrink-0 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 shadow-sm self-start ${className}`}
      >
        {content}
      </div>

      {/* Mobile Toggle Trigger */}
      <div className="md:hidden">
        <button
          type="button"
          onClick={() => setIsMobileOpen(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-700 dark:text-slate-200 shadow-sm"
        >
          <SlidersHorizontal className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          <span>Filters</span>
          {totalActiveFilters > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-emerald-500 text-white font-mono text-[10px]">
              {totalActiveFilters}
            </span>
          )}
        </button>

        {/* Mobile Slide-over Drawer */}
        {isMobileOpen && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Filter Options"
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex justify-end animate-in fade-in"
            onClick={() => setIsMobileOpen(false)}
          >
            <div
              className="w-80 h-full bg-white dark:bg-slate-900 p-5 shadow-2xl overflow-y-auto animate-in slide-in-from-right"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-end pb-2">
                <button
                  type="button"
                  onClick={() => setIsMobileOpen(false)}
                  className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              {content}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
