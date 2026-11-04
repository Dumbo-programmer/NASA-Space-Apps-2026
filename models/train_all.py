"""
Ignis mu / AgniShikha - train Models 2-5 on the verified NASA datasets (v1.0)
  Model 2  flex_extinction      : will the droplet flame go out before the fuel is used up?  (classifier)
  Model 3  flex_burning_rate    : droplet burning-rate constant K (mm^2/s)                   (regression)
  Model 4  spice_smoke_point    : smoke-point flame length (mm) - sooting tendency           (regression)
  Model 5  same_particle_size   : smoke particle count-mean diameter (um)                    (regression)
Validation is always GROUPED (whole test series / session / run-pair held out together).
Run: python train_all.py <datasets_dir>
"""
import sys, json, warnings
import numpy as np, pandas as pd, joblib
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, cross_val_predict
from sklearn.linear_model import LogisticRegression, LinearRegression, RidgeCV
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, brier_score_loss, mean_absolute_error, r2_score
from ignis_models import flex_features, spice_features, same_features
warnings.filterwarnings("ignore")
D = sys.argv[1]; RS = 42; summary = {}

def nn_limit(X):
    mu, sd = X.mean(), X.std(ddof=0).replace(0, 1); Z = ((X - mu) / sd).values; best = []
    for i in range(len(Z)):
        dd = np.sqrt(((Z - Z[i]) ** 2).sum(1)); dd[i] = np.inf; best.append(dd.min())
    return float(np.quantile(best, 0.99)), mu.to_dict(), sd.to_dict()

def ranges(df, cols):
    return {c: [round(float(df[c].min()), 4), round(float(df[c].max()), 4)] for c in cols}

def per_cat(df, by, cols):
    return {"by": by, "ranges": {k: ranges(g, cols) for k, g in df.groupby(by)}}

def save(name, bundle, cv_table, oof):
    joblib.dump(bundle, f"{name}.joblib"); cv_table.to_csv(f"{name}_cv_results.csv", index=False); oof.to_csv(f"{name}_oof.csv", index=False)
    summary[name] = {"chosen": bundle["model_label"], "validation": bundle["validation"], "rows": bundle["n_rows"], "groups": bundle["n_groups"]}

# =============================== FLEX ===============================
x = pd.read_csv(f"{D}/FLEX_PSI-69_clean_v1.0.csv")
x["co2_pct"] = x.x_CO2 * 100; x["he_pct"] = x.x_He * 100
RAW_FLEX = ["fuel", "pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]
SRC_FLEX = "NASA PSI-69 FLEX experimental table (CC0-1.0), DOI 10.60555/mbq8-0451"

# ---- Model 2: extinction classifier ----
u = x[x.use_for_extinction_model].reset_index(drop=True)
X, y, g = flex_features(u), u.extinguished.astype(int).values, u.flex_id.str[:3].values   # group = test series (same ambient)
cv = GroupKFold(n_splits=5)
cands = {"Prior (always 'extinguishes')": DummyClassifier(strategy="prior"),
         "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
         "Logistic regression (class-balanced)": make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000)),
         "Random forest": RandomForestClassifier(400, min_samples_leaf=3, random_state=RS),
         "Extra trees": ExtraTreesClassifier(400, min_samples_leaf=3, random_state=RS),
         "Extra trees (class-balanced)": ExtraTreesClassifier(400, min_samples_leaf=3, class_weight="balanced_subsample", random_state=RS)}
rows, probs = [], {}
base_rate = y.mean()
for n, m in cands.items():
    p = cross_val_predict(m, X, y, groups=g, cv=cv, method="predict_proba")[:, 1]; probs[n] = p
    thr = float(np.quantile(p, 1 - base_rate)) if p.std() > 0 else 0.5      # flag the same share of tests as the base rate
    rows.append({"model": n, "ROC_AUC": roc_auc_score(y, p) if p.std() > 0 else 0.5, "Brier": brier_score_loss(y, p),
                 "balanced_accuracy_at_threshold": balanced_accuracy_score(y, (p >= thr).astype(int)), "threshold": thr})
