"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import type { UserRole } from "@/types";
import {
  Layers,
  Search,
  GitCompare,
  ListTodo,
  ShieldCheck,
  Building2,
  UserCheck,
  BarChart3,
  Factory,
  Boxes,
  FileCheck,
  Compass,
  Truck,
  Table,
  BookOpen,
  ChevronDown,
  Sun,
  Moon,
  Sparkles,
  Menu,
  X,
  ShieldAlert,
} from "lucide-react";

interface NavGroup {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  items: {
    href: string;
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Harmonization",
    icon: GitCompare,
    items: [
      {
        href: "/standardizer",
        label: "Standardizer & Match",
        description: "Interactive normalization, extraction & candidate scoring",
        icon: Search,
      },
      {
        href: "/diff",
        label: "Diff Inspector",
        description: "Side-by-side lattice diffs and S1-S15 safety refusals",
        icon: GitCompare,
      },
      {
        href: "/queue",
        label: "Stewardship Queue",
        description: "Dual Maker-Checker approvals & conflict resolution",
        icon: ListTodo,
      },
    ],
  },
  {
    label: "Master Data",
    icon: BookOpen,
    items: [
      {
        href: "/catalogue",
        label: "Golden Catalogue",
        description: "National master browser with Verhoeff MPNG-17 lookups",
        icon: BookOpen,
      },
      {
        href: "/lots",
        label: "Lots & Life Monitor",
        description: "Shelf life tracking, consumption velocity & expiry alerts",
        icon: Boxes,
      },
    ],
  },
  {
    label: "Intake & Spares",
    icon: Layers,
    items: [
      {
        href: "/docs",
        label: "Document Intake & MTC",
        description: "300 DPI OCR canvas, camera capture & EN 10204 3.1 bounds",
        icon: FileCheck,
      },
      {
        href: "/upload",
        label: "Batch Ingest",
        description: "CSV/XLSX upload with column mapping profiles",
        icon: Table,
      },
      {
        href: "/locator",
        label: "Surplus Spares Locator",
        description: "Haversine distance search with privacy masking",
        icon: Compass,
      },
      {
        href: "/oem",
        label: "OEM Onboarding",
        description: "4-step manufacturer catalog ingestion & compliance",
        icon: Factory,
      },
    ],
  },
  {
    label: "Governance",
    icon: ShieldCheck,
    items: [
      {
        href: "/procurement",
        label: "Procurement & Pooling",
        description: "Stream A surplus transfers & Stream B joint demand pools",
        icon: Truck,
      },
      {
        href: "/dashboard",
        label: "Executive Dashboard",
        description: "Throughput metrics, cost avoidance & CPSE catalog health",
        icon: BarChart3,
      },
      {
        href: "/eval",
        label: "Release Eval Gate",
        description: "Clopper-Pearson binomial bounds & hard safety gates",
        icon: ShieldCheck,
      },
    ],
  },
];

