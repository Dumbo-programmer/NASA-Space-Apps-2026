"""
AgniShikha / Ignis mu - BASS (PSI-26) test log + SAFFIRE I-III builder
Inputs (folder): PSI-26_AsRunTestMatrix_extract_raw.csv, PSI-26_AsRunTestMatrix_O2_extract.csv,
                 PSI-98/99/100 SAFFIRE experimental tables (verbatim NASA CSVs)
Outputs: BASS_PSI-26_test_log_v1.0.csv, SAFFIRE_I-III_PSI-98-100_v1.0.csv
Run    : python build_bass_saffire.py <raw_dir> <out_dir>
"""
import sys, re
import numpy as np, pandas as pd
raw, out = sys.argv[1], sys.argv[2]

# ---------------- BASS (2012-2013, ISS MSG) ----------------
r = pd.read_csv(f"{raw}/PSI-26_AsRunTestMatrix_extract_raw.csv", dtype=str, keep_default_na=False)
# The extract kept sheet columns 1-16 and 28-31; header names in the raw extract are shifted, so rename by position.
r.columns = ["xlsx_row", "actual_date", "approx_start_gmt", "as_run_no", "test_no", "sample_no", "material", "igniter",
             "flow_restrictor", "sample_distance", "fan_display", "air_display_cm_s", "radiometer_gain",
             "radiometer_display", "gn2_pot", "gn2_display", "camera_filter", "pressure_atm", "co2_mmHg",
             "observations", "_empty"]
o2 = pd.read_csv(f"{raw}/PSI-26_AsRunTestMatrix_O2_extract.csv", dtype=str, keep_default_na=False)
r = r.merge(o2, on="xlsx_row", how="left")
r = r[r.as_run_no != "SETUP"].copy()

def mat_family(m):
    m = m.lower()
    if "pmma" in m or "sphere" in m: return "PMMA"
    if "sibal" in m: return "SIBAL (cotton-fiberglass)"
    if "nomex" in m: return "Nomex"
    if "ultem" in m: return "Ultem"
    if "japan" in m: return "Japan wax candle"
    if "paraffin" in m or "parrafin" in m or "wax" in m: return "Paraffin wax"
    if "candle" in m: return "Candle (paraffin)"
    return "other"
def geometry(m):
    m = m.lower()
    if "sphere" in m: return "sphere"
    if "slab" in m: return "slab"
    if "sheet" in m: return "sheet"
    if "candle" in m: return "candle"
    if "sibal" in m or "nomex" in m: return "fabric strip"
    return "other"

# conservative keyword rules on the NASA observation text (documented; check by hand before modelling)
R_NOIGN = r"no ignition|did not ignite|no joy|no flame|just smoked|not even any smoke|no luck keeping|not ignite|didn't work"
R_BRIEF = r"brief ignition|extinguished in ~|extinguished after \d+ seconds|died when igniter|winks? out|did not sustain|went out when igniter|burned for only"
R_HW = r"igniter broke before ignition|igniter is broken!|no useful digital stills|igniter seems to have broken"
def outcome(t):
    t = t.lower()
    if re.search(R_HW, t): return "no valid burn (hardware issue)"
    if re.search(R_BRIEF, t): return "brief flame, self-extinguished (no sustained spread)"
    if re.search(R_NOIGN, t): return "no ignition"
    return "sustained burn"

b = pd.DataFrame()
b["record_id"] = [f"BASS-{i:03d}" for i in range(1, len(r) + 1)]
b["psi_id"] = "PSI-26"
b["source_xlsx_row"] = r.xlsx_row.astype(int).values
b["as_run_no"] = r.as_run_no.values
b["test_no"] = r.test_no.values
b["sample_no"] = r.sample_no.values
b["gravity"] = "microgravity"
b["platform"] = "ISS MSG (BASS)"
b["material_raw"] = r.material.values
b["material_family"] = [mat_family(m) for m in r.material]
b["geometry"] = [geometry(m) for m in r.material]
b["flow_configuration"] = np.where(r.material.str.contains("oppos", case=False) | r.sample_distance.str.contains("oppos", case=False),
                                   "opposed", np.where(r.material.str.contains("wake", case=False) | r.igniter.str.contains("wake", case=False),
                                                        "wake ignition", "concurrent / stagnation (as run)"))
