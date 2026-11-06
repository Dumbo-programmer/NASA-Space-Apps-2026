"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Info, ShieldAlert } from "lucide-react";
import { Pill, SubCard } from "@/components/PanelFrame";
import {
  API_URL,
  loadCatalog,
  predictLive,
  predictPrecomputed,
  testedRange,
  type InputSpec,
  type Inputs,
  type Mode,
  type ModelCard,
  type Prediction,
} from "@/lib/ignisApi";

/** One view per NASA investigation. FLEX shows its two models side by side on the same inputs. */
const VIEWS = [
  {
    key: "flex",
    label: "FLEX droplet fire",
    models: ["flex_extinction", "flex_burning_rate"],
    data: "ISS droplet combustion, PSI-69",
  },
  {
    key: "bass2",
    label: "BASS-II flame spread",
    models: ["bass2_flame_spread"],
    data: "ISS flame spread over PMMA rods, PSI-25",
  },
  {
    key: "spice",
    label: "SPICE smoke point",
    models: ["spice_smoke_point"],
    data: "ISS laminar jet flames, PSI-107",
  },
  {
    key: "same",
    label: "SAME smoke particles",
    models: ["same_particle_size"],
    data: "ISS smoke aerosol, PSI-101/102",
  },
] as const;

type ViewKey = (typeof VIEWS)[number]["key"];

const fmt = (v: number, digits = 3) =>
  Math.abs(v) >= 100 ? v.toFixed(1) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(digits);

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function sliderBounds(range: [number, number] | null, fallback: number) {
  if (!range) return { min: 0, max: Math.max(1, fallback * 2), step: 0.01 };
  const [lo, hi] = range;
  const span = hi - lo || Math.max(Math.abs(hi), 1);
  const min = Math.max(0, lo - 0.15 * span);
  const max = hi + 0.15 * span;
  return { min, max, step: (max - min) / 200 };
}

