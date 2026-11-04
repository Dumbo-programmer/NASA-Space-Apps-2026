"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BrainCircuit,
  ExternalLink,
  Flame,
  Info,
  ShieldAlert,
  Siren,
  Table2,
  Timer,
  X,
} from "lucide-react";
import { MissionHeader } from "@/components/MissionHeader";
import { MicrogravityFlameCanvas } from "@/components/MicrogravityFlameCanvas";
import { TelemetryCards } from "@/components/TelemetryCards";
import { MaterialRiskScoreboard } from "@/components/MaterialRiskScoreboard";
import { ShapExplainability } from "@/components/ShapExplainability";
import { MitigationProtocols } from "@/components/MitigationProtocols";
import { ScenarioControls } from "@/components/ScenarioControls";
import { TabBar, type TabKey } from "@/components/TabBar";
import { PanelFrame, Pill } from "@/components/PanelFrame";
import { RiskMatrix } from "@/components/RiskMatrix";
import { getMaterial } from "@/lib/materials";
import { getExperiment } from "@/lib/experiments";
import { buildMitigationPlan } from "@/lib/protocols";
import { explainPrediction } from "@/lib/shap";
import {
  NOMINAL_ENVIRONMENT,
  REFERENCE_ENVIRONMENT,
  assessMission,
  predictTelemetry,
} from "@/lib/telemetry";
import { isReferenceGeometry } from "@/lib/geometry";
import type {
  EnvironmentState,
  ExperimentKey,
  GeometryState,
  MaterialKey,
  SimulationState,
} from "@/lib/types";

const READINESS_STYLE = {
  GO: { tone: "emerald", label: "GO · flame out" },
  CAUTION: { tone: "amber", label: "CAUTION · crew standby" },
  ABORT: { tone: "red", label: "ABORT · burn threat" },
} as const;

