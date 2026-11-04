"""
AgniShikha / Ignis mu - unified master table (one row per experiment run, all NASA sources)
Inputs : clean per-investigation files (this folder) + earlier BASS-II / WSTF files
Output : Ignis_mu_unified_master_v1.0.csv
Run    : python build_master.py <datasets_dir> <earlier_outputs_dir>
Schema (normalised for retrieval + ML routing):
  experiment_id, source_investigation, psi_id, gravity_level, platform, fuel_material, material_class,
  configuration, ignition_method, oxygen_pct, pressure_kpa, airflow_cm_s, airflow_note, diluent,
  characteristic_size_mm, temperature_c, smoke_signal_mg_m3, outcome_type, outcome_variable, outcome_value,
  outcome_unit, outcome_class, flame_behavior_notes, value_type, source_ref, source_record_id, quality_flags
"""
import sys
import numpy as np, pandas as pd
D, E = sys.argv[1], sys.argv[2]
COLS = ["experiment_id", "source_investigation", "psi_id", "gravity_level", "platform", "fuel_material", "material_class",
        "configuration", "ignition_method", "oxygen_pct", "pressure_kpa", "airflow_cm_s", "airflow_note", "diluent",
        "characteristic_size_mm", "temperature_c", "smoke_signal_mg_m3", "outcome_type", "outcome_variable",
        "outcome_value", "outcome_unit", "outcome_class", "flame_behavior_notes", "value_type", "source_ref",
        "source_record_id", "quality_flags"]
parts = []
def add(df):
    for c in COLS:
        if c not in df: df[c] = np.nan
    parts.append(df[COLS])

# 1. BASS-II flame spread (PMMA rods, opposed flow, microgravity)
f = pd.read_csv(f"{E}/BASS-II_flame_spread_microgravity_v1.0.csv")
add(pd.DataFrame({"experiment_id": f.record_id, "source_investigation": "BASS-II", "psi_id": "PSI-25",
    "gravity_level": "microgravity", "platform": "ISS MSG", "fuel_material": "PMMA (" + f.pmma_color + ")",
    "material_class": "solid", "configuration": "rod, opposed flow", "ignition_method": "hot-wire igniter",
    "oxygen_pct": f.o2_pct, "pressure_kpa": 101.3, "airflow_cm_s": f.opposed_flow_cm_s, "diluent": "N2 (vitiated air)",
    "characteristic_size_mm": f.diameter_mm, "outcome_type": "regression", "outcome_variable": "flame_spread_rate",
    "outcome_value": f.flame_spread_mm_s, "outcome_unit": "mm/s",
    "flame_behavior_notes": "Opposed-flow flame spread over a " + f.diameter_mm.astype(str) + " mm PMMA rod at " + f.o2_pct.astype(str) + "% O2",
    "value_type": "observed (published, processed by authors)", "source_ref": f.source, "source_record_id": f.record_id,
    "quality_flags": f.quality_flags}))

# 2. BASS-II test log (gas response)
g = pd.read_csv(f"{E}/BASS-II_PSI-25_clean_v0.1.csv")
add(pd.DataFrame({"experiment_id": "BASS2-LOG-" + g.source_row.astype(str).str.zfill(3), "source_investigation": "BASS-II",
    "psi_id": "PSI-25", "gravity_level": "microgravity", "platform": "ISS MSG", "fuel_material": g.material_family.fillna("not stated"),
    "material_class": "solid", "configuration": g.geometry.fillna("") , "ignition_method": "hot-wire igniter",
    "oxygen_pct": g.o2_initial_pct, "airflow_note": "air display settings: " + g.air_display_raw.astype(str),
    "characteristic_size_mm": g.diameter_mm.fillna(g.thickness_mm), "outcome_type": "regression",
    "outcome_variable": "delta_CO2_during_test", "outcome_value": g.delta_co2_pct, "outcome_unit": "% (vol)",
    "flame_behavior_notes": "BASS-II test " + g.test_id.astype(str) + " (" + g.pi_group.astype(str) + "); air settings: " + g.air_display_raw.astype(str),
    "value_type": "observed (ISS test log)", "source_ref": "NASA PSI-25 BASS-II experimental table (CC0-1.0)",
    "source_record_id": g.record_id, "quality_flags": g.quality_flags}))