export function NasaModelPanel() {
  const [mode, setMode] = useState<Mode | null>(null);
  const [cards, setCards] = useState<Record<string, ModelCard>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [view, setView] = useState<ViewKey>("flex");
  const [inputs, setInputs] = useState<Record<ViewKey, Inputs>>({
    flex: {},
    bass2: {},
    spice: {},
    same: {},
  });
  const [changed, setChanged] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, Prediction>>({});
  const [requestError, setRequestError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [explainModel, setExplainModel] = useState<string>("flex_extinction");
  const abortRef = useRef<AbortController | null>(null);

  // ---- catalog: live API first, precomputed files otherwise ----
  useEffect(() => {
    let alive = true;
    loadCatalog()
      .then(({ mode: m, models }) => {
        if (!alive) return;
        const byName: Record<string, ModelCard> = {};
        for (const c of models) byName[c.name] = c;
        const start = {} as Record<ViewKey, Inputs>;
        for (const v of VIEWS) {
          const first = byName[v.models[0]];
          start[v.key] = first
            ? Object.fromEntries(first.inputs.map((i) => [i.name, i.default]))
            : {};
        }
        setCards(byName);
        setInputs(start);
        setMode(m);
      })
      .catch(() => {
        if (alive) setLoadError("Model service and precomputed answers are both unavailable.");
      });
    return () => {
      alive = false;
    };
  }, []);

  const activeView = VIEWS.find((v) => v.key === view) ?? VIEWS[0];
  const primary = cards[activeView.models[0]];
  const current = inputs[view];

  // ---- predictions: debounced, stale requests cancelled ----
  useEffect(() => {
    if (!mode || !primary || Object.keys(current).length === 0) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const timer = setTimeout(async () => {
      setBusy(true);
      try {
        const answers = await Promise.all(
          activeView.models.map((m) =>
            mode === "live"
              ? predictLive(m, current, controller.signal)
              : predictPrecomputed(cards[m], current, changed),
          ),
        );
        if (controller.signal.aborted) return;
        setResults((prev) => {
          const next = { ...prev };
          activeView.models.forEach((m, i) => {
            next[m] = answers[i];
          });
          return next;
        });
        setRequestError(null);
      } catch (e) {
        if (!controller.signal.aborted) {
          setRequestError(e instanceof Error ? e.message : "Prediction failed");
        }
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    }, mode === "live" ? 180 : 0);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [mode, primary, current, changed, activeView, cards]);

  const setInput = (spec: InputSpec, value: string | number) => {
    setChanged(spec.type === "number" ? spec.name : null);
    setInputs((prev) => {
      const base =
        mode === "precomputed"
          ? // precomputed answers move one input at a time from the NASA reference point
            Object.fromEntries(primary.inputs.map((i) => [i.name, i.default]))
          : prev[view];
      const keepCategories =
        mode === "precomputed"
          ? Object.fromEntries(
              primary.inputs.filter((i) => i.type === "category").map((i) => [i.name, prev[view][i.name]]),
            )
          : {};
      return { ...prev, [view]: { ...base, ...keepCategories, [spec.name]: value } };
    });
  };

  const shownModel = activeView.models.includes(explainModel as never)
    ? explainModel
    : activeView.models[0];
  const explained = results[shownModel];
  const viewResults = activeView.models.map((m) => results[m]).filter(Boolean);
  const outOfDomain = viewResults.some((r) => !r.in_domain);
  const warnings = Array.from(new Set(viewResults.flatMap((r) => r.warnings)));

  if (loadError) {
    return (
      <SubCard className="p-4 text-[12px] text-red-300">
        {loadError} Start it with <code className="font-mono">python api/server.py</code>.
      </SubCard>
    );
  }
  if (!mode || !primary) {
    return <p className="p-4 font-mono text-[11px] text-slate-400">Loading NASA-trained models…</p>;
  }

  return (
    <div className="grid h-full min-h-0 gap-3 overflow-y-auto lg:grid-cols-12">
      {/* ---------- inputs ---------- */}
      <div className="flex min-h-0 flex-col gap-3 lg:col-span-4">
        <div className="flex flex-wrap items-center gap-1.5">
          {mode === "live" ? (
            <Pill tone="emerald">Live · Python API</Pill>
          ) : (
            <Pill tone="amber">Precomputed · same trained models</Pill>
          )}
          {busy ? <Pill tone="slate">computing</Pill> : null}
        </div>

        <div role="tablist" aria-label="NASA investigation" className="grid grid-cols-2 gap-1.5">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              type="button"
              role="tab"
              aria-selected={v.key === view}
              onClick={() => {
                setView(v.key);
                setChanged(null);
              }}
              className={`rounded-md border px-2 py-1.5 text-left text-[11px] transition-colors ${
                v.key === view
                  ? "border-cyan-500/60 bg-cyan-500/10 text-cyan-200"
                  : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700"
              }`}
            >
              <span className="block font-semibold">{v.label}</span>
              <span className="block font-mono text-[9px] uppercase tracking-wider text-slate-500">
                {v.data}
              </span>
            </button>
          ))}
        </div>

        <SubCard className="flex flex-col gap-3 p-3">
          {primary.inputs.map((spec) => {
            const value = current[spec.name];
            if (spec.type === "category") {
              return (
                <label key={spec.name} className="flex flex-col gap-1 text-[11px] text-slate-300">
                  {spec.label}
                  <select
                    value={String(value)}
                    onChange={(e) => {
                      const opt = spec.options?.find((o) => String(o) === e.target.value);
                      setInput(spec, opt ?? e.target.value);
                    }}
                    className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[12px] text-slate-100"
                  >
                    {spec.options?.map((o) => (
                      <option key={String(o)} value={String(o)}>
                        {String(o)}
                        {spec.unit ? ` ${spec.unit}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              );
            }
            const range = testedRange(spec, primary, current);
            const v = Number(value);
            const { min, max, step } = sliderBounds(range, Number(spec.default));
            const outside = range ? v < range[0] - 1e-9 || v > range[1] + 1e-9 : false;
            const id = `nasa-${view}-${spec.name}`;
            return (
              <div key={spec.name} className="flex flex-col gap-1">
                <label htmlFor={id} className="flex items-baseline justify-between text-[11px] text-slate-300">
                  <span>{spec.label}</span>
                  <span className={`font-mono ${outside ? "text-amber-300" : "text-slate-100"}`}>
                    {fmt(v)} {spec.unit}
                  </span>
                </label>
                <input
                  id={id}
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={v}
                  onChange={(e) => setInput(spec, Number(e.target.value))}
                  aria-valuetext={`${fmt(v)} ${spec.unit ?? ""}`}
                  className="range-control w-full"
                />
                <p className={`font-mono text-[9px] uppercase tracking-wider ${outside ? "text-amber-300" : "text-slate-500"}`}>
                  {range ? `NASA tested ${fmt(range[0])}–${fmt(range[1])} ${spec.unit ?? ""}` : "tested range unknown"}
                  {outside ? " · outside tested range" : ""}
                </p>
              </div>
            );
          })}
          {mode === "precomputed" ? (
            <p className="flex gap-1.5 text-[10px] leading-snug text-slate-400">
              <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
              Offline answers move one input at a time from NASA reference conditions. Run the
              model API for free combinations ({API_URL}).
            </p>
          ) : null}
        </SubCard>
      </div>

      {/* ---------- answers ---------- */}
      <div className="flex min-h-0 flex-col gap-3 lg:col-span-4">
        {activeView.models.map((m) => {
          const r = results[m];
          const card = cards[m];
          if (!card) return null;
          return (
            <SubCard key={m} className="p-3">
              <p className="font-mono text-[9px] uppercase tracking-widest text-slate-500">{card.target}</p>
              {!r ? (
                <p className="mt-2 text-[12px] text-slate-400">…</p>
              ) : r.task === "classification" ? (
                <>
                  <p className="mt-1 font-mono text-3xl font-semibold text-slate-50">
                    {Math.round((r.probability ?? 0) * 100)}%
                  </p>
                  <div className="relative mt-2 h-2 rounded-full bg-slate-800" aria-hidden="true">
                    <div
                      className="h-2 rounded-full bg-cyan-400"
                      style={{ width: `${(r.probability ?? 0) * 100}%` }}
                    />
                    {r.base_rate !== undefined ? (
                      <span
                        className="absolute -top-1 h-4 w-px bg-slate-300"
                        style={{ left: `${r.base_rate * 100}%` }}
                      />
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-[11px] text-slate-300">{r.predicted_class}</p>
                  <p className="text-[10px] text-slate-500">
                    Tick = NASA base rate ({Math.round((r.base_rate ?? 0) * 100)}% of tests)
                  </p>
                </>
              ) : (
                <>
                  <p className="mt-1 font-mono text-3xl font-semibold text-slate-50">
                    {fmt(r.prediction ?? 0)}{" "}
                    <span className="text-base font-normal text-slate-400">{r.unit}</span>
                  </p>
                  {r.interval_90 ? (
                    <p className="mt-1 font-mono text-[11px] text-slate-300">
                      90% range {fmt(r.interval_90[0])} – {fmt(r.interval_90[1])} {r.unit}
                    </p>
                  ) : null}
                </>
              )}
              {r ? (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <Pill tone={r.in_domain ? "emerald" : "amber"}>
                    {r.in_domain ? "inside NASA-tested range" : "extrapolation"}
                  </Pill>
                  {activeView.models.length > 1 ? (
                    <button
                      type="button"
                      onClick={() => setExplainModel(m)}
                      aria-pressed={shownModel === m}
                      className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ring-1 ${
                        shownModel === m
                          ? "bg-violet-500/10 text-violet-200 ring-violet-500/40"
                          : "text-slate-400 ring-slate-700 hover:text-slate-200"
                      }`}
                    >
                      explain this
                    </button>
                  ) : null}
                </div>
              ) : null}
            </SubCard>
          );
        })}

        {requestError ? (
          <SubCard className="border-red-500/40 p-3 text-[11px] text-red-200">
            The model refused these inputs: {requestError}
          </SubCard>
        ) : null}

        {outOfDomain || warnings.length ? (
          <SubCard className="border-amber-500/40 p-3">
            <p className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-200">
              <ShieldAlert className="size-3.5" aria-hidden="true" />
              Outside what NASA tested: treat with caution
            </p>
            <ul className="mt-1 list-disc pl-4 text-[11px] text-amber-100/90">
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </SubCard>
        ) : null}

        {viewResults[0] ? (
          <p className="font-mono text-[9px] leading-relaxed text-slate-500">
            Evaluated at:{" "}
            {Object.entries(viewResults[0].inputs)
              .map(([k, val]) => `${k}=${typeof val === "number" ? fmt(val) : val}`)
              .join(" · ")}
          </p>
        ) : null}
      </div>

      {/* ---------- why + evidence ---------- */}
      <div className="flex min-h-0 flex-col gap-3 lg:col-span-4">
        <SubCard className="p-3">
          <p className="font-mono text-[9px] uppercase tracking-widest text-slate-500">
            Why this answer · exact Shapley values
          </p>
          <ShapleyBars result={explained} />
        </SubCard>
        <ModelEvidence card={cards[shownModel]} />
      </div>
    </div>
  );
}