cvt = pd.DataFrame(rows); print("\nFLEX extinction\n", cvt.round(3).to_string(index=False))
prior_brier = cvt.iloc[0].Brier
ok = cvt.iloc[1:][cvt.iloc[1:].Brier < prior_brier]              # probabilities must beat the base rate (honest probabilities)
best = ok.sort_values("ROC_AUC", ascending=False).iloc[0].model
threshold = float(cvt[cvt.model == best].threshold.iloc[0])
final = cands[best].fit(X, y)
lim, mu, sd = nn_limit(X)
oof = u[["record_id", "flex_id", "fuel", "pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm", "test_end"]].assign(p_extinction_oof=probs[best].round(3))
save("flex_extinction", {
    "task": "classification", "feature_fn": "flex", "features": list(X.columns), "model": final, "model_label": best,
    "classes": ["burns to completion", "flame extinguishes before fuel is used up"],
    "target_label": "P(flame extinguishes before droplet burns out)",
    "prob_note": f"{int(round(base_rate*100))}% of the 206 ISS tests ended in extinction (base rate); 'burns to completion' is flagged when P < {threshold:.2f}",
    "threshold": threshold, "base_rate": float(base_rate),
    "groups": {c: [c] for c in X.columns}, "background": X,
    "domain": {"ranges": ranges(u, ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]), "categories": {"fuel": ["Methanol", "Heptane"]},
               "per_category_ranges": per_cat(u, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
    "valid_for": "isolated methanol or n-heptane droplets, quiescent microgravity (ISS CIR/MDCA), O2/N2 with CO2 or He diluent",
    "validation": {k: round(float(v), 3) for k, v in cvt[cvt.model == best].iloc[0].drop("model").items()} | {"cv": "GroupKFold(5) by FLEX test series", "baseline_AUC": 0.5, "baseline_Brier": round(float(prior_brier), 3)},
    "source": SRC_FLEX, "n_rows": int(len(u)), "n_groups": int(len(set(g))), "version": "1.0"}, cvt, oof)

# ---- Model 3: burning-rate constant K ----
k = x[x.burning_rate_K_mm2_s.notna() & x.d0_mm.notna() & x.pressure_kpa.notna() & (x.burning_rate_K_mm2_s > 0.1)].reset_index(drop=True)
X, y, g = flex_features(k), k.burning_rate_K_mm2_s.values, k.flex_id.str[:3].values
cands = {"Mean baseline": DummyRegressor(), "Linear": make_pipeline(StandardScaler(), LinearRegression()),
         "Extra trees": ExtraTreesRegressor(400, min_samples_leaf=3, random_state=RS),
         "Gradient boosting": GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=RS)}
rows, preds = [], {}
for n, m in cands.items():
    p = cross_val_predict(m, X, y, groups=g, cv=cv); preds[n] = p
    rows.append({"model": n, "MAE": mean_absolute_error(y, p), "R2": r2_score(y, p), "MAE_pct_of_mean": 100 * mean_absolute_error(y, p) / y.mean()})
