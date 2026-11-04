/**
 * Operator input envelope shared by the scenario controls and the predictor.
 * Every axis carries its nominal so the UI can show the calibration tick and
 * the model can pin geometry factors to 1.0 at the reference point.
 */

export interface AxisLimit {
  min: number;
  max: number;
  nominal: number;
  step: number;
  unit: string;
}

export const OXYGEN_LIMIT: AxisLimit = {
  min: 12,
  max: 30,
  nominal: 21,
  step: 0.1,
  unit: "% O₂",
};

export const PRESSURE_LIMIT: AxisLimit = {
  min: 50,
  max: 110,
  nominal: 101.3,
  step: 0.1,
  unit: "kPa",
};

export const AIRFLOW_LIMIT: AxisLimit = {
  min: 0,
  max: 50,
  nominal: 10,
  step: 0.5,
  unit: "cm/s",
};

export const BURNER_DIAMETER_LIMIT: AxisLimit = {
  min: 10,
  max: 50,
  nominal: 25,
  step: 1,
  unit: "mm",
};

export const SAMPLE_WIDTH_LIMIT: AxisLimit = {
  min: 20,
  max: 100,
  nominal: 50,
  step: 1,
  unit: "mm",
};

export const SAMPLE_THICKNESS_LIMIT: AxisLimit = {
  min: 2,
  max: 12,
  nominal: 6,
  step: 0.5,
  unit: "mm",
};

export const ORIENTATION_LIMIT: AxisLimit = {
  min: 0,
  max: 90,
  nominal: 90,
  step: 5,
  unit: "°",
};

/** NASA validated training envelope for the surrogate model. */
export const TRAINING_ENVELOPE = {
  oxygenMin: 12,
  oxygenMax: 25,
  pressureMin: 70,
  pressureMax: 101.3,
  airflowMax: 30,
} as const;

/** Assumed habitable module volume used by the suppressant mass budget. */
export const MODULE_VOLUME_M3 = 62;

/** Crew oxygen floor for unrestricted egress (NASA-STD-3001 / SMAC). */
export const CREW_O2_FLOOR = 12;