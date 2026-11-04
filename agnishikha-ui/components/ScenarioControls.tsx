"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Beaker,
  ChevronDown,
  Compass,
  Gauge,
  Ruler,
  Sliders,
  Thermometer,
  Wind,
} from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import {
  AIRFLOW_LIMIT,
  BURNER_DIAMETER_LIMIT,
  ORIENTATION_LIMIT,
  OXYGEN_LIMIT,
  PRESSURE_LIMIT,
  SAMPLE_THICKNESS_LIMIT,
  SAMPLE_WIDTH_LIMIT,
} from "@/lib/axes";
import { EXPERIMENTS, getExperiment } from "@/lib/experiments";
import { MATERIALS } from "@/lib/materials";
import { isReferenceGeometry } from "@/lib/geometry";
import type { AxisLimit } from "@/lib/axes";
import type {
  EnvironmentState,
  ExperimentKey,
  GeometryState,
  MaterialKey,
} from "@/lib/types";

export interface ScenarioControlsProps {
  /** Namespace for element ids - the rail and the mobile drawer both mount this. */
  idPrefix?: string;
  environment: EnvironmentState;
  onEnvironmentChange: (patch: Partial<EnvironmentState>) => void;
  onGeometryChange: (patch: Partial<GeometryState>) => void;
  onSelectExperiment: (key: ExperimentKey) => void;
}

function Group({
  icon: Icon,
  title,
  accent,
  children,
  note,
  delay = 0,
}: {
  icon: LucideIcon;
  title: string;
  accent: string;
  children: ReactNode;
  note?: string;
  delay?: number;
}) {
  return (
    <section
      className="animate-rise-in flex flex-col gap-2.5 rounded-xl border border-slate-800/80 bg-slate-900/40 p-3 transition-colors duration-300 hover:border-slate-700/80"
      style={{ animationDelay: `${delay}ms` }}
    >
      <header className="flex items-center gap-2">
        <span className={`flex size-6 items-center justify-center rounded-md ring-1 ${accent}`}>
          <Icon className="size-3.5" aria-hidden="true" />
        </span>
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
          {title}
        </h2>
      </header>
      {children}
      {note ? (
        <p className="font-mono text-[10px] leading-relaxed text-slate-400">{note}</p>
      ) : null}
    </section>
  );
}