cvt = pd.DataFrame(rows); print("\nFLEX burning rate K\n", cvt.round(3).to_string(index=False))
best = cvt.iloc[1:].sort_values("MAE").iloc[0].model; final = cands[best].fit(X, y)
q90 = float(np.quantile(np.abs(y - preds[best]), 0.9)); lim, mu, sd = nn_limit(X)
save("flex_burning_rate", {
    "task": "regression", "feature_fn": "flex", "features": list(X.columns), "model": final, "model_label": best,
    "target_label": "droplet burning-rate constant K (d^2 shrinks at K mm^2/s)", "unit": "mm^2/s",
    "target_transform": "none", "band": ("additive", q90), "groups": {c: [c] for c in X.columns}, "background": X,
    "domain": {"ranges": ranges(k, ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]), "categories": {"fuel": ["Methanol", "Heptane"]},
               "per_category_ranges": per_cat(k, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
    "valid_for": "isolated methanol or n-heptane droplets, quiescent microgravity (ISS FLEX)",
    "validation": {k2: round(float(v), 4) for k2, v in cvt[cvt.model == best].iloc[0].drop("model").items()} | {"cv": "GroupKFold(5) by FLEX test series", "q90_abs_error": round(q90, 4)},
    "source": SRC_FLEX, "n_rows": int(len(k)), "n_groups": int(len(set(g))), "version": "1.0"},
    cvt, k[["record_id", "fuel", "o2_pct", "pressure_kpa", "d0_mm", "burning_rate_K_mm2_s"]].assign(pred_oof=preds[best].round(4)))

# =============================== SPICE ===============================
s = pd.read_csv(f"{D}/SPICE_PSI-107_smoke_points_v1.0.csv")
X, yl, g = spice_features(s), np.log(s.smoke_point_length_mm.values), s.gmt_day_2009.astype(str).values   # group = ISS session
logo = LeaveOneGroupOut()
cands = {"Mean baseline": DummyRegressor(), "Power law (log-linear, physics form)": LinearRegression(),
         "Ridge power law": RidgeCV(alphas=np.logspace(-3, 2, 30)),
         "Extra trees": ExtraTreesRegressor(400, min_samples_leaf=2, random_state=RS)}
rows, preds = [], {}
yt = s.smoke_point_length_mm.values
for n, m in cands.items():
    p = np.exp(cross_val_predict(m, X, yl, groups=g, cv=logo)); preds[n] = p
    rows.append({"model": n, "MAE_mm": mean_absolute_error(yt, p), "R2": r2_score(yt, p), "MAPE_pct": 100 * np.mean(np.abs(p - yt) / yt)})
cvt = pd.DataFrame(rows); print("\nSPICE smoke point\n", cvt.round(3).to_string(index=False))
best = cvt.iloc[1:].sort_values("MAE_mm").iloc[0].model; final = cands[best].fit(X, yl)
ratio = np.maximum(preds[best] / yt, yt / preds[best]); q90 = float(np.quantile(ratio, 0.9)); lim, mu, sd = nn_limit(X)
coef = dict(zip(X.columns, np.round(final.coef_, 3))) if hasattr(final, "coef_") else {}
save("spice_smoke_point", {
    "task": "regression", "feature_fn": "spice", "features": list(X.columns), "model": final, "model_label": best,
    "target_label": "smoke-point flame length (shorter = sootier, more smoke)", "unit": "mm",
    "target_transform": "log", "band": ("multiplicative", q90),
    "groups": {"burner diameter": ["log_burner_d"], "coflow air velocity": ["log_coflow"], "fuel": [c for c in X.columns if c.startswith("fuel_")]},
    "background": X, "power_law_coefficients": coef,
    "domain": {"ranges": ranges(s, ["burner_diameter_mm", "coflow_air_velocity_cm_s"]),
               "categories": {"fuel": sorted(s.fuel.unique().tolist())},
               "per_category_ranges": per_cat(s, "fuel", ["burner_diameter_mm", "coflow_air_velocity_cm_s"]),
               "nn_limit": lim, "z_mean": mu, "z_std": sd},
    "valid_for": "laminar gas-jet diffusion flames in coflowing air, microgravity (ISS SPICE), 1 atm",
    "validation": {k2: round(float(v), 3) for k2, v in cvt[cvt.model == best].iloc[0].drop("model").items()} | {"cv": "leave-one-ISS-session-out (11 sessions)", "q90_ratio": round(q90, 3)},
    "source": "NASA PSI-107 SPICE, SmokePointReview-0g-3.xlsx (CC0-1.0), DOI 10.60555/9kbh-e962", "n_rows": int(len(s)), "n_groups": int(len(set(g))), "version": "1.0"},
    cvt, s[["record_id", "fuel", "burner_diameter_mm", "coflow_air_velocity_cm_s", "smoke_point_length_mm"]].assign(pred_oof=preds[best].round(2)))
print("power-law coefficients:", coef)

# =============================== SAME ===============================
m0 = pd.read_csv(f"{D}/SAME_PSI-101-102_smoke_particles_v1.0.csv")
m0 = m0[m0.use_for_particle_size_model & m0.sample_temperature_c.notna() & m0.net_aging_time_s.notna()].reset_index(drop=True)
raw = pd.DataFrame({"material": m0.material, "sample_temperature_c": m0.sample_temperature_c, "air_velocity_cm_s": m0.inlet_air_velocity_cm_s,
                    "aging_time_s": m0.net_aging_time_s, "campaign": np.where(m0.psi_id == "PSI-102", "SAME", "SAME-R")})
X, yl, g = same_features(raw), np.log(m0.count_mean_diameter_um.values), (m0.campaign.str[:6] + m0.same_run.str.rstrip("a")).values  # fresh+aged pair together
yt = m0.count_mean_diameter_um.values
cands = {"Mean baseline": DummyRegressor(), "Log-linear": make_pipeline(StandardScaler(), LinearRegression()),
         "Extra trees": ExtraTreesRegressor(400, min_samples_leaf=2, random_state=RS),
         "Gradient boosting": GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=RS)}
