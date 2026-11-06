import type { HazardLevel, MaterialKey, MaterialRecord } from "./types";

/**
 * Traceable flammability reference set for the AstraFlame risk scoreboard.
 * Values are representative of NASA PSI microgravity combustion campaigns
 * (BASS-II, FLEX, SAFFIRE-I, SAME, SPICE) and are used both as the offline
 * training envelope and as the seed coefficients of the runtime predictor.
 */
export const MATERIALS: readonly MaterialRecord[] = [
  {
    key: "pmma",
    name: "PMMA (Acrylic)",
    shortName: "PMMA",
    flameSpreadRate: 42,
    minExtinctionO2: 12.5,
    smokeYield: 38,
    pyrolysisHeat: 1.05,
    flameLength: 10,
    sootFraction: 0.55,
    fuelLoad: 1,
    flameTempK: 1520,
    sourceTag: "BASS-II / PSI-25",
    hazard: "HIGH",
    smokeHazard: "HIGH",
    note: "Calibration reference specimen. Sharp luminous microgravity flame, high sooting, clean oxygen demand.",
  },
  {
    key: "nomex",
    name: "Nomex",
    shortName: "Nomex",
    flameSpreadRate: 18,
    minExtinctionO2: 15.5,
    smokeYield: 5,
    pyrolysisHeat: 0.42,
    flameLength: 6,
    sootFraction: 0.2,
    fuelLoad: 0.7,
    flameTempK: 1180,
    sourceTag: "FLEX / PSI-69",
    hazard: "LOW",
    smokeHazard: "LOW",
    note: "Self-extinguishing aramid used in crew garment layers; chars instead of propagating.",
  },
  {
    key: "silicone",
    name: "Silicone Rubber",
    shortName: "Silicone",
    flameSpreadRate: 27,
    minExtinctionO2: 16.5,
    smokeYield: 24,
    pyrolysisHeat: 0.78,
    flameLength: 8,
    sootFraction: 0.72,
    fuelLoad: 0.85,
    flameTempK: 1290,
    sourceTag: "FLEX / PSI-71",
    hazard: "MODERATE",
    smokeHazard: "MODERATE",
    note: "Gasket and seal stock. High silicone-oxide aerosol loading obscures optics quickly.",
  },
  {
    key: "polyethylene",
    name: "Polyethylene",
    shortName: "Polyethylene",
    flameSpreadRate: 55,
    minExtinctionO2: 13.5,
    smokeYield: 64,
    pyrolysisHeat: 1.22,
    flameLength: 12,
    sootFraction: 0.85,
    fuelLoad: 1.15,
    flameTempK: 1420,
    sourceTag: "SAFFIRE-I / PSI-98",
    hazard: "SEVERE",
    smokeHazard: "HIGH",
    note: "Worst-case cabin polymer. Fastest propagation and heaviest soot yield in the set.",
  },
  {
    key: "methanol",
    name: "Methanol Droplet",
    shortName: "Methanol",
    flameSpreadRate: 24,
    minExtinctionO2: 11,
    smokeYield: 9,
    pyrolysisHeat: 0.35,
    flameLength: 7,
    sootFraction: 0.18,
    fuelLoad: 0.35,
    flameTempK: 1250,
    sourceTag: "SAME / PSI-102",
    hazard: "MODERATE",
    smokeHazard: "LOW",
    note: "Liquid fuel mist hazard. Lowest extinction limit, so ignites in the widest O2 window.",
  },
];

export const HAZARD_RANK: Record<HazardLevel, number> = {
  LOW: 0,
  MODERATE: 1,
  HIGH: 2,
  SEVERE: 3,
};

/** Default dropdown order. */
export const MATERIAL_KEYS: readonly MaterialKey[] = MATERIALS.map((m) => m.key);

/** PMMA is the calibration reference material for every normalized coefficient. */
export const REFERENCE_MATERIAL: MaterialRecord = MATERIALS[0];

const MATERIAL_INDEX: Record<MaterialKey, MaterialRecord> = MATERIALS.reduce(
  (acc, material) => {
    acc[material.key] = material;
    return acc;
  },
  {} as Record<MaterialKey, MaterialRecord>,
);

export function getMaterial(key: MaterialKey): MaterialRecord {
  return MATERIAL_INDEX[key];
}