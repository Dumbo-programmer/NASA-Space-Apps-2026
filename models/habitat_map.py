"""
AstraFlame - habitat fire map (novelty thread: "what does NASA know about the habitat atmosphere?")

Builds one JSON (models/reports/habitat_map.json, copied to agnishikha-ui/public/ignis/) holding:
  1. coverage   - how much microgravity data exists near the habitat (8.2 psia = 56.5 kPa, 34 % O2)
  2. grid       - FLEX methanol extinction probability over O2 x pressure + distance to nearest NASA test
  3. tests      - every NASA microgravity test with O2 and pressure (dots on the map)
  4. materials  - material safety card from WSTF 1g oxygen limits (Hirsch 2011), burn / no-burn at ISS and habitat O2
  5. next_tests - top recommended FLEX tests inside the habitat envelope (uncertainty x distance rule, same as v3_final)
Run: python habitat_map.py   (needs the trained bundles in models/artifacts)
"""
import json
import warnings

import joblib
import numpy as np
import pandas as pd

import config as C
import preprocess_v3 as P

warnings.filterwarnings("ignore")
HAB = {"o2_pct": 34.0, "pressure_kpa": 56.5, "label": "Proposed habitat (8.2 psia, 34 % O2)"}
ISS = {"o2_pct": 21.0, "pressure_kpa": 101.3, "label": "ISS air (14.7 psia, 21 % O2)"}
O2_LO, O2_HI, P_LO, P_HI = 12.0, 36.0, 40.0, 320.0


def coverage(mg):
    d_o2 = (mg.oxygen_pct - HAB["o2_pct"]) / (O2_HI - O2_LO)
    d_p = (mg.pressure_kpa - HAB["pressure_kpa"]) / (P_HI - P_LO)
    dist = np.sqrt(d_o2 ** 2 + d_p ** 2).dropna()
    has_p = mg.pressure_kpa.notna() & mg.oxygen_pct.notna()
    return {
        "microgravity_rows": int(len(mg)),
        "rows_with_o2_and_pressure": int(has_p.sum()),
        "rows_at_or_below_70kpa": int((mg.pressure_kpa <= 70).sum()),
        "lowest_tested_pressure_kpa": float(mg.pressure_kpa.min()),
        "rows_o2_30_or_more": int((mg.oxygen_pct >= 30).sum()),
        "rows_o2_30_or_more_solids": int(((mg.oxygen_pct >= 30) & (mg.material_class == "solid")).sum()),
        "max_o2_solid_pct": float(mg[mg.material_class == "solid"].oxygen_pct.max()),
        "rows_within_box_o2_30_36_p_45_70": int(((mg.oxygen_pct.between(30, 36)) & (mg.pressure_kpa.between(45, 70))).sum()),
        "nearest_test_distance_normalised": round(float(dist.min()), 3),
        "lowest_test_above_habitat_by_kpa": round(float(mg.pressure_kpa.min() - HAB["pressure_kpa"]), 1),
    }


def material_card(d):
    w = d[d.outcome_variable == "maximum_oxygen_concentration_MOC"].copy()
    w["moc"] = w.outcome_value
    g = w.groupby("fuel_material").agg(moc_med=("moc", "median"), moc_min=("moc", "min"), moc_max=("moc", "max"), n=("moc", "size"),
                                       tested_kpa=("pressure_kpa", lambda s: sorted(set(round(v, 1) for v in s))))
    rows = []
    for name, r in g.iterrows():
        rows.append({
            "material": name, "moc_pct": float(r.moc_med), "moc_min_pct": float(r.moc_min), "moc_max_pct": float(r.moc_max), "n_tests": int(r.n),
            "tested_kpa": r.tested_kpa,
            # headline limit = median of the material's tests (gives the 12 / 20 of 22 in the brief);
            # the 34 % result (20 of 22) is the same under min, median, mean and max
            "burns_at_21": bool(r.moc_med <= 21.0), "burns_at_34": bool(r.moc_med <= HAB["o2_pct"]),
            "margin_at_34_pct_o2": round(float(HAB["o2_pct"] - r.moc_med), 1),
            "note": "1g data at 70-101 kPa; 56.5 kPa is extrapolated",
        })
    return sorted(rows, key=lambda x: x["moc_pct"])


