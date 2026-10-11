import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { AuthProvider } from "@/lib/auth-context";
import DashboardPage from "@/app/dashboard/page";
import OemOnboardingPage from "@/app/oem/page";
import LotsLifeMonitorPage from "@/app/lots/page";
import DocumentIntakeMtcPage from "@/app/docs/page";

describe("Dashboard Page (Module 10)", () => {
  it("renders catalog completeness and 14 clusters table", async () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Executive Catalog Health & Inter-CPSE Dashboard/i)).toBeInTheDocument();
    });

    // Check completeness card
    expect(screen.getByText(/Item Completeness/i)).toBeInTheDocument();
    expect(screen.getByText(/88.4%/i)).toBeInTheDocument();

    // Check audit status
    expect(screen.getByText(/Audit Chain:/i)).toBeInTheDocument();

    // Check cluster rows
    expect(screen.getByText(/Motors 55 kW 4P B3 Ex d IIB T4 IE3/i)).toBeInTheDocument();
    expect(screen.getByText(/ISMB 300 E250A, 12 m/i)).toBeInTheDocument();
  });
});

describe("OEM Onboarding Wizard (Module 10)", () => {
  it("displays draft proposals and detects supersession mapping", () => {
    render(
      <AuthProvider>
        <OemOnboardingPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Bulk OEM Spares Ingestion & Supersession Mapping/i)).toBeInTheDocument();
    expect(screen.getByText("OLD-PUMP-01")).toBeInTheDocument();
    expect(screen.getByText("NEWPUMP02")).toBeInTheDocument();
    expect(screen.getByText(/Supersedes: OLDPUMP01/i)).toBeInTheDocument();
  });
});

describe("Stock Lots & Life Monitor (Module 10)", () => {
  it("renders lots and FEFO disposition ladder", async () => {
    render(
      <AuthProvider>
        <LotsLifeMonitorPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/FEFO Disposition Ladder Hierarchy/i)).toBeInTheDocument();
      expect(screen.getByText(/Koyali Refinery/i)).toBeInTheDocument();
    });
  });
});

describe("Document Intake & MTC Screen (Module 10)", () => {
  it("calculates CE_IIW and checks ASTM limits", () => {
    render(
      <AuthProvider>
        <DocumentIntakeMtcPage />
      </AuthProvider>
    );

    expect(screen.getByText(/Document Ingestion & Material Test Certificate/i)).toBeInTheDocument();
    expect(screen.getByText(/Calculated CE_IIW:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/A105/i).length).toBeGreaterThan(0);
  });
});
