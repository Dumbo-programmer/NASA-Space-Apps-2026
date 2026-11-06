"""
Ignis mu / AgniShikha - strict data contract for data/processed (runs before any model is trained).
Data Science Lead: Prachya Biswas

    python data/scripts/validate_processed.py            # exit 0 = every check passed; report -> data/validation_report.json

What is checked, per processed file
  schema        every required column exists; numeric columns really are numeric
  identity      primary key present and unique; expected row count (frozen dataset v1.0.x)
  categories    closed sets (fuel, gravity, campaign, PSI id, ...) contain only known values
  physics       values inside physical / experimental bounds (O2 0-100 %, sizes > 0, mole fractions sum ~1, ...)
  consistency   derived columns agree with their sources (kPa = mmHg x 0.1333, o2_pct = 100 x_O2, 1/d, ...)
  lineage       every master-table row points to an existing record in its source file
Model-time checks (group leakage in every CV split, target leakage in features) live in models/ml_selection.py and
models/preprocess_v3.py, because a leak is a property of a split or a feature set, not of a data file.
"""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd

DATA = Path(__file__).resolve().parents[1]
PROC = Path(os.environ.get("IGNIS_DATA_DIR", DATA / "processed"))      # override to validate a copy
ERRORS, WARNINGS, PASSED = [], [], []


def check(ok, msg, warn=False):
    if ok:
        PASSED.append(msg)
    else:
        (WARNINGS if warn else ERRORS).append(msg)


def bounds(df, f, col, lo, hi):
    v = pd.to_numeric(df[col], errors="coerce").dropna()
    bad = v[(v < lo) | (v > hi)]
    check(bad.empty, f"{f}: {col} within [{lo}, {hi}]" + ("" if bad.empty else f" - {len(bad)} rows out, e.g. {bad.iloc[0]}"))


CONTRACT = {
    "BASS-II_flame_spread_microgravity_v1.0.csv": dict(
        rows=52, key="record_id",
        numeric=["diameter_cm", "diameter_mm", "inv_diameter_per_cm", "o2_pct", "opposed_flow_cm_s", "flow_step", "flame_spread_mm_s"],
        required=["test_id", "pmma_color", "source", "value_type"],
        categories={"gravity": {"microgravity"}, "psi_id": {"PSI-25"}, "pmma_color": {"black", "clear"}},
        bounds={"o2_pct": (10, 30), "opposed_flow_cm_s": (0.1, 20), "diameter_cm": (0.1, 5), "flame_spread_mm_s": (0.001, 1.0)}),
    "FLEX_PSI-69_clean_v1.0.csv": dict(
        rows=274, key="record_id",
        numeric=["pressure_kpa", "x_O2", "x_N2", "x_CO2", "x_He", "o2_pct", "d0_mm", "burning_rate_K_mm2_s", "extinguished"],
        required=["flex_id", "fuel", "test_end", "use_for_extinction_model", "source"],
        categories={"fuel": {"Methanol", "Heptane"}, "test_end": {"Extinction", "Completion", "Disruption"}, "psi_id": {"PSI-69"}},
        bounds={"pressure_kpa": (30, 1000), "x_O2": (0, 1), "x_N2": (0, 1), "x_CO2": (0, 1), "x_He": (0, 1), "o2_pct": (0, 100),
                "d0_mm": (0.1, 10), "d_ext_mm": (0, 10), "burning_rate_K_mm2_s": (0, 3), "burn_time_s": (0, 300)}),
    "SPICE_PSI-107_smoke_points_v1.0.csv": dict(
        rows=55, key="record_id",
        numeric=["burner_diameter_mm", "coflow_air_velocity_cm_s", "smoke_point_length_mm", "fuel_mole_fraction", "gmt_day_2009"],
        required=["fuel", "source"],
        categories={"fuel": {"Ethylene", "Propane", "Propylene", "Propylene/N2 50%", "Propylene/N2 75%"}, "psi_id": {"PSI-107"}},
        bounds={"burner_diameter_mm": (0.1, 10), "coflow_air_velocity_cm_s": (0, 200), "smoke_point_length_mm": (1, 500),
                "fuel_mole_fraction": (0, 1), "gmt_day_2009": (1, 366)}),
    "SAME_PSI-101-102_smoke_particles_v1.0.csv": dict(
        rows=154, key="record_id",
        numeric=["inlet_air_velocity_cm_s", "heater_resistance_ratio_rt_r0", "sample_temperature_c", "net_aging_time_s", "count_mean_diameter_um"],
        required=["campaign", "same_run", "material", "use_for_particle_size_model", "source"],
        categories={"psi_id": {"PSI-101", "PSI-102"}},
        bounds={"inlet_air_velocity_cm_s": (0, 50), "heater_resistance_ratio_rt_r0": (1, 3), "sample_temperature_c": (20, 1000),
                "net_aging_time_s": (0, 10000), "count_mean_diameter_um": (0.001, 10), "geometric_std_dev": (1, 10)}),
    "BASS_PSI-26_test_log_v1.0.csv": dict(
        rows=121, key="record_id", numeric=["o2_pct", "pressure_kpa"], required=["material_family", "outcome_label", "source"],
        categories={"psi_id": {"PSI-26"}}, bounds={"o2_pct": (10, 30), "pressure_kpa": (50, 150)}),
    "SAFFIRE_I-III_PSI-98-100_v1.0.csv": dict(
        rows=13, key="record_id", numeric=["flow_cm_s"], required=["material", "source"], categories={},
        bounds={"flow_cm_s": (0, 100), "thickness_mm": (0, 100)}),
    "Ignis_mu_unified_master_v1.0.csv": dict(
        rows=850, key="experiment_id", numeric=["oxygen_pct", "pressure_kpa", "airflow_cm_s", "outcome_value"],
        required=["source_investigation", "psi_id", "gravity_level", "source_ref", "source_record_id", "value_type"],
        categories={}, bounds={"oxygen_pct": (0, 100), "pressure_kpa": (0, 1000), "airflow_cm_s": (0, 200), "characteristic_size_mm": (0, 1000),
                               "temperature_c": (-50, 1500)}),
}


