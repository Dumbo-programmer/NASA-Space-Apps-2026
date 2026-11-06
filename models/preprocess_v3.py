"""
Agnishikha - preprocessing v3, designed FOR the chosen model (physics-informed Gaussian process)
Data Science Lead: Prachya Biswas

Why preprocessing changes with the model
----------------------------------------
The objective is a fire-risk envelope: for given cabin conditions, will a flame survive, how fast does it spread,
and how sure are we. The model chosen for that objective is a physics-informed Gaussian process (PI-GP):
    target (in physics space) = physics law (ridge on physics terms)  +  GP correction  +  noise
So the preprocessing has to deliver four things the PI-GP needs:
  1. a PHYSICS SPACE: inputs and target transformed so the known law is linear there
     (power laws -> logs; oxygen availability -> O2 partial pressure; thin rods -> 1/diameter)
  2. CLEAN ROWS with a clear outcome (rows whose outcome is undefined are removed, with the reason logged)
  3. GROUPS (ISS test / session / run pair), because rows from one test are not independent
  4. a NOISE PRIOR: run-to-run noise measured from near-replicate runs, given to the GP as its starting noise
Every step is logged with row counts (preprocessing_log_v3.json), so the presentation can show what was done and why.
"""
import json
import config as C
import numpy as np, pandas as pd

LOG = {}


def _log(name, step, why, rows_after):
    LOG.setdefault(name, []).append({"step": step, "why": why, "rows_after": int(rows_after)})


def replicate_noise(Z, y, g, tol):
    """Noise variance from near-identical runs in DIFFERENT groups (standardised input distance <= tol)."""
    Z = np.asarray(Z, float); Z = (Z - Z.mean(0)) / np.where(Z.std(0) > 0, Z.std(0), 1); d2 = []
    for i in range(len(Z)):
        for j in range(i + 1, len(Z)):
            if g[i] != g[j] and np.sqrt(((Z[i] - Z[j]) ** 2).sum()) <= tol:
                d2.append((y[i] - y[j]) ** 2)
    return (float(np.mean(d2) / 2), len(d2)) if len(d2) >= 5 else (None, len(d2))


def bass2_X(d):
    return pd.DataFrame({"log_o2": np.log(d.o2_pct), "log_flow": np.log(d.opposed_flow_cm_s), "log_inv_d": np.log(1 / d.diameter_cm),
                         "o2_pct": d.o2_pct, "flow": d.opposed_flow_cm_s, "inv_d": 1 / d.diameter_cm})


def bass2(D=None):
    D = D or C.DATA_DIR
    n = "bass2_flame_spread"
    d = pd.read_csv(f"{D}/BASS-II_flame_spread_microgravity_v1.0.csv")
    _log(n, "load NASA PSI-25 / Link et al. 2018 Table S1", "verified extract of measured spread rates", len(d))
    _log(n, "keep flow steps as separate rows, group = ISS test", "flow changes within a test; rows of one test share hardware and are not independent", len(d))
    X = bass2_X(d)
    _log(n, "physics space: log O2, log(1/diameter), log flow + flow; target log(spread)", "spread follows power laws in O2 and rod size (thin-rod spread ~ 1/d); in microgravity spread first rises with opposed flow (more O2 delivered) then falls (flame cooled/blown off), so flow enters as u^a * exp(b*u)", len(d))
    y, g = d.flame_spread_mm_s.values, d.test_id.values
    nv, pairs = replicate_noise(X[["o2_pct", "flow", "inv_d"]], np.log(y), g, 0.35)
    _log(n, f"noise prior from {pairs} near-replicate pairs (log scale)", "the GP starts from measured run-to-run noise instead of guessing it", len(d))
    return dict(name=n, df=d, X=X, y=y, g=g, task="regression", log_target=True,
                mean_cols=["log_o2", "log_flow", "flow", "log_inv_d"], gp_cols=["o2_pct", "log_flow", "inv_d"], noise=nv,
                key="o2_pct", key_sign=+1, raw_inputs=["o2_pct", "opposed_flow_cm_s", "diameter_cm"])


def _flex(D):
    x = pd.read_csv(f"{D}/FLEX_PSI-69_clean_v1.0.csv"); x["co2_pct"] = x.x_CO2 * 100; x["he_pct"] = x.x_He * 100
    return x