function ShapleyBars({ result }: { result: Prediction | undefined }) {
  const rows = useMemo(() => {
    if (!result?.contributions) return [];
    return Object.entries(result.contributions).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  }, [result]);
  if (!result || rows.length === 0) {
    return <p className="mt-2 text-[11px] text-slate-400">No breakdown for this answer.</p>;
  }
  const isProb = result.task === "classification";
  const scale = Math.max(...rows.map(([, v]) => Math.abs(v)), 1e-12);
  const show = (v: number) => (isProb ? `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)} pts` : `${v >= 0 ? "+" : ""}${fmt(v)}`);
  return (
    <div className="mt-2 flex flex-col gap-1.5">
      {rows.map(([name, v]) => (
        <div key={name} className="grid grid-cols-[96px_1fr_64px] items-center gap-2 text-[11px]">
          <span className="truncate text-slate-300" title={name}>
            {name}
          </span>
          <div className="relative h-2.5 rounded bg-slate-800/70" aria-hidden="true">
            <span className="absolute inset-y-0 left-1/2 w-px bg-slate-600" />
            <span
              className={`absolute inset-y-0 rounded ${v >= 0 ? "left-1/2 bg-orange-400" : "right-1/2 bg-cyan-400"}`}
              style={{ width: `${(Math.abs(v) / scale) * 50}%` }}
            />
          </div>
          <span className="text-right font-mono text-slate-200">{show(v)}</span>
        </div>
      ))}
      <p className="mt-1 text-[10px] text-slate-500">
        Starts from the average answer ({isProb ? `${Math.round((result.base_value ?? 0) * 100)}%` : fmt(result.base_value ?? 0)}
        ); orange raises it, cyan lowers it, and the bars add up exactly to this answer.
      </p>
    </div>
  );
}

