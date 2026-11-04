"use client";

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Flame,
  ShieldCheck,
  Timer,
  TriangleAlert,
  Waves,
} from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { Pill } from "./PanelFrame";
import { TELEMETRY_REFERENCE, riskIndex } from "@/lib/telemetry";
import { signed } from "@/lib/math";
import type { Telemetry } from "@/lib/types";

export interface TelemetryCardsProps {
  telemetry: Telemetry;
  materialName: string;
  oxygenPct: number;
}

type MetricTone = "orange" | "amber" | "cyan" | "violet" | "rose";

interface MetricCardProps {
  label: string;
  icon: LucideIcon;
  tone: MetricTone;
  /** Numeric readout, eased toward the prediction. */
  value: number;
  decimals: number;
  unit: string;
  tag: string;
  /** Normalized 0 - 1 position for the inline gauge. */
  fill: number;
  caption: string;
  delta: string;
  deltaTone: "up" | "down" | "flat";
}

const TONE_RING: Record<MetricTone, string> = {
  orange: "ring-orange-500/30 text-orange-400",
  amber: "ring-amber-500/30 text-amber-400",
  cyan: "ring-cyan-500/30 text-cyan-400",
  violet: "ring-violet-500/30 text-violet-400",
  rose: "ring-rose-500/30 text-rose-400",
};

const TONE_BAR: Record<MetricTone, string> = {
  orange: "from-orange-500 to-amber-400",
  amber: "from-amber-500 to-yellow-300",
  cyan: "from-cyan-500 to-sky-300",
  violet: "from-violet-500 to-fuchsia-300",
  rose: "from-rose-500 to-red-300",
};

const DELTA_TONE: Record<MetricCardProps["deltaTone"], string> = {
  up: "text-orange-300",
  down: "text-emerald-300",
  flat: "text-slate-500",
};

