import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { DemoBanner } from "@/components/common/DemoBanner";
import { Header } from "@/components/common/Header";

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
    >
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
        <AuthProvider>
          <DemoBanner />
          <Header />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs font-mono text-slate-500">
            <div className="max-w-7xl mx-auto px-4 flex flex-wrap items-center justify-between gap-4">
              <span>Samanvay AI &middot; Architecture Release 0.8 &middot; Governed by Invariants S1–S15</span>
              <span>Audit Chain Integrity: Append-Only SHA-256</span>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
