/**
 * AstraFlame shared domain types.
 * Project: Agnishikha (NASA Space Apps Challenge).
 */

export type ConfidenceBand = "HIGH" | "MODERATE" | "LIMITED";

export type MaterialKey =
  | "pmma"
  | "nomex"
  | "silicone"
  | "polyethylene"
  | "methanol";

export type HazardLevel = "LOW" | "MODERATE" | "HIGH" | "SEVERE";

export interface MaterialRecord {
  key: MaterialKey;
  /** Full display name, e.g. "PMMA (Acrylic)". */
  name: string;
  /** Compact label used in dense UI slots. */
  shortName: string;
  /** Laminar flame spread rate (mm/s) at 21% O2 / 101.3 kPa / still cabin air. */
  flameSpreadRate: number;
  /** Minimum O2 concentration (vol %) at which the fuel can hold a flame. */
  minExtinctionO2: number;
  /** Specific smoke yield (mg/min) at nominal cabin conditions. */
  smokeYield: number;
  /** Relative pyrolysis heat-release multiplier (PMMA = 1.0 reference). */
  pyrolysisHeat: number;
  /** Reference diffusion flame length (cm) at nominal cabin conditions. */
  flameLength: number;
  /** Fraction of the flame length at which soot loading becomes optically visible. */
  sootFraction: number;
  /** Equivalent fuel load driving large-scale burn duration. */
  fuelLoad: number;
  /** Peak adiabatic flame temperature (K). */
  flameTempK: number;
  /** NASA PSI traceability tag. */
  sourceTag: string;
  /** Ignition + propagation hazard classification. */
  hazard: HazardLevel;
  /** Cabin particulate / obscurant hazard classification. */
  smokeHazard: HazardLevel;
  /** Engineering note surfaced in the risk scoreboard tooltip. */
  note: string;
}

export type ExperimentKey =
  | "bass-ii-pmma"
  | "flex-nomex"
  | "flex-silicone"
  | "saffire-i-pe"
  | "same-methanol"
  | "custom";

export interface GeometryState {
  /** Burner diameter, mm */
  burnerDiameterMm: number;
  /** Sample width, mm */
  sampleWidthMm: number;
  /** Sample thickness, mm */
  sampleThicknessMm: number;
  /** Sample orientation, degrees (0 = horizontal, 90 = vertical) */
  orientationDeg: number;
}

export interface EnvironmentState {
  /** Ambient O2 concentration, 12 - 30 vol %. */
  oxygenPct: number;
  /** Ambient pressure, 50 - 110 kPa. */
  pressureKpa: number;
  /** Forced convection velocity, 0 - 50 cm/s. */
  airflowCms: number;
  material: MaterialKey;
  /** Selected NASA experiment case */
  experiment: ExperimentKey;
  /** Geometry configuration for the test rig */
  geometry: GeometryState;
}

export interface Telemetry {
  /** Laminar flame spread rate, mm/s. */
  flameSpreadRate: number;
  /** Probability the flame fails to establish / self-extinguishes, 0 - 1. */
  extinctionProb: number;
  /** Large-scale propagation duration on the available fuel load, seconds. */
  burnDuration: number;
  /** Diffusion flame length, cm. */
  flameLength: number;
  /** Height at which soot inception becomes visible, cm. */
  sootPoint: number;
  /** Smoke and particle mass yield, mg/min. */
  smokeYield: number;
  /** True while O2 stays inside the 12 - 25 % NASA validated training envelope. */
  inDomain: boolean;
  confidenceBand: ConfidenceBand;
  /** Smoothed 0 - 100 model confidence readout. */
  confidencePct: number;
  /** Normalized combustion vigor, 0 (extinct) to ~1.5 (oxygen enriched). */
  combustionVigor: number;
  /** Predicted heat release rate, watts. */
  heatReleaseW: number;
  /** Predicted peak flame temperature, K. */
  flameTempK: number;
  /** Airflow actually reaching the flame zone once the vent damper state is applied. */
  effectiveAirflowCms: number;
  /** Suppression factor applied by an open damper (1 = normal, <1 = starved). */
  ventilationFactor: number;
  /** Rig-geometry scaling applied to spread, envelope size and heat release. */
  geometryFactor: number;
}

export interface SimulationState {
  isVentilationCut: boolean;
}

export interface DashboardState {
  environment: EnvironmentState;
  simulation: SimulationState;
}