"""
Agnishikha - v3: does the objective-driven model (physics-informed GP) beat the alternatives?
Data Science Lead: Prachya Biswas

Same rows and SAME outer grouped splits as v2 (so every model is scored on identical held-out ISS tests).
Scored on what the objective needs, not only accuracy:
  accuracy      MAE, R2 (regression) / ROC-AUC, Brier, log-loss (classifier)
  trust         90 % interval coverage, mean interval width, does the stated uncertainty track the real error (Spearman)
  physics       % of NASA rows where moving the key input in its tested range moves the prediction the WRONG way
Run: python compare_v3.py        -> v3_comparison.csv, v3_physics_check.csv, *_v3_oof.csv
"""
import json, time, warnings
import config as C
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr, norm
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, brier_score_loss, log_loss
from ml_selection import checked_splits, make_cv, select, regression_families, classification_families, LOGLOSS
from pigp import PhysicsGPRegressor, PhysicsGPClassifier
import preprocess_v3 as P
from ignis_models import bass2_features, flex2_features, spice_features, same2_features
warnings.filterwarnings("ignore")

S = P.all_specs()
NEST = joblib.load(C.artifact("v2_nested_cache.joblib"))
OUTER = {"bass2_flame_spread": "logo", "flex_extinction": "kfold", "flex_burning_rate": "kfold", "spice_smoke_point": "logo", "same_particle_size": "kfold"}
V2_TRANSFORM = {"bass2_flame_spread": "tune", "flex_extinction": None, "flex_burning_rate": "tune", "spice_smoke_point": "log", "same_particle_size": "log"}
HYB = "top-3 average + physics-form fallback outside tested domain"
FAMS = ["Ridge (linear)", "k-nearest neighbours", "Support vector regression (RBF)", "Gaussian process (ARD)", "Random forest", "Extra trees", "Gradient boosting"]
CFAMS = ["Logistic regression", "k-nearest neighbours", "Support vector machine (RBF)", "Random forest", "Extra trees", "Gradient boosting"]
z90 = norm.ppf(0.95)


def splits(name):
    sp = S[name]; reps = NEST[name]["res"]["reps"]
    return [checked_splits(make_cv(OUTER[name], len(np.unique(sp["g"])), seed=r), sp["X"], sp["y"], sp["g"], f"{name} repeat {r}") for r in range(reps)]


def fixed_band(y, p, folds, log):
    """band width learned from the OTHER folds' residuals (never from the fold being scored)"""
    lo, hi = np.zeros(len(y)), np.zeros(len(y))
    err = np.log(np.maximum(p / y, y / p)) if log else np.abs(y - p)
    for tr, te in folds:
        q = np.quantile(err[tr], 0.9)
        lo[te], hi[te] = (p[te] * np.exp(-q), p[te] * np.exp(q)) if log else (p[te] - q, p[te] + q)
    return lo, hi


rows, oofs, t_all = [], {}, time.time()
for name, sp in S.items():
    t0 = time.time(); X, y, g = sp["X"], sp["y"], sp["g"]; R = splits(name); cls = sp["task"] == "classification"
    P1 = np.zeros((len(R), len(y))); LO = np.zeros_like(P1); HI = np.zeros_like(P1); SD = np.zeros_like(P1); PH = np.zeros_like(P1)
    for r, folds in enumerate(R):
        for tr, te in folds:
            if cls:
                m = PhysicsGPClassifier(gp_cols=sp["gp_cols"]).fit(X.iloc[tr], y[tr])
                P1[r, te] = m.predict_proba(X.iloc[te])[:, 1]
            else:
                m = PhysicsGPRegressor(mean_cols=sp["mean_cols"], gp_cols=sp["gp_cols"], log_target=sp["log_target"], noise=sp["noise"]).fit(X.iloc[tr], y[tr], groups=g[tr])
                P1[r, te] = m.predict(X.iloc[te]); LO[r, te], HI[r, te] = m.predict_interval(X.iloc[te]); SD[r, te] = m.predict_t(X.iloc[te])[1]
                PH[r, te] = m.physics_only(X.iloc[te])
    res = NEST[name]["res"]
    cands = {"PI-GP (proposed)": P1}
    if not cls:
        cands["Physics law only (PI-GP mean)"] = PH
    cands["v2: top-3 average + fallback"] = res["proc_pred"][HYB]
    for f in (CFAMS if cls else FAMS):
        cands[f + " (tuned, v2)"] = res["fam_pred"][f]
    for c, M in cands.items():
        ms = []
        for r, folds in enumerate(R):
            p = M[r]
            if cls:
                pc = np.clip(p, 1e-4, 1 - 1e-4)
                ms.append({"ROC_AUC": roc_auc_score(y, pc), "Brier": brier_score_loss(y, pc), "log_loss": log_loss(y, pc)})
            else:
                if c == "PI-GP (proposed)":
                    lo, hi = LO[r], HI[r]; sp_r = spearmanr(SD[r], np.abs(np.log(p / y)) if sp["log_target"] else np.abs(p - y)).correlation
                else:
                    lo, hi = fixed_band(y, p, folds, sp["log_target"]); sp_r = 0.0
                width = np.mean(np.log(hi / lo)) if sp["log_target"] else np.mean(hi - lo)
                ms.append({"MAE": mean_absolute_error(y, p), "R2": r2_score(y, p), "coverage90_pct": 100 * np.mean((y >= lo) & (y <= hi)),
                           "mean_width": width, "uncertainty_tracks_error_spearman": sp_r})
        rows.append({"model_task": name, "model": c} | pd.DataFrame(ms).mean().round(4).to_dict())
    oofs[name] = pd.DataFrame({"y": y, "group": g, "pigp_pred": P1[0]} | ({} if cls else {"pigp_lo90": LO[0], "pigp_hi90": HI[0], "physics_only": PH[0]}))
    oofs[name].to_csv(C.report(f"{name}_v3_oof.csv"), index=False)
    print(f"{name}: {time.time()-t0:.0f}s"); print(pd.DataFrame([r for r in rows if r["model_task"] == name]).drop(columns="model_task").to_string(index=False), flush=True)

