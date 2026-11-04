import { getMaterial } from "./materials";
import { geometryDeviation, geometryFactor } from "./geometry";
import { clamp, clamp01, round } from "./math";
import type {
  ConfidenceBand,
  EnvironmentState,
  GeometryState,
  MaterialRecord,
  Telemetry,
} from "./types";

/* ------------------------------------------------------------------ */
/* Re-export the operator input envelope for existing importers        */
/* ------------------------------------------------------------------ */

export {
  AIRFLOW_LIMIT,
  BURNER_DIAMETER_LIMIT,
  CREW_O2_FLOOR,
  MODULE_VOLUME_M3,
  ORIENTATION_LIMIT,
  OXYGEN_LIMIT,
  PRESSURE_LIMIT,
  SAMPLE_THICKNESS_LIMIT,
  SAMPLE_WIDTH_LIMIT,
  TRAINING_ENVELOPE,
} from "./axes";
export type { AxisLimit } from "./axes";

import {
  AIRFLOW_LIMIT,
  OXYGEN_LIMIT,
  PRESSURE_LIMIT,
  TRAINING_ENVELOPE,
} from "./axes";

/* ------------------------------------------------------------------ */
/* Reference state - the point the surrogate is calibrated at          */
/* ------------------------------------------------------------------ */

export const REFERENCE_ENVIRONMENT: EnvironmentState = {
  oxygenPct: OXYGEN_LIMIT.nominal,
  pressureKpa: PRESSURE_LIMIT.nominal,
  airflowCms: AIRFLOW_LIMIT.nominal,
  material: "pmma",
  experiment: "bass-ii-pmma",
  geometry: {
    burnerDiameterMm: 25,
    sampleWidthMm: 50,
    sampleThicknessMm: 6,
    orientationDeg: 90,
  },
};

/** Default state the dashboard boots into (the calibration case). */
export const NOMINAL_ENVIRONMENT: EnvironmentState = REFERENCE_ENVIRONMENT;

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

/**
 * Reaction-rate contribution of total pressure. Peak reactivity sits slightly
 * below 1 atm (p_norm ~ 0.85) and decays toward both the vacuum limit and the
 * high-pressure regime, matching BASS-II / FLEX observations.
 */
export function pressureFactor(pressureKpa: number): number {
  const pNorm = clamp(
    (pressureKpa - PRESSURE_LIMIT.min) / (PRESSURE_LIMIT.max - PRESSURE_LIMIT.min),
    0,
    1,
  );
  const factor = 0.55 + 1.05 * pNorm - 0.62 * pNorm * pNorm;
  return clamp(factor, 0.4, 1.05);
}

/**
 * Forced convection contribution. Microgravity flames are diffusion dominated,
 * so cabin air velocity both feeds oxygen to the reaction zone and stretches
 * the flame envelope.
 */
export function airflowFactor(effectiveAirflowCms: number): number {
  const norm = clamp(effectiveAirflowCms / AIRFLOW_LIMIT.max, 0, 1);
  return 0.85 + 0.45 * norm;
}

/**
 * Characteristic oxygen margin above a fuel's extinction limit, in percentage
 * points, at which that fuel burns at full vigor. 8.5 pp is the PMMA margin at
 * 21 % O2, so the reference specimen still reads exactly 1.0 at calibration.
 */
export const REFERENCE_OXYGEN_MARGIN = 8.5;

/**
 * Normalized combustion vigor, driven by the *absolute* oxygen margin above
 * each material's own extinction limit. Normalizing per-material (as opposed
 * to per-atmosphere) keeps a low-LOI fuel such as methanol far more ignitable
 * than an aramid at the same 21 % O2, which is what the FLEX campaign measured.
 * Sub-linear above atmosphere because reaction vigor saturates as the oxidizer
 * fraction rises.
 */
export function combustionVigor(
  material: MaterialRecord,
  oxygenPct: number,
): number {
  const raw =
    (oxygenPct - material.minExtinctionO2) / REFERENCE_OXYGEN_MARGIN;
  return raw <= 0 ? 0 : Math.pow(raw, 0.75);
}

