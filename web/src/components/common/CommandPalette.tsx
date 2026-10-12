"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Sparkles,
  Layers,
  GitCompare,
  ListTodo,
  BookOpen,
  Boxes,
  FileCheck,
  Table,
  Compass,
  Factory,
  Truck,
  BarChart3,
  ShieldCheck,
  X,
  CornerDownLeft,
} from "lucide-react";

interface CommandItem {
  id: string;
  title: string;
  subtitle: string;
  category: "Harmonization" | "Master Data" | "Intake & Spares" | "Governance" | "Quick Codes";
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const COMMAND_ITEMS: CommandItem[] = [
  // Harmonization
  {
    id: "standardizer",
    title: "Standardizer & Match",
    subtitle: "Interactive material description normalization and candidate ranking",
    category: "Harmonization",
    href: "/standardizer",
    icon: Search,
  },
  {
    id: "diff",
    title: "Diff Inspector",
    subtitle: "Side-by-side attribute comparison and safety verdict matrix",
    category: "Harmonization",
    href: "/diff",
    icon: GitCompare,
  },
  {
    id: "queue",
    title: "Stewardship Task Queue",
    subtitle: "Maker-checker dual approval inbox and conflict resolution",
    category: "Harmonization",
    href: "/queue",
    icon: ListTodo,
  },
  // Master Data
  {
    id: "catalogue",
    title: "Golden Master Catalogue",
    subtitle: "Search verified Verhoeff MPNG-17 material master records",
    category: "Master Data",
    href: "/catalogue",
    icon: BookOpen,
  },
  {
    id: "lots",
    title: "Lots & Life Monitor",
    subtitle: "Shelf life tracking, consumption velocity, and degradation alerts",
    category: "Master Data",
    href: "/lots",
    icon: Boxes,
  },
  // Intake & Spares
  {
    id: "docs",
    title: "Document Intake & MTC",
    subtitle: "300 DPI OCR canvas review, camera capture, and EN 10204 3.1 chemistry",
    category: "Intake & Spares",
    href: "/docs",
    icon: FileCheck,
  },
  {
    id: "upload",
    title: "Batch Ingest & Mapping",
    subtitle: "CSV/XLSX file ingestion with column mapping profiles",
    category: "Intake & Spares",
    href: "/upload",
    icon: Table,
  },
  {
    id: "locator",
    title: "Surplus Spares Locator",
    subtitle: "Geospatial spare search with Haversine distance and privacy masking",
    category: "Intake & Spares",
    href: "/locator",
    icon: Compass,
  },
  {
    id: "oem",
    title: "OEM Onboarding Wizard",
    subtitle: "4-step manufacturer catalog mapping and compliance verification",
    category: "Intake & Spares",
    href: "/oem",
    icon: Factory,
  },
  // Governance
  {
    id: "procurement",
    title: "Procurement & Pooling",
    subtitle: "Stream A surplus stock transfers and Stream B demand tender pools",
    category: "Governance",
    href: "/procurement",
    icon: Truck,
  },
  {
    id: "dashboard",
    title: "Executive Dashboard",
    subtitle: "Pipeline throughput, deduplication savings, and CPSE health metrics",
    category: "Governance",
    href: "/dashboard",
    icon: BarChart3,
  },
  {
    id: "eval",
    title: "Release Evaluation Gate",
    subtitle: "Clopper-Pearson binomial confidence bounds and hard safety gates",
    category: "Governance",
    href: "/eval",
    icon: ShieldCheck,
  },
  // Quick Codes
  {
    id: "code-valve",
    title: "MPNG-0004821937-3",
    subtitle: "GATE VALVE 100 NB CL150 WCB FLG RF API 600",
    category: "Quick Codes",
    href: "/catalogue?search=MPNG-0004821937-3",
    icon: Sparkles,
  },
  {
    id: "code-motor",
    title: "MPNG-0005918231-8",
    subtitle: "MOTOR 55 KW 4P 415V FOOT B3 EX D IIC T4",
    category: "Quick Codes",
    href: "/catalogue?search=MPNG-0005918231-8",
    icon: Sparkles,
  },
];

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  // Global keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };

    const handleCustomOpen = () => setIsOpen(true);

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("open-command-palette", handleCustomOpen);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("open-command-palette", handleCustomOpen);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const filteredItems = COMMAND_ITEMS.filter((item) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.subtitle.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    );
  });

  const handleSelect = (item: CommandItem) => {
    setIsOpen(false);
    router.push(item.href);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === "Enter" && filteredItems[selectedIndex]) {
      e.preventDefault();
      handleSelect(filteredItems[selectedIndex]);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 dark:bg-black/80 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={() => setIsOpen(false)}
    >
      <div
        className="w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200 dark:border-slate-800">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleInputKeyDown}
            placeholder="Type a screen, national code (MPNG-...), or keyword..."
            className="flex-1 bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            aria-label="Close command palette"
            className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 divide-y divide-slate-100 dark:divide-slate-800/40">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">
              No matching pages or national codes found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelect(item)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-lg text-left transition-colors text-xs ${
                    isSelected
                      ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-300 border border-emerald-500/30"
                      : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`p-1.5 rounded-md ${
                        isSelected
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                        {item.title}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        {item.subtitle}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                      {item.category}
                    </span>
                    {isSelected && (
                      <CornerDownLeft className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">↑↓</kbd> Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">↵</kbd> Select
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">ESC</kbd> Close
            </span>
          </div>
          <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-sans">
            <Sparkles className="w-3 h-3" /> Samanvay Spotlight
          </span>
        </div>
      </div>
    </div>
  );
}