def main():
    d = pd.read_csv(C.DATA_DIR / "Ignis_mu_unified_master_v1.0.csv")
    mg = d[d.gravity_level == "microgravity"]
    S = P.all_specs()
    fx = joblib.load(C.artifact("flex_extinction.joblib"))["model"]
    flex = S["flex_extinction"]["df"]
    meth = flex[flex.fuel == "Methanol"]

    O2 = np.linspace(O2_LO, O2_HI, 61); PR = np.linspace(P_LO, P_HI, 61)
    OO, PP = np.meshgrid(O2, PR)
    G = pd.DataFrame({"fuel": "Methanol", "pressure_kpa": PP.ravel(), "o2_pct": OO.ravel(), "co2_pct": 0.0, "he_pct": 0.0, "d0_mm": 3.0})
    p_ext = fx.predict_proba(P.flex_features(G))[:, 1]
    Zt = np.c_[(meth.o2_pct - O2_LO) / (O2_HI - O2_LO), (meth.pressure_kpa - P_LO) / (P_HI - P_LO)]
    Zg = np.c_[(G.o2_pct - O2_LO) / (O2_HI - O2_LO), (G.pressure_kpa - P_LO) / (P_HI - P_LO)]
    dist = np.sqrt(((Zg[:, None, :] - Zt[None, :, :]) ** 2).sum(2)).min(1)

    # next tests: uncertainty x distance, restricted to the habitat envelope (O2 >= 21, 45-101 kPa)
    score = p_ext * (1 - p_ext) * np.minimum(dist / 0.15, 1.0)
    env = (G.o2_pct >= 21) & (G.pressure_kpa.between(45, 101.3))
    order = np.argsort(-np.where(env, score, -1))
    picks, used = [], []
    for i in order:                       # greedy, keep picks apart so they are not near-duplicates
        z = Zg[i]
        if all(np.hypot(*(z - u)) > 0.12 for u in used):
            picks.append({"o2_pct": round(float(G.o2_pct[i]), 1), "pressure_kpa": round(float(G.pressure_kpa[i]), 1),
                          "p_extinguish": round(float(p_ext[i]), 3), "distance_to_nearest_test": round(float(dist[i]), 3),
                          "score": round(float(score[i]), 4)})
            used.append(z)
        if len(picks) == 5:
            break
    keep = ["source_investigation", "material_class", "fuel_material", "oxygen_pct", "pressure_kpa"]
    tests = (mg[keep].dropna(subset=["oxygen_pct", "pressure_kpa"]).round(2)
             .rename(columns={"source_investigation": "src", "material_class": "cls", "fuel_material": "mat",
                              "oxygen_pct": "o2", "pressure_kpa": "p"}).to_dict("records"))
    here = fx.predict_proba(P.flex_features(pd.DataFrame([{"fuel": "Methanol", "pressure_kpa": HAB["pressure_kpa"], "o2_pct": HAB["o2_pct"], "co2_pct": 0.0, "he_pct": 0.0, "d0_mm": 3.0}])))[:, 1][0]
    mats = material_card(d)
    out = {
        "habitat": HAB, "iss": ISS, "axes": {"o2": [O2_LO, O2_HI], "pressure_kpa": [P_LO, P_HI]},
        "coverage": coverage(mg),
        "habitat_point_prediction": {"fuel": "Methanol droplet (3 mm)", "p_extinguish": round(float(here), 3),
                                     "status": "extrapolation: no microgravity test below 70 kPa in this dataset"},
        "grid": {"o2": [round(float(v), 2) for v in O2], "pressure_kpa": [round(float(v), 1) for v in PR],
                 "p_extinguish": [round(float(v), 3) for v in p_ext.reshape(OO.shape).ravel()],
                 "distance": [round(float(v), 3) for v in dist]},
        "tests": tests, "next_tests": picks,
        "materials": {"n": len(mats), "burn_at_21": sum(m["burns_at_21"] for m in mats),
                      "burn_at_34": sum(m["burns_at_34"] for m in mats), "items": mats,
                      "caveat": "Hirsch 2011 1g data at 70-101 kPa. 56.5 kPa is outside it; first estimate only."},
        "layers_note": "Heat map = FLEX methanol droplets (microgravity). Material markers = 1g solids. Different data, shown on the same axes for context only.",
    }
    (C.REPORTS / "habitat_map.json").write_text(json.dumps(out, separators=(",", ":")))
    pd.DataFrame(mats).to_csv(C.REPORTS / "material_safety_card.csv", index=False)
    print(json.dumps({k: out[k] for k in ("coverage", "habitat_point_prediction", "next_tests")}, indent=1))
    print("materials:", out["materials"]["n"], "burn@21:", out["materials"]["burn_at_21"], "burn@34:", out["materials"]["burn_at_34"])


if __name__ == "__main__":
    main()