function MetricCard({
  label,
  icon: Icon,
  tone,
  value,
  decimals,
  unit,
  tag,
  fill,
  caption,
  delta,
  deltaTone,
}: MetricCardProps) {
  const animated = useAnimatedNumber(value, decimals);
  const animatedFill = useAnimatedNumber(Math.min(1, Math.max(0, fill)), 3);

  return (
    <article className="group relative flex flex-col gap-1 overflow-hidden rounded-lg border border-slate-800 bg-slate-900/50 p-2.5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:bg-slate-900/70">
      <div className="flex items-start justify-between gap-1.5">
        <span
          className={`flex size-5 shrink-0 items-center justify-center rounded ring-1 ${TONE_RING[tone]}`}
        >
          <Icon className="size-2.5" aria-hidden="true" />
        </span>
        <Pill tone="slate">{tag}</Pill>
      </div>

      <div>
        <p className="text-[10px] font-medium uppercase leading-tight tracking-wider text-slate-400">
          {label}
        </p>
        <p className="mt-0.5 font-mono text-xl font-bold tabular-nums text-slate-50">
          {animated.toFixed(decimals)}
          <span className="ml-0.5 text-[10px] font-medium text-slate-400">{unit}</span>
        </p>
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${TONE_BAR[tone]} transition-[width] duration-200 ease-out`}
          style={{ width: `${Math.min(100, Math.max(1.5, animatedFill * 100))}%` }}
        />
      </div>

      <div className="flex items-center justify-between gap-1.5">
        <span className="truncate text-[10px] text-slate-400">{caption}</span>
        <span
          className={`shrink-0 font-mono text-[10px] tabular-nums ${DELTA_TONE[deltaTone]}`}
        >
          {delta}
        </span>
      </div>
    </article>
  );
}

function deltaTone(
  value: number,
  reference: number,
  tolerance: number,
): MetricCardProps["deltaTone"] {
  if (Math.abs(value - reference) <= tolerance) return "flat";
  return value > reference ? "up" : "down";
}

function ConfidenceMeter({ telemetry }: { telemetry: Telemetry }) {
  const animated = useAnimatedNumber(telemetry.confidencePct, 0);
  const bandTone =
    telemetry.confidenceBand === "HIGH"
      ? "emerald"
      : telemetry.confidenceBand === "MODERATE"
        ? "amber"
        : "red";

  return (
    <div className="rounded-lg border border-slate-800/80 bg-slate-900/50 p-2.5 ring-1 ring-white/[0.02] transition-colors duration-200 hover:border-slate-700/80">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
          Model confidence
        </span>
        <Pill tone={bandTone}>{telemetry.confidenceBand}</Pill>
      </div>
      <div className="mt-1.5 flex flex-wrap items-end gap-x-1.5 gap-y-0.5">
        <span className="font-mono text-lg font-bold tabular-nums text-slate-100">
          {animated.toFixed(0)}
          <span className="text-[10px] text-slate-400">%</span>
        </span>
        <span className="pb-0.5 font-mono text-[10px] leading-tight text-slate-400">
          vigor {telemetry.combustionVigor.toFixed(2)} · {telemetry.heatReleaseW.toFixed(1)} W ·{" "}
          {telemetry.flameTempK} K · geo ×{telemetry.geometryFactor.toFixed(2)}
        </span>
      </div>
      <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-sky-400 to-emerald-400 transition-[width] duration-200 ease-out"
          style={{ width: `${animated}%` }}
        />
      </div>
    </div>
  );
}

function RiskMeter({ telemetry }: { telemetry: Telemetry }) {
  const risk = riskIndex(telemetry);
  const animated = useAnimatedNumber(risk * 100, 0);
  const tone = risk > 0.66 ? "red" : risk > 0.4 ? "amber" : "emerald";
  const label = risk > 0.66 ? "ELEVATED" : risk > 0.4 ? "GUARDED" : "NOMINAL";

  return (
    <div className="rounded-lg border border-slate-800/80 bg-slate-900/50 p-2.5 ring-1 ring-white/[0.02] transition-colors duration-200 hover:border-slate-700/80">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
          Composite risk index
        </span>
        <Pill tone={tone}>{label}</Pill>
      </div>
      <div className="mt-1.5 flex flex-wrap items-end gap-x-1.5 gap-y-0.5">
        <span className="font-mono text-lg font-bold tabular-nums text-slate-100">
          {animated.toFixed(0)}
          <span className="text-[10px] text-slate-400">/100</span>
        </span>
        <span className="pb-0.5 text-[10px] leading-tight text-slate-400">
          weighted spread · soot · duration · propagation
        </span>
      </div>
      <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-200 ease-out ${
            risk > 0.66
              ? "from-orange-500 to-red-500"
              : risk > 0.4
                ? "from-amber-500 to-orange-400"
                : "from-emerald-500 to-teal-400"
          }`}
          style={{ width: `${animated}%` }}
        />
      </div>
    </div>
  );
}