export default function MissionControlPage() {
  const [environment, setEnvironment] = useState<EnvironmentState>(
    NOMINAL_ENVIRONMENT,
  );
  const [simulation, setSimulation] = useState<SimulationState>({
    isVentilationCut: false,
  });
  const [tab, setTab] = useState<TabKey>("simulation");
  const [controlsOpen, setControlsOpen] = useState(false);

  useEffect(() => {
    if (!controlsOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setControlsOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [controlsOpen]);

  const handleEnvironmentChange = useCallback(
    (patch: Partial<EnvironmentState>) => {
      setEnvironment((current) => ({ ...current, ...patch }));
    },
    [],
  );

  const handleGeometryChange = useCallback(
    (patch: Partial<GeometryState>) => {
      setEnvironment((current) => ({
        ...current,
        geometry: { ...current.geometry, ...patch },
      }));
    },
    [],
  );

  const handleSelectMaterial = useCallback((material: MaterialKey) => {
    setEnvironment((current) => ({ ...current, material }));
  }, []);

  const handleSelectExperiment = useCallback((key: ExperimentKey) => {
    const preset = getExperiment(key);
    setEnvironment((current) => ({
      ...current,
      experiment: key,
      material: preset.material,
      oxygenPct: preset.oxygenPct,
      pressureKpa: preset.pressureKpa,
      airflowCms: preset.airflowCms,
      geometry: { ...preset.geometry },
    }));
  }, []);

  const handleToggleVentilation = useCallback(() => {
    setSimulation((current) => ({ isVentilationCut: !current.isVentilationCut }));
  }, []);

  const telemetry = useMemo(
    () => predictTelemetry(environment, simulation.isVentilationCut),
    [environment, simulation.isVentilationCut],
  );

  const explanation = useMemo(
    () => explainPrediction(environment, telemetry, simulation.isVentilationCut),
    [environment, telemetry, simulation.isVentilationCut],
  );

  const mitigation = useMemo(
    () =>
      buildMitigationPlan(environment, telemetry, simulation.isVentilationCut),
    [environment, telemetry, simulation.isVentilationCut],
  );

  const material = getMaterial(environment.material);
  const experiment = getExperiment(environment.experiment);
  const readiness = assessMission(telemetry, simulation.isVentilationCut);
  const readinessStyle = READINESS_STYLE[readiness];
  const isBaseline =
    environment.oxygenPct === REFERENCE_ENVIRONMENT.oxygenPct &&
    environment.pressureKpa === REFERENCE_ENVIRONMENT.pressureKpa &&
    environment.airflowCms === REFERENCE_ENVIRONMENT.airflowCms &&
    environment.material === REFERENCE_ENVIRONMENT.material &&
    isReferenceGeometry(environment.geometry) &&
    !simulation.isVentilationCut;

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-slate-950">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_-10%,rgba(249,115,22,0.13),transparent_55%),radial-gradient(ellipse_at_85%_10%,rgba(34,211,238,0.09),transparent_50%)]"
        aria-hidden="true"
      />
      <div className="grid-texture pointer-events-none absolute inset-0" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-0 shadow-[inset_0_0_180px_rgba(0,0,0,0.65)]" aria-hidden="true" />

      <div className="relative flex min-h-0 flex-1 flex-col">
        <MissionHeader
          environment={environment}
          simulation={simulation}
          onToggleVentilation={handleToggleVentilation}
        />

        <TabBar
          activeTab={tab}
          onTabChange={setTab}
          onOpenControls={() => setControlsOpen((open) => !open)}
          controlsOpen={controlsOpen}
          controlsId="scenario-drawer"
        />

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-[286px] shrink-0 overflow-y-auto border-r border-slate-800/80 bg-slate-950/30 p-3 backdrop-blur-sm xl:block 2xl:w-[320px]">
          <ScenarioControls
            idPrefix="rail"
            environment={environment}
            onEnvironmentChange={handleEnvironmentChange}
            onGeometryChange={handleGeometryChange}
            onSelectExperiment={handleSelectExperiment}
          />
        </aside>

        {controlsOpen ? (
          <div className="fixed inset-0 z-50 flex xl:hidden">
            <button
              type="button"
              aria-label="Close scenario controls"
              onClick={() => setControlsOpen(false)}
              className="animate-fade-in absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
            />
            <div
              id="scenario-drawer"
              role="dialog"
              aria-modal="true"
              aria-label="Scenario controls"
              className="animate-drop-in relative ml-auto flex h-full w-[300px] max-w-[86vw] flex-col border-l border-slate-800 bg-slate-950 shadow-2xl"
            >
              <div className="flex shrink-0 items-center justify-between border-b border-slate-800 px-3 py-2">
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
                  Scenario controls
                </p>
                <button
                  type="button"
                  onClick={() => setControlsOpen(false)}
                  aria-label="Close scenario controls"
                  className="rounded-md border border-slate-700 p-1 text-slate-400 transition-colors hover:border-slate-600 hover:text-slate-200"
                >
                  <X className="size-3.5" aria-hidden="true" />
                </button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto p-3">
                <ScenarioControls
                  idPrefix="drawer"
                  environment={environment}
                  onEnvironmentChange={handleEnvironmentChange}
                  onGeometryChange={handleGeometryChange}
                  onSelectExperiment={handleSelectExperiment}
                />
              </div>
            </div>
          </div>
        ) : null}

        <main className="flex min-w-0 flex-1 flex-col gap-2.5 p-2.5 sm:p-3">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800/80 bg-slate-900/50 px-3 py-1.5 shadow-sm ring-1 ring-white/[0.02]">
            <div className="flex flex-wrap items-center gap-1.5">
              <span role="status" aria-live="polite">
                <Pill
                  tone={readinessStyle.tone}
                  className={
                    readiness === "ABORT"
                      ? "animate-pulse shadow-[0_0_14px_rgba(239,68,68,0.45)]"
                      : readiness === "CAUTION"
                        ? "shadow-[0_0_12px_rgba(251,191,36,0.28)]"
                        : ""
                  }
                >
                  {readinessStyle.label}
                </Pill>
              </span>
              <Pill tone="cyan">{material.sourceTag}</Pill>
              <Pill tone="violet">{telemetry.confidenceBand} confidence</Pill>
              {simulation.isVentilationCut ? (
                <Pill tone="red">damper closed</Pill>
              ) : null}
              <span className="font-mono text-[10px] uppercase tracking-wider text-slate-400">
                {experiment.campaign} · {material.name} ·{" "}
                {environment.oxygenPct.toFixed(1)} % O₂ ·{" "}
                {environment.pressureKpa.toFixed(1)} kPa ·{" "}
                {telemetry.effectiveAirflowCms.toFixed(1)} cm/s
              </span>
            </div>
            <span
              className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                isBaseline
                  ? "text-slate-400"
                  : "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/25"
              }`}
            >
              {isBaseline
                ? "BASS-II calibration case"
                : "Off-baseline simulation"}
            </span>
          </div>

          <div
            key={tab}
            role="tabpanel"
            id={`panel-${tab}`}
            aria-labelledby={`tab-${tab}`}
            tabIndex={0}
            className="animate-fade-in grid min-h-0 flex-1 auto-rows-fr grid-cols-1 gap-2.5 overflow-y-auto xl:auto-rows-auto xl:grid-cols-12 xl:overflow-hidden"
          >
            {tab === "simulation" ? (
              <>
                <PanelFrame
                  index="P1"
                  title="Microgravity Flame Visualizer"
                  subtitle="Canvas rAF loop · 190-particle envelope · model-driven"
                  icon={Flame}
                  accent="orange"
                  className="min-h-0 xl:col-span-7"
                  bodyClassName="min-h-0 overflow-hidden"
                  actions={
                    <Pill tone={simulation.isVentilationCut ? "red" : "emerald"}>
                      {simulation.isVentilationCut ? "Damper closed" : "Damper open"}
                    </Pill>
                  }
                >
                  <MicrogravityFlameCanvas
                    flameLength={telemetry.flameLength}
                    sootPoint={telemetry.sootPoint}
                    smokeYield={telemetry.smokeYield}
                    oxygenPct={environment.oxygenPct}
                    pressureKpa={environment.pressureKpa}
                    airflowCms={environment.airflowCms}
                    heatReleaseW={telemetry.heatReleaseW}
                    flameTempK={telemetry.flameTempK}
                    extinctionProb={telemetry.extinctionProb}
                    materialName={material.name}
                    isVentilationCut={simulation.isVentilationCut}
                    geometry={environment.geometry}
                  />
                </PanelFrame>

                <PanelFrame
                  index="P2"
                  title="Required Metric Telemetry"
                  subtitle="Five PSI-traceable readouts · surrogate inference"
                  icon={Timer}
                  accent="cyan"
                  className="min-h-0 xl:col-span-5"
                  bodyClassName="min-h-0 overflow-hidden"
                  actions={
                    <Pill tone={telemetry.inDomain ? "emerald" : "red"}>
                      {telemetry.inDomain ? "In-domain" : "Out-of-domain"}
                    </Pill>
                  }
                >
                  <TelemetryCards
                    telemetry={telemetry}
                    materialName={material.name}
                    oxygenPct={environment.oxygenPct}
                  />
                </PanelFrame>
              </>
            ) : null}

            {tab === "risk" ? (
              <>
                <PanelFrame
                  index="P3"
                  title="Material Flammability Risk Scoreboard"
                  subtitle="Traceable registry · sortable · active specimen highlighted"
                  icon={Table2}
                  accent="amber"
                  className="min-h-0 xl:col-span-7"
                  bodyClassName="min-h-0 overflow-hidden"
                >
                  <MaterialRiskScoreboard
                    selectedMaterial={environment.material}
                    onSelectMaterial={handleSelectMaterial}
                  />
                </PanelFrame>

                <div className="grid min-h-0 auto-rows-fr grid-cols-1 gap-2.5 xl:col-span-5 xl:auto-rows-auto xl:grid-rows-2">
                  <PanelFrame
                    index="P3b"
                    title="Risk Matrix"
                    subtitle="Likelihood vs consequence"
                    icon={ShieldAlert}
                    accent="amber"
                    className="min-h-0"
                    bodyClassName="min-h-0 overflow-y-auto"
                  >
                    <RiskMatrix telemetry={telemetry} />
                  </PanelFrame>
                  <PanelFrame
                    index="P3c"
                    title="Specimen Engineering Note"
                    subtitle="Registry note for the active fuel"
                    icon={Info}
                    accent="cyan"
                    className="min-h-0"
                    bodyClassName="min-h-0 overflow-y-auto"
                  >
                    <div className="flex h-full flex-col justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-100">
                          {material.name}
                        </p>
                        <p className="mt-1 text-xs leading-relaxed text-slate-400">
                          {material.note}
                        </p>
                      </div>
                      <dl className="grid grid-cols-2 gap-2">
                        {[
                          ["Spread rate", `${material.flameSpreadRate.toFixed(0)} mm/s`],
                          ["Extinction limit", `${material.minExtinctionO2.toFixed(1)} % O₂`],
                          ["Smoke yield", `${material.smokeYield.toFixed(0)} mg/min`],
                          ["Peak flame T", `${material.flameTempK} K`],
                          ["Pyrolysis heat", `×${material.pyrolysisHeat.toFixed(2)}`],
                          ["Fuel load", `×${material.fuelLoad.toFixed(2)}`],
                        ].map(([label, value]) => (
                          <div
                            key={label}
                            className="rounded-md border border-slate-800 bg-slate-950/50 px-2 py-1.5"
                          >
                            <dt className="text-[10px] uppercase tracking-wider text-slate-400">
                              {label}
                            </dt>
                            <dd className="font-mono text-xs font-semibold text-slate-200">
                              {value}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  </PanelFrame>
                </div>
              </>
            ) : null}

            {tab === "explain" ? (
              <PanelFrame
                index="P4"
                title="AI SHAP Explainability"
                subtitle="Feature contribution drivers · exact additive attribution"
                icon={BrainCircuit}
                accent="violet"
                className="min-h-0 xl:col-span-12"
                bodyClassName="min-h-0 overflow-hidden"
                actions={<Pill tone="violet">{explanation.modelLabel}</Pill>}
              >
                <ShapExplainability explanation={explanation} />
              </PanelFrame>
            ) : null}

            {tab === "protocols" ? (
              <PanelFrame
                index="P5"
                title="Mission Fire Mitigation Protocols"
                subtitle="Actionable crew directives generated from the active case"
                icon={ShieldAlert}
                accent="emerald"
                className="min-h-0 xl:col-span-12"
                bodyClassName="min-h-0 overflow-hidden"
                actions={<Pill tone="red">Crew-facing · advisory only</Pill>}
              >
                <MitigationProtocols
                  airflow={mitigation.airflow}
                  suppressant={mitigation.suppressant}
                  smoke={mitigation.smoke}
                />
              </PanelFrame>
            ) : null}
          </div>
        </main>
      </div>

        <footer className="shrink-0 border-t border-slate-800/80 bg-slate-950/70 backdrop-blur-sm">
          <div className="mx-auto flex w-full max-w-[1800px] flex-wrap items-center justify-between gap-2 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-400 sm:px-4">
            <p>
              Agnishikha · AstraFlame · NASA Space Apps build · surrogate inference
              runs client-side against the offline PSI training envelope
            </p>
            <a
              href="https://psi.nasa.gov"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded px-1 py-0.5 text-cyan-400/80 transition-colors hover:bg-cyan-500/10 hover:text-cyan-300"
            >
              <Siren className="size-2.5" aria-hidden="true" />
              Primary sources: psi.nasa.gov
              <ExternalLink className="size-2.5" aria-hidden="true" />
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}