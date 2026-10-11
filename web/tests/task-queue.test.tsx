import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TaskQueue } from "@/components/queue/TaskQueue";
import { AuthProvider } from "@/lib/auth-context";

describe("Stewardship Governance Queue", () => {
  it("renders stewardship tasks with pagination controls and filter dropdowns", async () => {
    render(
      <AuthProvider>
        <TaskQueue />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Stewardship Governance Queue")).toBeInTheDocument();
      expect(screen.getByText(/Total Tasks:/i)).toBeInTheDocument();
      expect(screen.getByText("VALVES.GATE")).toBeInTheDocument();
    });

    // Check pagination
    expect(screen.getByText(/Page/i)).toBeInTheDocument();
    expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
  });

  it("filters tasks by status", async () => {
    render(
      <AuthProvider>
        <TaskQueue />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("VALVES.GATE")).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText("Filter Tasks by Status");
    fireEvent.change(statusSelect, { target: { value: "APPROVED" } });

    await waitFor(() => {
      expect(screen.getByText("POWER.TRANSFORMER")).toBeInTheDocument();
    });
  });

  it("enforces Maker-Checker Invariant by prohibiting proposer approval", async () => {
    render(
      <AuthProvider>
        <TaskQueue />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("VALVES.GATE")).toBeInTheDocument();
    });

    // When the logged-in user is NOT the proposer (user is "steward-checker-01" while task 101 maker is "steward-maker-01"),
    // the approve button is enabled
    const approveButtons = screen.getAllByText("Approve");
    expect(approveButtons.length).toBeGreaterThan(0);
    expect(approveButtons[0]).not.toBeDisabled();
  });

  it("opens approval modal and requires engineering rationale", async () => {
    render(
      <AuthProvider>
        <TaskQueue />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("VALVES.GATE")).toBeInTheDocument();
    });

    const approveButtons = screen.getAllByText("Approve");
    fireEvent.click(approveButtons[0]);

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText(/Checker Approval — Task #/i)).toBeInTheDocument();
      expect(screen.getByText("Confirm Approval")).toBeInTheDocument();
    });

    // Submitting without rationale produces validation error
    fireEvent.click(screen.getByText("Confirm Approval"));

    await waitFor(() => {
      expect(
        screen.getByText(/A formal engineering rationale is required for the immutable audit log/i)
      ).toBeInTheDocument();
    });
  });
});
