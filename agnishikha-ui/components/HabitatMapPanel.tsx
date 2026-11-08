"use client";

import { useEffect, useRef, useState } from "react";
import {
  loadHabitat,
  locateLive,
  readChamber,
  type HabitatMap,
  type LocateResult,
  type Mode,
} from "@/lib/ignisApi";

type Scenario = "iss" | "habitat" | "custom" | "chamber";
const W = 640;
const H = 400;

/** Habitat fire map: what NASA knows (dots), what the model says (heat), where we are, what to test next. */
export function HabitatMapPanel() {
  const [data, setData] = useState<{ mode: Mode; map: HabitatMap } | null>(null);
  const [scenario, setScenario] = useState<Scenario>("habitat");
  const [custom, setCustom] = useState({ o2: 27, p: 80 });
  const [chamber, setChamber] = useState<{ pressure_kpa: number; o2_pct: number } | null>(null);
  const [loc, setLoc] = useState<LocateResult | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    loadHabitat().then(setData).catch(() => setData(null));
  }, []);

  useEffect(() => {
    if (scenario !== "chamber") return;
    const tick = () => readChamber().then((c) => c && setChamber(c));
    tick();
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, [scenario]);

  const map = data?.map;
  const pt = !map
    ? null
    : scenario === "iss"
      ? { o2: map.iss.o2_pct, p: map.iss.pressure_kpa }
      : scenario === "habitat"
        ? { o2: map.habitat.o2_pct, p: map.habitat.pressure_kpa }
        : scenario === "chamber" && chamber
          ? { o2: chamber.o2_pct, p: chamber.pressure_kpa }
          : { o2: custom.o2, p: custom.p };

  useEffect(() => {
    if (!pt || data?.mode !== "live") return setLoc(null);
    const ac = new AbortController();
    locateLive(pt.p, pt.o2, ac.signal).then(setLoc).catch(() => setLoc(null));
    return () => ac.abort();
  }, [pt?.o2, pt?.p, data?.mode]); // eslint-disable-line react-hooks/exhaustive-deps

  const [o2lo, o2hi] = map?.axes.o2 ?? [0, 1];
  const [plo, phi] = map?.axes.pressure_kpa ?? [0, 1];
  const X = (o2: number) => 40 + ((o2 - o2lo) / (o2hi - o2lo)) * (W - 56);
  const Y = (p: number) => H - 32 - ((p - plo) / (phi - plo)) * (H - 48);

  useEffect(() => {
    const c = canvas.current;
    if (!c || !map) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    const { o2, pressure_kpa: pr, p_extinguish: pe, distance } = map.grid;
    const cw = (W - 56) / (o2.length - 1) + 1;
    const ch = (H - 48) / (pr.length - 1) + 1;
    pr.forEach((p, i) =>
      o2.forEach((o, j) => {
        const k = i * o2.length + j;
        const v = pe[k]; // 1 = flame goes out (safer), 0 = burns to completion
        ctx.fillStyle = `rgba(${Math.round(235 - 190 * v)},${Math.round(104 + 40 * v)},${Math.round(52 + 160 * v)},${distance[k] > 0.1 ? 0.28 : 0.7})`;
        ctx.fillRect(X(o) - cw / 2, Y(p) - ch / 2, cw, ch);
      }),
    );
  }, [map]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!map) return <p className="p-4 text-sm text-slate-400">Loading habitat map…</p>;
  const cov = map.coverage;
  const mats = map.materials;

  return (
    <div className="grid gap-4 overflow-auto p-3 text-slate-200 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div>
        <p className="mb-2 text-sm">
          <b className="text-orange-300">NASA has run {cov.rows_at_or_below_70kpa} microgravity tests at or below 70 kPa.</b>{" "}
          The habitat is {map.habitat.pressure_kpa} kPa; the lowest tested pressure is {cov.lowest_tested_pressure_kpa} kPa.
          Only {cov.rows_o2_30_or_more} of {cov.microgravity_rows} microgravity rows reach 30% O₂ (all fuel droplets,{" "}
          {cov.rows_o2_30_or_more_solids} solids; solids max at {cov.max_o2_solid_pct.toFixed(1)}%).
        </p>
        <div className="relative" style={{ width: "100%", maxWidth: W, aspectRatio: `${W}/${H}` }}>
          <canvas ref={canvas} width={W} height={H} className="absolute inset-0 h-full w-full" />
          <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 h-full w-full" role="img"
               aria-label="Fire map over oxygen and pressure with NASA tests and habitat point">
            <rect x={40} y={16} width={W - 56} height={H - 48} fill="none" stroke="#475569" />
            {map.tests.map((t, i) => (
              <circle key={i} cx={X(t.o2)} cy={Y(t.p)} r={2.2} fill="#0f172a" fillOpacity={0.75} />
            ))}
            {map.next_tests.map((n, i) => (
              <g key={i}><path d={`M${X(n.o2_pct)} ${Y(n.pressure_kpa) - 7}l2 5h5l-4 3 1.5 5-4.5-3-4.5 3 1.5-5-4-3h5z`} fill="#fbbf24" stroke="#0f172a" />
                <text x={X(n.o2_pct) + 8} y={Y(n.pressure_kpa) + 4} fontSize={10} fill="#fde68a">#{i + 1}</text></g>
            ))}
            <circle cx={X(map.iss.o2_pct)} cy={Y(map.iss.pressure_kpa)} r={6} fill="none" stroke="#22d3ee" strokeWidth={2} />
            <text x={X(map.iss.o2_pct) + 9} y={Y(map.iss.pressure_kpa) - 6} fontSize={11} fill="#67e8f9">ISS</text>
            <rect x={X(map.habitat.o2_pct) - 6} y={Y(map.habitat.pressure_kpa) - 6} width={12} height={12} fill="none" stroke="#f87171" strokeWidth={2} />
            <text x={X(map.habitat.o2_pct) - 8} y={Y(map.habitat.pressure_kpa) - 10} fontSize={11} fill="#fca5a5" textAnchor="end">Habitat</text>
            {pt ? (
              <g><circle cx={X(pt.o2)} cy={Y(pt.p)} r={7} fill="#a78bfa" stroke="#fff" strokeWidth={2} />
                <text x={X(pt.o2) + 10} y={Y(pt.p) + 16} fontSize={11} fill="#ddd6fe">you are here</text></g>
            ) : null}
            <text x={W / 2} y={H - 6} fontSize={11} fill="#94a3b8" textAnchor="middle">Oxygen (%)  {o2lo}–{o2hi}</text>
            <text x={12} y={H / 2} fontSize={11} fill="#94a3b8" transform={`rotate(-90 12 ${H / 2})`} textAnchor="middle">Pressure (kPa)</text>
          </svg>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Heat: orange = flame burns to completion, blue = flame goes out ({map.habitat_point_prediction.fuel}, FLEX). Faded = far from any NASA test.
          Dots = NASA microgravity tests. Stars = recommended next tests. {map.layers_note}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          {(["iss", "habitat", "custom", "chamber"] as Scenario[]).map((s) => (
            <button key={s} type="button" onClick={() => setScenario(s)}
              className={`rounded px-2 py-1 ring-1 ${scenario === s ? "bg-violet-500/30 ring-violet-400" : "ring-slate-600"}`}>
              {s === "chamber" ? "Live chamber" : s === "iss" ? "ISS air" : s === "habitat" ? "Habitat air" : "Custom"}
            </button>
          ))}
          {scenario === "custom" ? (
            <>
              <label>O₂ {custom.o2}% <input type="range" min={o2lo} max={o2hi} value={custom.o2} onChange={(e) => setCustom({ ...custom, o2: +e.target.value })} /></label>
              <label>P {custom.p} kPa <input type="range" min={plo} max={phi} value={custom.p} onChange={(e) => setCustom({ ...custom, p: +e.target.value })} /></label>
            </>
          ) : null}
          {scenario === "chamber" && !chamber ? <span className="text-amber-300">No chamber feed (set NEXT_PUBLIC_CHAMBER_URL)</span> : null}
        </div>
        {pt ? (
          <p className="mt-2 text-sm">
            At {pt.o2.toFixed(1)}% O₂ and {pt.p.toFixed(1)} kPa:{" "}
            {loc ? (
              <>P(flame goes out) = <b>{((loc.prediction.probability ?? 0) * 100).toFixed(0)}%</b> · {loc.status} · distance to nearest NASA test {loc.distance_to_nearest_nasa_test.toFixed(2)}</>
            ) : (
              <span className="text-slate-400">live answer needs the API (precomputed mode shows the map only)</span>
            )}
          </p>
        ) : null}
      </div>

      <div className="space-y-4">
        <section>
          <h3 className="text-sm font-semibold text-amber-300">Next experiments (largest uncertainty × distance from NASA tests)</h3>
          <ol className="mt-1 space-y-0.5 text-xs">
            {map.next_tests.map((n, i) => (
              <li key={i}>#{i + 1} {n.o2_pct}% O₂, {n.pressure_kpa} kPa: P(out) {Math.round(n.p_extinguish * 100)}%, {n.distance_to_nearest_test.toFixed(2)} from nearest test</li>
            ))}
          </ol>
          <p className="mt-1 text-[11px] text-slate-500">Simple rule, not full Bayesian design. Methanol droplets only.</p>
        </section>
        <section>
          <h3 className="text-sm font-semibold text-red-300">
            Material card: {mats.burn_at_34} of {mats.n} materials burn at 34% O₂ ({mats.burn_at_21} at 21%)
          </h3>
          <table className="mt-1 w-full text-xs">
            <thead><tr className="text-left text-slate-400"><th>Material</th><th>Limit O₂ %</th><th>Margin @34%</th><th>Burns</th></tr></thead>
            <tbody>
              {mats.items.map((m) => (
                <tr key={m.material} className="border-t border-slate-800">
                  <td>{m.material}</td>
                  <td>{m.moc_pct}{m.moc_min_pct !== m.moc_max_pct ? ` (${m.moc_min_pct}–${m.moc_max_pct})` : ""}</td>
                  <td>{m.margin_at_34_pct_o2 > 0 ? `+${m.margin_at_34_pct_o2}` : m.margin_at_34_pct_o2}</td>
                  <td>{m.burns_at_34 ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-[11px] text-slate-500">{mats.caveat} Decision support, not certification.</p>
        </section>
      </div>
    </div>
  );
}
