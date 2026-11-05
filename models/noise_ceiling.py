"""
How good CAN a model get? Replicate-based noise ceiling (pure-error analysis).
Pairs of runs from DIFFERENT ISS tests whose inputs are (almost) identical should give the same answer.
Their disagreement is measurement + run-to-run noise that no model can explain:
    noise variance  ~  mean( (y_i - y_j)^2 ) / 2   over near-replicate pairs
    best possible R2 ~ 1 - noise variance / total variance
"""
import numpy as np, pandas as pd, json
from ignis_models import flex2_features, spice_features, same2_features, bass2_features

def ceiling(X, y, g, tol, log=False):
    y = np.log(y) if log else np.asarray(y, float)
    Z = ((X - X.mean()) / X.std(ddof=0).replace(0, 1)).values; d2 = []
    for i in range(len(Z)):
        for j in range(i + 1, len(Z)):
            if g[i] != g[j] and np.sqrt(((Z[i] - Z[j]) ** 2).sum()) <= tol:
                d2.append((y[i] - y[j]) ** 2)
    if len(d2) < 5:
        return None
    noise = np.mean(d2) / 2
    return {"replicate_pairs": len(d2), "noise_sd": float(np.sqrt(noise)), "total_sd": float(y.std()),
            "max_R2_possible": float(1 - noise / y.var()), "scale": "log" if log else "original"}

D = "data"; out = {}
d = pd.read_csv(f"{D}/BASS-II_flame_spread_microgravity_v1.0.csv")
out["bass2_flame_spread"] = ceiling(bass2_features(d), d.flame_spread_mm_s.values, d.test_id.values, 0.35)
x = pd.read_csv(f"{D}/FLEX_PSI-69_clean_v1.0.csv"); x["co2_pct"] = x.x_CO2 * 100; x["he_pct"] = x.x_He * 100
k = x[x.burning_rate_K_mm2_s.notna() & x.d0_mm.notna() & x.pressure_kpa.notna() & (x.burning_rate_K_mm2_s > 0.1)].reset_index(drop=True)
out["flex_burning_rate"] = ceiling(flex2_features(k), k.burning_rate_K_mm2_s.values, k.flex_id.str[:3].values, 0.25)
s = pd.read_csv(f"{D}/SPICE_PSI-107_smoke_points_v1.0.csv")
out["spice_smoke_point"] = ceiling(spice_features(s), s.smoke_point_length_mm.values, s.gmt_day_2009.values, 0.25, log=False)
m0 = pd.read_csv(f"{D}/SAME_PSI-101-102_smoke_particles_v1.0.csv")
m0 = m0[m0.use_for_particle_size_model & m0.sample_temperature_c.notna() & m0.net_aging_time_s.notna()].reset_index(drop=True)
raw = pd.DataFrame({"material": m0.material, "sample_temperature_c": m0.sample_temperature_c, "air_velocity_cm_s": m0.inlet_air_velocity_cm_s,
                    "aging_time_s": m0.net_aging_time_s, "campaign": np.where(m0.psi_id == "PSI-102", "SAME", "SAME-R")})
out["same_particle_size"] = ceiling(same2_features(raw), m0.count_mean_diameter_um.values, (m0.campaign.str[:6] + m0.same_run.str.rstrip("a")).values, 0.35, log=False)
for kname, v in out.items():
    print(kname, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in (v or {}).items()})
json.dump(out, open("noise_ceiling.json", "w"), indent=2)
