"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";
const KEY = "astraflame-theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");
  useEffect(() => {
    let t: Theme = window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
    try { const s = localStorage.getItem(KEY); if (s === "light" || s === "dark") t = s; } catch { /* storage blocked */ }
    setTheme(t);
    document.documentElement.dataset.theme = t;
  }, []);
  const flip = () => {
    const t: Theme = theme === "dark" ? "light" : "dark";
    setTheme(t);
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem(KEY, t); } catch { /* ignore */ }
  };
  return (
    <button type="button" onClick={flip} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className="af-press h-10 rounded-full bg-slate-800 px-4 text-sm font-medium text-slate-200 ring-1 ring-slate-700 hover:bg-slate-700">
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}
