import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DiffInspector } from "@/components/diff/DiffInspector";
import { DEMO_MATCH_RESPONSES } from "@/lib/api";
import { AuthProvider } from "@/lib/auth-context";

describe("Diff Inspector Screen", () => {
  it("renders side-by-side attribute matrix with copy 'Explains the decision'", () => {
    const candidate = DEMO_MATCH_RESPONSES.valve.candidates[0];

    render(
      <AuthProvider>
        <DiffInspector candidate={candidate} rawText="VALVE GATE 100 NB CL150" />
      </AuthProvider>
    );

    expect(screen.getByText("Diff Inspector")).toBeInTheDocument();
    expect(screen.getByText("Explains the decision")).toBeInTheDocument();
    expect(screen.getByText(candidate.golden_code)).toBeInTheDocument();

    // Column headers
    expect(screen.getByText("Raw Item Extracted")).toBeInTheDocument();
    expect(screen.getByText("Golden Master")).toBeInTheDocument();
    expect(screen.getByText("Verdict")).toBeInTheDocument();
  });

  it("renders Safety Routing banner and MISSING badges for Tier 2 required gap", () => {
    const candidate = DEMO_MATCH_RESPONSES.valve.candidates[0]; // Tier 2

    render(
      <AuthProvider>
        <DiffInspector candidate={candidate} />
      </AuthProvider>
    );

    expect(screen.getByText(/SAFETY ROUTING: Required Attribute Gap/i)).toBeInTheDocument();
    expect(screen.getByText(/Tier 2: Steward Review/i)).toBeInTheDocument();
    expect(screen.getAllByText("MISSING").length).toBeGreaterThanOrEqual(1);
  });

  it("renders Safety Refusal banner and MISMATCH badge for Tier 3 hard rating mismatch", () => {
    const candidate = DEMO_MATCH_RESPONSES.valve.candidates[1]; // Tier 3 (ASME_150 vs ASME_300)

    render(
      <AuthProvider>
        <DiffInspector candidate={candidate} />
      </AuthProvider>
    );

    expect(screen.getByText(/SAFETY REFUSAL: Hard Attribute Mismatch Detected/i)).toBeInTheDocument();
    expect(screen.getByText(/Tier 3: Refused \(Mismatch\)/i)).toBeInTheDocument();
    expect(screen.getByText("MISMATCH")).toBeInTheDocument();
  });

  it("renders Spec Compliant banner for Tier 1 match", () => {
    const candidate = DEMO_MATCH_RESPONSES.motor.candidates[0]; // Tier 1

    render(
      <AuthProvider>
        <DiffInspector candidate={candidate} />
      </AuthProvider>
    );

    expect(screen.getByText(/SPECIFICATION COMPLIANT: All Hard & Required Attributes Match/i)).toBeInTheDocument();
    expect(screen.getByText(/Tier 1: Auto-Harmonized/i)).toBeInTheDocument();
  });
});
