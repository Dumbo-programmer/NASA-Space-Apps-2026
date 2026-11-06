"use client";

import {
  Cpu,
  Flame,
  Orbit,
  Power,
  Radio,
  Wind,
} from "lucide-react";
import { TRAINING_ENVELOPE } from "@/lib/axes";
import { getMaterial } from "@/lib/materials";
import type { EnvironmentState, SimulationState } from "@/lib/types";

export interface MissionHeaderProps {
  environment: EnvironmentState;
  simulation: SimulationState;
  onToggleVentilation: () => void;
}

export function MissionHeader({
  environment,
  simulation,
  onToggleVentilation,
}: MissionHeaderProps) {
  const material = getMaterial(environment.material);
  const isVentilationCut = simulation.isVentilationCut;

  return (
    <header className="relative shrink-0 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md">
      <span
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-orange-500/60 via-cyan-500/25 to-transparent"
        aria-hidden="true"
      />
      <div className="mx-auto flex w-full max-w-[1800px] flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2 sm:px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="relative flex size-8 shrink-0 items-center justify-center rounded-lg border border-orange-500/40 bg-orange-500/10 shadow-[0_0_20px_rgba(249,115,22,0.25)]">
            <span
              className="absolute inset-0 animate-ping-slow rounded-lg bg-orange-500/20"
              aria-hidden="true"
            />
            <Flame className="animate-flicker relative size-4 text-orange-400" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="flex items-center gap-1.5 truncate text-sm font-bold leading-tight tracking-tight text-slate-50">
              AstraFlame
              <span className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-cyan-300 ring-1 ring-cyan-500/30">
                Agnishikha
              </span>
            </h1>
            <p className="hidden items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-slate-400 sm:flex">
              <span className="inline-flex items-center gap-1">
                <Orbit className="size-2.5 text-slate-500" aria-hidden="true" />
                ISS Columbus · µg
              </span>
              <span className="text-slate-600">|</span>
              <span>
                envelope {TRAINING_ENVELOPE.oxygenMin}–{TRAINING_ENVELOPE.oxygenMax} % O₂
              </span>
              <span className="text-slate-600">|</span>
              <span>PSI surrogate v2.4 · offline</span>
            </p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="hidden items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900/60 px-2 py-1 lg:flex">
            <span className="relative flex size-1.5">
              <span className="animate-ping-slow absolute inline-flex size-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex size-1.5 rounded-full bg-emerald-400" />
            </span>
            <p className="font-mono text-[10px] uppercase tracking-widest text-emerald-300">
              <Radio className="mr-1 inline size-2.5" aria-hidden="true" />
              Surrogate · offline
            </p>
          </div>

          <div className="hidden items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900/60 px-2 py-1 md:flex">
            <Cpu className="size-3 text-slate-500" aria-hidden="true" />
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
              KB2 · TEGEL · 30 Hz
            </p>
          </div>

          <div className="hidden rounded-md border border-slate-800 bg-slate-900/60 px-2 py-1 lg:block">
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
              Specimen
            </p>
            <p className="truncate font-mono text-[11px] font-semibold text-amber-300">
              {material.name}
            </p>
          </div>

          <button
            type="button"
            onClick={onToggleVentilation}
            aria-pressed={isVentilationCut}
            className={`flex items-center gap-1.5 whitespace-nowrap rounded-md border px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider transition-all duration-200 active:scale-95 ${
              isVentilationCut
                ? "animate-pulse border-red-400 bg-red-600/90 text-white shadow-[0_0_22px_rgba(239,68,68,0.55)]"
                : "border-amber-500/50 bg-amber-500/10 text-amber-300 hover:border-amber-400 hover:bg-amber-500/20 hover:shadow-[0_0_16px_rgba(251,191,36,0.2)]"
            }`}
          >
            {isVentilationCut ? (
              <Power className="size-3.5" aria-hidden="true" />
            ) : (
              <Wind className="size-3.5" aria-hidden="true" />
            )}
            {isVentilationCut ? "Ventilation isolated · restore" : "Cut ventilation"}
          </button>
        </div>
      </div>
    </header>
  );
}