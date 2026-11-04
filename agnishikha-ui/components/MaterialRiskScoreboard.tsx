"use client";

import { useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ExternalLink,
  Table2,
} from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { HAZARD_RANK, MATERIALS } from "@/lib/materials";
import type { HazardLevel, MaterialKey } from "@/lib/types";

export interface MaterialRiskScoreboardProps {
  selectedMaterial: MaterialKey;
  onSelectMaterial: (key: MaterialKey) => void;
}

type SortKey =
  | "name"
  | "flameSpreadRate"
  | "minExtinctionO2"
  | "smokeHazard"
  | "sourceTag";

type SortDirection = "asc" | "desc";

interface ColumnDefinition {
  key: SortKey;
  label: string;
  align: "left" | "right";
}

const COLUMNS: ColumnDefinition[] = [
  { key: "name", label: "Material Name", align: "left" },
  { key: "flameSpreadRate", label: "Flame Spread", align: "right" },
  { key: "minExtinctionO2", label: "Min Ext. O₂", align: "right" },
  { key: "smokeHazard", label: "Smoke Hazard", align: "left" },
  { key: "sourceTag", label: "NASA Source Tag", align: "left" },
];

const HAZARD_TONE: Record<HazardLevel, string> = {
  LOW: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  MODERATE: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
  HIGH: "bg-orange-500/10 text-orange-300 ring-orange-500/30",
  SEVERE: "bg-red-500/10 text-red-300 ring-red-500/30",
};

const MAX_SPREAD = Math.max(...MATERIALS.map((m) => m.flameSpreadRate));

