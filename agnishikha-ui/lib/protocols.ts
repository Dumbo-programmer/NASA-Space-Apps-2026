import { getMaterial } from "./materials";
import { clamp } from "./math";
import {
  CREW_O2_FLOOR,
  MODULE_VOLUME_M3,
  resolveEffectiveAirflow,
} from "./telemetry";
import type { EnvironmentState, Telemetry } from "./types";

export type ProtocolSeverity = "info" | "caution" | "critical";

export interface SuppressantOption {
  label: string;
  value: string;
}

export interface AirflowProtocol {
  severity: ProtocolSeverity;
  title: string;
  currentCms: number;
  recommendedCms: number;
  reductionPct: number;
  /** Seconds for the flame envelope to collapse once the setpoint is reached. */
  decaySeconds: number;
  directive: string;
  detail: string;
  /** Ordered crew actions, executed top to bottom. */
  steps: string[];
}

export interface SuppressantProtocol {
  severity: ProtocolSeverity;
  title: string;
  targetO2Pct: number;
  extinctionLimitO2Pct: number;
  purgeFractionPct: number;
  n2MassKg: number;
  crewFloorBreach: boolean;
  directive: string;
  detail: string;
  options: SuppressantOption[];
  steps: string[];
}

export interface SmokeProtocol {
  severity: ProtocolSeverity;
  title: string;
  regime: string;
  residenceSeconds: number;
  suspendedMassMg: number;
  wakeZones: string[];
  directive: string;
  detail: string;
  steps: string[];
}

export interface MitigationPlan {
  airflow: AirflowProtocol;
  suppressant: SuppressantProtocol;
  smoke: SmokeProtocol;
}

/** Oxygen concentration the cabin must recover above before masks come off. */
export const CREW_O2_RECOVERY_PCT = 14;

/** Nitrogen density (kg/m³) at the ambient pressure and a 294.15 K cabin. */
function nitrogenDensity(pressureKpa: number): number {
  return (pressureKpa * 1000 * 0.028013) / (8.314 * 294.15);
}

export function buildAirflowProtocol(
  environment: EnvironmentState,
  telemetry: Telemetry,
  isVentilationCut: boolean,
): AirflowProtocol {
  const currentCms = resolveEffectiveAirflow(environment, isVentilationCut);

  if (isVentilationCut) {
    return {
      severity: "info",
      title: "Airflow Shutdown Protocol",
      currentCms: 0,
      recommendedCms: 0,
      reductionPct: 100,
      decaySeconds: 3,
      directive: "DAMPER ISOLATED · HOLD 0 cm/s",
      detail:
        "Forced convection at the flame zone is already suppressed. Convective oxygen delivery has stopped and the flame is tracking passive extinction. Keep the damper shut until smoke opacity falls below 20 % and core temperature reads under 900 K.",
      steps: [
        "Hold the damper isolated at 0 cm/s — do not reopen for convection.",
        "Confirm flame length is decaying toward zero on the P1 visualizer.",
        "Wait for core temperature under 900 K and smoke opacity under 20 %.",
        "Reopen the damper only after the mitigation board clears to GO.",
      ],
    };
  }

  const target =
    telemetry.extinctionProb >= 0.5 ? 0 : Math.min(12, Math.round(currentCms / 2 / 0.5) * 0.5);
  const reductionPct =
    currentCms > 0 ? Math.round((1 - target / currentCms) * 100) : 0;
  const decaySeconds = Math.max(4, Math.round(telemetry.flameLength * 1.4 + 6));

  const severity: ProtocolSeverity =
    telemetry.flameSpreadRate > 45 || telemetry.extinctionProb < 0.3
      ? "critical"
      : telemetry.flameSpreadRate > 25
        ? "caution"
        : "info";

  return {
    severity,
    title: "Airflow Shutdown Protocol",
    currentCms,
    recommendedCms: target,
    reductionPct,
    decaySeconds,
    directive:
      target === 0
        ? `CLOSE CABIN FANS · ${currentCms.toFixed(1)} → 0.0 cm/s`
        : `REDUCE CABIN FANS · ${currentCms.toFixed(1)} → ${target.toFixed(1)} cm/s`,
    detail:
      severity === "critical"
        ? `Forced convection is feeding the reaction zone at ${currentCms.toFixed(1)} cm/s and the propagation front is outrunning the crew response window. Step the cabin fan setpoint down to ${target.toFixed(1)} cm/s; the flame envelope collapses in roughly ${decaySeconds} s at that setting.`
        : `Hold cabin velocity at or below ${target.toFixed(1)} cm/s. Microgravity flames are diffusion dominated, so each cm/s of forced convection adds stretch and soot entrainment; expect the envelope to relax in about ${decaySeconds} s.`,
    steps: [
      `Announce cabin fan reduction to ${target.toFixed(1)} cm/s on the fire loop.`,
      `Step the fan setpoint down from ${currentCms.toFixed(1)} cm/s and confirm the change.`,
      `Hold ${target.toFixed(1)} cm/s for ${decaySeconds} s — do not throttle airflow back up.`,
      "Log the envelope decay on P1 and hand off to the suppressant board.",
    ],
  };
}

