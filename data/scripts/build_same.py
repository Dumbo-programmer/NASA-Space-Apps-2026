"""
AgniShikha / Ignis mu - SAME + SAME-R smoke-particle dataset builder
Input : PSI-101_SAME_SAME-R_Results_ReducedDataSheet_extract.csv
        (NASA PSI-101 file 'PSI-101_Analyzed Data_SAME, SAME-R_Results.xlsx', sheet 'Reduced data sheet';
         numbers kept to 6 significant digits)
Output: SAME_PSI-101-102_smoke_particles_v1.0.csv  (154 ISS smoke runs: SAME 2008 + SAME-R 2010)
Run   : python build_same.py <extract_csv> <out_dir>
"""
import sys
import numpy as np, pandas as pd

src, out_dir = sys.argv[1], sys.argv[2]
x = pd.read_csv(src, dtype=str, keep_default_na=False)
ERR = {"#DIV/0!", "#NUM!", "#VALUE!", "??", "n/a", "NA", "x", ""}

def num(series, label, flags):
    out = []
    for i, v in series.items():
        v = v.strip()
        if v in ERR:
            out.append(np.nan)
            if v not in ("", "n/a", "NA"):
                flags[i].append(f"{label}: '{v}' in NASA sheet -> missing")
        else:
            out.append(float(v))
    return pd.Series(out, index=series.index)

flags = {i: [] for i in x.index}
s = pd.DataFrame(index=x.index)
s["record_id"] = [f"SAME-{r:03d}" for r in range(1, len(x) + 1)]
s["psi_id"] = np.where(x.flight == "1", "PSI-102", "PSI-101")
s["campaign"] = np.where(x.flight == "1", "SAME (2008, ISS Expedition 15)", "SAME-R (2010, ISS Expedition 24)")
s["source_xlsx_row"] = x.xlsx_row.astype(int)
s["same_run"] = x.same_run
s["is_aged_reading"] = x.same_run.str.endswith("a")        # 'a' = same smoke re-measured after secondary aging
s["gravity"] = "microgravity"
s["platform"] = "ISS MSG (SAME)"
s["material"] = x.material.replace({"DBP": "Dibutyl phthalate (DBP)", "Lampwick": "Lampwick (cotton)"})
s["description"] = x.description
s["inlet_air_velocity_cm_s"] = num(x.inlet_velocity_cm_s, "inlet velocity", flags)
s["heater_resistance_ratio_rt_r0"] = num(x.rt_r0, "Rt/R0", flags)   # proxy for heater temperature setting
s["sample_temperature_c"] = num(x.sample_temp_c, "sample temperature", flags)
# a heated sample (Rt/R0 > 1) cannot be at 0 C: NASA's sheet uses 0 as a blank here (v1.1 fix, found by validate_processed.py)
_zero_t = (s["sample_temperature_c"] == 0) & (s["heater_resistance_ratio_rt_r0"] > 1)
for i in s.index[_zero_t]:
    flags[i].append("sample temperature: 0 in NASA sheet while heater on (Rt/R0 > 1) -> missing")
s.loc[_zero_t, "sample_temperature_c"] = np.nan
s["net_aging_time_s"] = num(x.net_aging_s, "net aging time", flags)
s["mass_loss_mg"] = num(x.mass_loss_mg, "mass loss", flags)
# outputs (particle statistics from the moment method)
s["number_conc_per_cm3"] = num(x.m0_number_conc_per_cm3, "M0", flags)
s["count_mean_diameter_um"] = num(x.count_mean_diameter_um, "count mean diameter", flags)
s["diameter_avg_mass_um"] = num(x.diam_avg_mass_um, "diameter of average mass", flags)
s["geometric_mean_diameter_um"] = num(x.hatch_choate_dg_um, "Hatch-Choate Dg", flags)
s["geometric_std_dev"] = num(x.hatch_choate_sigma_g, "Hatch-Choate sigma_g", flags)
s["mass_conc_dusttrak_mg_m3"] = num(x.dusttrak_b_mg_m3, "DustTrak", flags)
s["m1_diameter_conc_mm_cm3"] = num(x.m1_mm_per_cm3, "M1", flags)

zero_out = (s.number_conc_per_cm3 == 0) & (s.count_mean_diameter_um == 0)
for i in s.index[zero_out]:
    flags[i].append("all particle moments = 0 (DBP liquid aerosol not reduced in this sheet / instrument issue) -> treat as missing")
s.loc[zero_out, ["number_conc_per_cm3", "count_mean_diameter_um", "diameter_avg_mass_um",
                 "geometric_mean_diameter_um", "geometric_std_dev", "m1_diameter_conc_mm_cm3"]] = np.nan
bad_zero_cmd = (s.count_mean_diameter_um == 0)
s.loc[bad_zero_cmd, ["count_mean_diameter_um", "diameter_avg_mass_um", "geometric_mean_diameter_um", "geometric_std_dev"]] = np.nan
for i in s.index[bad_zero_cmd]:
    flags[i].append("count mean diameter = 0 (particle counter not run, e.g. 'no Ptrak') -> missing")

s["use_for_particle_size_model"] = s.count_mean_diameter_um.notna() & s.diameter_avg_mass_um.notna() & \
    s.inlet_air_velocity_cm_s.notna() & s.heater_resistance_ratio_rt_r0.notna()
s["value_type"] = "inputs: observed settings; particle statistics: derived by NASA/NIST team (moment method)"
s["source"] = ("NASA PSI-101/PSI-102 SAME & SAME-R (CC0-1.0); file 'PSI-101_Analyzed Data_SAME, SAME-R_Results.xlsx', "
               "sheet 'Reduced data sheet'; method: Urban et al. AIAA 2012 / Mulholland et al. Aerosol Sci. Tech. 2015")
s["quality_flags"] = [" | ".join(flags[i]) for i in s.index]
s.to_csv(f"{out_dir}/SAME_PSI-101-102_smoke_particles_v1.0.csv", index=False)

print(s.shape, "| usable for particle-size model:", int(s.use_for_particle_size_model.sum()))
print(s.groupby(["campaign", "material"]).size().to_string())
u = s[s.use_for_particle_size_model]
print(u.groupby("material")[["count_mean_diameter_um", "diameter_avg_mass_um"]].median().round(3).to_string())
print("aged vs fresh CMD median:", u.groupby("is_aged_reading").count_mean_diameter_um.median().round(3).to_dict())
print("no-flow vs flow CMD median:", u.groupby(u.inlet_air_velocity_cm_s == 0).count_mean_diameter_um.median().round(3).to_dict())
