"use client";

import { useRef } from "react";
import type { LucideIcon } from "lucide-react";
import {
  BrainCircuit,
  Flame,
  ShieldAlert,
  Table2,
  SlidersHorizontal,
} from "lucide-react";

export type TabKey = "simulation" | "risk" | "explain" | "protocols";

export const TABS: readonly {
  key: TabKey;
  label: string;
  short: string;
  icon: LucideIcon;
}[] = [
  {
    key: "simulation",
    label: "Simulation",
    short: "Flame",
    icon: Flame,
  },
  { key: "risk", label: "Risk Matrix", short: "Risk", icon: Table2 },
  {
    key: "explain",
    label: "Explainability",
    short: "Why",
    icon: BrainCircuit,
  },
  { key: "protocols", label: "Protocols", short: "Action", icon: ShieldAlert },
];

export interface TabBarProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  onOpenControls: () => void;
  controlsOpen: boolean;
  controlsId: string;
}

export function TabBar({
  activeTab,
  onTabChange,
  onOpenControls,
  controlsOpen,
  controlsId,
}: TabBarProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const moveFocus = (direction: 1 | -1) => {
    const index = TABS.findIndex(({ key }) => key === activeTab);
    const next = (index + direction + TABS.length) % TABS.length;
    const target = TABS[next];
    onTabChange(target.key);
    listRef.current
      ?.querySelector<HTMLButtonElement>(`[data-tab="${target.key}"]`)
      ?.focus();
  };

  return (
    <div className="flex shrink-0 items-center gap-1.5 border-b border-slate-800/80 bg-slate-950/60 px-2 py-1.5 backdrop-blur-sm sm:px-3">
      <button
        type="button"
        onClick={onOpenControls}
        aria-expanded={controlsOpen}
        aria-controls={controlsId}
        className="flex shrink-0 items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-300 transition-all hover:border-orange-500/50 hover:bg-slate-800 hover:text-orange-300 active:scale-95 xl:hidden"
      >
        <SlidersHorizontal className="size-3.5" aria-hidden="true" />
        Scenario
      </button>

      <div
        ref={listRef}
        role="tablist"
        aria-label="Dashboard sections"
        className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto"
      >
        {TABS.map(({ key, label, short, icon: Icon }) => {
          const active = key === activeTab;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              data-tab={key}
              id={`tab-${key}`}
              aria-selected={active}
              aria-controls={`panel-${key}`}
              tabIndex={active ? 0 : -1}
              onClick={() => onTabChange(key)}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight") {
                  event.preventDefault();
                  moveFocus(1);
                } else if (event.key === "ArrowLeft") {
                  event.preventDefault();
                  moveFocus(-1);
                }
              }}
              className={`relative flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-all duration-200 active:scale-95 ${
                active
                  ? "bg-slate-800/80 text-slate-50 shadow-[inset_0_0_0_1px_rgba(148,163,184,0.18)]"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              <Icon
                className={`size-3.5 transition-colors duration-200 ${
                  active ? "text-orange-400" : "text-slate-500"
                }`}
                aria-hidden="true"
              />
              <span className="hidden sm:inline">{label}</span>
              <span className="sm:hidden">{short}</span>
              <span
                className={`absolute inset-x-1.5 -bottom-[7px] h-[2px] rounded-full bg-gradient-to-r from-orange-400 to-amber-300 transition-all duration-300 ${
                  active ? "opacity-100" : "scale-x-0 opacity-0"
                }`}
                aria-hidden="true"
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
