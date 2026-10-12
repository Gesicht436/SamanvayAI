"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { UserRole } from "@/types";
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
} from "lucide-react";

export function Header() {
  const pathname = usePathname();
  const { user, selectedOrg, setSelectedOrg, setRole, availableOrgs } = useAuth();

  const navLinks = [
    { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
    { href: "/standardizer", label: "Standardizer", icon: Search },
    { href: "/diff", label: "Diff", icon: GitCompare },
    { href: "/queue", label: "Queue", icon: ListTodo },
    { href: "/upload", label: "Upload", icon: Table },
    { href: "/catalogue", label: "Catalogue", icon: BookOpen },
    { href: "/locator", label: "Locator", icon: Compass },
    { href: "/procurement", label: "Procurement", icon: Truck },
    { href: "/oem", label: "OEM Wizard", icon: Factory },
    { href: "/lots", label: "Lots & Life", icon: Boxes },
    { href: "/docs", label: "Intake & MTC", icon: FileCheck },
    { href: "/eval", label: "Eval Gate", icon: ShieldCheck },
  ];


  return (
    <header className="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-40 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-900/40 border border-emerald-400/40">
                <Layers className="w-5 h-5 text-slate-950" />
              </div>
              <div>
                <span className="text-base font-bold text-slate-100 tracking-tight flex items-center gap-2">
                  Samanvay AI
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                    v0.8-CPSE
                  </span>
                </span>
                <p className="text-[11px] text-slate-400 hidden sm:block">
                  National Inter-CPSE Material Harmonization
                </p>
              </div>
            </Link>

            {/* Navigation Links */}
            <nav className="hidden md:flex items-center gap-1">
              {navLinks.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-slate-800 text-emerald-400 border border-emerald-500/30"
                        : "text-slate-300 hover:text-slate-100 hover:bg-slate-900"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right Controls: Org Switcher and Role Switcher */}
          <div className="flex items-center gap-3">
            {/* Organisation Switcher (No default organisation per spec) */}
            <div className="flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-slate-400 hidden sm:block" />
              <select
                aria-label="Select CPSE Organisation"
                className={`text-xs rounded-md border px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans ${
                  selectedOrg
                    ? "bg-slate-900 border-slate-700 text-slate-200"
                    : "bg-amber-950/30 border-amber-600/40 text-amber-300 font-medium"
                }`}
                value={selectedOrg?.code || ""}
                onChange={(e) => {
                  const found = availableOrgs.find((o) => o.code === e.target.value);
                  setSelectedOrg(found || null);
                }}
              >
                <option value="">Select CPSE Organisation...</option>
                {availableOrgs.map((org) => (
                  <option key={org.code} value={org.code}>
                    {org.code} — {org.name.split(" ")[0]} ({org.sector})
                  </option>
                ))}
              </select>
            </div>

            {/* Role Switcher */}
            <div className="flex items-center gap-1.5 border-l border-slate-800 pl-3">
              <UserCheck className="w-4 h-4 text-slate-400 hidden sm:block" />
              <select
                aria-label="Select User Role"
                className="text-xs bg-slate-900 border border-slate-700 text-emerald-400 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
                value={user.role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                <option value="VIEWER">Role: VIEWER</option>
                <option value="MAKER">Role: MAKER</option>
                <option value="CHECKER">Role: CHECKER</option>
                <option value="ADMIN">Role: ADMIN</option>
              </select>
            </div>

            {/* User Domain Tags */}
            <div className="hidden lg:flex items-center gap-1 pl-2">
              <span className="text-[10px] text-slate-500 font-mono">Domains:</span>
              <div className="flex gap-0.5">
                {user.domains.slice(0, 3).map((d) => (
                  <span
                    key={d}
                    className="text-[9px] font-mono px-1 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800"
                  >
                    {d}
                  </span>
                ))}
                {user.domains.length > 3 && (
                  <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                    +{user.domains.length - 3}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
