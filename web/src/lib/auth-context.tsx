"use client";

import React, { createContext, useContext, useState } from "react";
import { User, Org, UserRole } from "@/types";
import { SAMPLE_ORGS } from "./api";

interface AuthContextType {
  user: User;
  selectedOrg: Org | null;
  setSelectedOrg: (org: Org | null) => void;
  setRole: (role: UserRole) => void;
  setDomains: (domains: string[]) => void;
  availableOrgs: Org[];
}

const DEFAULT_USER: User = {
  id: "steward-checker-01",
  email: "checker.power@cpse.gov.in",
  name: "Dr. P. Sharma (Chief Materials Steward)",
  role: "CHECKER",
  domains: ["COMMON", "POWER", "STEEL", "MINING", "HEAVY_ENG"],
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(DEFAULT_USER);
  // Spec invariant: "organisation switcher with no default organisation"
  const [selectedOrg, setSelectedOrg] = useState<Org | null>(null);

  const handleSetSelectedOrg = (org: Org | null) => {
    setSelectedOrg(org);
    setUser((prev) => ({ ...prev, org_code: org?.code }));
  };

  const setRole = (role: UserRole) => {
    setUser((prev) => ({ ...prev, role }));
  };

  const setDomains = (domains: string[]) => {
    setUser((prev) => ({ ...prev, domains }));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        selectedOrg,
        setSelectedOrg: handleSetSelectedOrg,
        setRole,
        setDomains,
        availableOrgs: SAMPLE_ORGS,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
