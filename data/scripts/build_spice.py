"""
AgniShikha / Ignis mu - SPICE (PSI-107) smoke-point dataset builder
Input : PSI-107_SmokePointReview-0g-3_SmokePointDatasheet_extract.csv
        (columns extracted from NASA PSI-107 file 'PSI-107_Raw Data_SmokePointReview-0g-3.xlsx',
         sheet 'Smoke Point Datasheet' = "Master Sheets of ISS Tests for SPICE"; numbers kept to 6 significant digits)
Output: SPICE_PSI-107_smoke_points_v1.0.csv  (55 ISS microgravity smoke points, 2009)
Run   : python build_spice.py <extract_csv> <out_dir>
"""
import sys
import numpy as np, pandas as pd

src, out_dir = sys.argv[1], sys.argv[2]
x = pd.read_csv(src, dtype={"gmt_day": str, "no": str})
iss = x[(x.xlsx_row >= 5) & (x.xlsx_row <= 59)].copy()          # ISS SPICE block; rows 63+ are reference/other blocks
for col in iss.columns:
    if col not in ("gmt_day", "no", "tp_id", "fuel"):
        iss[col] = pd.to_numeric(iss[col])                       # file mixes a text header row lower down

fuel_map = {"Ethylene": ("Ethylene", 1.00), "Propane": ("Propane", 1.00), "Propylene": ("Propylene", 1.00),
            "75 % Propylene": ("Propylene/N2 75%", 0.75), "50 % Propylene": ("Propylene/N2 50%", 0.50)}
s = pd.DataFrame()
s["record_id"] = [f"SPICE-SP-{i:03d}" for i in range(1, len(iss) + 1)]
s["psi_id"] = "PSI-107"
s["source_xlsx_row"] = iss.xlsx_row.values
s["gmt_day_2009"] = iss.gmt_day.values
s["test_point"] = iss.tp_id.values
s["gravity"] = "microgravity"
s["platform"] = "ISS MSG (SPICE)"
s["fuel"] = [fuel_map[f][0] for f in iss.fuel]
s["fuel_mole_fraction"] = iss.x_fuel.values
s["burner_diameter_mm"] = iss.nozzle_mm.values
s["pressure_kpa"] = (iss.pressure_pa / 1000).round(3).values
s["coflow_air_velocity_cm_s"] = iss.u_air_cm_s.values
s["fuel_jet_velocity_cm_s"] = iss.u_fuel_cm_s.values
s["fuel_flow_total_sccm"] = iss.total_fuel_rate_sccm.values
s["fuel_flow_hc_sccm"] = iss.hc_fuel_rate_sccm.values
s["fuel_mass_flow_total_mg_s"] = iss.mdot_burner_mg_s.values
s["fuel_mass_flow_hc_mg_s"] = iss.mdot_hc_mg_s.values          # hydrocarbon mass flow AT the smoke point
s["smoke_point_length_mm"] = iss.smoke_point_length_mm.values  # TARGET: luminous flame length at smoke point
s["flame_width_mm"] = iss.flame_width_mm.values
s["reynolds_number"] = iss.Re_air_visc.values                  # NASA team's derived value (air viscosity basis)
s["residence_time_ms"] = iss.t_res_ms.values                   # NASA team's derived estimate
s["image_pixel_length"] = iss.pixel_length.values
s["value_type"] = ("smoke_point_length/flow rates: observed (NASA team reduction of ISS images and flow meters); "
                   "reynolds_number, residence_time: derived by NASA team")
s["source"] = ("NASA PSI-107 SPICE (CC0-1.0), DOI 10.60555/9kbh-e962; file PSI-107_Raw Data_SmokePointReview-0g-3.xlsx, "
               "sheet 'Smoke Point Datasheet'; see Dotson et al. 2011 Fire Safety J. 46:550")
flags = []
for _, r in iss.iterrows():
    f = []
    if r.rad > 5:
        f.append(f"radiometer column shows {r.rad} (outlier, not used)")
    if pd.isna(r.no):
        f.append("test number blank in NASA sheet")
    flags.append(" | ".join(f))
s["quality_flags"] = flags

s.to_csv(f"{out_dir}/SPICE_PSI-107_smoke_points_v1.0.csv", index=False)
print(s.shape)
print(s.groupby(["fuel", "burner_diameter_mm"]).size().to_string())
print(s[["coflow_air_velocity_cm_s", "smoke_point_length_mm", "fuel_mass_flow_hc_mg_s"]].describe().round(2).loc[["min", "max"]])
# physics check: published scaling L_sp ~ d^-0.91 * u_air^0.41 (Dotson et al. 2011, 55 smoke points)
ok = s.coflow_air_velocity_cm_s > 0
X = np.c_[np.ones(ok.sum()), np.log(s.burner_diameter_mm[ok]), np.log(s.coflow_air_velocity_cm_s[ok]),
          pd.get_dummies(s.fuel[ok], drop_first=True).values.astype(float)]
b = np.linalg.lstsq(X, np.log(s.smoke_point_length_mm[ok]), rcond=None)[0]
print(f"fitted exponents with fuel dummies: d^{b[1]:.2f}  u_air^{b[2]:.2f}  (paper: d^-0.91 u^0.41)")
