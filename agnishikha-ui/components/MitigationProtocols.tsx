"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Fan, Snowflake, TriangleAlert, Waves, Wind } from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { Pill, SubCard } from "./PanelFrame";
import type {
  AirflowProtocol,
  ProtocolSeverity,
  SmokeProtocol,
  SuppressantProtocol,
} from "@/lib/protocols";

export interface MitigationProtocolsProps {
  airflow: AirflowProtocol;
  suppressant: SuppressantProtocol;
  smoke: SmokeProtocol;
}

const SEVERITY_TONE: Record<ProtocolSeverity, "emerald" | "amber" | "red"> = {
  info: "emerald",
  caution: "amber",
  critical: "red",
};

const SEVERITY_LABEL: Record<ProtocolSeverity, string> = {
  info: "Advisory",
  caution: "Caution",
  critical: "Critical",
};

const SEVERITY_BORDER: Record<ProtocolSeverity, string> = {
  info: "border-slate-800",
  caution: "border-amber-500/40",
  critical: "border-red-500/50 shadow-[0_0_28px_rgba(239,68,68,0.12)]",
};

interface ProtocolCardShellProps {
  icon: LucideIcon;
  step: string;
  protocol: AirflowProtocol | SuppressantProtocol | SmokeProtocol;
  iconClassName: string;
  /** Extra badge in the header, e.g. the smoke transport regime. */
  regime?: string;
  /** Stagger for the entrance animation, in milliseconds. */
  delay?: number;
  children: ReactNode;
}

function Readout({
  label,
  value,
  unit,
  tone = "default",
}: {
  label: string;
  value: number;
  unit: string;
  tone?: "default" | "accent";
}) {
  const animated = useAnimatedNumber(value, value % 1 === 0 ? 0 : 1);
  return (
    <SubCard className="px-2 py-1.5">
      <p className="text-[10px] font-medium uppercase leading-tight tracking-wider text-slate-400 2xl:text-[11px]">
        {label}
      </p>
      <p
        className={`font-mono text-sm font-bold tabular-nums 2xl:text-base ${
          tone === "accent" ? "text-cyan-300" : "text-slate-100"
        }`}
      >
        {animated.toFixed(value % 1 === 0 ? 0 : 1)}
        <span className="ml-0.5 text-[10px] font-normal text-slate-400 2xl:text-[11px]">{unit}</span>
      </p>
    </SubCard>
  );
}

function ActionSteps({ steps }: { steps: string[] }) {
  return (
    <ol className="flex min-h-0 flex-1 flex-col justify-between gap-1.5 overflow-y-auto border-t border-slate-800 pt-2">
      {steps.map((step, index) => (
        <li key={`${index}-${step}`} className="flex items-start gap-2">
          <span className="mt-px flex size-4 shrink-0 items-center justify-center rounded bg-slate-800 font-mono text-[9px] font-bold text-slate-300">
            {index + 1}
          </span>
          <span className="text-[11px] leading-snug text-slate-300 2xl:text-[12px]">{step}</span>
        </li>
      ))}
    </ol>
  );
}