# 3. WSTF 1g ground reference (NASA-STD-6001B style, Hirsch et al. 2011)
w = pd.read_excel(f"{E}/Ignis_mu_NASA_flammability_dataset_v0.1.xlsx", sheet_name="Master")
add(pd.DataFrame({"experiment_id": w.record_id, "source_investigation": "WSTF 1g ground (Hirsch 2011)", "psi_id": "",
    "gravity_level": "1g (ground)", "platform": "NASA WSTF", "fuel_material": w.material_name, "material_class": "solid",
    "configuration": w.form_config.astype(str) + ", " + w.mounting.astype(str), "ignition_method": w.ignition_method,
    "pressure_kpa": (w.test_pressure_psia * 6.89476).round(1), "airflow_note": "quiescent (upward flame propagation test)",
    "characteristic_size_mm": (w.thickness_or_dia_in * 25.4).round(3), "outcome_type": "threshold",
    "outcome_variable": "maximum_oxygen_concentration_MOC", "outcome_value": w.MOC_pct_O2, "outcome_unit": "% O2",
    "flame_behavior_notes": "1g upward-propagation flammability limit; ULOI " + w.ULOI_pct_O2.astype(str) + "% O2",
    "value_type": "observed (published table)", "source_ref": w.source_ref, "source_record_id": w.record_id,
    "quality_flags": "1g reference - do not mix with microgravity rows in training; " + w.verified_status.fillna("verification pending").astype(str)}))

# 4. FLEX droplets
x = pd.read_csv(f"{D}/FLEX_PSI-69_clean_v1.0.csv")
add(pd.DataFrame({"experiment_id": x.record_id, "source_investigation": "FLEX", "psi_id": "PSI-69", "gravity_level": "microgravity",
    "platform": x.platform, "fuel_material": x.fuel, "material_class": "liquid droplet", "configuration": "isolated droplet, quiescent",
    "ignition_method": "hot-wire igniter", "oxygen_pct": x.o2_pct, "pressure_kpa": x.pressure_kpa, "airflow_cm_s": 0.0,
    "airflow_note": "quiescent", "diluent": x.diluent_added + " (" + x.diluent_pct.astype(str) + "%)",
    "characteristic_size_mm": x.d0_mm, "outcome_type": "classification", "outcome_variable": "test_end",
    "outcome_value": x.d_ext_mm, "outcome_unit": "mm (visible flame extinction diameter)", "outcome_class": x.test_end,
    "flame_behavior_notes": x.fuel + " droplet " + x.d0_mm.astype(str) + " mm, test ended by " + x.test_end.str.lower() +
        np.where(x.extinction_regime_hint.fillna("") != "", " (" + x.extinction_regime_hint.fillna("") + ")", "") +
        "; burning-rate constant " + x.burning_rate_K_mm2_s.astype(str) + " mm2/s",
    "value_type": x.value_type, "source_ref": x.source, "source_record_id": x.flex_id, "quality_flags": x.quality_flags}))

# 5. SPICE smoke points
s = pd.read_csv(f"{D}/SPICE_PSI-107_smoke_points_v1.0.csv")
add(pd.DataFrame({"experiment_id": s.record_id, "source_investigation": "SPICE", "psi_id": "PSI-107", "gravity_level": "microgravity",
    "platform": s.platform, "fuel_material": s.fuel, "material_class": "gas jet", "configuration": "coflow jet diffusion flame",
    "oxygen_pct": 21.0, "pressure_kpa": s.pressure_kpa, "airflow_cm_s": s.coflow_air_velocity_cm_s, "airflow_note": "coflowing air",
    "diluent": np.where(s.fuel_mole_fraction < 1, "N2 in fuel", "none"), "characteristic_size_mm": s.burner_diameter_mm,
    "outcome_type": "regression", "outcome_variable": "smoke_point_flame_length", "outcome_value": s.smoke_point_length_mm,
    "outcome_unit": "mm", "flame_behavior_notes": s.fuel + " jet flame at its smoke point; fuel flow " +
        s.fuel_mass_flow_hc_mg_s.round(3).astype(str) + " mg/s (shorter smoke point = sootier fuel)",
    "value_type": s.value_type, "source_ref": s.source, "source_record_id": s.test_point, "quality_flags": s.quality_flags}))