def flex_features(df):
    p, o2 = df["pressure_kpa"].astype(float), df["o2_pct"].astype(float)
    return pd.DataFrame({"is_heptane": (df["fuel"].str.lower() == "heptane").astype(float), "log_p": np.log(p), "o2_pct": o2,
                         "o2_partial_kpa": o2 / 100 * p, "co2_pct": df["co2_pct"].astype(float), "he_pct": df["he_pct"].astype(float),
                         "d0_mm": df["d0_mm"].astype(float)})


def flex_extinction(D=None):
    D = D or C.DATA_DIR
    n = "flex_extinction"
    x = _flex(D); _log(n, "load NASA PSI-69 FLEX table", "274 ISS droplet tests", len(x))
    u = x[x.use_for_extinction_model].reset_index(drop=True)
    _log(n, "drop 68 tests: 61 'Disruption' (no clean outcome) + 7 with droplet size or pressure missing in the NASA file", "a droplet that broke up has neither extinguished nor burned out: its label is undefined", len(u))
    X = flex_features(u)
    _log(n, "physics features: O2 partial pressure, log pressure, diluent %, droplet size, fuel", "extinction depends on how much O2 reaches the flame (partial pressure), heat loss (size, diluent) and fuel", len(u))
    _log(n, "group = FLEX test series (first 3 characters of the FLEX id)", "a series shares the same chamber fill; whole series are held out", len(u))
    return dict(name=n, df=u, X=X, y=u.extinguished.astype(int).values, g=u.flex_id.str[:3].values, task="classification",
                gp_cols=list(X.columns), key="o2_pct", key_sign=-1, raw_inputs=["fuel", "pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"])


def flex_burning_rate(D=None):
    D = D or C.DATA_DIR
    n = "flex_burning_rate"
    x = _flex(D); _log(n, "load NASA PSI-69 FLEX table", "274 ISS droplet tests", len(x))
    k = x[x.burning_rate_K_mm2_s.notna() & x.d0_mm.notna() & x.pressure_kpa.notna() & (x.burning_rate_K_mm2_s > 0.1)].reset_index(drop=True)
    _log(n, "drop 16 tests without K, 1 with K <= 0.1 and those missing size or pressure", "K is the slope of the d^2-law; it must be measured and physical", len(k))
    X = flex_features(k)
    _log(n, "physics features (same as extinction); target K in mm^2/s", "d^2-law: K = (8k / rho c_p) ln(1+B); B grows with available O2, falls with diluent", len(k))
    nv, pairs = replicate_noise(X, k.burning_rate_K_mm2_s.values, k.flex_id.str[:3].values, 0.25)
    _log(n, f"noise prior from {pairs} near-replicate pairs", "measured run-to-run noise for the GP", len(k))
    return dict(name=n, df=k, X=X, y=k.burning_rate_K_mm2_s.values, g=k.flex_id.str[:3].values, task="regression", log_target=False,
                mean_cols=list(X.columns), gp_cols=list(X.columns), noise=nv, key="o2_pct", key_sign=+1,
                raw_inputs=["fuel", "pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"])


SPICE_FUELS = ["Ethylene", "Propane", "Propylene", "Propylene/N2 50%", "Propylene/N2 75%"]


def spice_features(df):
    X = pd.DataFrame({"log_burner_d": np.log(df["burner_diameter_mm"].astype(float)), "log_coflow": np.log(df["coflow_air_velocity_cm_s"].astype(float))})
    for f in SPICE_FUELS[1:]:
        X[f"fuel_{f}"] = (df["fuel"] == f).astype(float)
    return X


def spice(D=None):
    D = D or C.DATA_DIR
    n = "spice_smoke_point"
    s = pd.read_csv(f"{D}/SPICE_PSI-107_smoke_points_v1.0.csv")
    _log(n, "load NASA PSI-107 SmokePointReview-0g-3.xlsx rows 5-59", "the sheet that holds measured smoke points (not test settings)", len(s))
    X = spice_features(s)
    _log(n, "physics space: log burner diameter, log coflow, fuel; target log(smoke-point length)", "smoke-point length follows a power law in burner size and coflow (Dotson et al. 2011)", len(s))
    _log(n, "group = ISS session (GMT day)", "a session shares hardware state and calibration", len(s))
    nv, pairs = replicate_noise(X, np.log(s.smoke_point_length_mm.values), s.gmt_day_2009.values, 0.25)
    _log(n, f"noise prior from {pairs} near-replicate pairs (log scale)", "measured run-to-run noise for the GP", len(s))
    return dict(name=n, df=s, X=X, y=s.smoke_point_length_mm.values, g=s.gmt_day_2009.astype(str).values, task="regression", log_target=True,
                mean_cols=list(X.columns), gp_cols=list(X.columns), noise=nv, key="log_coflow", key_sign=+1,
                raw_inputs=["fuel", "burner_diameter_mm", "coflow_air_velocity_cm_s"])