function ProtocolCardShell({
  icon: Icon,
  step,
  protocol,
  iconClassName,
  regime,
  delay = 0,
  children,
}: ProtocolCardShellProps) {
  const severity = protocol.severity;
  return (
    <article
      className={`animate-rise-in flex min-h-0 flex-col gap-2 rounded-lg border bg-slate-900/50 p-2.5 transition-colors duration-300 ${SEVERITY_BORDER[severity]}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <header className="flex shrink-0 items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-2">
          <span
            className={`flex size-6 shrink-0 items-center justify-center rounded ring-1 ring-slate-700 ${iconClassName}`}
          >
            <Icon className="size-3" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
              Protocol {step}
            </p>
            <h3 className="truncate text-[12px] font-semibold text-slate-100 2xl:text-[13px]">
              {protocol.title}
            </h3>
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-0.5">
          {regime ? <Pill tone="violet">{regime}</Pill> : null}
          <Pill tone={SEVERITY_TONE[severity]}>
            {severity === "critical" ? (
              <TriangleAlert className="size-2.5 animate-pulse" aria-hidden="true" />
            ) : null}
            {SEVERITY_LABEL[severity]}
          </Pill>
        </div>
      </header>

      <p className="shrink-0 rounded border border-slate-800 bg-slate-950/60 px-2 py-1.5 font-mono text-[11px] font-semibold uppercase leading-relaxed tracking-wide text-slate-200 2xl:text-[12px]">
        {protocol.directive}
      </p>

      {children}
    </article>
  );
}

export function MitigationProtocols({
  airflow,
  suppressant,
  smoke,
}: MitigationProtocolsProps) {
  const residenceMinutes = smoke.residenceSeconds / 60;

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-2.5 lg:grid-cols-3">
      <ProtocolCardShell
        icon={Fan}
        step="01"
        protocol={airflow}
        iconClassName="bg-violet-500/10 text-violet-300"
      >
        <div className="grid grid-cols-2 gap-2">
          <Readout label="Commanded" value={airflow.currentCms} unit="cm/s" />
          <Readout
            label="Recommended ceiling"
            value={airflow.recommendedCms}
            unit="cm/s"
            tone="accent"
          />
        </div>
        <p className="text-[10px] leading-snug text-slate-400 2xl:text-[11px]">{airflow.detail}</p>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-slate-800 pt-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-400">
          <Wind className="size-3 text-violet-400" aria-hidden="true" />
          <span>Fan reduction {airflow.reductionPct} %</span>
          <span className="text-slate-600">|</span>
          <span>Envelope decay ≈ {airflow.decaySeconds} s</span>
        </div>
        <ActionSteps steps={airflow.steps} />
      </ProtocolCardShell>

      <ProtocolCardShell
        icon={Snowflake}
        step="02"
        protocol={suppressant}
        iconClassName="bg-cyan-500/10 text-cyan-300"
        delay={70}
      >
        <div className="grid grid-cols-2 gap-2">
          <Readout
            label="O₂ target / LOI"
            value={suppressant.targetO2Pct}
            unit="%"
            tone="accent"
          />
          <Readout
            label="N₂ mass budget"
            value={suppressant.n2MassKg}
            unit="kg"
          />
        </div>
        <p className="text-[10px] leading-snug text-slate-400 2xl:text-[11px]">{suppressant.detail}</p>
        {suppressant.crewFloorBreach ? (
          <p className="flex items-start gap-1.5 rounded border border-red-500/40 bg-red-500/10 px-2 py-1.5 font-mono text-[10px] leading-tight text-red-200">
            <TriangleAlert className="mt-px size-3 shrink-0" aria-hidden="true" />
            Target O₂ is below the crew egress floor — continuous oxygen masks required
            for the burn window.
          </p>
        ) : null}
        <dl className="flex flex-col gap-1 border-t border-slate-800 pt-1.5">
          {suppressant.options.map((option) => (
            <div key={option.label} className="flex items-center justify-between gap-2">
              <dt className="truncate text-[10px] text-slate-400">{option.label}</dt>
              <dd className="shrink-0 font-mono text-[10px] font-semibold text-slate-200">
                {option.value}
              </dd>
            </div>
          ))}
        </dl>
        <ActionSteps steps={suppressant.steps} />
      </ProtocolCardShell>

      <ProtocolCardShell
        icon={Waves}
        step="03"
        protocol={smoke}
        iconClassName="bg-amber-500/10 text-amber-300"
        regime={smoke.regime}
        delay={140}
      >
        <div className="grid grid-cols-2 gap-2">
          <Readout
            label="Residence time"
            value={residenceMinutes}
            unit="min"
          />
          <Readout
            label="Suspended soot"
            value={smoke.suspendedMassMg}
            unit="mg"
          />
        </div>
        <p className="text-[10px] leading-snug text-slate-400 2xl:text-[11px]">{smoke.detail}</p>
        <ul className="flex flex-col gap-1 border-t border-slate-800 pt-1.5">
          {smoke.wakeZones.map((zone) => (
            <li
              key={zone}
              className="flex items-start gap-2 font-mono text-[10px] leading-tight text-slate-400"
            >
              <span className="mt-1 size-1 shrink-0 rounded-full bg-amber-400" />
              {zone}
            </li>
          ))}
        </ul>
        <ActionSteps steps={smoke.steps} />
      </ProtocolCardShell>
    </div>
  );
}