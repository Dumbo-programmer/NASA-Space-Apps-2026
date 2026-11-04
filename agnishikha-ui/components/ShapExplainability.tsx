"use client";

import {
  BrainCircuit,
  FlaskConical,
  Library,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wind,
} from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { Pill, SubCard } from "./PanelFrame";
import { signed } from "@/lib/math";
import type {
  RegistryComparison,
  ShapDriver,
  ShapExplanation,
  ShapTone,
} from "@/lib/shap";

export interface ShapExplainabilityProps {
  explanation: ShapExplanation;
}

/** Widest impact share the bar scale is normalized against, in percent. */
const BAR_SCALE_MAX = 50;

const TONE_BAR: Record<ShapTone, string> = {
  up: "from-orange-500 to-amber-300",
  down: "from-sky-500 to-cyan-300",
  neutral: "from-slate-500 to-slate-400",
};

const TONE_TEXT: Record<ShapTone, string> = {
  up: "text-orange-300",
  down: "text-cyan-300",
  neutral: "text-slate-400",
};

function TrendIcon({ tone }: { tone: ShapTone }) {
  if (tone === "up") {
    return <TrendingUp className="size-3" aria-hidden="true" />;
  }
  if (tone === "down") {
    return <TrendingDown className="size-3" aria-hidden="true" />;
  }
  return <Sparkles className="size-3" aria-hidden="true" />;
}

function DriverRow({
  driver,
  rank,
  delay,
}: {
  driver: ShapDriver;
  rank: number;
  delay: number;
}) {
  const barWidth = useAnimatedNumber(
    Math.min(100, (driver.impactPct / BAR_SCALE_MAX) * 100),
    1,
  );
  const contribution = useAnimatedNumber(driver.contribution, 1);

  return (
    <li
      className="animate-rise-in transition-opacity"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="w-3 shrink-0 text-center font-mono text-[10px] text-slate-500">
            {rank}
          </span>
          <span className="truncate text-[11px] font-medium text-slate-200 2xl:text-xs">
            {driver.label}
          </span>
          {driver.dominant ? <Pill tone="violet">Dominant</Pill> : null}
        </span>
        <span className="shrink-0 font-mono text-[11px] font-bold tabular-nums text-slate-100 2xl:text-xs">
          {driver.impactPct}%
        </span>
      </div>

      <div className="mt-1 flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800 2xl:h-2.5">
          <div
            className={`h-full rounded-full bg-gradient-to-r ${TONE_BAR[driver.tone]} transition-[width] duration-500 ease-out`}
            style={{ width: `${Math.max(2, barWidth)}%` }}
          />
        </div>
        <span
          className={`flex w-[84px] shrink-0 items-center justify-end gap-1 font-mono text-[10px] tabular-nums 2xl:text-[11px] ${TONE_TEXT[driver.tone]}`}
        >
          <TrendIcon tone={driver.tone} />
          {signed(contribution, 1)} mm/s
        </span>
      </div>

      <p
        title={driver.detail}
        className="truncate pl-5 font-mono text-[10px] text-slate-400 2xl:text-[11px]"
      >
        {driver.detail}
      </p>
    </li>
  );
}

function SimilarExperimentRow({
  name,
  tag,
  match,
}: {
  name: string;
  tag: string;
  match: number;
}) {
  const animatedMatch = useAnimatedNumber(match, 0);
  return (
    <li className="flex items-center gap-2">
      <span
        title={name}
        className="w-28 shrink-0 truncate text-[10px] text-slate-300 2xl:text-[11px]"
      >
        {name}
      </span>
      <span className="w-14 shrink-0 truncate font-mono text-[10px] text-slate-400 2xl:text-[11px]">
        {tag}
      </span>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-800 2xl:h-1.5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-sky-300 transition-[width] duration-500 ease-out"
          style={{ width: `${animatedMatch}%` }}
        />
      </div>
      <span className="w-7 shrink-0 text-right font-mono text-[10px] text-cyan-300 2xl:text-[11px]">
        {animatedMatch.toFixed(0)}%
      </span>
    </li>
  );
}

function ComparisonCell({ row }: { row: RegistryComparison }) {
  const registry = useAnimatedNumber(row.registry, row.digits);
  const model = useAnimatedNumber(row.model, row.digits);

  const delta = row.model - row.registry;
  // 10 % of the registry mean, floored at one display step, is the band we call
  // "agrees with the campaign mean".
  const tolerance = Math.max(Math.pow(10, -row.digits), Math.abs(row.registry) * 0.1);
  const agrees = Math.abs(delta) <= tolerance;

  return (
    <SubCard className="rounded-md px-2 py-1.5">
      <p className="text-[10px] uppercase tracking-wider text-slate-400 2xl:text-[11px]">
        {row.label}
      </p>
      <p className="font-mono text-[11px] font-semibold tabular-nums text-slate-200 2xl:text-xs">
        {registry.toFixed(row.digits)}
        <span className="text-slate-500"> / </span>
        <span className={agrees ? "text-emerald-300" : "text-amber-300"}>
          {model.toFixed(row.digits)}
        </span>
        <span className="ml-0.5 text-[10px] font-normal text-slate-400 2xl:text-[11px]">
          {row.unit}
        </span>
      </p>
      <p className="font-mono text-[10px] text-slate-400 2xl:text-[11px]">
        {signed(delta, row.digits, " vs registry")}
      </p>
    </SubCard>
  );
}

