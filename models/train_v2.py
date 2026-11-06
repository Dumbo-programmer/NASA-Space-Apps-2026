"""
Ignis mu / AgniShikha - train all five models with NESTED grouped model selection (v2)
Data Science Lead: Prachya Biswas

  Model 1  bass2_flame_spread   : flame spread over a PMMA rod, opposed flow (mm/s)        regression
  Model 2  flex_extinction      : P(droplet flame goes out before the fuel is used up)     classification
  Model 3  flex_burning_rate    : droplet burning-rate constant K (mm^2/s)                 regression
  Model 4  spice_smoke_point    : smoke-point flame length (mm)                            regression
  Model 5  same_particle_size   : smoke particle count-mean diameter (um)                  regression

Phase 1  nested grouped CV per model: 8 regression / 7 classification families tuned in the inner loop,
         three selection PROCEDURES scored honestly in the outer loop:
            (a) best inner score   (b) 1-SE rule: simplest near-best   (c) top-3 average (ensemble)
Phase 2  ONE procedure is chosen for all five models = best mean rank across the five datasets
         (one global decision instead of five -> little room for optimism).
Phase 3  that procedure is run on all rows of each dataset -> final model, bands, domain, bundle.

Run: python train_v2.py data            (phase 1 cached in v2_nested_cache.joblib; add --reuse to skip it)
"""
import sys, os, json, time
import numpy as np, pandas as pd, joblib
from sklearn.base import clone
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, brier_score_loss
from sklearn.ensemble import ExtraTreesRegressor, ExtraTreesClassifier
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from ml_selection import (nested_cv, summarise, select, regression_families, classification_families, make_cv,
                          reg_metrics, clf_metrics, group_bootstrap_ci, AveragedModel, PROCEDURES, LOGLOSS)
from ignis_models import flex_features, same_features, flex2_features, spice_features, same2_features, bass2_features

D = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "data"
REUSE = "--reuse" in sys.argv
REPEATS, RS = 3, 42


def nn_limit(X):
    mu, sd = X.mean(), X.std(ddof=0).replace(0, 1); Z = ((X - mu) / sd).values; best = []
    for i in range(len(Z)):
        dd = np.sqrt(((Z - Z[i]) ** 2).sum(1)); dd[i] = np.inf; best.append(dd.min())
    return float(np.quantile(best, 0.99)), mu.to_dict(), sd.to_dict()

def ranges(df, cols):
    return {c: [round(float(df[c].min()), 4), round(float(df[c].max()), 4)] for c in cols}

def per_cat(df, by, cols):
    return {"by": by, "ranges": {k: ranges(gr, cols) for k, gr in df.groupby(by)}}

def r4(v):
    return round(float(v), 4) if isinstance(v, (float, np.floating, int, np.integer)) else v


