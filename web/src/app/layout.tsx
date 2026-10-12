import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { DemoBanner } from "@/components/common/DemoBanner";
import { Header } from "@/components/common/Header";
import { CommandPalette } from "@/components/common/CommandPalette";
import { AuditDrawer } from "@/components/common/AuditDrawer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Samanvay AI — National Inter-CPSE Material Harmonization & Stewardship",
  description:
    "Industrial material standardization, deterministic safety gating, and inventory deduplication for Indian Public Enterprises.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans selection:bg-emerald-500/30 selection:text-emerald-700 dark:selection:text-emerald-200 transition-colors">
        <ThemeProvider>
          <AuthProvider>
            <DemoBanner />
            <Header />
            <main className="flex-1">{children}</main>
            <footer className="border-t border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-950 py-6 text-center text-xs font-mono text-slate-500 dark:text-slate-400 transition-colors">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
                <span>
                  Samanvay AI &middot; Architecture Release 0.8 &middot; Governed by Invariants S1–S15
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Audit Chain Integrity: Append-Only SHA-256
                </span>
              </div>
            </footer>
            <CommandPalette />
            <AuditDrawer />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