function Slider({
  id,
  label,
  icon: Icon,
  axis,
  value,
  decimals = 1,
  accent,
  onChange,
}: {
  id: string;
  label: string;
  icon: LucideIcon;
  axis: AxisLimit;
  value: number;
  decimals?: number;
  accent: string;
  onChange: (value: number) => void;
}) {
  const animated = useAnimatedNumber(value, decimals);
  const offNominal = Math.abs(value - axis.nominal) > axis.step * 0.5;
  const fillPct = ((value - axis.min) / (axis.max - axis.min)) * 100;

  return (
    <div className="group">
      <div className="flex items-baseline justify-between gap-2">
        <label
          htmlFor={id}
          className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-400 transition-colors group-hover:text-slate-300"
        >
          <Icon className={`size-3 ${accent}`} aria-hidden="true" />
          {label}
        </label>
        <span className="font-mono text-xs font-semibold tabular-nums text-slate-100 transition-colors group-hover:text-white">
          {animated.toFixed(decimals)}
          <span className="ml-0.5 text-[10px] font-normal text-slate-400">
            {axis.unit}
          </span>
        </span>
      </div>
      <div className="relative mt-1.5">
        <input
          id={id}
          type="range"
          min={axis.min}
          max={axis.max}
          step={axis.step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          aria-valuetext={`${animated.toFixed(decimals)} ${axis.unit}`}
          className={`range-control h-1 w-full cursor-pointer rounded-full ${accent}`}
          style={{
            background: `linear-gradient(to right, currentColor 0%, currentColor ${fillPct}%, rgb(30 41 59) ${fillPct}%, rgb(30 41 59) 100%)`,
          }}
        />
        <span
          className="pointer-events-none absolute -top-0.5 h-2 w-px bg-slate-500"
          style={{
            left: `${((axis.nominal - axis.min) / (axis.max - axis.min)) * 100}%`,
          }}
          aria-hidden="true"
        />
      </div>
      <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-slate-400">
        <span>
          {axis.min}
          {axis.unit}
        </span>
        <span
          className={`transition-colors ${offNominal ? "text-amber-400" : "text-slate-500"}`}
        >
          {offNominal ? "off-nominal" : "nominal"}
        </span>
        <span>
          {axis.max}
          {axis.unit}
        </span>
      </div>
    </div>
  );
}

function Select<T extends string>({
  id,
  label,
  icon: Icon,
  accent,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  icon: LucideIcon;
  accent: string;
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="min-w-0">
      <label
        htmlFor={id}
        className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-400"
      >
        <Icon className={`size-3 ${accent}`} aria-hidden="true" />
        {label}
      </label>
      <div className="relative mt-1">
        <select
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value as T)}
          className="w-full cursor-pointer appearance-none rounded-md border border-slate-700 bg-slate-900 py-1.5 pl-2 pr-7 text-xs font-medium text-slate-100 outline-none transition-colors hover:border-slate-600 focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-2 top-1/2 size-3.5 -translate-y-1/2 text-slate-500"
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

export function ScenarioControls({
  idPrefix,
  environment,
  onEnvironmentChange,
  onGeometryChange,
  onSelectExperiment,
}: ScenarioControlsProps) {
  const { oxygenPct, pressureKpa, airflowCms, material, experiment, geometry } =
    environment;
  const preset = getExperiment(experiment);
  const geoNominal = isReferenceGeometry(geometry);
  const uid = idPrefix ? `${idPrefix}-` : "";

  return (
    <div className="flex flex-col gap-3">
      <Group
        icon={Compass}
        title="Experiment case"
        accent="ring-cyan-500/30 bg-cyan-500/10 text-cyan-300"
        note={preset?.notes}
      >
        <Select<ExperimentKey>
          id={`${uid}experiment`}
          label="NASA campaign"
          icon={Beaker}
          accent="text-cyan-400"
          value={experiment}
          options={EXPERIMENTS.map((item) => ({
            value: item.key,
            label: item.label,
          }))}
          onChange={onSelectExperiment}
        />
        <Select<MaterialKey>
          id={`${uid}material`}
          label="Fuel specimen"
          icon={Sliders}
          accent="text-amber-400"
          value={material}
          options={MATERIALS.map((record) => ({
            value: record.key,
            label: record.name,
          }))}
          onChange={(value) => onEnvironmentChange({ material: value })}
        />
        <div className="flex items-center justify-between font-mono text-[10px] text-slate-400">
          <span>{preset?.campaign}</span>
          <span className="text-amber-400">{preset?.sourceTag}</span>
        </div>
      </Group>

      <Group
        icon={Gauge}
        title="Cabin atmosphere"
        accent="ring-orange-500/30 bg-orange-500/10 text-orange-300"
        delay={70}
      >
        <Slider
          id={`${uid}oxygen`}
          label="O₂ concentration"
          icon={Gauge}
          axis={OXYGEN_LIMIT}
          value={oxygenPct}
          accent="text-orange-400"
          onChange={(value) => onEnvironmentChange({ oxygenPct: value })}
        />
        <Slider
          id={`${uid}pressure`}
          label="Ambient pressure"
          icon={Thermometer}
          axis={PRESSURE_LIMIT}
          value={pressureKpa}
          accent="text-cyan-400"
          onChange={(value) => onEnvironmentChange({ pressureKpa: value })}
        />
        <Slider
          id={`${uid}airflow`}
          label="Forced convection"
          icon={Wind}
          axis={AIRFLOW_LIMIT}
          value={airflowCms}
          decimals={1}
          accent="text-violet-400"
          onChange={(value) => onEnvironmentChange({ airflowCms: value })}
        />
      </Group>

      <Group
        icon={Ruler}
        title="Rig geometry"
        accent="ring-violet-500/30 bg-violet-500/10 text-violet-300"
        delay={140}
        note="Rig metadata. The surrogate seeds from material-level means, so geometry applies as an explicit operator scaling term pinned to 1.0 at the BASS-II reference."
      >
        <Slider
          id={`${uid}burner-diameter`}
          label="Burner diameter"
          icon={Ruler}
          axis={BURNER_DIAMETER_LIMIT}
          value={geometry.burnerDiameterMm}
          decimals={0}
          accent="text-violet-400"
          onChange={(value) => onGeometryChange({ burnerDiameterMm: value })}
        />
        <Slider
          id={`${uid}sample-width`}
          label="Sample width"
          icon={Ruler}
          axis={SAMPLE_WIDTH_LIMIT}
          value={geometry.sampleWidthMm}
          decimals={0}
          accent="text-violet-400"
          onChange={(value) => onGeometryChange({ sampleWidthMm: value })}
        />
        <Slider
          id={`${uid}sample-thickness`}
          label="Sample thickness"
          icon={Ruler}
          axis={SAMPLE_THICKNESS_LIMIT}
          value={geometry.sampleThicknessMm}
          accent="text-violet-400"
          onChange={(value) => onGeometryChange({ sampleThicknessMm: value })}
        />
        <Slider
          id={`${uid}orientation`}
          label="Orientation"
          icon={Compass}
          axis={ORIENTATION_LIMIT}
          value={geometry.orientationDeg}
          decimals={0}
          accent="text-violet-400"
          onChange={(value) => onGeometryChange({ orientationDeg: value })}
        />
        <div className="flex items-center justify-between font-mono text-[10px] text-slate-400">
          <span>geometry factor</span>
          <span className={geoNominal ? "text-emerald-400" : "text-amber-400"}>
            {geoNominal ? "1.000 · pinned" : "operator scaling"}
          </span>
        </div>
      </Group>
    </div>
  );
}