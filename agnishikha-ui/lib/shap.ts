import { getMaterial, REFERENCE_MATERIAL } from "./materials";
import { EXPERIMENTS } from "./experiments";
import { clamp01, signed } from "./math";
import {
  AIRFLOW_LIMIT,
  OXYGEN_LIMIT,
  PRESSURE_LIMIT,
  predictTelemetry,
  resolveEffectiveAirflow,
} from "./telemetry";
import type { EnvironmentState, MaterialKey, Telemetry } from "./types";

export type ShapKey = "oxygen" | "airflow" | "material" | "pressure";

export type ShapTone = "up" | "down" | "neutral";

export interface ShapDriver {
  key: ShapKey;
  label: string;
  shortLabel: string;
  /** Normalized global importance share in percent. The four shares sum to 100. */
  impactPct: number;
  /** Signed per-sample contribution to the predicted spread rate, mm/s. */
  contribution: number;
  tone: ShapTone;
  detail: string;
  /** True for the feature carrying the largest |contribution| for this sample. */
  dominant: boolean;
}

export interface SimilarExperiment {
  name: string;
  tag: string;
  match: number;
}

/**
 * One row of the nominal-condition comparison against the PSI registry.
 *
 * `registry` is the campaign mean recorded at 21 % O2 / 101.3 kPa in still
 * cabin air. `model` is what the surrogate predicts for the *active* case, so
 * the gap is a nominal-vs-active delta and not a model validation residual -
 * they only coincide at the calibration case.
 */
export interface RegistryComparison {
  label: string;
  unit: string;
  registry: number;
  model: number;
  digits: number;
}

export interface ShapExplanation {
  drivers: ShapDriver[];
  /** f(base): prediction with every feature at its calibration value. */
  basePrediction: number;
  /** f(x): prediction for the active case. */
  currentPrediction: number;
  /** Same case with the damper forced open, mm/s. */
  openDamperPrediction: number;
  /** Spread shift caused by the damper state itself (not a feature), mm/s. */
  damperDelta: number;
  /** Sum of |phi| across the four features for this sample, mm/s. */
  totalAbsContribution: number;
  topDriver: ShapDriver;
  modelLabel: string;
  similarExperiments: SimilarExperiment[];
  registryVsModel: RegistryComparison[];
}

/**
 * Baseline global importances from the offline SHAP summary over the PSI
 * training set. They reproduce exactly at the calibration state (PMMA, 21 % O2,
 * 101.3 kPa, 10 cm/s) and re-weight away from it as features move.
 */
const BASE_IMPORTANCE: Record<ShapKey, number> = {
  oxygen: 42,
  airflow: 28,
  material: 18,
  pressure: 12,
};

/** Fixed ablation order for the per-sample decomposition. */
const FEATURE_ORDER: ShapKey[] = ["oxygen", "airflow", "material", "pressure"];

/** Sensitivity of attribution to a unit-normalized departure from nominal. */
const DEVIATION_GAIN = 0.6;
const OXYGEN_SPAN = (OXYGEN_LIMIT.max - OXYGEN_LIMIT.nominal) / 2;
const AIRFLOW_SPAN = AIRFLOW_LIMIT.max - AIRFLOW_LIMIT.nominal;
const PRESSURE_SPAN = Math.max(
  PRESSURE_LIMIT.max - PRESSURE_LIMIT.nominal,
  PRESSURE_LIMIT.nominal - PRESSURE_LIMIT.min,
);
const MATERIAL_SPAN = 24;

interface FeatureSnapshot {
  oxygen: number;
  airflow: number;
  material: MaterialKey;
  pressure: number;
}

function toneFromSign(value: number, epsilon = 0.15): ShapTone {
  if (value > epsilon) return "up";
  if (value < -epsilon) return "down";
  return "neutral";
}

/**
 * Single-sample additive explanation of the flame spread prediction.
 *
 * Importance ranking comes from the global SHAP summary. The per-sample term
 * uses an ordered ablation: each feature is relaxed from its calibration value
 * to the active value one at a time, and the marginal change in f is recorded
 * as that feature's phi. The four terms are therefore exact - they sum to
 * f(x) - f(base) with no residual - and each keeps its true sign.
 *
 * The emergency damper is a context switch rather than a regression feature,
 * so its effect is reported separately as damperDelta.
 */
