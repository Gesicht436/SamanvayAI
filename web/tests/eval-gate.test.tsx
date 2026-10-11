import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import EvalPage from "@/app/eval/page";
import { AuthProvider } from "@/lib/auth-context";

describe("Evaluation Gate Screen", () => {
  it("renders 3 baselines side-by-side with exact Clopper-Pearson bounds", async () => {
    render(
      <AuthProvider>
        <EvalPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Evaluation Harness & Release Gate Verification")).toBeInTheDocument();
      // Baselines
      expect(screen.getByText("Raw Cosine Similarity")).toBeInTheDocument();
      expect(screen.getByText("Character Trigram Sim")).toBeInTheDocument();
      expect(screen.getByText("Deterministic Safety Path")).toBeInTheDocument();
      // Error rates
      expect(screen.getByText("67.6%")).toBeInTheDocument();
      expect(screen.getByText("55.9%")).toBeInTheDocument();
      expect(screen.getAllByText(/0\.0%/).length).toBeGreaterThanOrEqual(1);
      // Clopper-Pearson bound
      expect(screen.getAllByText(/2\.15%/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders hard release gate checklist and parity tables", async () => {
    render(
      <AuthProvider>
        <EvalPage />
      </AuthProvider>
    );

    await waitFor(() => {
      // Hard gates
      expect(screen.getByText("Hard-negative false merges")).toBeInTheDocument();
      expect(screen.getByText("Missing-attribute routing to Tier 2")).toBeInTheDocument();
      expect(screen.getAllByText("PASS").length).toBeGreaterThanOrEqual(5);

      // Sector and org parity
      expect(screen.getByText("Sector Parity Breakdown")).toBeInTheDocument();
      expect(screen.getByText("CPSE Organisation Parity Breakdown")).toBeInTheDocument();
      expect(screen.getAllByText("In Parity").length).toBe(4);
    });
  });
});
