"use client";

import React from "react";
import { AlignJustify, List, Rows3 } from "lucide-react";

export type TableDensity = "compact" | "standard" | "comfortable";

interface DensityToggleProps {
  density: TableDensity;
  onChange: (density: TableDensity) => void;
}

export function DensityToggle({ density, onChange }: DensityToggleProps) {
  const options: { id: TableDensity; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "compact", label: "Compact", icon: AlignJustify },
    { id: "standard", label: "Standard", icon: List },
    { id: "comfortable", label: "Comfortable", icon: Rows3 },
  ];

  return (
    <div
      role="group"
      aria-label="Table row density"
      className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900/60 text-xs font-mono"
    >
      {options.map((opt) => {
        const Icon = opt.icon;
        const isActive = density === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => onChange(opt.id)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-colors ${
              isActive
                ? "bg-white dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold shadow-xs"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
            title={`${opt.label} Row Density`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function getDensityRowClasses(density: TableDensity): string {
  switch (density) {
    case "compact":
      return "py-1.5 px-3 text-[11px]";
    case "comfortable":
      return "py-3.5 px-4 text-xs";
    case "standard":
    default:
      return "py-2.5 px-3.5 text-xs";
  }
}