function metric(v: Record<string, unknown>, key: string, pct = false) {
  const x = num(v[key]);
  if (x === null) return null;
  return pct ? `${x.toFixed(1)}%` : x.toFixed(3);
}

function ci(v: Record<string, unknown>, key: string) {
  const c = v[key];
  if (Array.isArray(c) && c.length === 2 && num(c[0]) !== null && num(c[1]) !== null) {
    return ` (95% CI ${(c[0] as number).toFixed(2)}–${(c[1] as number).toFixed(2)})`;
  }
  return "";
}

function ModelEvidence({ card }: { card: ModelCard | undefined }) {
  if (!card) return null;
  const v = card.validation;
  const lines: string[] = [];
  if (card.task === "classification") {
    const auc = metric(v, "ROC_AUC");
    if (auc) lines.push(`ROC-AUC ${auc}${ci(v, "ROC_AUC_95CI")}`);
    const brier = metric(v, "Brier");
    const base = metric(v, "baseline_Brier");
    if (brier) lines.push(`Brier ${brier}${base ? ` vs ${base} always-guess-the-base-rate (lower is better)` : ""}`);
  } else {
    const r2 = metric(v, "R2");
    if (r2) lines.push(`R² ${r2}${ci(v, "R2_95CI")}`);
    const mae = metric(v, "MAE");
    if (mae) lines.push(`MAE ${mae} ${card.unit ?? ""}`);
    const cov = metric(v, "coverage90_pct", true);
    if (cov) lines.push(`90% range held the true value ${cov} of the time`);
  }
  return (
    <SubCard className="p-3 text-[11px] text-slate-300">
      <p className="font-mono text-[9px] uppercase tracking-widest text-slate-500">Model card</p>
      <p className="mt-1 font-semibold text-slate-100">{card.model}</p>
      <p className="text-slate-400">
        Trained on {card.training_rows} NASA runs from {card.training_groups} independent tests; scored
        only on whole tests it never saw.
      </p>
      <ul className="mt-1.5 list-disc pl-4 font-mono text-[10px] text-slate-200">
        {lines.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
      <p className="mt-1.5 text-[10px] text-slate-400">Valid for: {card.valid_for}</p>
      <p className="mt-1 flex items-start gap-1 text-[10px] text-cyan-300/90">
        <ExternalLink className="mt-0.5 size-2.5 shrink-0" aria-hidden="true" />
        {card.source}
      </p>
    </SubCard>
  );
}