/** Airflow that actually reaches the flame zone with the damper state applied. */
export function resolveEffectiveAirflow(
  environment: EnvironmentState,
  isVentilationCut: boolean,
): number {
  return isVentilationCut ? 0 : environment.airflowCms;
}

/**
 * Open damper starves the flame of convective oxygen delivery. The cabin bulk
 * concentration lags behind, so the model applies an immediate suppression
 * factor while the visualizer animates the 3 s extinction transient.
 *
 * Heuristic, not fitted: the PSI target set carries no airflow-dependent
 * measured spread targets, so the suppressed rate must not be read as a
 * validated prediction.
 */
export function ventilationFactor(isVentilationCut: boolean): number {
  return isVentilationCut ? 0.55 : 1;
}

/** Zero the sample scaling when the operator has cleared the environment. */
function geometryOf(environment: EnvironmentState): GeometryState {
  return environment.geometry ?? REFERENCE_ENVIRONMENT.geometry;
}

/* ------------------------------------------------------------------ */
/* Core predictor                                                      */
/* ------------------------------------------------------------------ */

export function predictTelemetry(
  environment: EnvironmentState,
  isVentilationCut: boolean,
): Telemetry {
  const material = getMaterial(environment.material);

  const oxygenPct = clamp(
    environment.oxygenPct,
    OXYGEN_LIMIT.min,
    OXYGEN_LIMIT.max,
  );
  const pressureKpa = clamp(
    environment.pressureKpa,
    PRESSURE_LIMIT.min,
    PRESSURE_LIMIT.max,
  );
  const commandedAirflow = clamp(
    environment.airflowCms,
    AIRFLOW_LIMIT.min,
    AIRFLOW_LIMIT.max,
  );

  const effectiveAirflowCms = resolveEffectiveAirflow(
    environment,
    isVentilationCut,
  );
  const vent = ventilationFactor(isVentilationCut);

  const geometry = geometryOf(environment);
  const geo = geometryFactor(geometry);

  const vigor = combustionVigor(material, oxygenPct);
  const pFactor = pressureFactor(pressureKpa);
  const aFactor = airflowFactor(effectiveAirflowCms);

  // Flame spread: reference rate scaled by chemistry, pressure and convection.
  const flameSpreadRate = clamp(
    material.flameSpreadRate * vigor * pFactor * aFactor * vent * geo,
    0,
    160,
  );

  // Large-scale propagation duration on the available fuel load.
  const burnDuration = clamp(
    (900 * material.fuelLoad * (0.3 + 0.7 * pFactor)) /
      Math.max(flameSpreadRate, 6),
    4,
    320,
  );

  // Flame envelope length: elongation grows with both chemistry and convection.
  const airflowNorm = effectiveAirflowCms / AIRFLOW_LIMIT.max;
  const flameLength = clamp(
    material.flameLength *
      vigor *
      pFactor *
      (0.6 + 0.9 * airflowNorm) *
      vent *
      clamp(geo, 0.35, 1.8),
    0,
    90,
  );

  // Soot inception height: low-swirl microgravity flames load soot in the
  // upper third, so it tracks flame length through the material soot factor.
  const sootPoint = flameLength * material.sootFraction;

  // Smoke mass yield: chemical loading scaled by vigor, pressure and sweep.
  const smokeYield = clamp(
    material.smokeYield *
      clamp(vigor, 0, 1.6) *
      pFactor *
      (0.85 + 0.45 * airflowNorm) *
      vent,
    0,
    140,
  );

  // Extinction probability: chemistry dominates, with low-pressure starvation
  // and high-velocity blowback as secondary failure modes.
  let extinctionProb = 1 - clamp01(vigor / 1.35);
  extinctionProb += Math.max(0, 0.75 - pFactor) * 0.55;
  if (effectiveAirflowCms > 44) {
    extinctionProb += ((effectiveAirflowCms - 44) / 6) * 0.2;
  }
  if (material.key === "methanol" && commandedAirflow > 30) {
    extinctionProb += 0.12;
  }
  if (isVentilationCut) {
    extinctionProb += 0.32;
  }
  extinctionProb = clamp01(extinctionProb);

  // Derived thermodynamics.
  const heatReleaseW = clamp(
    material.pyrolysisHeat * 22 * vigor * pFactor * aFactor * vent * geo,
    0,
    400,
  );
  const flameTempK = Math.round(
    clamp(
      material.flameTempK *
        (0.86 + 0.14 * clamp01(vigor)) *
        (0.94 + 0.06 * pFactor) *
        (isVentilationCut ? 0.93 : 1),
      600,
      2400,
    ),
  );

  const inDomain =
    oxygenPct >= TRAINING_ENVELOPE.oxygenMin &&
    oxygenPct <= TRAINING_ENVELOPE.oxygenMax;

  const confidencePct = computeConfidencePct(
    oxygenPct,
    pressureKpa,
    commandedAirflow,
    extinctionProb,
    inDomain,
    geometryDeviation(geometry),
  );

  return {
    flameSpreadRate: round(flameSpreadRate, 1),
    extinctionProb: round(extinctionProb, 3),
    burnDuration: round(burnDuration, 1),
    flameLength: round(flameLength, 1),
    sootPoint: round(sootPoint, 1),
    smokeYield: round(smokeYield, 1),
    inDomain,
    confidenceBand: bandFromConfidence(inDomain, confidencePct),
    confidencePct: round(confidencePct, 0),
    combustionVigor: round(vigor, 3),
    heatReleaseW: round(heatReleaseW, 1),
    flameTempK,
    effectiveAirflowCms: round(effectiveAirflowCms, 1),
    ventilationFactor: vent,
    geometryFactor: round(geo, 3),
  };
}