export function Header() {
  const pathname = usePathname();
  const { user, selectedOrg, setSelectedOrg, setRole, availableOrgs } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setActiveDropdown(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close dropdown on route change
  useEffect(() => {
    setActiveDropdown(null);
    setMobileMenuOpen(false);
  }, [pathname]);

  const handleOpenCommandPalette = () => {
    window.dispatchEvent(new CustomEvent("open-command-palette"));
  };

  const handleOpenAuditDrawer = () => {
    window.dispatchEvent(new CustomEvent("open-audit-drawer"));
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/90 dark:bg-slate-950/90 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">
          {/* Brand Logo & National Indicator */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-3 group focus:outline-none">
              <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold shadow-md shadow-emerald-950/20 group-hover:scale-105 transition-transform">
                <span className="font-mono text-base">स</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm tracking-tight text-slate-900 dark:text-slate-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                    Samanvay AI
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                    MPNG-17
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block">
                  National Inter-CPSE Material Harmonization
                </p>
              </div>
            </Link>

            {/* Apple-style Categorized Dropdown Navigation (Desktop) */}
            <nav ref={dropdownRef} className="hidden lg:flex items-center gap-1">
              {NAV_GROUPS.map((group) => {
                const isGroupActive = group.items.some((item) => item.href === pathname);
                const isOpen = activeDropdown === group.label;
                const GroupIcon = group.icon;

                return (
                  <div key={group.label} className="relative">
                    <button
                      type="button"
                      onClick={() => setActiveDropdown(isOpen ? null : group.label)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isGroupActive
                          ? "bg-slate-100 dark:bg-slate-800/80 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 font-semibold"
                          : isOpen
                          ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          : "text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-900/60"
                      }`}
                    >
                      <GroupIcon className="w-3.5 h-3.5" />
                      <span>{group.label}</span>
                      <ChevronDown
                        className={`w-3 h-3 text-slate-400 transition-transform ${
                          isOpen ? "rotate-180" : ""
                        }`}
                      />
                    </button>

                    {/* Dropdown Menu */}
                    {isOpen && (
                      <div className="absolute top-full left-0 mt-1.5 w-72 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-2 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
                        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 px-2.5 py-1">
                          {group.label} Domain
                        </div>
                        <div className="space-y-1">
                          {group.items.map((item) => {
                            const ItemIcon = item.icon;
                            const isItemActive = pathname === item.href;
                            return (
                              <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-start gap-3 p-2 rounded-lg text-left transition-colors ${
                                  isItemActive
                                    ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-300 border border-emerald-500/20"
                                    : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60"
                                }`}
                              >
                                <div
                                  className={`p-1.5 rounded-md shrink-0 mt-0.5 ${
                                    isItemActive
                                      ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                                      : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                                  }`}
                                >
                                  <ItemIcon className="w-3.5 h-3.5" />
                                </div>
                                <div className="min-w-0">
                                  <div className="text-xs font-semibold leading-tight text-slate-900 dark:text-slate-100">
                                    {item.label}
                                  </div>
                                  <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug mt-0.5 line-clamp-1">
                                    {item.description}
                                  </div>
                                </div>
                              </Link>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </nav>
          </div>

          {/* Right Controls: Command Bar, Org Switcher, Role, Theme & Audit */}
          <div className="flex items-center gap-2.5">
            {/* Global Command Palette Trigger Button (Cmd+K) */}
            <button
              type="button"
              onClick={handleOpenCommandPalette}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs text-slate-500 dark:text-slate-400 transition-colors shadow-sm"
              title="Global Spotlight Search"
            >
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden md:inline">Search codes & pages...</span>
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500">
                ⌘K
              </kbd>
            </button>

            {/* CPSE Organization Switcher */}
            <div className="flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-slate-400 hidden xl:block" />
              <select
                aria-label="Select CPSE Organisation"
                value={selectedOrg?.code ?? ""}
                onChange={(e) => {
                  const org = availableOrgs.find((o) => o.code === e.target.value) || null;
                  setSelectedOrg(org);
                }}
                className={`text-xs rounded-lg border px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans transition-colors ${
                  selectedOrg
                    ? "bg-slate-50 dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100"
                    : "bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-700/60 text-amber-800 dark:text-amber-300"
                }`}
              >
                <option value="" disabled>Select CPSE...</option>
                {availableOrgs.map((org) => (
                  <option key={org.code} value={org.code}>
                    {org.name} ({org.sector.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>

            {/* Maker-Checker Role Switcher */}
            <div className="flex items-center gap-1">
              <UserCheck className="w-3.5 h-3.5 text-slate-400 hidden xl:block" />
              <select
                aria-label="Select User Role"
                value={user?.role ?? "VIEWER"}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className={`text-xs rounded-lg border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans transition-colors ${
                  user?.role === "CHECKER"
                    ? "bg-purple-50 dark:bg-purple-950/40 border-purple-300 dark:border-purple-700 text-purple-900 dark:text-purple-300 font-medium"
                    : user?.role === "MAKER"
                    ? "bg-sky-50 dark:bg-sky-950/40 border-sky-300 dark:border-sky-700 text-sky-900 dark:text-sky-300 font-medium"
                    : "bg-slate-50 dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                }`}
              >
                <option value="MAKER">Maker</option>
                <option value="CHECKER">Checker</option>
                <option value="ADMIN">Admin</option>
                <option value="VIEWER">Viewer</option>
              </select>
            </div>

            {/* Tamper-Evident Audit Chain Inspector Button */}
            <button
              type="button"
              onClick={handleOpenAuditDrawer}
              aria-label="Open SHA-256 Audit Drawer"
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors relative"
              title="Open SHA-256 Audit Log Inspector"
            >
              <ShieldCheck className="w-4 h-4" />
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-950" />
            </button>

            {/* 1-Click Dark/Light Theme Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme mode"
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} mode`}
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-slate-600" />
              )}
            </button>

            {/* Mobile Menu Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              aria-label="Toggle navigation menu"
              className="lg:hidden p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300"
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-4 border-t border-slate-200 dark:border-slate-800 space-y-4 animate-in slide-in-from-top-2 duration-150">
            {NAV_GROUPS.map((group) => (
              <div key={group.label} className="space-y-1">
                <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 font-bold">
                  {group.label}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                  {group.items.map((item) => {
                    const ItemIcon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                          isActive
                            ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-400 font-semibold"
                            : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                        }`}
                      >
                        <ItemIcon className="w-4 h-4 text-slate-400" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