SAME_MATERIALS = ["Kapton", "Lampwick (cotton)", "Pyrell", "Silicone", "Teflon"]


def same_features(df):
    X = pd.DataFrame({"sample_temperature_c": df["sample_temperature_c"].astype(float), "air_velocity_cm_s": df["air_velocity_cm_s"].astype(float),
                      "log_aging_s": np.log1p(df["aging_time_s"].astype(float)), "same_r_campaign": (df["campaign"] == "SAME-R").astype(float)})
    for m in SAME_MATERIALS[1:]:
        X[f"mat_{m}"] = (df["material"] == m).astype(float)
    return X


def same(D=None):
    D = D or C.DATA_DIR
    n = "same_particle_size"
    m0 = pd.read_csv(f"{D}/SAME_PSI-101-102_smoke_particles_v1.0.csv"); _log(n, "load NASA PSI-101/102 results workbook", "154 smoke readings", len(m0))
    m0 = m0[m0.use_for_particle_size_model].reset_index(drop=True)
    _log(n, "drop 24 readings with all particle moments = 0 or '#NUM!'", "an instrument/reduction failure, not a real zero-size smoke", len(m0))
    m0 = m0[m0.sample_temperature_c.notna() & m0.net_aging_time_s.notna()].reset_index(drop=True)
    _log(n, "drop readings with '??' temperature or missing aging time", "the input is unknown, so the row cannot teach the model", len(m0))
    raw = pd.DataFrame({"material": m0.material, "sample_temperature_c": m0.sample_temperature_c, "air_velocity_cm_s": m0.inlet_air_velocity_cm_s,
                        "aging_time_s": m0.net_aging_time_s, "campaign": np.where(m0.psi_id == "PSI-102", "SAME", "SAME-R")})
    X = same_features(raw)
    _log(n, "features: temperature, airflow, log aging time, material, campaign; target log(diameter)", "particle size spans a factor ~20, so errors are relative; aging coagulates particles roughly logarithmically in time", len(m0))
    _log(n, "group = run (fresh + aged reading of the same run kept together)", "the aged reading is the same smoke measured later", len(m0))
    g = (m0.campaign.str[:6] + m0.same_run.str.rstrip("a")).values
    nv, pairs = replicate_noise(X, np.log(m0.count_mean_diameter_um.values), g, 0.35)
    _log(n, f"noise prior from {pairs} near-replicate pairs (log scale)", "measured run-to-run noise for the GP", len(m0))
    return dict(name=n, df=m0, raw=raw, X=X, y=m0.count_mean_diameter_um.values, g=g, task="regression", log_target=True,
                mean_cols=list(X.columns), gp_cols=list(X.columns), noise=nv, key="log_aging_s", key_sign=+1,
                raw_inputs=["material", "sample_temperature_c", "air_velocity_cm_s", "aging_time_s", "campaign"])


def check_no_target_leak(spec):
    """No feature may be the target (or a copy of it); every row must carry a group id."""
    X, y = spec["X"], np.asarray(spec["y"], float)
    for c in X.columns:
        v = X[c].to_numpy(float)
        for t in (y, np.log(np.clip(y, 1e-12, None))):
            if np.allclose(v, t, equal_nan=False) or (np.std(v) > 0 and np.std(t) > 0 and abs(np.corrcoef(v, t)[0, 1]) > 0.999):
                raise AssertionError(f"{spec['name']}: feature '{c}' is (almost) the target - target leakage")
    if pd.isna(pd.Series(spec["g"])).any():
        raise AssertionError(f"{spec['name']}: rows without a group id")
    if len(X) != len(y):
        raise AssertionError(f"{spec['name']}: X and y lengths differ")


def all_specs(D=None):
    LOG.clear()
    S = {f.__name__: f(D) for f in (bass2, flex_extinction, flex_burning_rate, spice, same)}
    out = {s["name"]: s for s in S.values()}
    for s in out.values():
        check_no_target_leak(s)
    C.report("preprocessing_log_v3.json").write_text(json.dumps(LOG, indent=1))
    return out
