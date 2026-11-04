import { REFERENCE_GEOMETRY } from "./geometry";
import type { ExperimentKey, GeometryState, MaterialKey } from "./types";

export interface ExperimentPreset {
  key: ExperimentKey;
  /** Short UI label, e.g. "BASS-II - PMMA panel". */
  label: string;
  campaign: string;
  material: MaterialKey;
  oxygenPct: number;
  pressureKpa: number;
  airflowCms: number;
  geometry: GeometryState;
  /** PSI traceability tag for the primary record. */
  sourceTag: string;
  /** What this campaign actually measured. */
  notes: string;
}

/**
 * Published test conditions for the reference campaigns in the training set.
 * Picking one loads a real NASA test case rather than an arbitrary scenario.
 */
export const EXPERIMENTS: readonly ExperimentPreset[] = [
  {
    key: "bass-ii-pmma",
    label: "BASS-II - PMMA panel",
    campaign: "BASS-II",
    material: "pmma",
    oxygenPct: 21,
    pressureKpa: 101.3,
    airflowCms: 10,
    geometry: { ...REFERENCE_GEOMETRY },
    sourceTag: "PSI-25",
    notes:
      "Calibration case. Heated-wire ignition of a free-floating PMMA panel at cabin pressure; the dashboard's reference state.",
  },
  {
    key: "flex-nomex",
    label: "FLEX - Nomex textile",
    campaign: "FLEX",
    material: "nomex",
    oxygenPct: 21,
    pressureKpa: 101.3,
    airflowCms: 8,
    geometry: { ...REFERENCE_GEOMETRY },
    sourceTag: "PSI-69",
    notes:
      "Crew garment layer specimen. Aramid chars and self-extinguishes rather than propagating across the sample.",
  },
  {
    key: "flex-silicone",
    label: "FLEX - Silicone gasket",
    campaign: "FLEX",
    material: "silicone",
    oxygenPct: 21,
    pressureKpa: 101.3,
    airflowCms: 8,
    geometry: { ...REFERENCE_GEOMETRY },
    sourceTag: "PSI-71",
    notes:
      "Gasket and seal stock. Low flame spread but heavy silicone-oxide aerosol loading that obscures optics quickly.",
  },
  {
    key: "saffire-i-pe",
    label: "SAFFIRE-I - polyethylene",
    campaign: "SAFFIRE-I",
    material: "polyethylene",
    oxygenPct: 21,
    pressureKpa: 101.3,
    airflowCms: 12,
    geometry: { ...REFERENCE_GEOMETRY },
    sourceTag: "PSI-98",
    notes:
      "Worst-case cabin polymer. Fastest propagation front and heaviest soot yield in the reference set.",
  },
  {
    key: "same-methanol",
    label: "SAME - methanol mist",
    campaign: "SAME",
    material: "methanol",
    oxygenPct: 21,
    pressureKpa: 101.3,
    airflowCms: 15,
    geometry: { ...REFERENCE_GEOMETRY },
    sourceTag: "PSI-102",
    notes:
      "Liquid fuel mist. Lowest extinction limit in the set, so it ignites across the widest oxygen window.",
  },
  {
    key: "custom",
    label: "Custom scenario",
    campaign: "Operator defined",
    material: "pmma",
    oxygenPct: 21,
    pressureKpa: 101.3,
    airflowCms: 10,
    geometry: { ...REFERENCE_GEOMETRY },
    sourceTag: "No campaign match",
    notes:
      "Off-baseline case. Predictions are surrogate extrapolations and are not traceable to a measured NASA record.",
  },
];

const INDEX = EXPERIMENTS.reduce(
  (acc, preset) => {
    acc[preset.key] = preset;
    return acc;
  },
  {} as Record<ExperimentKey, ExperimentPreset>,
);

export function getExperiment(key: ExperimentKey): ExperimentPreset {
  return INDEX[key] ?? INDEX.custom;
}