export function buildSuppressantProtocol(
  environment: EnvironmentState,
  telemetry: Telemetry,
): SuppressantProtocol {
  const material = getMaterial(environment.material);
  const targetO2Pct = Math.round(clamp(material.minExtinctionO2 - 1.2, 6, 24) * 10) / 10;
  const purgeFractionPct =
    Math.round(clamp(1 - targetO2Pct / Math.max(environment.oxygenPct, 1), 0, 0.92) * 1000) /
    10;
  const n2MassKg =
    Math.round(
      (purgeFractionPct / 100) * MODULE_VOLUME_M3 * nitrogenDensity(environment.pressureKpa) * 100,
    ) / 100;
  const co2VolPct = Math.round(clamp((purgeFractionPct / 100) * 18, 2, 14) * 10) / 10;
  const waterMist = Math.round(clamp(0.8 + (purgeFractionPct / 100) * 1.6, 0.8, 3) * 100) / 100;

  const crewFloorBreach = targetO2Pct < CREW_O2_FLOOR;
  const severity: ProtocolSeverity = crewFloorBreach
    ? "critical"
    : purgeFractionPct > 35
      ? "caution"
      : "info";

  return {
    severity,
    title: "Suppressant Recommendation",
    targetO2Pct,
    extinctionLimitO2Pct: material.minExtinctionO2,
    purgeFractionPct,
    n2MassKg,
    crewFloorBreach,
    directive: `DRIVE LOCAL O₂ BELOW ${targetO2Pct.toFixed(1)} % · ${purgeFractionPct.toFixed(1)} % DILUTION`,
    detail: crewFloorBreach
      ? `${material.name} holds a flame down to ${material.minExtinctionO2.toFixed(1)} % O₂, so a ${targetO2Pct.toFixed(1)} % target drops module atmosphere under the ${CREW_O2_FLOOR.toFixed(1)} % crew egress floor. Purge from the ${MODULE_VOLUME_M3} m³ volume requires ~${purgeFractionPct.toFixed(1)} % displacement (≈ ${n2MassKg.toFixed(1)} kg N₂). Crew must be on continuous O₂ masks until concentration recovers above ${CREW_O2_RECOVERY_PCT} %.`
      : `A ${targetO2Pct.toFixed(1)} % local O₂ target sits ${(material.minExtinctionO2 - targetO2Pct).toFixed(1)} pp under the ${material.minExtinctionO2.toFixed(1)} % extinction limit for ${material.name} and stays above the ${CREW_O2_FLOOR.toFixed(1)} % crew egress floor. Displace ${purgeFractionPct.toFixed(1)} % of the ${MODULE_VOLUME_M3} m³ module volume (≈ ${n2MassKg.toFixed(1)} kg N₂ at ${environment.pressureKpa.toFixed(1)} kPa) into the flame zone.`,
    options: [
      { label: "N₂ dilution target", value: `${targetO2Pct.toFixed(1)} % O₂ · ${purgeFractionPct.toFixed(1)} % vol` },
      { label: "CO₂ flood concentration", value: `≥ ${co2VolPct.toFixed(1)} vol %` },
      { label: "Water mist density", value: `≥ ${waterMist.toFixed(2)} L·min⁻¹·m⁻³` },
      { label: "Predicted extinction prob.", value: `${(Math.max(telemetry.extinctionProb, 0.05) * 100).toFixed(0)} %` },
    ],
    steps: crewFloorBreach
      ? [
          `Don continuous O₂ masks before the purge — target ${targetO2Pct.toFixed(1)} % breaches the ${CREW_O2_FLOOR.toFixed(1)} % egress floor.`,
          `Arm the N₂ manifold for ≈ ${n2MassKg.toFixed(1)} kg into the ${MODULE_VOLUME_M3} m³ module volume.`,
          `Bleed ${purgeFractionPct.toFixed(1)} % displacement into the flame zone, watching local O₂ on the rail.`,
          `Hold until flame length reaches zero, then recover above ${CREW_O2_RECOVERY_PCT} % before doffing masks.`,
        ]
      : [
          `Arm the N₂ manifold for ≈ ${n2MassKg.toFixed(1)} kg into the ${MODULE_VOLUME_M3} m³ module volume.`,
          `Bleed ${purgeFractionPct.toFixed(1)} % displacement into the flame zone toward ${targetO2Pct.toFixed(1)} % local O₂.`,
          "Hold the target until the P1 envelope collapses — do not overshoot the purge.",
          `Recover cabin O₂ toward atmosphere before releasing the fire loop.`,
        ],
  };
}