# ============================================================ datasets (same rows as v1)
def load_specs():
    S = {}
    d = pd.read_csv(f"{D}/BASS-II_flame_spread_microgravity_v1.0.csv")
    S["bass2_flame_spread"] = dict(
        df=d, X=bass2_features(d), y=d.flame_spread_mm_s.values, g=d.test_id.values, task="regression", outer="logo", transform="tune",
        primary="MAE", v1=(ExtraTreesRegressor(300, min_samples_leaf=3, random_state=RS),
                           pd.DataFrame({"o2_pct": d.o2_pct, "opposed_flow_cm_s": d.opposed_flow_cm_s, "inv_diameter_per_cm": 1 / d.diameter_cm})),
        v1_reported={"MAE": 0.0094, "R2": 0.53}, dom=(d, "diameter_cm", ["o2_pct", "opposed_flow_cm_s"], ["o2_pct", "opposed_flow_cm_s"]))
    x = pd.read_csv(f"{D}/FLEX_PSI-69_clean_v1.0.csv"); x["co2_pct"] = x.x_CO2 * 100; x["he_pct"] = x.x_He * 100
    u = x[x.use_for_extinction_model].reset_index(drop=True)
    S["flex_extinction"] = dict(
        df=u, X=flex2_features(u), y=u.extinguished.astype(int).values, g=u.flex_id.str[:3].values, task="classification", outer="kfold",
        transform=None, primary="log_loss", v1=(ExtraTreesClassifier(400, min_samples_leaf=3, random_state=RS), flex_features(u)),
        v1_reported={"ROC_AUC": 0.842, "Brier": 0.092}, dom=(u, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"], ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]))
    k = x[x.burning_rate_K_mm2_s.notna() & x.d0_mm.notna() & x.pressure_kpa.notna() & (x.burning_rate_K_mm2_s > 0.1)].reset_index(drop=True)
    S["flex_burning_rate"] = dict(
        df=k, X=flex2_features(k), y=k.burning_rate_K_mm2_s.values, g=k.flex_id.str[:3].values, task="regression", outer="kfold",
        transform="tune", primary="MAE", v1=(make_pipeline(StandardScaler(), LinearRegression()), flex_features(k)),
        v1_reported={"MAE": 0.0473, "R2": 0.7202}, dom=(k, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"], ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]))
    s = pd.read_csv(f"{D}/SPICE_PSI-107_smoke_points_v1.0.csv")
    S["spice_smoke_point"] = dict(
        df=s, X=spice_features(s), y=s.smoke_point_length_mm.values, g=s.gmt_day_2009.astype(str).values, task="regression", outer="logo",
        transform="log", primary="MAE", v1=(LinearRegression(), spice_features(s)), v1_reported={"MAE": 5.686, "R2": 0.849},
        dom=(s, "fuel", ["burner_diameter_mm", "coflow_air_velocity_cm_s"], ["burner_diameter_mm", "coflow_air_velocity_cm_s"]))
    m0 = pd.read_csv(f"{D}/SAME_PSI-101-102_smoke_particles_v1.0.csv")
    m0 = m0[m0.use_for_particle_size_model & m0.sample_temperature_c.notna() & m0.net_aging_time_s.notna()].reset_index(drop=True)
    raw = pd.DataFrame({"material": m0.material, "sample_temperature_c": m0.sample_temperature_c, "air_velocity_cm_s": m0.inlet_air_velocity_cm_s,
                        "aging_time_s": m0.net_aging_time_s, "campaign": np.where(m0.psi_id == "PSI-102", "SAME", "SAME-R")})
    S["same_particle_size"] = dict(
        df=m0, raw=raw, X=same2_features(raw), y=m0.count_mean_diameter_um.values, g=(m0.campaign.str[:6] + m0.same_run.str.rstrip("a")).values,
        task="regression", outer="kfold", transform="log", primary="MAE",
        v1=(ExtraTreesRegressor(400, min_samples_leaf=2, random_state=RS), same_features(raw)), v1_reported={"MAE": 0.0602, "R2": 0.4977},
        dom=(raw, "material", ["sample_temperature_c"], ["sample_temperature_c", "air_velocity_cm_s", "aging_time_s"]),
        physics_form=False)   # no established physical law for smoke particle size -> no physics-form fallback
    return S


def threshold_fn(y):
    br = float(np.mean(y)); return lambda p: float(np.quantile(p, 1 - br))


# ============================================================ phase 1: nested CV
S = load_specs()
NEST = {}
if REUSE and os.path.exists("v2_nested_cache.joblib"):
    try:
        NEST = joblib.load("v2_nested_cache.joblib")
    except Exception as e:                       # e.g. a different scikit-learn version
        print(f"cache could not be loaded ({type(e).__name__}); running the full nested CV instead")
if True:
    for name, sp in S.items():
        if name in NEST:
            print(f"(cached) {name}"); continue
        t0 = time.time(); print(f"\n================ {name}  ({len(sp['y'])} rows, {len(np.unique(sp['g']))} groups)", flush=True)
        res = nested_cv(sp["X"], sp["y"], sp["g"], sp["task"], outer=sp["outer"], repeats=REPEATS, transform=sp["transform"])
        thr = threshold_fn(sp["y"]) if sp["task"] == "classification" else None
        table = summarise(res, sp["y"], sp["g"], sp["task"], thr)
        est, Xv1 = sp["v1"]; y = sp["y"]; P = np.zeros((res["reps"], len(y)))
        yfit = np.log(y) if sp["transform"] == "log" else y
        for r in range(res["reps"]):                               # v1 model on exactly the same outer splits
            cv = make_cv(sp["outer"], len(np.unique(sp["g"])), seed=r)
            if sp["task"] == "classification":
                P[r] = cross_val_predict(clone(est), Xv1, y, groups=sp["g"], cv=cv, method="predict_proba")[:, 1]
            else:
                p = cross_val_predict(clone(est), Xv1, yfit, groups=sp["g"], cv=cv); P[r] = np.exp(p) if sp["transform"] == "log" else p
        ms = pd.DataFrame([reg_metrics(y, P[r]) if sp["task"] == "regression" else clf_metrics(y, P[r], thr(P[r])) for r in range(res["reps"])])
        table = pd.concat([table, pd.DataFrame([{"model": "[v1] model, same outer splits"} | ms.mean().to_dict()])], ignore_index=True)
        print(table.round(4).to_string(index=False), f"\n({time.time()-t0:.0f}s)", flush=True)
        NEST[name] = {"res": res, "table": table, "v1_pred": P}
        joblib.dump(NEST, "v2_nested_cache.joblib")


# ============================================================ phase 1b: ensemble + physics fallback outside the tested domain
FALLBACK = {"regression": "Ridge (linear)", "classification": "Logistic regression"}
HYB = "top-3 average + physics-form fallback outside tested domain"

def in_domain_mask(sp, tr, te):
    """Same rule the deployed model uses: numeric ranges, per-category ranges, nearest-neighbour distance (training rows only)."""
    df, cat, cat_cols, num_cols = sp["dom"]; df = df.reset_index(drop=True); X = sp["X"].reset_index(drop=True)
    A, B = df.iloc[tr], df.iloc[te]; ok = np.ones(len(te), bool)
    for c in num_cols:
        ok &= (B[c].values >= A[c].min() - 1e-9) & (B[c].values <= A[c].max() + 1e-9)
    for i, (_, row) in enumerate(B.iterrows()):
        sub = A[A[cat] == row[cat]]
        if len(sub) == 0:
            ok[i] = False; continue
        for c in cat_cols:
            if not (sub[c].min() - 1e-9 <= row[c] <= sub[c].max() + 1e-9):
                ok[i] = False
    lim, mu, sd = nn_limit(X.iloc[tr]); mu, sd = pd.Series(mu), pd.Series(sd).replace(0, 1)
    Z = ((X.iloc[tr] - mu) / sd).values; z = ((X.iloc[te] - mu) / sd).values
    nn = np.sqrt(((z[:, None, :] - Z[None, :, :]) ** 2).sum(2)).min(1)
    return ok & (nn <= lim)

for name, sp in S.items():
    res = NEST[name]["res"]; y, g = sp["y"], sp["g"]
    P = res["proc_pred"]["top-3 average"].copy(); F = res["fam_pred"][FALLBACK[sp["task"]]]; share = []
    for r in range(res["reps"]):
        cv = make_cv(sp["outer"], len(np.unique(g)), seed=r)
        for tr, te in cv.split(sp["X"], y, g):
            m = in_domain_mask(sp, tr, te)
            if not sp.get("physics_form", True):
                m[:] = True                         # keep the ensemble everywhere (out-of-domain inputs still get a warning)
            P[r, te[~m]] = F[r, te[~m]]; share.append((~m).sum())
    res["proc_pred"][HYB] = P
    thr = threshold_fn(y) if sp["task"] == "classification" else None
    ms = pd.DataFrame([reg_metrics(y, P[r]) if sp["task"] == "regression" else clf_metrics(y, P[r], thr(P[r])) for r in range(res["reps"])])
    row = {"model": f"[procedure] {HYB}"} | ms.mean().to_dict()
    t = NEST[name]["table"]; t = t[t.model != row["model"]]
    NEST[name]["table"] = pd.concat([t.iloc[:3], pd.DataFrame([row]), t.iloc[3:]], ignore_index=True)
    NEST[name]["fallback_share_pct"] = round(100 * sum(share) / (len(y) * res["reps"]), 1)
    print(f"{name}: " + (f"{NEST[name]['fallback_share_pct']}% of held-out rows were outside the training domain -> physics fallback"
                         if sp.get("physics_form", True) else "no physics-form law -> ensemble used everywhere (out-of-domain inputs are still flagged)"))

joblib.dump(NEST, "v2_nested_cache.joblib")          # keep the hybrid procedure's honest predictions too

# ============================================================ phase 2: one global procedure
ranks = []
for name, sp in S.items():
    t = NEST[name]["table"]; higher = sp["primary"] in ("R2", "ROC_AUC")
    sub = t[t.model.str.startswith("[procedure]")].set_index("model")[sp["primary"]]
    ranks.append(sub.rank(ascending=not higher).rename(name))
R = pd.concat(ranks, axis=1); R["mean_rank"] = R.mean(axis=1)
tiebreak = {"[procedure] 1-SE rule (simplest near-best)": 0, "[procedure] best inner score": 1, "[procedure] top-3 average": 2, f"[procedure] {HYB}": 3}
PROC = min(R.index, key=lambda i: (R.loc[i, "mean_rank"], tiebreak[i])).replace("[procedure] ", "")
print("\nPROCEDURE RANKS (1 = best on that model's primary metric)\n", R.round(2).to_string(), f"\n=> global procedure: {PROC}")
R.round(3).to_csv("v2_procedure_ranks.csv")

# ============================================================ phase 3: final models
summary, comparison = {}, []
SRC_FLEX = "NASA PSI-69 FLEX experimental table (CC0-1.0), DOI 10.60555/mbq8-0451"
flex_groups = {"fuel": ["is_heptane"], "pressure": ["log_pressure"], "oxygen": ["o2_pct", "o2_partial_kpa"],
               "CO2 diluent": ["co2_pct"], "helium diluent": ["he_pct"], "droplet size": ["d0_mm"]}

for name, sp in S.items():
    X, y, g, task = sp["X"], sp["y"], sp["g"], sp["task"]
    res, table = NEST[name]["res"], NEST[name]["table"]
    fams = regression_families(X.shape[1], allow_log=(sp["transform"] == "tune")) if task == "regression" else classification_families(X.shape[1])
    scoring = "neg_mean_absolute_error" if task == "regression" else LOGLOSS
    yfit = np.log(y) if sp["transform"] == "log" else y
    t0 = time.time(); sel = select(X, yfit, g, fams, scoring, seed=999)
    names = sel["members"]["top-3 average" if PROC == HYB else PROC]
    final = sel["table"][names[0]]["est"] if len(names) == 1 else AveragedModel([sel["table"][n]["est"] for n in names], names, task)
    label = names[0] if len(names) == 1 else "Average of " + " + ".join(names)
    params = {n: {k: str(getattr(v, "__name__", v)) for k, v in sel["table"][n]["params"].items()} for n in names}
    inner = pd.DataFrame([{"model": n, "inner_cv_score": i["score"], "paired_se_vs_best": i.get("se"), "complexity_rank": i["rank"],
                           "in_final_model": n in names, "best_params": json.dumps({k: str(getattr(v, "__name__", v)) for k, v in i["params"].items()})}
                          for n, i in sel["table"].items()]).sort_values("inner_cv_score", ascending=False)
    print(f"\n{name}: FINAL = {label}  ({time.time()-t0:.0f}s)", flush=True)

    proc = res["proc_pred"][PROC]; row = table[table.model == f"[procedure] {PROC}"].iloc[0]
    if task == "regression":
        val = {k: r4(row[k]) for k in ["MAE", "RMSE", "R2", "MAPE_pct"]}
        val |= {"MAE_95CI": [r4(v) for v in group_bootstrap_ci(y, proc[0], g, mean_absolute_error)],
                "R2_95CI": [r4(v) for v in group_bootstrap_ci(y, proc[0], g, r2_score)]}
    else:
        thr = threshold_fn(y)(proc[0]); br = float(y.mean())
        val = {k: r4(row[k]) for k in ["ROC_AUC", "Brier", "log_loss", "balanced_accuracy"]}
        val |= {"ROC_AUC_95CI": [r4(v) for v in group_bootstrap_ci(y, proc[0], g, roc_auc_score)],
                "Brier_95CI": [r4(v) for v in group_bootstrap_ci(y, proc[0], g, brier_score_loss)],
                "baseline_Brier": r4(brier_score_loss(y, np.full(len(y), br))), "baseline_AUC": 0.5, "threshold": r4(thr)}
    val["method"] = (f"nested grouped CV - outer: {'leave-one-group-out' if sp['outer'] == 'logo' else f'GroupKFold(5) x {REPEATS} repeats'}; "
                     f"inner: tuning of {len(fams)} model families; procedure: {PROC}")
    lim, mu, sd = nn_limit(X)
    fb = sel["table"][FALLBACK[task]]["est"] if PROC == HYB and sp.get("physics_form", True) else None
    if fb is not None:
        val["physics_fallback"] = f"{FALLBACK[task]} (physics form) is used when the inputs are outside the tested domain"
        val["fallback_share_in_cv_pct"] = NEST[name]["fallback_share_pct"]
    common = {"fallback_model": fb, "fallback_label": FALLBACK[task] if fb is not None else None, "features": list(X.columns), "model": final, "model_label": label, "background": X, "task": task,
              "validation": val, "n_rows": int(len(y)), "n_groups": int(len(np.unique(g))), "version": "2.0"}

    if name == "bass2_flame_spread":
        d = sp["df"]; q = float(np.quantile(np.abs(y - proc[0]), 0.9))
        b = common | {"feature_fn": "bass2", "target_label": "flame spread rate over a PMMA rod (opposed flow)", "unit": "mm/s", "target_transform": "none",
                      "band": ("additive", q), "groups": {"oxygen": ["o2_pct"], "opposed airflow": ["opposed_flow_cm_s", "log_flow"], "rod size": ["inv_diameter_per_cm"]},
                      "domain": {"ranges": ranges(d, ["o2_pct", "opposed_flow_cm_s"]), "categories": {"diameter_cm": sorted(d.diameter_cm.unique().tolist())},
                                 "per_category_ranges": per_cat(d, "diameter_cm", ["o2_pct", "opposed_flow_cm_s"]),
                                 "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "PMMA rods, opposed flow, microgravity (ISS BASS-II), ~1 atm",
                      "source": "Link et al. 2018, Sci Rep 8:120, doi:10.1038/s41598-017-18398-4 (Table S1); NASA PSI-25"}
        b["validation"]["q90_abs_error"] = r4(q)
        oof = d[["record_id", "test_id", "o2_pct", "opposed_flow_cm_s", "diameter_cm", "pmma_color", "flame_spread_mm_s"]]
    elif name == "flex_extinction":
        u = sp["df"]; br = float(y.mean()); thr = val["threshold"]
        b = common | {"feature_fn": "flex2", "classes": ["burns to completion", "flame extinguishes before fuel is used up"],
                      "target_label": "P(flame extinguishes before droplet burns out)",
                      "prob_note": f"{int(round(br*100))}% of the {len(u)} ISS tests ended in extinction (base rate); 'burns to completion' is flagged when P < {thr:.2f}",
                      "threshold": thr, "base_rate": br, "groups": flex_groups,
                      "domain": {"ranges": ranges(u, ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]), "categories": {"fuel": ["Methanol", "Heptane"]},
                                 "per_category_ranges": per_cat(u, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "isolated methanol or n-heptane droplets, quiescent microgravity (ISS CIR/MDCA), O2/N2 with CO2 or He diluent", "source": SRC_FLEX}
        oof = u[["record_id", "flex_id", "fuel", "pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm", "test_end"]]
    elif name == "flex_burning_rate":
        k = sp["df"]; q = float(np.quantile(np.abs(y - proc[0]), 0.9))
        b = common | {"feature_fn": "flex2", "target_label": "droplet burning-rate constant K (d^2 shrinks at K mm^2/s)", "unit": "mm^2/s", "target_transform": "none",
                      "band": ("additive", q), "groups": flex_groups,
                      "domain": {"ranges": ranges(k, ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]), "categories": {"fuel": ["Methanol", "Heptane"]},
                                 "per_category_ranges": per_cat(k, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "isolated methanol or n-heptane droplets, quiescent microgravity (ISS FLEX)", "source": SRC_FLEX}
        b["validation"]["q90_abs_error"] = r4(q)
        oof = k[["record_id", "fuel", "o2_pct", "pressure_kpa", "d0_mm", "burning_rate_K_mm2_s"]]
    elif name == "spice_smoke_point":
        s = sp["df"]; q = float(np.quantile(np.maximum(proc[0] / y, y / proc[0]), 0.9))
        b = common | {"feature_fn": "spice2", "target_label": "smoke-point flame length (shorter = sootier, more smoke)", "unit": "mm", "target_transform": "log",
                      "band": ("multiplicative", q),
                      "groups": {"burner diameter": ["log_burner_d"], "coflow air velocity": ["log_coflow"], "fuel": [c for c in X.columns if c.startswith("fuel_")]},
                      "domain": {"ranges": ranges(s, ["burner_diameter_mm", "coflow_air_velocity_cm_s"]), "categories": {"fuel": sorted(s.fuel.unique().tolist())},
                                 "per_category_ranges": per_cat(s, "fuel", ["burner_diameter_mm", "coflow_air_velocity_cm_s"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "laminar gas-jet diffusion flames in coflowing air, microgravity (ISS SPICE), 1 atm",
                      "source": "NASA PSI-107 SPICE, SmokePointReview-0g-3.xlsx (CC0-1.0), DOI 10.60555/9kbh-e962"}
        b["validation"]["q90_ratio"] = r4(q)
        oof = s[["record_id", "fuel", "burner_diameter_mm", "coflow_air_velocity_cm_s", "smoke_point_length_mm"]]
    else:
        m0, raw = sp["df"], sp["raw"]; q = float(np.quantile(np.maximum(proc[0] / y, y / proc[0]), 0.9))
        b = common | {"feature_fn": "same2", "target_label": "smoke particle count-mean diameter (what an optical smoke detector must see)", "unit": "um",
                      "target_transform": "log", "band": ("multiplicative", q),
                      "groups": {"sample temperature": ["sample_temperature_c"], "air velocity": ["air_velocity_cm_s", "no_flow"], "aging time": ["log_aging_s"],
                                 "campaign/instruments": ["same_r_campaign"], "material": [c for c in X.columns if c.startswith("mat_")]},
                      "domain": {"ranges": ranges(raw, ["sample_temperature_c", "air_velocity_cm_s", "aging_time_s"]),
                                 "categories": {"material": sorted(raw.material.unique().tolist()), "campaign": ["SAME", "SAME-R"]},
                                 "per_category_ranges": per_cat(raw, "material", ["sample_temperature_c"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "smoke from overheated (non-flaming) spacecraft materials, microgravity (ISS SAME/SAME-R)",
                      "source": "NASA PSI-101/102 SAME & SAME-R results workbook (CC0-1.0)"}
        b["validation"]["q90_ratio"] = r4(q)
        oof = m0[["record_id", "material", "sample_temperature_c", "inlet_air_velocity_cm_s", "net_aging_time_s", "count_mean_diameter_um"]]

    joblib.dump(b, f"{name}.joblib"); os.makedirs("v2_archive", exist_ok=True); joblib.dump(b, f"v2_archive/{name}.joblib")
    table.to_csv(f"{name}_v2_nested_cv.csv", index=False); inner.to_csv(f"{name}_v2_final_selection.csv", index=False)
    oof.assign(pred_nested=np.round(proc[0], 5), pred_v1_same_splits=np.round(NEST[name]["v1_pred"][0], 5)).to_csv(f"{name}_v2_oof.csv", index=False)
    summary[name] = {"chosen": label, "hyperparameters": params, "validation": b["validation"], "rows": b["n_rows"], "groups": b["n_groups"]}
    v1row = table[table.model == "[v1] model, same outer splits"].iloc[0]
    extra = {"log_loss": None, "balanced_accuracy": None} if task == "classification" else {}
    for metric, rep in (sp["v1_reported"] | extra).items():
        higher = metric in ("R2", "ROC_AUC", "balanced_accuracy")
        comparison.append({"model": name, "metric": metric, "v1_reported_in_v1": rep, "v1_on_same_outer_splits": r4(v1row[metric]),
                           "v2_nested": r4(row[metric]), "v2_better": bool(row[metric] > v1row[metric]) if higher else bool(row[metric] < v1row[metric])})

summary["_selection"] = {"procedure": PROC, "procedure_ranks": R.round(3).to_dict(),
                         "note": "every score above is from nested grouped CV: the rows scored were never used to tune or choose the model"}
json.dump(summary, open("model_summary.json", "w"), indent=2, default=str)
cmp = pd.DataFrame(comparison); cmp.to_csv("v1_vs_v2.csv", index=False)
print("\nV1 vs V2\n", cmp.to_string(index=False))