export function ShapExplainability({ explanation }: ShapExplainabilityProps) {
  const {
    drivers,
    basePrediction,
    currentPrediction,
    openDamperPrediction,
    damperDelta,
    totalAbsContribution,
    topDriver,
    modelLabel,
    similarExperiments,
    registryVsModel,
  } = explanation;

  const base = useAnimatedNumber(basePrediction, 1);
  const current = useAnimatedNumber(currentPrediction, 1);
  const openDamper = useAnimatedNumber(openDamperPrediction, 1);
  const delta = useAnimatedNumber(damperDelta, 1);
  const total = useAnimatedNumber(totalAbsContribution, 1);

  const shift = currentPrediction - basePrediction;
  const damperActive = Math.abs(damperDelta) > 0.05;
  const atBaseline = Math.abs(shift) < 0.05;

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-[1.05fr_1fr]">
      <div className="flex min-h-0 flex-col gap-2.5">
        <div className="animate-rise-in flex shrink-0 items-center justify-between gap-2 rounded-lg border border-violet-500/25 bg-violet-500/5 px-2.5 py-2">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-violet-300">
              Additive explanation · f(x) = f(base) + Σφ
            </p>
            <p className="mt-0.5 font-mono text-[13px] font-semibold text-slate-100 2xl:text-sm">
              f(base) {base.toFixed(1)} → f(x) {current.toFixed(1)}
              <span className="text-[10px] text-slate-500"> mm/s</span>
            </p>
          </div>
          <div className="text-right">
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
              Σ|φ|
            </p>
            <p className="font-mono text-[13px] font-semibold tabular-nums text-slate-100 2xl:text-sm">
              {total.toFixed(1)}
              <span className="text-[10px] text-slate-500"> mm/s</span>
            </p>
          </div>
        </div>

        <ol className="flex min-h-0 flex-1 flex-col justify-between gap-2">
          {drivers.map((driver, index) => (
            <DriverRow
              key={driver.key}
              driver={driver}
              rank={index + 1}
              delay={index * 60}
            />
          ))}
        </ol>

        {damperActive ? (
          <div className="animate-rise-in flex items-start gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-2.5 py-2">
            <Wind className="mt-0.5 size-3 shrink-0 text-red-400" aria-hidden="true" />
            <p className="text-[10px] leading-relaxed text-red-200">
              The damper is a context switch, not a regression feature, so it is
              attributed outside the four drivers: open it and this case predicts{" "}
              <span className="font-mono font-semibold">
                {openDamper.toFixed(1)} mm/s
              </span>
              , closed{" "}
              <span className="font-mono font-semibold">
                {current.toFixed(1)} mm/s
              </span>{" "}
              — a{" "}
              <span className="font-mono font-semibold">
                {signed(delta, 1)} mm/s
              </span>{" "}
              suppression from convective O₂ starvation alone. Heuristic only: the PSI
              target set has no airflow-dependent measured spread targets, so the
              suppressed rate is not experimentally validated.
            </p>
          </div>
        ) : null}
      </div>

      <div className="flex min-h-0 flex-col gap-2.5">
        <SubCard
          className="animate-rise-in flex flex-1 flex-col justify-between gap-2 p-2.5"
          interactive
        >
          <div className="flex items-center gap-1.5">
            <FlaskConical className="size-3 text-cyan-400" aria-hidden="true" />
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
              Similar NASA campaigns
            </p>
          </div>
          <ul className="flex flex-col gap-1.5">
            {similarExperiments.slice(0, 3).map((experiment) => (
              <SimilarExperimentRow
                key={experiment.tag}
                name={experiment.name}
                tag={experiment.tag}
                match={experiment.match}
              />
            ))}
          </ul>
          <p className="font-mono text-[10px] leading-relaxed text-slate-400 2xl:text-[11px]">
            Ranked by weighted distance across the same four-feature space that sets
            the importance shares, measured against each campaign&apos;s published
            conditions. 100 % means the active case sits exactly on that campaign.
          </p>
        </SubCard>

        <SubCard
          className="animate-rise-in flex flex-1 flex-col justify-between gap-2 p-2.5"
          interactive
        >
          <div className="flex items-center gap-1.5">
            <Library className="size-3 text-violet-400" aria-hidden="true" />
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
              Model vs registry mean
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {registryVsModel.map((row) => (
              <ComparisonCell key={row.label} row={row} />
            ))}
          </div>
          <p className="font-mono text-[10px] leading-relaxed text-slate-400 2xl:text-[11px]">
            Registry column is the real campaign mean from the PSI record at 21 % O₂ /
            101.3 kPa in still air; model column is the active case. This is a
            nominal-vs-active delta, <em>not</em> a validation residual — the two only
            coincide at the calibration case.
          </p>
        </SubCard>

        <SubCard
          className="animate-rise-in flex flex-1 flex-col justify-between gap-2 p-2.5"
          interactive
        >
          <div className="flex items-start gap-2">
            <BrainCircuit
              className="mt-0.5 size-3 shrink-0 text-violet-400"
              aria-hidden="true"
            />
            <p className="text-[10px] leading-relaxed text-slate-400 2xl:text-[11px]">
              {atBaseline
                ? `Sample sits at the calibration point, so every additive term is zero while global importance still ranks ${topDriver.label.toLowerCase()} first at ${topDriver.impactPct} %.`
                : `Prediction moved ${signed(shift, 1)} mm/s from the calibration point across the four features. ${topDriver.label} is the largest global driver at ${topDriver.impactPct} % of total attribution.`}
              {damperActive
                ? ` The closed damper removes a further ${Math.abs(damperDelta).toFixed(1)} mm/s.`
                : ""}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-800 pt-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-400">
            <span>{modelLabel}</span>
            <span className="text-slate-600">|</span>
            <span>Exact additive · ordered ablation</span>
            <span className="text-slate-600">|</span>
            <span>Shares sum 100 %</span>
          </div>
        </SubCard>
      </div>
    </div>
  );
}