b["o2_pct"] = (pd.to_numeric(r.o2_vol_frac, errors="coerce") * 100).round(2).values
b["pressure_kpa"] = (pd.to_numeric(r.pressure_atm, errors="coerce") * 101.325).round(1).values
b["co2_mmHg"] = pd.to_numeric(r.co2_mmHg, errors="coerce").values
b["air_flow_settings_cm_s"] = r.air_display_cm_s.values          # free text, e.g. "10, 5" = sequence of settings
b["gn2_suppression_used"] = (~r.gn2_pot.isin(["", "n/a", "0"])).values & r.observations.str.contains(r"N2|GN2", case=False).values
b["observations"] = r.observations.values                         # NASA crew/PI notes: use for retrieval text
b["outcome_label"] = [outcome(t) for t in r.observations]
b["outcome_label_method"] = "keyword rule on NASA observation text"
# Hand review (Nov 2026) of every non-'sustained' row and every 'sustained' row mentioning failure words:
SUSTAINED = "sustained burn"
NOSPREAD = "brief flame, self-extinguished (no sustained spread)"
OVERRIDES = {
    "BASS-069": (SUSTAINED, "'did not ignite first 2 attempts' then ignited and burned"),
    "BASS-078": (SUSTAINED, "igniter replaced, then 8-minute burn"),
    "BASS-096": (SUSTAINED, "'no joy' refers to GN2 failing to blow the flame out"),
    "BASS-103": (SUSTAINED, "ignited on 3rd igniter, burned at stagnation region with minimal spread"),
    "BASS-050": (NOSPREAD, "'Tiny blue flame. Self-extinguished.'"),
    "BASS-051": (NOSPREAD, "'brief flame a few times, but went out'"),
    "BASS-098": (NOSPREAD, "'brief flame at 62 but also flamed out'"),
    "BASS-117": (NOSPREAD, "'ignited briefly ... but went out'"),
    "BASS-108": (NOSPREAD, "'didn't propagate at all. Went out on its own ... after 75 seconds'"),
}
for rid, (lab, why) in OVERRIDES.items():
    k = b.index[b.record_id == rid][0]
    b.loc[k, "outcome_label"] = lab
    b.loc[k, "outcome_label_method"] = f"hand-corrected: {why}"
b.loc[~b.record_id.isin(OVERRIDES), "outcome_label_method"] = "keyword rule on NASA observation text (hand-reviewed)"
b["vitiated_atmosphere"] = b.o2_pct < 19
b["value_type"] = "settings/atmosphere: observed (ISS log); outcome_label: derived (keyword rule)"
b["source"] = "NASA PSI-26 BASS (CC0-1.0); file 'PSI-26_Science Documents_As Run_Test Matrix.xlsx', sheet 'as run matrix'"
qf = []
for _, row in r.iterrows():
    f = []
    if not re.fullmatch(r"\d+", row.actual_date or ""): f.append(f"date cell non-standard in NASA sheet ('{row.actual_date}')")
    if row.pressure_atm in ("", "?"): f.append("pressure not recorded")
    if row.o2_vol_frac in ("", '""'): f.append("O2 not recorded")
    qf.append(" | ".join(f))
b["quality_flags"] = qf
b.to_csv(f"{out}/BASS_PSI-26_test_log_v1.0.csv", index=False)
print("BASS", b.shape); print(b.outcome_label.value_counts().to_string()); print(b.material_family.value_counts().to_string())

# ---------------- SAFFIRE I-III (Cygnus, large scale) ----------------
s1 = pd.read_csv(f"{raw}/PSI-98_Experimental_table_SAFFIRE-1.csv", dtype=str, keep_default_na=False)
s2 = pd.read_csv(f"{raw}/PSI-99_Experimental_table_SAFFIRE-2.csv", dtype=str, keep_default_na=False)
s3 = pd.read_csv(f"{raw}/PSI-100_Experimental_table_SAFFIRE-3.csv", dtype=str, keep_default_na=False)
s1.columns = [c.strip() for c in s1.columns]; s2.columns = [c.strip() for c in s2.columns]; s3.columns = [c.strip() for c in s3.columns]
rows = []
for _, q in s1[s1["Sample Number"].isin(["S1", "S2"])].iterrows():
    rows.append(dict(flight="Saffire-I (2016)", psi_id="PSI-98", sample=q["Sample Number"], material="SIBAL (cotton-fiberglass)",
        thickness_mm=float(q["Sample Thickness (cm)"]) * 10, length_cm=94.0, width_cm=40.6,
        flow_cm_s=float(q["Air Flow (cm/s)"]), flow_direction=q["Flow Direction"].strip(), o2_pct_note=q["Percent O2"],
        ignition_power_w=float(q["Ignition Power (W)"]), ignition_time_s=float(q["Ignition Time (s)"]),
        ug_burn_time_s=float(q["Burn Time (s)"]), ug_burn_length_cm=np.nan, ug_spread_rate_mm_s=np.nan,
        g1_burn_length="", g1_spread="",
        notes="NASA table lists length 40.6 and width 94; sample is 94 cm long x 40.6 cm wide (Saffire-III table) - swapped here"))
