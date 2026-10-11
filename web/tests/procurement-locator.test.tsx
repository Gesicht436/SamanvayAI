import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AuthProvider } from "@/lib/auth-context";
import SpareLocatorPage from "@/app/locator/page";
import ProcurementHubPage from "@/app/procurement/page";

describe("Inter-CPSE Spare Locator (Module 11 Part 1)", () => {
  it("renders locator with distance matrix and privacy disclosure masking", async () => {
    render(
      <AuthProvider>
        <SpareLocatorPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Geographic Spare Inventory & Surplus Locator/i)).toBeInTheDocument();
    });

    // Check location filters
    expect(screen.getByText("All India")).toBeInTheDocument();
    expect(screen.getByText("500 km")).toBeInTheDocument();
    expect(screen.getByText("1000 km")).toBeInTheDocument();

    // Check masked privacy indicator
    expect(screen.getByText(/Section 9.3 Masked Identity/i)).toBeInTheDocument();

    // Check results table rows
    await waitFor(() => {
      expect(screen.getByText("Mathura")).toBeInTheDocument();
      expect(screen.getByText("Korba")).toBeInTheDocument();
      expect(screen.getByText("Bhilai")).toBeInTheDocument();
    });

    // Verify privacy masking on external CPSE rows
    expect(screen.getAllByText("Partner Masked").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Internal Inventory")).toBeInTheDocument();
  });
});


describe("Procurement Hub (Module 11 Part 1)", () => {
  it("renders Stream A surplus requisitions and Stream B demand pools", async () => {
    render(
      <AuthProvider>
        <ProcurementHubPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Inter-CPSE Surplus Transfer & Joint Demand Pooling Hub/i)
      ).toBeInTheDocument();
    });

    // Verify tabs
    expect(screen.getByText(/Stream A: Surplus Redeployment Transfers/i)).toBeInTheDocument();
    expect(screen.getByText(/Stream B: Forward Demand Pooling & Tender Packs/i)).toBeInTheDocument();

    // Check KPI cards
    expect(screen.getByText(/Avoided Purchase Cost/i)).toBeInTheDocument();
    expect(screen.getByText(/Net Financial Benefit/i)).toBeInTheDocument();

    // Check active transfer orders in table
    await waitFor(() => {
      expect(screen.getByText("TRF-2026-0081")).toBeInTheDocument();
      expect(screen.getByText("TRF-2026-0045")).toBeInTheDocument();
    });
  });
});
