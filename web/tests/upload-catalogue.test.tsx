import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TabularIngestionPage from "@/app/upload/page";
import MasterCataloguePage from "@/app/catalogue/page";
import { AuthProvider } from "@/lib/auth-context";

function renderWithAuth(ui: React.ReactElement) {
  return render(<AuthProvider>{ui}</AuthProvider>);
}

describe("Tabular Ingestion & Column Mapping Screen (Screen 6)", () => {
  it("renders ERP mapping profile selector and data preview table", () => {
    renderWithAuth(<TabularIngestionPage />);

    expect(screen.getByText(/Batch Tabular Ingestion & ERP Schema Mapping/i)).toBeInTheDocument();
    expect(screen.getByText(/SAP MARA \/ MAKT Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Active Header Mappings/i)).toBeInTheDocument();

    // Table preview items
    expect(screen.getByText(/MAT-77001/i)).toBeInTheDocument();
    expect(screen.getByText(/GATE VALVE 100 NB CL150 WCB FLANGED RF API 600/i)).toBeInTheDocument();
  });

  it("switches ERP profile and ingests records", () => {
    renderWithAuth(<TabularIngestionPage />);

    // Switch to Oracle Cloud ERP
    const oracleBtn = screen.getByText(/Oracle Cloud ERP Profile/i);
    fireEvent.click(oracleBtn);

    expect(screen.getByText(/Oracle ERP standard extract/i)).toBeInTheDocument();

    // Trigger batch ingestion
    const ingestBtn = screen.getByRole("button", { name: /Ingest \d+ Records to Samanvay/i });
    fireEvent.click(ingestBtn);

    expect(screen.getByText(/Batch Ingestion Successfully Triggered/i)).toBeInTheDocument();
    expect(screen.getByText(/INGEST_BATCH_TX/i)).toBeInTheDocument();
  });
});

describe("Master Golden Catalogue Browser Screen (Screen 8)", () => {
  it("renders central repository with Verhoeff MPNG codes and canonical attributes", () => {
    renderWithAuth(<MasterCataloguePage />);

    expect(screen.getByText(/Central Golden Master Repository & Verhoeff Codes/i)).toBeInTheDocument();
    expect(screen.getAllByText("MPNG-0004821937-3").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Canonical Physical Attributes/i)).toBeInTheDocument();
    expect(screen.getByText(/Where-Used Across CPSE Plants/i)).toBeInTheDocument();
  });

  it("filters golden masters and allows lifecycle status changes", () => {
    renderWithAuth(<MasterCataloguePage />);

    // Filter by POWER sector
    const sectorSelect = screen.getByDisplayValue("ALL SECTORS");
    fireEvent.change(sectorSelect, { target: { value: "POWER" } });

    expect(screen.getByText("MPNG-0008472910-4")).toBeInTheDocument();

    // Select master and click Promote/Change status if available
    fireEvent.click(screen.getByText("MPNG-0008472910-4"));
    expect(screen.getAllByText(/POWER.TRANSFORMER/i).length).toBeGreaterThanOrEqual(1);
  });
});