for _, q in s2[s2["Sample Number"].str.match(r"2-\d")].iterrows():
    mat = q["Material"].strip() or ("Cotton-Fiberglass (SIBAL)" if q["Sample Number"] == "2-6" else "PMMA")
    th = q["Samle Thickness"].strip()
    thv = {"037 mm": 0.37}.get(th, np.nan)
    if re.fullmatch(r"[\d.]+ mm", th): thv = float(th.split()[0])
    if th == "1 cm": thv = 10.0
    def cm(v):
        m = re.match(r"~?\s*([\d.]+)\s*cm", v.strip()); return float(m.group(1)) if m else (0.0 if v.strip().startswith("~ 0") else np.nan)
    def mms(v):
        m = re.match(r"([\d.]+)\s*mm/s", v.strip()); return float(m.group(1)) if m else np.nan
    bt = q["Burn Time (s)"].strip()
    rows.append(dict(flight="Saffire-II (2016)", psi_id="PSI-99", sample=q["Sample Number"], material=mat.replace("Cotton-Fiberglass (SIBAL)", "SIBAL (cotton-fiberglass)"),
        thickness_mm=thv, length_cm=29.0, width_cm=5.0, flow_cm_s=20.0, flow_direction=q["Flow Direction"].strip(),
        o2_pct_note=q["Percent O2 (Note 1)"], ignition_power_w=float(q["Ignition Power (W)"].split()[0]),
        ignition_time_s=float(q["Ignition Time (s)"].split()[0]),
        ug_burn_time_s=float(bt.split()[0]) if bt[0].isdigit() else np.nan,
        ug_burn_length_cm=cm(q["?-g Burn Length"]), ug_spread_rate_mm_s=mms(q["?-g Spread Length"]),
        g1_burn_length=q["1-g Burn Length"].strip(), g1_spread=q["1-g Spread Rate"].strip(),
        notes=("thickness printed '037 mm' in NASA table (0.37 mm)" if th == "037 mm" else "") +
              ("; material blank in NASA table, inferred from neighbouring sample" if not q["Material"].strip() else "") +
              ("; 'Insignificant' burn in microgravity (did not spread)" if bt == "Insignificant" else "")))
for _, q in s3.iterrows():
    rows.append(dict(flight="Saffire-III (2017)", psi_id="PSI-100", sample=q["Sample Number"], material="SIBAL (cotton-fiberglass)",
        thickness_mm=3.3, length_cm=94.0, width_cm=40.6, flow_cm_s=30.0, flow_direction=q["Direction"].strip(), o2_pct_note="",
        ignition_power_w=np.nan, ignition_time_s=np.nan, ug_burn_time_s=np.nan, ug_burn_length_cm=np.nan, ug_spread_rate_mm_s=np.nan,
        g1_burn_length="", g1_spread="", notes="NASA table gives conditions only; results in telemetry/merge files"))
sf = pd.DataFrame(rows)
sf.insert(0, "record_id", [f"SAFFIRE-{i:02d}" for i in range(1, len(sf) + 1)])
sf["gravity"] = "microgravity (Cygnus vehicle, unmanned)"
sf["ug_sustained_spread"] = np.where(sf.ug_burn_length_cm.gt(0) | sf.ug_burn_time_s.gt(0), "yes",
                                     np.where(sf.ug_burn_length_cm.eq(0), "no", "unknown"))
sf["value_type"] = "observed (NASA experimental table)"
sf["source"] = "NASA PSI-98/99/100 Saffire-I/II/III experimental tables (CC0-1.0)"
sf.to_csv(f"{out}/SAFFIRE_I-III_PSI-98-100_v1.0.csv", index=False)
print("SAFFIRE", sf.shape); print(sf[["record_id", "material", "flow_direction", "ug_burn_time_s", "ug_spread_rate_mm_s", "g1_burn_length", "ug_sustained_spread"]].to_string(index=False))
