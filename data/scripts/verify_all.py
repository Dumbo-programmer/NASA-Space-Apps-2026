"""Independent re-check: random rows of every clean/master file vs the verbatim NASA extracts."""
import sys, numpy as np, pandas as pd
R, D = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(7); problems = []; checks = 0
def eq(a, b, tol=1e-6):
    if pd.isna(a) and pd.isna(b): return True
    try: return abs(float(a) - float(b)) <= tol * max(1, abs(float(b)))
    except: return str(a).strip() == str(b).strip()

# FLEX
raw = pd.read_csv(f"{R}/PSI-69_Experimental_table_FLEX.csv", dtype=str); cl = pd.read_csv(f"{D}/FLEX_PSI-69_clean_v1.0.csv")
for i in rng.choice(len(raw), 40, replace=False):
    r, c = raw.iloc[i], cl.iloc[i]
    pairs = [(c.flex_id, r["FLEX Identifier"]), (c.fuel, r.Fuel), (c.x_O2, r.iloc[6]), (c.x_CO2, r.iloc[8]), (c.x_He, r.iloc[9]), (c.test_end, r["Test end"])]
    if r.iloc[5] != "0": pairs.append((c.pressure_mmHg, r.iloc[5]))
    for col, rc in [("d0_mm", 10), ("d_ext_mm", 11), ("burning_rate_K_mm2_s", 12)]:
        v = r.iloc[rc]
        if isinstance(v, str) and "�" not in v: pairs.append((c[col], v))
    for a, b in pairs:
        checks += 1
        if not eq(a, b): problems.append(f"FLEX row {i}: {a} vs {b}")
# SPICE
ex = pd.read_csv(f"{R}/PSI-107_SmokePointReview-0g-3_SmokePointDatasheet_extract.csv", dtype=str); sp = pd.read_csv(f"{D}/SPICE_PSI-107_smoke_points_v1.0.csv")
for _, c in sp.sample(25, random_state=3).iterrows():
    r = ex[ex.xlsx_row == str(c.source_xlsx_row)].iloc[0]
    for a, b in [(c.smoke_point_length_mm, r.smoke_point_length_mm), (c.burner_diameter_mm, r.nozzle_mm), (c.coflow_air_velocity_cm_s, r.u_air_cm_s), (c.fuel_mass_flow_hc_mg_s, r.mdot_hc_mg_s)]:
        checks += 1
        if not eq(a, b): problems.append(f"SPICE {c.record_id}: {a} vs {b}")
# SAME
ex = pd.read_csv(f"{R}/PSI-101_SAME_SAME-R_Results_ReducedDataSheet_extract.csv", dtype=str, keep_default_na=False); sm = pd.read_csv(f"{D}/SAME_PSI-101-102_smoke_particles_v1.0.csv")
for _, c in sm.sample(40, random_state=5).iterrows():
    r = ex[ex.xlsx_row == str(c.source_xlsx_row)].iloc[0]
    for a, b in [(c.material.split(" ")[0][:5], r.material[:5] if r.material != "DBP" else "Dibut"), (c.inlet_air_velocity_cm_s, r.inlet_velocity_cm_s), (c.heater_resistance_ratio_rt_r0, r.rt_r0)]:
        checks += 1
        if not eq(a, b): problems.append(f"SAME {c.record_id}: {a} vs {b}")
    if pd.notna(c.count_mean_diameter_um):
        checks += 1
        if not eq(c.count_mean_diameter_um, r.count_mean_diameter_um): problems.append(f"SAME {c.record_id} CMD")
# BASS
ex = pd.read_csv(f"{R}/PSI-26_AsRunTestMatrix_extract_raw.csv", dtype=str, keep_default_na=False); bs = pd.read_csv(f"{D}/BASS_PSI-26_test_log_v1.0.csv")
o2 = pd.read_csv(f"{R}/PSI-26_AsRunTestMatrix_O2_extract.csv", dtype=str, keep_default_na=False)
for _, c in bs.sample(30, random_state=9).iterrows():
    r = ex[ex.xlsx_row == str(c.source_xlsx_row)].iloc[0]; q = o2[o2.xlsx_row == str(c.source_xlsx_row)]
    checks += 2
    if c.material_raw != r.iloc[6]: problems.append(f"BASS {c.record_id} material")
    if c.observations != r.iloc[19]: problems.append(f"BASS {c.record_id} observations")
    if len(q) and q.o2_vol_frac.iloc[0] not in ("", '""'):
        checks += 1
        if not eq(c.o2_pct, round(float(q.o2_vol_frac.iloc[0]) * 100, 2)): problems.append(f"BASS {c.record_id} O2")
# master: unique ids, ranges, microgravity rows physically sensible
M = pd.read_csv(f"{D}/Ignis_mu_unified_master_v1.0.csv")
checks += 1
if M.experiment_id.duplicated().any(): problems.append(f"master duplicate ids: {M.experiment_id[M.experiment_id.duplicated()].tolist()[:5]}")
for col, lo, hi in [("oxygen_pct", 10, 40), ("pressure_kpa", 20, 400), ("airflow_cm_s", 0, 100)]:
    v = M[col].dropna(); checks += 1
    if ((v < lo) | (v > hi)).any(): problems.append(f"master {col} out of [{lo},{hi}]: {v[(v<lo)|(v>hi)].tolist()[:5]}")
print(f"checks run: {checks}; problems: {len(problems)}")
for p in problems[:30]: print("  ", p)