function computeConfidencePct(
  oxygenPct: number,
  pressureKpa: number,
  airflowCms: number,
  extinctionProb: number,
  inDomain: boolean,
  geometryDeviation: number,
): number {
  let confidence = 98;
  confidence -= Math.max(0, oxygenPct - TRAINING_ENVELOPE.oxygenMax) * 9;
  confidence -= Math.max(0, TRAINING_ENVELOPE.oxygenMin - oxygenPct) * 14;
  confidence -= Math.max(0, pressureKpa - TRAINING_ENVELOPE.pressureMax) * 0.55;
  confidence -= Math.max(0, TRAINING_ENVELOPE.pressureMin - pressureKpa) * 0.35;
  confidence -= Math.max(0, airflowCms - TRAINING_ENVELOPE.airflowMax) * 0.7;
  confidence -= extinctionProb * 18;
  confidence -= geometryDeviation * 10;
  if (!inDomain) confidence -= 6;
  return clamp(confidence, 22, 97);
}

function bandFromConfidence(
  inDomain: boolean,
  confidencePct: number,
): ConfidenceBand {
  if (!inDomain) return "LIMITED";
  if (confidencePct >= 82) return "HIGH";
  if (confidencePct >= 58) return "MODERATE";
  return "LIMITED";
}

/* ------------------------------------------------------------------ */
/* Derived hazard verdict                                               */
/* ------------------------------------------------------------------ */

export type MissionReadiness = "GO" | "CAUTION" | "ABORT";

export function assessMission(
  telemetry: Telemetry,
  isVentilationCut: boolean,
): MissionReadiness {
  if (isVentilationCut || telemetry.extinctionProb >= 0.7) return "GO";
  if (riskIndex(telemetry) >= 0.6 || telemetry.flameSpreadRate > 45) return "ABORT";
  return "CAUTION";
}

/** Normalized 0 - 1 composite risk index used for the readiness strip. */
export function riskIndex(telemetry: Telemetry): number {
  const spreadRisk = clamp01(telemetry.flameSpreadRate / 70);
  const smokeRisk = clamp01(telemetry.smokeYield / 80);
  const durationRisk = clamp01(telemetry.burnDuration / 180);
  const propagationRisk = 1 - telemetry.extinctionProb;
  return clamp01(
    0.34 * spreadRisk + 0.24 * smokeRisk + 0.18 * durationRisk + 0.24 * propagationRisk,
  );
}

export const TELEMETRY_REFERENCE = predictTelemetry(REFERENCE_ENVIRONMENT, false);