T = pd.DataFrame(rows); T.to_csv(C.report("v3_comparison.csv"), index=False)

# ---------------- physics consistency: move the key input across its tested range, row by row ----------------
KEY = {"bass2_flame_spread": ("o2_pct", +1), "flex_extinction": ("o2_pct", -1), "flex_burning_rate": ("o2_pct", +1),
       "spice_smoke_point": ("coflow_air_velocity_cm_s", +1), "same_particle_size": ("aging_time_s", +1)}

def raw_df(name):
    return S[name]["raw"].copy() if name == "same_particle_size" else S[name]["df"].copy()

def v2_X(name, df):
    if name == "bass2_flame_spread": return bass2_features(df)
    if name.startswith("flex"): return flex2_features(df.assign(co2_pct=df.co2_pct, he_pct=df.he_pct))
    if name == "spice_smoke_point": return spice_features(df)
    return same2_features(df)

def v3_X(name, df):
    if name == "bass2_flame_spread": return P.bass2_X(df)
    if name.startswith("flex"): return P.flex_features(df)
    if name == "spice_smoke_point": return P.spice_features(df)
    return P.same_features(df)

phys = []
for name, sp in S.items():
    cls = sp["task"] == "classification"; col, sign = KEY[name]; df = raw_df(name)
    grid = np.linspace(df[col].min(), df[col].max(), 12)
    models = {}
    if cls:
        models["PI-GP (proposed)"] = (PhysicsGPClassifier(gp_cols=sp["gp_cols"]).fit(sp["X"], sp["y"]), v3_X)
    else:
        models["PI-GP (proposed)"] = (PhysicsGPRegressor(mean_cols=sp["mean_cols"], gp_cols=sp["gp_cols"], log_target=sp["log_target"], noise=sp["noise"]).fit(sp["X"], sp["y"], groups=sp["g"]), v3_X)
    Xv2 = v2_X(name, df); yfit = np.log(sp["y"]) if V2_TRANSFORM[name] == "log" else sp["y"]
    fams = classification_families(Xv2.shape[1]) if cls else regression_families(Xv2.shape[1], allow_log=V2_TRANSFORM[name] == "tune")
    keep = CFAMS if cls else FAMS
    sel = select(Xv2, yfit, sp["g"], {k: v for k, v in fams.items() if k in keep}, LOGLOSS if cls else "neg_mean_absolute_error", seed=999)
    for f in keep:
        models[f + " (tuned, v2)"] = (sel["table"][f]["est"], v2_X)
    b = joblib.load(C.archived("v2", f"{name}.joblib")); models["v2: top-3 average + fallback"] = (b["model"], v2_X)
    for mname, (m, fx) in models.items():
        bad = 0
        for i in range(len(df)):
            G = pd.concat([df.iloc[[i]]] * len(grid), ignore_index=True); G[col] = grid
            Xg = fx(name, G)
            Xg = Xg[m.feature_names_in_] if hasattr(m, "feature_names_in_") else Xg
            p = m.predict_proba(Xg)[:, 1] if cls else np.asarray(m.predict(Xg), float)
            span = max(np.ptp(p), 1e-12) if np.ptp(p) > 0 else 1.0
            steps = sign * np.diff(p)
            if (steps < -0.02 * (abs(p).mean() + 1e-12)).any():
                bad += 1
        phys.append({"model_task": name, "model": mname, "key_input": col, "expected": "up" if sign > 0 else "down",
                     "rows_violating_pct": round(100 * bad / len(df), 1)})
    print(name, "physics check done", flush=True)
PC = pd.DataFrame(phys); PC.to_csv(C.report("v3_physics_check.csv"), index=False)
print(PC.pivot(index="model", columns="model_task", values="rows_violating_pct").to_string())
print(f"total {time.time()-t_all:.0f}s")
