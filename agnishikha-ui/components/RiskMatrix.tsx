"use client";

import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { riskIndex } from "@/lib/telemetry";
import type { Telemetry } from "@/lib/types";

export interface RiskMatrixProps {
  telemetry: Telemetry;
}

const LIKELIHOOD_LABELS = ["Rare", "Unlikely", "Possible", "Likely", "Certain"];
const CONSEQUENCE_LABELS = [
  "Minor",
  "Moderate",
  "Serious",
  "Major",
  "Catastrophic",
];

const RISK_BANDS = [
  { max: 0.2, label: "LOW", cell: "bg-emerald-500/25", text: "text-emerald-300" },
  { max: 0.4, label: "GUARDED", cell: "bg-lime-500/25", text: "text-lime-300" },
  { max: 0.6, label: "MODERATE", cell: "bg-amber-500/25", text: "text-amber-300" },
  { max: 0.8, label: "HIGH", cell: "bg-orange-500/30", text: "text-orange-300" },
  { max: 1.01, label: "SEVERE", cell: "bg-red-500/30", text: "text-red-300" },
];

function bandFor(score: number) {
  return RISK_BANDS.find((band) => score < band.max) ?? RISK_BANDS[0];
}

export function RiskMatrix({ telemetry }: RiskMatrixProps) {
  const risk = riskIndex(telemetry);
  const animatedRisk = useAnimatedNumber(risk, 3);
  const animatedSpread = useAnimatedNumber(telemetry.flameSpreadRate, 1);

  const likelihood = Math.min(4, Math.floor(animatedRisk * 5));
  const consequence = Math.min(4, Math.floor((animatedSpread / 70) * 5));
  const activeBand = bandFor(risk);

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="min-h-0 flex-1">
        <div className="grid h-full grid-cols-[auto_repeat(5,minmax(0,1fr))] gap-1">
          <div aria-hidden="true" />
          {CONSEQUENCE_LABELS.map((label) => (
            <div
              key={label}
              className="flex items-end justify-center pb-1 text-center text-[10px] uppercase leading-tight tracking-wider text-slate-400"
            >
              {label}
            </div>
          ))}

          {LIKELIHOOD_LABELS.map((label, lIdx) => (
            <div key={label} className="contents">
              <div className="flex items-center justify-end pr-1.5 text-[10px] text-slate-400">
                {label}
              </div>
              {CONSEQUENCE_LABELS.map((_, cIdx) => {
                const bandScore = (lIdx + cIdx + 2) / 10;
                const band = bandFor(bandScore);
                const active = lIdx === likelihood && cIdx === consequence;
                return (
                  <div
                    key={`${lIdx}-${cIdx}`}
                    className={`relative min-h-[26px] rounded border border-slate-800/80 transition-all duration-300 ${
                      band.cell
                    } ${active ? "scale-105 border-white/70 shadow-[0_0_14px_rgba(255,255,255,0.25)]" : ""}`}
                  >
                    {active ? (
                      <span
                        aria-hidden="true"
                        className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold text-white"
                      >
                        ●
                      </span>
                    ) : null}
                    <span className="sr-only">
                      {label} likelihood, {CONSEQUENCE_LABELS[cIdx]} consequence —{" "}
                      {band.label} band, risk index {(bandScore * 100).toFixed(0)} of
                      100{active ? ", current case" : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="shrink-0 space-y-1.5">
        <div className="grid grid-cols-3 gap-2">
          {[
            ["Likelihood", LIKELIHOOD_LABELS[likelihood]],
            ["Consequence", CONSEQUENCE_LABELS[consequence]],
            ["Band", activeBand.label],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-md border border-slate-800/80 bg-slate-950/40 px-2 py-1.5 ring-1 ring-white/[0.02]"
            >
              <p className="text-[10px] uppercase tracking-wider text-slate-400">
                {label}
              </p>
              <p
                className={`truncate font-mono text-[11px] font-semibold ${
                  label === "Band" ? activeBand.text : "text-slate-200"
                }`}
              >
                {value}
              </p>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between gap-2 font-mono text-[10px] text-slate-400">
          <span>Risk index</span>
          <div
            className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800"
            role="progressbar"
            aria-label="Composite risk index"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(risk * 100)}
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 transition-[width] duration-300 ease-out"
              style={{ width: `${Math.min(100, animatedRisk * 100)}%` }}
            />
          </div>
          <span className="tabular-nums text-slate-200">
            {(animatedRisk * 100).toFixed(0)}%
          </span>
        </div>

        <p className="text-[10px] leading-relaxed text-slate-400">
          Cells bin the composite risk index against propagation front speed. This is a
          presentational mapping of the surrogate, not a calibrated FMEA scoring
          scheme.
        </p>
      </div>
    </div>
  );
}
