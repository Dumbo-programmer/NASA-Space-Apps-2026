"""Ignis μ · BASS-II (PSI-25) gas-response dataset builder.
Input : BASS-II_PSI-25_clean_v0.1.csv   Output: BASS-II_gas_response_v0.1.csv
Run   : python build_gas_response.py"""
import pandas as pd, numpy as np
c = pd.read_csv("BASS-II_PSI-25_clean_v0.1.csv")
g = c[["record_id","psi_id","source_row","pi_group","test_id","sample_no"]].copy()      # IDs (not features)
g["material_family"] = c.material_family.str.replace(r" \(.*\)", "", regex=True)       # features
g["material_inferred"] = c.material_family.str.contains("inferred", na=False)
for k in ["geometry","thickness_mm","diameter_mm","width_cm","rod_color","burning_sides","flow_restrictor"]: g[k] = c[k]
g["o2_initial_pct"] = c.o2_initial_pct
g["co2_background_pct"] = c.co2_initial_pct
g["co_background_ppm"] = c.co_initial_ppm
g["air_setting_initial"] = c.air_display_initial
g["air_setting_steps"] = c.air_display_n_settings
g["flow_reduced_to_extinction"] = c.air_text_mentions_extinction
g["frames_shot_duration_proxy"] = c.frames_shot
g["delta_o2_pct"], g["delta_co2_pct"], g["delta_co_ppm"] = c.delta_o2_pct, c.delta_co2_pct, c.delta_co_ppm  # targets
g["co_censored"] = c.co_final_over_range | c.co_initial_over_range
g["co2_per_o2_ratio"] = np.where(g.delta_o2_pct > 0.05, (g.delta_co2_pct / g.delta_o2_pct).round(2), np.nan)  # physics-derived
g["co2_per_o2_theoretical"] = g.material_family.map({"PMMA": 5/6, "SIBAL": 1.0}).round(2)  # PMMA C5H8O2+6O2->5CO2; cellulose 6:6
g["co_to_co2_ratio"] = np.where(g.delta_co2_pct > 0.02, ((g.delta_co_ppm/1e4)/g.delta_co2_pct).round(4), np.nan)
g["delta_co2_per_frame"] = np.where(g.frames_shot_duration_proxy > 0, (g.delta_co2_pct/g.frames_shot_duration_proxy).round(5), np.nan)
bad_o2 = c.quality_flags.fillna("").str.contains("final O2")                          # inclusion rules
g["use_for_o2_co2"] = ~bad_o2 & g.delta_o2_pct.notna() & g.delta_co2_pct.notna() & (g.material_family != "not stated")
g["use_for_co"] = g.use_for_o2_co2 & ~g.co_censored & g.delta_co_ppm.notna()
g["small_material_group"] = g.material_family.map(g.material_family.value_counts()) < 5
g.to_csv("BASS-II_gas_response_v0.1.csv", index=False)
print(g.shape, "usable O2/CO2:", int(g.use_for_o2_co2.sum()), "usable CO:", int(g.use_for_co.sum()))
