"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light" | "system";

interface ThemeContextType {
  theme: Theme;
  resolvedTheme: "dark" | "light";
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [resolvedTheme, setResolvedTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("samanvay-theme") as Theme | null;
    if (saved && (saved === "dark" || saved === "light" || saved === "system")) {
      setThemeState(saved);
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    let effective: "dark" | "light" = "dark";

    if (theme === "system") {
      const media = window.matchMedia("(prefers-color-scheme: dark)");
      effective = media.matches ? "dark" : "light";
      const listener = (e: MediaQueryListEvent) => {
        const next = e.matches ? "dark" : "light";
        setResolvedTheme(next);
        if (next === "dark") {
          root.classList.add("dark");
        } else {
          root.classList.remove("dark");
        }
      };
      media.addEventListener("change", listener);
      return () => media.removeEventListener("change", listener);
    } else {
      effective = theme;
    }

    setResolvedTheme(effective);
    if (effective === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("samanvay-theme", theme);
  }, [theme]);

  const setTheme = (next: Theme) => {
    setThemeState(next);
  };

  const toggleTheme = () => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