def validate():
    frames = {}
    for f, c in CONTRACT.items():
        p = PROC / f
        check(p.exists(), f"{f}: file exists")
        if not p.exists():
            continue
        df = pd.read_csv(p); frames[f] = df
        missing = [col for col in c["numeric"] + c["required"] + [c["key"]] if col not in df.columns]
        check(not missing, f"{f}: required columns present" + (f" - missing {missing}" if missing else ""))
        for col in c["numeric"]:
            if col in df:
                check(pd.api.types.is_numeric_dtype(df[col]), f"{f}: {col} is numeric")
        check(len(df) == c["rows"], f"{f}: {c['rows']} rows (found {len(df)})")
        check(df[c["key"]].notna().all() and df[c["key"]].is_unique, f"{f}: {c['key']} present and unique")
        for col, allowed in c["categories"].items():
            extra = set(df[col].dropna().unique()) - allowed
            check(not extra, f"{f}: {col} only in {sorted(allowed)}" + (f" - unexpected {sorted(extra)}" if extra else ""))
        for col, (lo, hi) in c["bounds"].items():
            if col in df:
                bounds(df, f, col, lo, hi)

    # ---- cross-field consistency
    x = frames.get("FLEX_PSI-69_clean_v1.0.csv")
    if x is not None:
        s = x[["x_O2", "x_N2", "x_CO2", "x_He"]].sum(axis=1)
        check(s.between(0.97, 1.03).all(), "FLEX: mole fractions sum to 1 +/- 0.03")
        check(np.allclose(x.o2_pct, 100 * x.x_O2, atol=1e-6), "FLEX: o2_pct = 100 x x_O2")
        k = x.dropna(subset=["pressure_kpa", "pressure_mmHg"])
        check(np.allclose(k.pressure_kpa, k.pressure_mmHg * 0.133322, rtol=1e-3), "FLEX: pressure_kpa = pressure_mmHg x 0.1333")
        m = x.extinguished.notna()
        check(((x.loc[m, "extinguished"] == 1) == (x.loc[m, "test_end"] == "Extinction")).all(), "FLEX: extinguished label agrees with test_end")
        check((x.loc[x.test_end == "Disruption", "use_for_extinction_model"] == False).all(), "FLEX: Disruption tests never used for the extinction model")
        d = x.dropna(subset=["d0_mm", "d_ext_mm"])
        check((d.d_ext_mm <= d.d0_mm * 1.01).all(), "FLEX: extinction diameter <= initial diameter")
    b = frames.get("BASS-II_flame_spread_microgravity_v1.0.csv")
    if b is not None:
        check(np.allclose(b.diameter_mm, 10 * b.diameter_cm), "BASS-II: diameter_mm = 10 x diameter_cm")
        check(np.allclose(b.inv_diameter_per_cm, 1 / b.diameter_cm, rtol=1e-3), "BASS-II: inv_diameter = 1 / diameter")
        check(np.allclose(b.flame_spread_mm_s, b.vf_x1e3_cm_s_raw / 1000 * 10, rtol=1e-6), "BASS-II: spread mm/s = Table S1 value x 1e-3 cm/s")
        check(b.groupby("test_id").o2_pct.nunique().max() == 1, "BASS-II: one O2 level per ISS test")
    s = frames.get("SAME_PSI-101-102_smoke_particles_v1.0.csv")
    if s is not None:
        hot = s.heater_resistance_ratio_rt_r0 > 1
        check(not ((s.sample_temperature_c == 0) & hot).any(), "SAME: no heated sample recorded at 0 C (placeholder treated as missing)")
        used = s[s.use_for_particle_size_model]
        check(used.count_mean_diameter_um.notna().all() and (used.count_mean_diameter_um > 0).all(), "SAME: every row used for modelling has a positive particle size")
    sp = frames.get("SPICE_PSI-107_smoke_points_v1.0.csv")
    if sp is not None:
        check((sp.fuel_flow_hc_sccm <= sp.fuel_flow_total_sccm + 1e-9).all(), "SPICE: hydrocarbon flow <= total fuel flow")
        check((sp.pressure_kpa.round(3) == 101.325).all(), "SPICE: all smoke points at 1 atm")

    # ---- lineage: every master row points to an existing record in its source file
    M = frames.get("Ignis_mu_unified_master_v1.0.csv")
    if M is not None:
        def ids(f, col, folder=PROC):
            p = folder / f
            return set(pd.read_csv(p)[col].astype(str)) if p.exists() else set()
        LINK = {"FLEX": ids("FLEX_PSI-69_clean_v1.0.csv", "flex_id"),
                "SPICE": ids("SPICE_PSI-107_smoke_points_v1.0.csv", "test_point"),
                "SAME": ids("SAME_PSI-101-102_smoke_particles_v1.0.csv", "same_run"),
                "SAME-R": ids("SAME_PSI-101-102_smoke_particles_v1.0.csv", "same_run"),
                "BASS": ids("BASS_PSI-26_test_log_v1.0.csv", "as_run_no"),
                "BASS-II": ids("BASS-II_flame_spread_microgravity_v1.0.csv", "record_id") | ids("BASS-II_PSI-25_clean_v0.1.csv", "record_id", DATA / "bass2_and_wstf"),
                "Saffire-I": ids("SAFFIRE_I-III_PSI-98-100_v1.0.csv", "sample"), "Saffire-II": ids("SAFFIRE_I-III_PSI-98-100_v1.0.csv", "sample"),
                "Saffire-III": ids("SAFFIRE_I-III_PSI-98-100_v1.0.csv", "sample")}
        for inv, known in LINK.items():
            src = M.loc[M.source_investigation == inv, "source_record_id"].astype(str)
            dangling = src[~src.isin(known)]
            check(len(src) > 0 and dangling.empty, f"master lineage: {len(src)} {inv} rows link to their source records" +
                  ("" if dangling.empty else f" - {len(dangling)} dangling, e.g. {dangling.iloc[0]}"))
        check(M.gravity_level.isin(["microgravity", "1g (ground)"]).all(), "master: gravity_level is 'microgravity' or '1g (ground)'")
        check((M.gravity_level == "1g (ground)").sum() == 52, "master: exactly 52 1g ground-reference rows (never used to train microgravity models)")

    report = {"passed": len(PASSED), "errors": ERRORS, "warnings": WARNINGS, "checks": PASSED + ERRORS + WARNINGS}
    Path(os.environ.get("IGNIS_VALIDATION_REPORT", DATA / "validation_report.json")).write_text(json.dumps(report, indent=1))
    print(f"data contract: {len(PASSED)} passed, {len(WARNINGS)} warnings, {len(ERRORS)} errors")
    for e in ERRORS:
        print("  ERROR  ", e)
    for w in WARNINGS:
        print("  WARNING", w)
    return not ERRORS


if __name__ == "__main__":
    sys.exit(0 if validate() else 1)
