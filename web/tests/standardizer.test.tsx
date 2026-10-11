import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import StandardizerPage from "@/app/standardizer/page";
import { AuthProvider } from "@/lib/auth-context";

describe("Standardizer Screen", () => {
  it("renders input box, sample chips, and button", () => {
    render(
      <AuthProvider>
        <StandardizerPage />
      </AuthProvider>
    );

    expect(screen.getByText("Material Standardizer & Match Engine")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/e\.g\. VLV GT 100 NB CL150/i)
    ).toBeInTheDocument();
    expect(screen.getByText("Gate Valve 100NB Cl150")).toBeInTheDocument();
    expect(screen.getByText("Standardize & Match")).toBeInTheDocument();
  });

  it("submits description and renders extracted attributes and ranked candidates", async () => {
    render(
      <AuthProvider>
        <StandardizerPage />
      </AuthProvider>
    );

    const button = screen.getByText("Standardize & Match");
    fireEvent.click(button);

    await waitFor(() => {
      // Extracted subcategory
      expect(screen.getByText("VALVES.GATE")).toBeInTheDocument();
      // Clean normalization indicator
      expect(screen.getByText("Clean Normalization")).toBeInTheDocument();
      // Candidate code
      expect(screen.getByText("MPNG-0004821937-3")).toBeInTheDocument();
      // Tier 2 badge
      expect(screen.getByText("Tier 2: Steward Review")).toBeInTheDocument();
      // Tier 3 badge
      expect(screen.getByText("Tier 3: Refused (Mismatch)")).toBeInTheDocument();
    });
  });

  it("triggers Diff Inspector view when Inspect Diff Matrix button is clicked", async () => {
    render(
      <AuthProvider>
        <StandardizerPage />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText("Standardize & Match"));

    await waitFor(() => {
      expect(screen.getByText("MPNG-0004821937-3")).toBeInTheDocument();
    });

    const diffButtons = screen.getAllByText("Inspect Diff Matrix");
    fireEvent.click(diffButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Diff Inspector")).toBeInTheDocument();
      expect(screen.getByText("Explains the decision")).toBeInTheDocument();
      expect(screen.getByText("← Back to Candidates")).toBeInTheDocument();
    });
  });
});