rows, preds = [], {}
for n, mdl in cands.items():
    p = np.exp(cross_val_predict(mdl, X, yl, groups=g, cv=cv)); preds[n] = p
    rows.append({"model": n, "MAE_um": mean_absolute_error(yt, p), "R2": r2_score(yt, p), "MAPE_pct": 100 * np.mean(np.abs(p - yt) / yt)})
cvt = pd.DataFrame(rows); print("\nSAME particle size\n", cvt.round(3).to_string(index=False))
best = cvt.iloc[1:].sort_values("MAE_um").iloc[0].model; final = cands[best].fit(X, yl)
ratio = np.maximum(preds[best] / yt, yt / preds[best]); q90 = float(np.quantile(ratio, 0.9)); lim, mu, sd = nn_limit(X)
save("same_particle_size", {
    "task": "regression", "feature_fn": "same", "features": list(X.columns), "model": final, "model_label": best,
    "target_label": "smoke particle count-mean diameter (what an optical smoke detector must see)", "unit": "um",
    "target_transform": "log", "band": ("multiplicative", q90),
    "groups": {"sample temperature": ["sample_temperature_c"], "air velocity": ["air_velocity_cm_s"], "aging time": ["log_aging_s"],
               "campaign/instruments": ["same_r_campaign"], "material": [c for c in X.columns if c.startswith("mat_")]},
    "background": X,
    "domain": {"ranges": ranges(raw, ["sample_temperature_c", "air_velocity_cm_s", "aging_time_s"]),
               "categories": {"material": sorted(raw.material.unique().tolist()), "campaign": ["SAME", "SAME-R"]},
               "per_category_ranges": per_cat(raw, "material", ["sample_temperature_c"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
    "valid_for": "smoke from overheated (non-flaming) spacecraft materials, microgravity (ISS SAME/SAME-R)",
    "validation": {k2: round(float(v), 4) for k2, v in cvt[cvt.model == best].iloc[0].drop("model").items()} | {"cv": "GroupKFold(5), fresh+aged readings of a run kept together", "q90_ratio": round(q90, 3)},
    "source": "NASA PSI-101/102 SAME & SAME-R results workbook (CC0-1.0)", "n_rows": int(len(m0)), "n_groups": int(len(set(g))), "version": "1.0"},
    cvt, m0[["record_id", "material", "sample_temperature_c", "inlet_air_velocity_cm_s", "net_aging_time_s", "count_mean_diameter_um"]].assign(pred_oof=preds[best].round(4)))

json.dump(summary, open("model_summary.json", "w"), indent=2, default=str)
print("\nSUMMARY\n", json.dumps(summary, indent=1, default=str))
