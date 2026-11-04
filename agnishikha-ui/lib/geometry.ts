import {
  BURNER_DIAMETER_LIMIT,
  ORIENTATION_LIMIT,
  SAMPLE_THICKNESS_LIMIT,
  SAMPLE_WIDTH_LIMIT,
} from "./axes";
import { clamp } from "./math";
import type { GeometryState } from "./types";

/** BASS-II reference rig geometry. Every geometry factor is pinned to 1.0 here. */
export const REFERENCE_GEOMETRY: GeometryState = {
  burnerDiameterMm: BURNER_DIAMETER_LIMIT.nominal,
  sampleWidthMm: SAMPLE_WIDTH_LIMIT.nominal,
  sampleThicknessMm: SAMPLE_THICKNESS_LIMIT.nominal,
  orientationDeg: ORIENTATION_LIMIT.nominal,
};

/** True when the rig matches the geometry the surrogate was pinned against. */
export function isReferenceGeometry(geometry: GeometryState): boolean {
  return (
    geometry.burnerDiameterMm === REFERENCE_GEOMETRY.burnerDiameterMm &&
    geometry.sampleWidthMm === REFERENCE_GEOMETRY.sampleWidthMm &&
    geometry.sampleThicknessMm === REFERENCE_GEOMETRY.sampleThicknessMm &&
    geometry.orientationDeg === REFERENCE_GEOMETRY.orientationDeg
  );
}

/**
 * Rig-geometry coupling for spread rate and envelope size.
 *
 * The PSI campaigns vary sample thickness and burner diameter, but this build
 * seeds the surrogate from material-level means, so geometry is applied here as
 * an explicit operator-scaling term rather than a fitted coefficient. It is
 * pinned to exactly 1.0 at REFERENCE_GEOMETRY, so the BASS-II calibration case
 * is unchanged, and it carries no claim of experimental validation.
 *
 * - wider sample   -> more lateral surface to propagate across
 * - thicker sample -> more fuel mass per unit area, so a longer burn
 * - larger burner   -> lower strain rate at the same velocity, so less stretch
 * - vertical sample burns at the reference rate; horizontal runs slightly hotter
 */
export function geometryFactor(geometry: GeometryState): number {
  const width = clamp(
    geometry.sampleWidthMm / SAMPLE_WIDTH_LIMIT.nominal,
    0.4,
    2,
  );
  const thickness = clamp(
    geometry.sampleThicknessMm / SAMPLE_THICKNESS_LIMIT.nominal,
    0.33,
    2,
  );
  const burner = clamp(
    BURNER_DIAMETER_LIMIT.nominal / geometry.burnerDiameterMm,
    0.5,
    2.5,
  );
  const tilt = 1 - Math.sin((geometry.orientationDeg * Math.PI) / 180);
  const orientation = 1 + 0.1 * tilt;

  return clamp(width * thickness * burner * orientation, 0.2, 3);
}

/** 0 - 1 measure of how far the rig sits from the pinned geometry. */
export function geometryDeviation(geometry: GeometryState): number {
  const axes = [
    [geometry.burnerDiameterMm, BURNER_DIAMETER_LIMIT],
    [geometry.sampleWidthMm, SAMPLE_WIDTH_LIMIT],
    [geometry.sampleThicknessMm, SAMPLE_THICKNESS_LIMIT],
    [geometry.orientationDeg, ORIENTATION_LIMIT],
  ] as const;

  let worst = 0;
  for (const [value, axis] of axes) {
    const span = axis.max - axis.min;
    worst = Math.max(worst, Math.abs(value - axis.nominal) / span);
  }
  return clamp(worst * 2, 0, 1);
}