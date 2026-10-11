import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/lib/auth-context";

function TestConsumer() {
  const { user, selectedOrg, setSelectedOrg, setRole, availableOrgs } = useAuth();
  return (
    <div>
      <div data-testid="org-code">{selectedOrg ? selectedOrg.code : "NO_ORG"}</div>
      <div data-testid="user-role">{user.role}</div>
      <div data-testid="user-org">{user.org_code || "UNASSIGNED"}</div>
      <button
        data-testid="select-oil"
        onClick={() => setSelectedOrg(availableOrgs.find((o) => o.code === "OIL-1") || null)}
      >
        Select OIL-1
      </button>
      <button data-testid="set-maker" onClick={() => setRole("MAKER")}>
        Set Maker
      </button>
    </div>
  );
}

describe("Auth and Organisation Context", () => {
  it("initializes with NO default organisation per specification invariant", () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Hard requirement: organisation switcher has no default organisation
    expect(screen.getByTestId("org-code").textContent).toBe("NO_ORG");
    expect(screen.getByTestId("user-org").textContent).toBe("UNASSIGNED");
  });

  it("updates selected organisation and syncs user org_code", () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    fireEvent.click(screen.getByTestId("select-oil"));
    expect(screen.getByTestId("org-code").textContent).toBe("OIL-1");
    expect(screen.getByTestId("user-org").textContent).toBe("OIL-1");
  });

  it("updates user role correctly", () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    fireEvent.click(screen.getByTestId("set-maker"));
    expect(screen.getByTestId("user-role").textContent).toBe("MAKER");
  });
});