function SpreadCell({ value, active }: { value: number; active: boolean }) {
  const animated = useAnimatedNumber(value, 0);
  const width = useAnimatedNumber((value / MAX_SPREAD) * 100, 1);

  return (
    <div className="flex flex-col items-end">
      <span className="font-mono text-sm tabular-nums text-slate-100">
        {animated.toFixed(0)}
        <span className="ml-1 text-[10px] text-slate-400">mm/s</span>
      </span>
      <div className="mt-1 h-1 w-full max-w-[110px] overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-300 ease-out ${
            active
              ? "from-orange-400 to-red-500"
              : "from-amber-400/80 to-red-500/80"
          }`}
          style={{ width: `${Math.min(100, Math.max(3, width))}%` }}
        />
      </div>
    </div>
  );
}

export function MaterialRiskScoreboard({
  selectedMaterial,
  onSelectMaterial,
}: MaterialRiskScoreboardProps) {
  const [sortKey, setSortKey] = useState<SortKey>("flameSpreadRate");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const sortedRows = useMemo(() => {
    const factor = sortDirection === "asc" ? 1 : -1;
    return [...MATERIALS].sort((a, b) => {
      switch (sortKey) {
        case "name":
          return a.name.localeCompare(b.name) * factor;
        case "minExtinctionO2":
          return (a.minExtinctionO2 - b.minExtinctionO2) * factor;
        case "smokeHazard":
          return (HAZARD_RANK[a.smokeHazard] - HAZARD_RANK[b.smokeHazard]) * factor;
        case "sourceTag":
          return a.sourceTag.localeCompare(b.sourceTag) * factor;
        case "flameSpreadRate":
        default:
          return (a.flameSpreadRate - b.flameSpreadRate) * factor;
      }
    });
  }, [sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDirection(key === "name" || key === "sourceTag" ? "asc" : "desc");
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex shrink-0 items-center justify-between gap-2 font-mono text-[10px] uppercase tracking-wider text-slate-400">
        <span>Ranked registry · select a header to sort</span>
        <span className="text-slate-500">
          {sortedRows.length} specimens · PSI traceable
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full min-w-[600px] border-separate border-spacing-0 text-left">
          <thead className="sticky top-0 z-10 bg-slate-900 backdrop-blur">
            <tr>
              {COLUMNS.map((column) => {
                const isActive = column.key === sortKey;
                const SortIcon = !isActive
                  ? ArrowUpDown
                  : sortDirection === "asc"
                    ? ArrowUp
                    : ArrowDown;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={
                      isActive
                        ? sortDirection === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                    }
                    className={`border-b border-slate-800 pb-1.5 text-[10px] font-semibold uppercase tracking-wider ${
                      column.align === "right" ? "text-right" : "text-left"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSort(column.key)}
                      className={`inline-flex items-center gap-1 transition-colors hover:text-slate-200 ${
                        isActive ? "text-amber-400" : "text-slate-400"
                      } ${column.align === "right" ? "flex-row-reverse" : ""}`}
                    >
                      <SortIcon className="size-3" aria-hidden="true" />
                      {column.label}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((material, index) => {
              const isSelected = material.key === selectedMaterial;
              return (
                <tr
                  key={material.key}
                  onClick={() => onSelectMaterial(material.key)}
                  aria-current={isSelected ? "true" : undefined}
                  className={`cursor-pointer transition-colors duration-150 ${
                    isSelected
                      ? "bg-amber-500/10 hover:bg-amber-500/15"
                      : "hover:bg-slate-800/40"
                  }`}
                >
                  <td className="border-b border-slate-800/70 py-2 pl-2 pr-3">
                    <button
                      type="button"
                      onClick={() => onSelectMaterial(material.key)}
                      aria-pressed={isSelected}
                      className="flex w-full items-center gap-2 rounded text-left"
                    >
                      <span
                        className={`w-4 shrink-0 text-center font-mono text-[10px] ${
                          isSelected ? "text-amber-400" : "text-slate-500"
                        }`}
                      >
                        {index + 1}
                      </span>
                      <span
                        className={`text-[13px] font-medium ${
                          isSelected ? "text-amber-200" : "text-slate-200"
                        }`}
                      >
                        {material.name}
                      </span>
                      {isSelected ? (
                        <span className="rounded bg-amber-400/20 px-1 py-0.5 font-mono text-[9px] uppercase tracking-widest text-amber-200">
                          Active
                        </span>
                      ) : null}
                    </button>
                  </td>

                  <td className="border-b border-slate-800/70 px-3 py-2 text-right">
                    <SpreadCell
                      value={material.flameSpreadRate}
                      active={isSelected}
                    />
                  </td>

                  <td className="border-b border-slate-800/70 px-3 py-2 text-right font-mono text-[13px] tabular-nums text-slate-200">
                    {material.minExtinctionO2.toFixed(1)}
                    <span className="ml-1 text-[10px] text-slate-400">%</span>
                  </td>

                  <td className="border-b border-slate-800/70 px-3 py-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span
                        className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ring-1 ${HAZARD_TONE[material.smokeHazard]}`}
                      >
                        {material.smokeHazard}
                      </span>
                      <span className="font-mono text-[10px] text-slate-400">
                        {material.smokeYield.toFixed(0)} mg/min
                      </span>
                    </div>
                  </td>

                  <td className="border-b border-slate-800/70 px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[10px] text-slate-400">
                        {material.sourceTag}
                      </span>
                      <a
                        href="https://psi.nasa.gov"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(event) => event.stopPropagation()}
                        title={`Open ${material.name} flammability record at psi.nasa.gov`}
                        className="inline-flex items-center gap-1 rounded bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-cyan-300 ring-1 ring-cyan-500/30 transition-all hover:bg-cyan-500/20 active:scale-95"
                      >
                        psi.nasa.gov
                        <ExternalLink className="size-2.5" aria-hidden="true" />
                      </a>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-auto flex shrink-0 items-start gap-2 rounded-lg border border-slate-800/80 bg-slate-900/50 p-2.5 ring-1 ring-white/[0.02]">
        <Table2 className="mt-0.5 size-3 shrink-0 text-slate-400" aria-hidden="true" />
        <p className="text-[10px] leading-relaxed text-slate-400">
          Flame spread values are campaign means at 21 % O₂ / 101.3 kPa in still cabin
          air; select a row to re-drive the full telemetry stack. Every row links to the
          NASA PSI flammability registry for primary-source traceability.
        </p>
      </div>
    </div>
  );
}