export function TelemetryCards({
  telemetry,
  materialName,
  oxygenPct,
}: TelemetryCardsProps) {
  const reference = TELEMETRY_REFERENCE;

  const spreadDelta = telemetry.flameSpreadRate - reference.flameSpreadRate;
  const extinctionDelta = telemetry.extinctionProb - reference.extinctionProb;
  const burnDelta = telemetry.burnDuration - reference.burnDuration;
  const smokeDelta = telemetry.smokeYield - reference.smokeYield;
  const lengthDelta = telemetry.flameLength - reference.flameLength;

  const metrics: MetricCardProps[] = [
    {
      label: "Flame Spread Rate",
      icon: Flame,
      tone: "orange",
      value: telemetry.flameSpreadRate,
      decimals: 1,
      unit: "mm/s",
      tag: "BASS-II / PSI-25",
      fill: telemetry.flameSpreadRate / 80,
      caption: "Propagation front velocity",
      delta: `${signed(spreadDelta)} mm/s vs nominal`,
      deltaTone: deltaTone(telemetry.flameSpreadRate, reference.flameSpreadRate, 1),
    },
    {
      label: "Extinction Probability",
      icon: TriangleAlert,
      tone: "amber",
      value: telemetry.extinctionProb * 100,
      decimals: 0,
      unit: "%",
      tag: "FLEX / PSI-69",
      fill: telemetry.extinctionProb,
      caption: `Sustains ignition in ${Math.round((1 - telemetry.extinctionProb) * 100)} of 100 trials`,
      delta: `${signed(extinctionDelta * 100, 0, " pp")} vs nominal`,
      deltaTone: deltaTone(
        telemetry.extinctionProb,
        reference.extinctionProb,
        0.02,
      ),
    },
    {
      label: "Large-Scale Burn Duration",
      icon: Timer,
      tone: "cyan",
      value: telemetry.burnDuration,
      decimals: 0,
      unit: "s",
      tag: "SAFFIRE-I / PSI-98",
      fill: telemetry.burnDuration / 180,
      caption: "Propagation to fuel depletion",
      delta: `${signed(burnDelta, 0, " s")} vs nominal`,
      deltaTone: deltaTone(telemetry.burnDuration, reference.burnDuration, 1.5),
    },
    {
      label: "Smoke & Particle Yield",
      icon: Waves,
      tone: "violet",
      value: telemetry.smokeYield,
      decimals: 1,
      unit: "mg/min",
      tag: "SAME / PSI-102",
      fill: telemetry.smokeYield / 80,
      caption: "Soot mass loading in cabin loop",
      delta: `${signed(smokeDelta)} mg/min vs nominal`,
      deltaTone: deltaTone(telemetry.smokeYield, reference.smokeYield, 0.6),
    },
    {
      label: "Flame Length & Soot Point",
      icon: Activity,
      tone: "rose",
      value: telemetry.flameLength,
      decimals: 1,
      unit: "cm",
      tag: "SPICE / PSI-107",
      fill: telemetry.flameLength / 25,
      caption: `Soot inception at ${telemetry.sootPoint.toFixed(1)} cm`,
      delta: `${signed(lengthDelta)} cm vs nominal`,
      deltaTone: deltaTone(telemetry.flameLength, reference.flameLength, 0.4),
    },
  ];

  return (
    <div className="flex h-full flex-col gap-2">
      {telemetry.inDomain ? (
        <div className="flex animate-fade-in items-center justify-between gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5">
          <span className="flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase tracking-widest text-emerald-300">
            <ShieldCheck className="size-3.5" aria-hidden="true" />
            In-domain
          </span>
          <span className="text-right text-[10px] leading-tight text-emerald-200">
            Inside the 12–25 % validated envelope for {materialName}
          </span>
        </div>
      ) : (
        <div
          role="alert"
          className="flex animate-fade-in items-start gap-2 rounded-lg border border-red-500/50 bg-red-500/10 px-2.5 py-1.5 shadow-[0_0_20px_rgba(239,68,68,0.18)]"
        >
          <TriangleAlert
            className="mt-0.5 size-3.5 shrink-0 animate-pulse text-red-400"
            aria-hidden="true"
          />
          <p className="font-mono text-[10px] font-semibold uppercase leading-tight tracking-wider text-red-200">
            Out of envelope — O₂ reads {oxygenPct.toFixed(1)} %, outside the 12–25 %
            surrogate domain. Treat every readout as low-confidence extrapolation.
          </p>
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 overflow-y-auto pr-0.5 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
        {metrics.map((metric, index) => (
          <div
            key={metric.label}
            className="animate-rise-in"
            style={{ animationDelay: `${index * 45}ms` }}
          >
            <MetricCard {...metric} />
          </div>
        ))}
      </div>

      <div className="grid shrink-0 grid-cols-1 gap-2 sm:grid-cols-2">
        <ConfidenceMeter telemetry={telemetry} />
        <RiskMeter telemetry={telemetry} />
      </div>
    </div>
  );
}