export function buildSmokeProtocol(
  environment: EnvironmentState,
  telemetry: Telemetry,
  isVentilationCut: boolean,
): SmokeProtocol {
  const airflow = resolveEffectiveAirflow(environment, isVentilationCut);
  const sootHeavy = telemetry.smokeYield > 45;

  let regime: string;
  let wakeZones: string[];
  let severity: ProtocolSeverity;

  if (airflow < 4) {
    regime = "QUIESCENT SETTLING";
    wakeZones = [
      "Sample-holder shadow · 0.3 m downstream of the rig",
      "Ceiling-to-wall corner dead-zones",
      "Recirculation pockets behind stowage racks",
    ];
    severity = sootHeavy ? "critical" : "caution";
  } else if (airflow < 12) {
    regime = "LAMINAR RECIRCULATION";
    wakeZones = [
      "Low-velocity wake behind the sample holder",
      "Ceiling return grille boundary layer",
      "Aft wall corner vortices",
    ];
    severity = sootHeavy ? "critical" : "caution";
  } else if (airflow < 24) {
    regime = "CONTROLLED IMPINGEMENT";
    wakeZones = [
      "Direct impingement on the aft wall panel",
      "Shear layer above the ignition head",
      "EVA hatch seal interface",
    ];
    severity = sootHeavy ? "caution" : "info";
  } else if (airflow < 38) {
    regime = "SHEAR-DOMINATED TRANSPORT";
    wakeZones = [
      "Bulk convection across the full rack face",
      "Optics and lens hoods on the camera boom",
      "Payload bay filter inlet",
    ];
    severity = "info";
  } else {
    regime = "TURBULENT WAKE TRANSPORT";
    wakeZones = [
      "Separated shear layer at the duct transition",
      "Grille-adjacent eddies downstream of the fan",
      "Open volume transport toward the crew compartment",
    ];
    severity = "info";
  }

  const residenceSeconds = Math.round(
    60 * (1 + 40 / (airflow + 5)) * (telemetry.smokeYield / 50 + 0.35),
  );
  const suspendedMassMg = Math.round(
    (telemetry.smokeYield * residenceSeconds) / 60 * 0.35,
  );

  return {
    severity,
    title: "Smoke Particle Trajectory",
    regime,
    residenceSeconds,
    suspendedMassMg,
    wakeZones,
    directive: `PRIMARY AGGREGATION · ${regime}`,
    detail: `At ${airflow.toFixed(1)} cm/s the smoke wake stagnates inside the rig envelope for about ${residenceSeconds} s (${(residenceSeconds / 60).toFixed(1)} min), holding roughly ${suspendedMassMg.toLocaleString()} mg of suspended soot in the cabin volume. Astronauts should treat the listed low-velocity regions as the highest obscuration and inhalation zones during the burn window.`,
    steps: [
      `Stow loose optics and lens hoods away from the ${regime.toLowerCase()} field.`,
      "Don particulate respirators before the soot front reaches the cabin volume.",
      `Keep clear of the listed wake zones — residence time runs about ${(residenceSeconds / 60).toFixed(1)} min.`,
      "Run the cabin particulate loop after flame length reaches zero.",
    ],
  };
}

export function buildMitigationPlan(
  environment: EnvironmentState,
  telemetry: Telemetry,
  isVentilationCut: boolean,
): MitigationPlan {
  return {
    airflow: buildAirflowProtocol(environment, telemetry, isVentilationCut),
    suppressant: buildSuppressantProtocol(environment, telemetry),
    smoke: buildSmokeProtocol(environment, telemetry, isVentilationCut),
  };
}