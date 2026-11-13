"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/** Smoothly tween a number (400 ms); instant when the user prefers reduced motion. */
function useTween(target: number) {
  const [v, setV] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { setV(target); from.current = target; return; }
    const a = from.current, t0 = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 400), e = 1 - Math.pow(1 - k, 3);
      from.current = a + (target - a) * e; setV(from.current);
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return v;
}
import { HelpTip, GLOSSARY } from "@/components/HelpTip";
import { loadHabitat, locateLive, readChamber, type HabitatMap, type LocateResult, type Mode } from "@/lib/ignisApi";

type Scenario = "iss" | "habitat" | "custom" | "chamber";
const W = 640, H = 400, PL = 52, PR = 70, PT = 14, PB = 44;
const NAMES: Record<Scenario, string> = { iss: "Space Station air", habitat: "Moon / Mars habitat air", custom: "Try your own", chamber: "Live chamber" };

/** Habitat fire map in plain language: what NASA tested, what the model says, what to test next. */
export function HabitatMapPanel() {
  const [data, setData] = useState<{ mode: Mode; map: HabitatMap } | null>(null);
  const [scenario, setScenario] = useState<Scenario>("habitat");
  const [custom, setCustom] = useState({ o2: 27, p: 80 });
  const [chamber, setChamber] = useState<{ pressure_kpa: number; o2_pct: number } | null>(null);
  const [loc, setLoc] = useState<LocateResult | null>(null);
  const [showMats, setShowMats] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => { loadHabitat().then(setData).catch(() => setData(null)); }, []);
  useEffect(() => {
    if (scenario !== "chamber") return;
    const tick = () => readChamber().then((c) => c && setChamber(c));
    tick();
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, [scenario]);

  const map = data?.map;
  const pt = useMemo(() => {
    if (!map) return null;
    if (scenario === "iss") return { o2: map.iss.o2_pct, p: map.iss.pressure_kpa };
    if (scenario === "habitat") return { o2: map.habitat.o2_pct, p: map.habitat.pressure_kpa };
    if (scenario === "chamber" && chamber) return { o2: chamber.o2_pct, p: chamber.pressure_kpa };
    return { o2: custom.o2, p: custom.p };
  }, [map, scenario, chamber, custom]);

  useEffect(() => {
    if (!pt || data?.mode !== "live") { setLoc(null); return; }
    const ac = new AbortController();
    locateLive(pt.p, pt.o2, ac.signal).then(setLoc).catch(() => setLoc(null));
    return () => ac.abort();
  }, [pt?.o2, pt?.p, data?.mode]); // eslint-disable-line react-hooks/exhaustive-deps

  const [o2lo, o2hi] = map?.axes.o2 ?? [0, 1];
  const [plo, phi] = map?.axes.pressure_kpa ?? [0, 1];
  const X = (o2: number) => PL + ((o2 - o2lo) / (o2hi - o2lo)) * (W - PL - PR);
  const Y = (p: number) => H - PB - ((p - plo) / (phi - plo)) * (H - PT - PB);

  useEffect(() => {
    const c = canvas.current;
    if (!c || !map) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    const { o2, pressure_kpa: pr, p_extinguish: pe, distance } = map.grid;
    const cw = (W - PL - PR) / (o2.length - 1) + 1, ch = (H - PT - PB) / (pr.length - 1) + 1;
    pr.forEach((p, i) => o2.forEach((o, j) => {
      const k = i * o2.length + j, v = pe[k];
      ctx.fillStyle = `rgba(${Math.round(235 - 190 * v)},${Math.round(104 + 40 * v)},${Math.round(52 + 160 * v)},${distance[k] > 0.1 ? 0.25 : 0.8})`;
      ctx.fillRect(X(o) - cw / 2, Y(p) - ch / 2, cw, ch);
    }));
  }, [map]); // eslint-disable-line react-hooks/exhaustive-deps

  const pOut = map && pt
    ? (() => {
        const { o2, pressure_kpa: pr, p_extinguish: pe } = map.grid;
        const j = o2.reduce((b, v, i) => (Math.abs(v - pt.o2) < Math.abs(o2[b] - pt.o2) ? i : b), 0);
        const i = pr.reduce((b, v, k) => (Math.abs(v - pt.p) < Math.abs(pr[b] - pt.p) ? k : b), 0);
        return pe[i * o2.length + j];
      })()
    : 0;
  const animatedPct = useTween(Math.round((loc?.prediction.probability ?? pOut) * 100));

  if (!map || !pt) return <div className="space-y-3 p-6" aria-busy="true"><div className="af-skeleton h-10 w-2/3" /><div data-tour="hab-stats" className="grid gap-3 sm:grid-cols-3"><div className="af-skeleton h-24" /><div className="af-skeleton h-24" /><div className="af-skeleton h-24" /></div><div className="af-skeleton h-72" /></div>;
  const cov = map.coverage, mats = map.materials;

  // answer for the chosen air: nearest model grid cell + distance to nearest NASA test (works without the API)
  const dist = Math.min(...map.tests.map((t) => Math.hypot((t.o2 - pt.o2) / (o2hi - o2lo), (t.p - pt.p) / (phi - plo))));
  const tested = loc ? !!loc.prediction.in_domain : pt.p >= cov.lowest_tested_pressure_kpa && dist < 0.08;
  const goesOut = pOut >= 0.67;
  const rightEdge = X(pt.o2) > W - PR - 70;

  return (
    <div className="af-stagger h-full min-h-0 space-y-5 overflow-y-auto p-4 text-slate-200 sm:p-6">
      <header>
        <h2 className="text-xl font-semibold text-slate-100 sm:text-2xl">
          The NASA data in this tool has no space fire test at habitat pressure.
        </h2>
        <p className="mt-1 text-base text-slate-400">
          Future Moon and Mars habitats may use thinner air with more oxygen (pressure in kPa <HelpTip text={GLOSSARY.kpa} />). This map shows the NASA tests in our data, what our model expects,
          and which experiments would teach the most.
        </p>
      </header>

      <div data-tour="hab-stats" className="grid gap-3 sm:grid-cols-3">
        {[
          [`${cov.rows_at_or_below_70kpa}`, `space fire tests (microgravity) at habitat-like pressure (${map.habitat.pressure_kpa} kPa). The lowest NASA tested is ${cov.lowest_tested_pressure_kpa} kPa.`],
          [`${cov.rows_o2_30_or_more} of ${cov.microgravity_rows}`, `space tests had 30%+ oxygen. All were fuel droplets, none were solid materials.`],
          [`${mats.burn_at_34} of ${mats.n}`, `common materials can burn at 34% oxygen in Earth gravity tests (${mats.burn_at_21} burn in normal air).`],
        ].map(([big, small]) => (
          <div key={big} className="af-card p-4 ring-1 ring-slate-800">
            <div className="text-3xl font-bold text-orange-400">{big}</div>
            <p className="mt-1 text-sm text-slate-400">{small}</p>
          </div>
        ))}
      </div>

      <section className="af-card p-4 ring-1 ring-slate-800">
        <h3 className="text-base font-semibold text-slate-100">1. Pick an atmosphere</h3>
        <div data-tour="hab-picker" className="mt-2 flex flex-wrap gap-2">
          {(Object.keys(NAMES) as Scenario[]).map((s) => (
            <button key={s} type="button" onClick={() => setScenario(s)}
              className={`af-press min-h-10 rounded-full px-4 py-2 text-sm font-medium ${scenario === s ? "bg-violet-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`}>
              {NAMES[s]}
            </button>
          ))}
        </div>
        {scenario === "custom" ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-sm">Oxygen: <b>{custom.o2}%</b>
              <input className="block w-full" type="range" min={o2lo} max={o2hi} value={custom.o2} onChange={(e) => setCustom({ ...custom, o2: +e.target.value })} /></label>
            <label className="text-sm">Pressure: <b>{custom.p} kPa</b>
              <input className="block w-full" type="range" min={plo} max={phi} value={custom.p} onChange={(e) => setCustom({ ...custom, p: +e.target.value })} /></label>
          </div>
        ) : null}
        {scenario === "chamber" && !chamber ? <p className="mt-2 text-sm text-amber-300">No chamber connected yet.</p> : null}

        <div data-tour="hab-answer" className={`af-enter mt-3 rounded-lg p-4 ring-1 ${tested ? "bg-emerald-500/10 ring-emerald-500/40" : "bg-amber-500/10 ring-amber-500/40"}`}>
          <p className="text-base font-semibold text-slate-100">
            {NAMES[scenario]}: {pt.o2.toFixed(0)}% oxygen, {pt.p.toFixed(0)} kPa
          </p>
          <p className="mt-1 text-base">
            A small methanol flame would most likely <b>{goesOut ? "go out on its own" : "keep burning until the fuel is gone"}</b>{" "}
            (chance it goes out: {Math.round(animatedPct)}% <HelpTip text={GLOSSARY.extinction} />).
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {tested
              ? "Our NASA data has tests close to this, so we trust the answer more."
              : "Our NASA data has no space test like this, so treat the answer as an informed guess."}
          </p>
        </div>
      </section>

      <section className="af-card p-4 ring-1 ring-slate-800">
        <h3 className="text-base font-semibold text-slate-100">2. See where it sits on the map</h3>
        <div className="mt-2 grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div data-tour="hab-map" className="relative w-full max-w-[640px]" style={{ aspectRatio: `${W}/${H}` }}>
            <canvas ref={canvas} width={W} height={H} className="absolute inset-0 h-full w-full" />
            <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 h-full w-full" role="img" aria-label="Map of oxygen and pressure with NASA tests">
              <rect x={PL} y={PT} width={W - PL - PR} height={H - PT - PB} fill="none" stroke="#94a3b8" />
              {Array.from({ length: Math.floor((o2hi - o2lo) / 4) + 1 }, (_, i) => o2lo + i * 4).map((v) => (
                <g key={`x${v}`}><line x1={X(v)} x2={X(v)} y1={H - PB} y2={H - PB + 4} stroke="#64748b" />
                  <text x={X(v)} y={H - PB + 16} fontSize={11} className="fill-slate-400" textAnchor="middle">{v}</text></g>
              ))}
              {[50, 100, 150, 200, 250, 300].filter((v) => v >= plo && v <= phi).map((v) => (
                <g key={`y${v}`}><line x1={PL - 4} x2={PL} y1={Y(v)} y2={Y(v)} stroke="#64748b" />
                  <text x={PL - 7} y={Y(v) + 4} fontSize={11} className="fill-slate-400" textAnchor="end">{v}</text></g>
              ))}
              <line x1={PL} x2={W - PR} y1={Y(cov.lowest_tested_pressure_kpa)} y2={Y(cov.lowest_tested_pressure_kpa)} stroke="#dc2626" strokeDasharray="5 3" />
              <text x={W - PR + 4} y={Y(cov.lowest_tested_pressure_kpa) - 2} fontSize={10} className="fill-red-300">Lowest test</text>
              <text x={W - PR + 4} y={Y(cov.lowest_tested_pressure_kpa) + 10} fontSize={10} className="fill-red-300">in our data</text>
              {map.tests.map((t, i) => <circle key={i} cx={X(t.o2)} cy={Y(t.p)} r={2.4} className="fill-slate-100" fillOpacity={0.85} />)}
              {map.next_tests.map((n, i) => (
                <g key={i}><circle cx={X(n.o2_pct)} cy={Y(n.pressure_kpa)} r={9} fill="#fbbf24" stroke="#0f172a" />
                  <text x={X(n.o2_pct)} y={Y(n.pressure_kpa) + 4} fontSize={11} fontWeight={700} textAnchor="middle" fill="#0f172a">{"ABCDE"[i]}</text></g>
              ))}
              <circle cx={X(map.iss.o2_pct)} cy={Y(map.iss.pressure_kpa)} r={7} className="fill-slate-900" stroke="#22d3ee" strokeWidth={3} />
              <text x={X(map.iss.o2_pct) + 10} y={Y(map.iss.pressure_kpa) - 8} fontSize={12} fontWeight={600} className="fill-cyan-300">Space Station</text>
              <rect x={X(map.habitat.o2_pct) - 7} y={Y(map.habitat.pressure_kpa) - 7} width={14} height={14} className="fill-slate-900" stroke="#f87171" strokeWidth={3} />
              <text x={X(map.habitat.o2_pct) - 10} y={Y(map.habitat.pressure_kpa) - 10} fontSize={12} fontWeight={600} className="fill-red-300" textAnchor="end">Habitat</text>
              <g className="af-dot" style={{ transform: `translate(${X(pt.o2)}px, ${Y(pt.p)}px)` }}>
                <circle r={8} fill="#7c3aed" stroke="#fff" strokeWidth={2.5} />
                <text x={rightEdge ? -12 : 12} y={20} fontSize={12} fontWeight={700} className="fill-violet-300" textAnchor={rightEdge ? "end" : "start"}>selected</text>
              </g>
              <text x={(PL + W - PR) / 2} y={H - 4} fontSize={12} className="fill-slate-300" textAnchor="middle">Oxygen in the air (%)</text>
              <text x={12} y={H / 2} fontSize={12} className="fill-slate-300" transform={`rotate(-90 12 ${H / 2})`} textAnchor="middle">Air pressure (kPa)</text>
            </svg>
          </div>
          <ul className="space-y-2 text-sm text-slate-300">
            <li><span className="mr-2 inline-block h-3 w-3 rounded-sm bg-blue-500" />Flame goes out by itself</li>
            <li><span className="mr-2 inline-block h-3 w-3 rounded-sm bg-orange-500" />Flame keeps burning</li>
            <li><span className="mr-2 inline-block h-3 w-3 rounded-sm bg-slate-600" />Faded: far from any NASA test (a guess)</li>
            <li><span className="mr-2 inline-block h-2 w-2 rounded-full bg-slate-100" />A past NASA space test</li>
            <li><span className="mr-2 inline-block h-3 w-3 rounded-full bg-amber-400 ring-1 ring-slate-100" />A–E: best next tests</li>
            <li className="text-xs text-slate-500">Colors come from our model of burning methanol droplets in space. Material results (below) come from Earth-gravity tests. They are different data.</li>
          </ul>
        </div>
      </section>

      <section className="af-card p-4 ring-1 ring-slate-800">
        <h3 className="text-base font-semibold text-slate-100">3. What should NASA test next?</h3>
        <p className="text-sm text-slate-400">We chose conditions where the model is least sure and our NASA data has no nearby test.</p>
        <ol className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {map.next_tests.map((n, i) => (
            <li key={i} className="rounded-lg bg-amber-500/10 p-3 text-sm ring-1 ring-amber-500/30">
              <b>Test {"ABCDE"[i]}:</b> {n.o2_pct}% oxygen at {n.pressure_kpa} kPa
              <div className="text-slate-400">Model says {Math.round(n.p_extinguish * 100)}% chance the flame goes out. Close to a coin toss means a lot to learn.</div>
            </li>
          ))}
        </ol>
      </section>

      <section data-tour="hab-materials" className="af-card p-4 ring-1 ring-slate-800">
        <button type="button" onClick={() => setShowMats((v) => !v)} className="text-left text-base font-semibold text-slate-100" aria-expanded={showMats}>
          4. Which materials can burn at 34% oxygen? {showMats ? "▲" : "▼"}
        </button>
        <p className="text-sm text-slate-400">{mats.burn_at_34} of {mats.n} can. Only the two PVC sheets resist. Tap to {showMats ? "hide" : "see"} the list.</p>
        {showMats ? (
          <table className="mt-2 w-full text-sm">
            <thead><tr className="text-left text-slate-500"><th className="py-1">Material</th><th>Stops burning below (% oxygen)</th><th>Result at 34%</th></tr></thead>
            <tbody>
              {mats.items.map((m) => (
                <tr key={m.material} className="border-t border-slate-800">
                  <td className="py-1">{m.material}</td>
                  <td>{m.moc_pct}</td>
                  <td><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${m.burns_at_34 ? "bg-red-500/15 text-red-300" : "bg-emerald-500/15 text-emerald-300"}`}>{m.burns_at_34 ? "can burn" : "resists"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        <p className="mt-2 text-xs text-slate-500">{mats.caveat} This is a planning aid, not a safety certification.</p>
      </section>
    </div>
  );
}