# 6. SAME / SAME-R smoke particles (pyrolysis, no flame)
m = pd.read_csv(f"{D}/SAME_PSI-101-102_smoke_particles_v1.0.csv")
add(pd.DataFrame({"experiment_id": m.record_id, "source_investigation": np.where(m.psi_id == "PSI-102", "SAME", "SAME-R"),
    "psi_id": m.psi_id, "gravity_level": "microgravity", "platform": m.platform, "fuel_material": m.material,
    "material_class": "heated solid/liquid (smoke, non-flaming)", "configuration": "heated sample in flow tube",
    "ignition_method": "electric heater (pyrolysis, no flame)", "oxygen_pct": np.nan, "airflow_cm_s": m.inlet_air_velocity_cm_s,
    "temperature_c": m.sample_temperature_c, "smoke_signal_mg_m3": m.mass_conc_dusttrak_mg_m3,
    "outcome_type": "regression", "outcome_variable": "count_mean_diameter", "outcome_value": m.count_mean_diameter_um,
    "outcome_unit": "um", "flame_behavior_notes": m.material + " smoke, " + m.description.astype(str) +
        np.where(m.is_aged_reading, " (re-measured after aging)", "") + "; mass-mean diameter " + m.diameter_avg_mass_um.round(3).astype(str) + " um",
    "value_type": m.value_type, "source_ref": m.source, "source_record_id": m.same_run.astype(str), "quality_flags": m.quality_flags}))

# 7. BASS (2012-13) test log with crew observations
b = pd.read_csv(f"{D}/BASS_PSI-26_test_log_v1.0.csv")
add(pd.DataFrame({"experiment_id": b.record_id, "source_investigation": "BASS", "psi_id": "PSI-26", "gravity_level": "microgravity",
    "platform": b.platform, "fuel_material": b.material_family, "material_class": "solid",
    "configuration": b.geometry + ", " + b.flow_configuration, "ignition_method": "hot-wire igniter",
    "oxygen_pct": b.o2_pct, "pressure_kpa": b.pressure_kpa, "airflow_note": "air settings (cm/s): " + b.air_flow_settings_cm_s.astype(str),
    "diluent": np.where(b.vitiated_atmosphere, "N2 (vitiated cabin)", "none"), "outcome_type": "classification",
    "outcome_variable": "burn_outcome", "outcome_class": b.outcome_label, "flame_behavior_notes": b.observations,
    "value_type": b.value_type, "source_ref": b.source, "source_record_id": b.as_run_no.astype(str), "quality_flags": b.quality_flags}))

# 8. SAFFIRE I-III
f3 = pd.read_csv(f"{D}/SAFFIRE_I-III_PSI-98-100_v1.0.csv")
add(pd.DataFrame({"experiment_id": f3.record_id, "source_investigation": f3.flight.str.split(" ").str[0], "psi_id": f3.psi_id,
    "gravity_level": "microgravity", "platform": "Cygnus resupply vehicle (unmanned)", "fuel_material": f3.material, "material_class": "solid",
    "configuration": "large sample card, " + f3.flow_direction.str.lower() + " flow", "ignition_method": "hot-wire igniter",
    "oxygen_pct": pd.to_numeric(f3.o2_pct_note.astype(str).str.extract(r"([\d.]+)")[0], errors="coerce"), "pressure_kpa": np.nan,
    "airflow_cm_s": f3.flow_cm_s, "characteristic_size_mm": f3.thickness_mm, "outcome_type": "classification",
    "outcome_variable": "sustained_spread_in_microgravity", "outcome_value": f3.ug_burn_time_s, "outcome_unit": "s (burn time)",
    "outcome_class": f3.ug_sustained_spread, "flame_behavior_notes": ("Microgravity spread " + f3.ug_spread_rate_mm_s.astype(str) +
        " mm/s; 1g comparison burn length: " + f3.g1_burn_length.fillna("").astype(str) + ", 1g spread: " + f3.g1_spread.fillna("").astype(str) +
        ". " + f3.notes.fillna("")).str.replace("nan mm/s", "not given"),
    "value_type": f3.value_type, "source_ref": f3.source, "source_record_id": f3["sample"], "quality_flags": f3.notes}))

M = pd.concat(parts, ignore_index=True)
M["quality_flags"] = M.quality_flags.fillna("")
M.to_csv(f"{D}/Ignis_mu_unified_master_v1.0.csv", index=False)
print(M.shape)
print(M.groupby(["source_investigation", "gravity_level"]).size().to_string())
print(M.outcome_type.value_counts().to_string())