export function explainPrediction(
  environment: EnvironmentState,
  telemetry: Telemetry,
  isVentilationCut: boolean,
): ShapExplanation {
  const material = getMaterial(environment.material);

  const currentFeatures: FeatureSnapshot = {
    oxygen: environment.oxygenPct,
    airflow: resolveEffectiveAirflow(environment, isVentilationCut),
    material: environment.material,
    pressure: environment.pressureKpa,
  };

  const nominalFeatures: FeatureSnapshot = {
    oxygen: OXYGEN_LIMIT.nominal,
    airflow: AIRFLOW_LIMIT.nominal,
    material: REFERENCE_MATERIAL.key,
    pressure: PRESSURE_LIMIT.nominal,
  };

  const evaluate = (features: FeatureSnapshot): number =>
    predictTelemetry(
      {
        oxygenPct: features.oxygen,
        pressureKpa: features.pressure,
        airflowCms: features.airflow,
        material: features.material,
        experiment: environment.experiment,
        geometry: environment.geometry,
      },
      isVentilationCut,
    ).flameSpreadRate;

  const basePrediction = evaluate(nominalFeatures);
  const openDamperPrediction = predictTelemetry(environment, false).flameSpreadRate;

  const contributionByKey = {} as Record<ShapKey, number>;
  let running = nominalFeatures;
  let runningPrediction = basePrediction;
  for (const key of FEATURE_ORDER) {
    const stepped: FeatureSnapshot = { ...running, [key]: currentFeatures[key] };
    const steppedPrediction = evaluate(stepped);
    contributionByKey[key] = steppedPrediction - runningPrediction;
    running = stepped;
    runningPrediction = steppedPrediction;
  }
  const currentPrediction = runningPrediction;

  const deviations: Record<ShapKey, number> = {
    oxygen: Math.abs(currentFeatures.oxygen - OXYGEN_LIMIT.nominal) / OXYGEN_SPAN,
    airflow: Math.abs(currentFeatures.airflow - AIRFLOW_LIMIT.nominal) / AIRFLOW_SPAN,
    material:
      Math.abs(material.flameSpreadRate - REFERENCE_MATERIAL.flameSpreadRate) /
      MATERIAL_SPAN,
    pressure:
      Math.abs(currentFeatures.pressure - PRESSURE_LIMIT.nominal) / PRESSURE_SPAN,
  };

  const magnitudeSum = FEATURE_ORDER.reduce(
    (sum, key) =>
      sum + BASE_IMPORTANCE[key] * (1 + DEVIATION_GAIN * deviations[key]),
    0,
  );

  const details: Record<ShapKey, string> = {
    oxygen: `${environment.oxygenPct.toFixed(1)} % O₂ ${signed(
      currentFeatures.oxygen - OXYGEN_LIMIT.nominal,
      1,
      " pp",
    )} vs 21.0 % nominal`,
    airflow: isVentilationCut
      ? `Damper isolated → 0.0 cm/s at the flame zone`
      : `${telemetry.effectiveAirflowCms.toFixed(1)} cm/s ${signed(
          currentFeatures.airflow - AIRFLOW_LIMIT.nominal,
          1,
          " cm/s",
        )} vs 10.0 cm/s nominal`,
    material: `${material.name} · pyrolysis ×${material.pyrolysisHeat.toFixed(2)}`,
    pressure: `${environment.pressureKpa.toFixed(1)} kPa ${signed(
      currentFeatures.pressure - PRESSURE_LIMIT.nominal,
      1,
      " kPa",
    )} vs 101.3 kPa nominal`,
  };

  const labels: Record<ShapKey, { label: string; shortLabel: string }> = {
    oxygen: { label: "O₂ Concentration", shortLabel: "O₂" },
    airflow: { label: "Airflow Velocity", shortLabel: "AIRFLOW" },
    material: { label: "Material Pyrolysis Heat", shortLabel: "PYROLYSIS" },
    pressure: { label: "Ambient Pressure", shortLabel: "PRESSURE" },
  };

  const drivers: ShapDriver[] = FEATURE_ORDER.map((key) => ({
    key,
    label: labels[key].label,
    shortLabel: labels[key].shortLabel,
    impactPct: Math.round(
      ((BASE_IMPORTANCE[key] * (1 + DEVIATION_GAIN * deviations[key])) /
        magnitudeSum) *
        100,
    ),
    contribution: Math.round(contributionByKey[key] * 10) / 10,
    tone: toneFromSign(contributionByKey[key]),
    detail: details[key],
    dominant: false,
  }));

  // Reconcile integer rounding so the four shares always sum to exactly 100.
  const roundedTotal = drivers.reduce((sum, driver) => sum + driver.impactPct, 0);
  drivers[0].impactPct += 100 - roundedTotal;

  const maxAbsContribution = drivers.reduce(
    (best, driver) =>
      Math.abs(driver.contribution) > Math.abs(best) ? driver.contribution : best,
    0,
  );
  const dominantKey: ShapKey | null =
    Math.abs(maxAbsContribution) > 0.05
      ? (drivers.find((driver) => driver.contribution === maxAbsContribution)?.key ??
        null)
      : null;
  for (const driver of drivers) {
    driver.dominant = driver.key === dominantKey;
  }

  const ranked = [...drivers].sort((a, b) => b.impactPct - a.impactPct);

  /*
   * Similar campaigns are ranked by a genuine weighted distance in the same
   * normalized four-feature space that defines the importance shares, measured
   * against each campaign's published conditions. Distance 0 - the active case
   * sitting exactly on a published campaign - maps to 100 %.
   */
  const importanceWeight: Record<ShapKey, number> = {
    oxygen: BASE_IMPORTANCE.oxygen / 100,
    airflow: BASE_IMPORTANCE.airflow / 100,
    material: BASE_IMPORTANCE.material / 100,
    pressure: BASE_IMPORTANCE.pressure / 100,
  };

  const activeVector: Record<ShapKey, number> = {
    oxygen: (currentFeatures.oxygen - OXYGEN_LIMIT.nominal) / OXYGEN_SPAN,
    airflow: (currentFeatures.airflow - AIRFLOW_LIMIT.nominal) / AIRFLOW_SPAN,
    material:
      (material.flameSpreadRate - REFERENCE_MATERIAL.flameSpreadRate) / MATERIAL_SPAN,
    pressure:
      (currentFeatures.pressure - PRESSURE_LIMIT.nominal) / PRESSURE_SPAN,
  };

  const similarExperiments = EXPERIMENTS.filter((preset) => preset.key !== "custom")
    .map((preset) => {
      const campaignMaterial = getMaterial(preset.material);
      const campaignVector: Record<ShapKey, number> = {
        oxygen: (preset.oxygenPct - OXYGEN_LIMIT.nominal) / OXYGEN_SPAN,
        airflow: (preset.airflowCms - AIRFLOW_LIMIT.nominal) / AIRFLOW_SPAN,
        material:
          (campaignMaterial.flameSpreadRate - REFERENCE_MATERIAL.flameSpreadRate) /
          MATERIAL_SPAN,
        pressure: (preset.pressureKpa - PRESSURE_LIMIT.nominal) / PRESSURE_SPAN,
      };

      const squared = FEATURE_ORDER.reduce(
        (sum, key) =>
          sum +
          importanceWeight[key] * (activeVector[key] - campaignVector[key]) ** 2,
        0,
      );
      const distance = Math.sqrt(squared);

      return {
        name: `${preset.campaign} ${campaignMaterial.shortName}`,
        tag: preset.sourceTag,
        match: Math.round(clamp01(Math.exp(-1.5 * distance)) * 100),
      };
    })
    .sort((a, b) => b.match - a.match || a.name.localeCompare(b.name));

  /*
   * Nominal-condition comparison against the PSI registry. Every `registry`
   * value below is a real campaign mean from `lib/materials.ts`; nothing here
   * is synthesised. Because those means were recorded at 21 % O2 / 101.3 kPa in
   * still air, the gap against the active prediction is a nominal-vs-active
   * delta rather than a validation residual.
   */
  const registryVsModel: RegistryComparison[] = [
    {
      label: "Flame spread",
      unit: "mm/s",
      registry: material.flameSpreadRate,
      model: currentPrediction,
      digits: 1,
    },
    {
      label: "Smoke yield",
      unit: "mg/min",
      registry: material.smokeYield,
      model: telemetry.smokeYield,
      digits: 1,
    },
    {
      label: "Peak flame temp",
      unit: "K",
      registry: material.flameTempK,
      model: telemetry.flameTempK,
      digits: 0,
    },
  ];

  return {
    drivers: ranked,
    basePrediction,
    currentPrediction,
    openDamperPrediction,
    damperDelta: Math.round((currentPrediction - openDamperPrediction) * 10) / 10,
    totalAbsContribution:
      Math.round(
        drivers.reduce((sum, driver) => sum + Math.abs(driver.contribution), 0) * 10,
      ) / 10,
    topDriver: ranked[0],
    modelLabel: "astra-xgb TreeSHAP surrogate v2.4",
    similarExperiments,
    registryVsModel,
  };
}