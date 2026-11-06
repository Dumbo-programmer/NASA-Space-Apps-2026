"""
Ignis mu / AgniShikha - v3 final: objective-driven model choice per output + side experiments
Data Science Lead: Prachya Biswas

Decision rule (from the objective, decided before looking at which model "wins"):
  map outputs (survive?, spread rate, burning rate) feed the safe-cabin map and the next-experiment pick, so they MUST
  (1) move the right way with oxygen, (2) give uncertainty that grows outside NASA's data, (3) be near-best in accuracy
  -> PI-GP when it meets all three
  smoke outputs (smoke point, particle size) are read inside the tested range -> most accurate model (v2 ensemble)
Also: safe-cabin map + next experiment figure, moving-average experiment, large-data scaling test.
Run: python v3_final.py   (needs compare_v3.py outputs)
"""
import json, time, warnings
import numpy as np, pandas as pd, joblib
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, brier_score_loss
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from ml_selection import group_bootstrap_ci
from pigp import PhysicsGPRegressor, PhysicsGPClassifier
import preprocess_v3 as P
warnings.filterwarnings("ignore")

S = P.all_specs("data"); T = pd.read_csv("v3_comparison.csv"); PC = pd.read_csv("v3_physics_check.csv")
summary = json.load(open("model_summary.json"))
BLUE, ORANGE, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF})


def ranges(df, cols):
    return {c: [round(float(df[c].min()), 4), round(float(df[c].max()), 4)] for c in cols}


def per_cat(df, by, cols):
    return {"by": by, "ranges": {k: ranges(gr, cols) for k, gr in df.groupby(by)}}


def nn_limit(X):
    mu, sd = X.mean(), X.std(ddof=0).replace(0, 1); Z = ((X - mu) / sd).values; best = []
    for i in range(len(Z)):
        dd = np.sqrt(((Z - Z[i]) ** 2).sum(1)); dd[i] = np.inf; best.append(dd.min())
    return float(np.quantile(best, 0.99)), mu.to_dict(), sd.to_dict()


def row(name, model):
    return T[(T.model_task == name) & (T.model == model)].iloc[0]


# ======================= final PI-GP bundles for the three map outputs =======================
FLEX_GROUPS = {"fuel": ["is_heptane"], "pressure": ["log_p"], "oxygen": ["o2_pct", "o2_partial_kpa"], "CO2 diluent": ["co2_pct"],
               "helium diluent": ["he_pct"], "droplet size": ["d0_mm"]}
SRC_FLEX = "NASA PSI-69 FLEX experimental table (CC0-1.0), DOI 10.60555/mbq8-0451"
for name in ["bass2_flame_spread", "flex_burning_rate", "flex_extinction"]:
    sp = S[name]; X, y, g = sp["X"], sp["y"], sp["g"]; cls = sp["task"] == "classification"
    oof = pd.read_csv(f"{name}_v3_oof.csv"); r = row(name, "PI-GP (proposed)")
    if cls:
        m = PhysicsGPClassifier(gp_cols=sp["gp_cols"]).fit(X, y)
        br = float(y.mean()); thr = float(np.quantile(oof.pigp_pred, 1 - br))
        val = {"ROC_AUC": round(r.ROC_AUC, 4), "Brier": round(r.Brier, 4), "log_loss": round(r.log_loss, 4),
               "ROC_AUC_95CI": [round(v, 4) for v in group_bootstrap_ci(y, oof.pigp_pred.values, g, roc_auc_score)],
               "Brier_95CI": [round(v, 4) for v in group_bootstrap_ci(y, oof.pigp_pred.values, g, brier_score_loss)],
               "baseline_Brier": round(float(brier_score_loss(y, np.full(len(y), br))), 4), "threshold": round(thr, 4)}
    else:
        m = PhysicsGPRegressor(mean_cols=sp["mean_cols"], gp_cols=sp["gp_cols"], log_target=sp["log_target"], noise=sp["noise"]).fit(X, y, groups=g)
        val = {"MAE": round(r.MAE, 4), "R2": round(r.R2, 4), "coverage90_pct": round(r.coverage90_pct, 1),
               "R2_95CI": [round(v, 4) for v in group_bootstrap_ci(y, oof.pigp_pred.values, g, r2_score)],
               "gp_correction_used": bool(m.use_correction_), "interval_scale": round(m.scale_, 3)}
    viol = PC[(PC.model_task == name) & (PC.model == "PI-GP (proposed)")].rows_violating_pct.iloc[0]
    val |= {"physics_violations_pct": float(viol),
            "method": "same outer grouped splits as v2 (leave-one-test-out or GroupKFold(5) x 3); PI-GP fitted on training folds only"}
    lim, mu, sd = nn_limit(X); df = sp["df"]
    common = {"task": sp["task"], "features": list(X.columns), "model": m, "background": X, "validation": val, "version": "3.0",
              "n_rows": int(len(y)), "n_groups": int(len(np.unique(g)))}
    if name == "bass2_flame_spread":
        b = common | {"feature_fn": "v3_bass", "model_label": "Physics-informed Gaussian process (power law + GP correction + test offset)",
                      "target_label": "flame spread rate over a PMMA rod (opposed flow)", "unit": "mm/s", "target_transform": "none", "band": ("model", None),
                      "groups": {"oxygen": ["log_o2", "o2_pct"], "opposed airflow": ["log_flow", "flow"], "rod size": ["log_inv_d", "inv_d"]},
                      "domain": {"ranges": ranges(df, ["o2_pct", "opposed_flow_cm_s"]), "categories": {"diameter_cm": sorted(df.diameter_cm.unique().tolist())},
                                 "per_category_ranges": per_cat(df, "diameter_cm", ["o2_pct", "opposed_flow_cm_s"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "PMMA rods, opposed flow, microgravity (ISS BASS-II), ~1 atm",
                      "source": "Link et al. 2018, Sci Rep 8:120, doi:10.1038/s41598-017-18398-4 (Table S1); NASA PSI-25"}
    elif name == "flex_burning_rate":
        b = common | {"feature_fn": "v3_flex", "model_label": "Physics-informed Gaussian process (d2-law terms + GP correction + series offset)",
                      "target_label": "droplet burning-rate constant K (d^2 shrinks at K mm^2/s)", "unit": "mm^2/s", "target_transform": "none", "band": ("model", None),
                      "groups": FLEX_GROUPS,
                      "domain": {"ranges": ranges(df, ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]), "categories": {"fuel": ["Methanol", "Heptane"]},
                                 "per_category_ranges": per_cat(df, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "isolated methanol or n-heptane droplets, quiescent microgravity (ISS FLEX)", "source": SRC_FLEX}
    else:
        b = common | {"feature_fn": "v3_flex", "model_label": "Physics-informed Gaussian process classifier",
                      "classes": ["burns to completion", "flame extinguishes before fuel is used up"],
                      "target_label": "P(flame extinguishes before droplet burns out)",
                      "prob_note": f"{int(round(br*100))}% of the {len(y)} ISS tests ended in extinction (base rate); 'burns to completion' is flagged when P < {thr:.2f}",
                      "threshold": thr, "base_rate": br, "groups": FLEX_GROUPS,
                      "domain": {"ranges": ranges(df, ["pressure_kpa", "o2_pct", "co2_pct", "he_pct", "d0_mm"]), "categories": {"fuel": ["Methanol", "Heptane"]},
                                 "per_category_ranges": per_cat(df, "fuel", ["o2_pct", "pressure_kpa", "d0_mm"]), "nn_limit": lim, "z_mean": mu, "z_std": sd},
                      "valid_for": "isolated methanol or n-heptane droplets, quiescent microgravity (ISS CIR/MDCA), O2/N2 with CO2 or He diluent", "source": SRC_FLEX}
    if not cls and not m.use_correction_:
        b["model_label"] = b["model_label"].replace("GP correction + ", "") + " (inner CV: GP correction not needed)"
    joblib.dump(b, f"{name}.joblib")
    summary[name] = {"chosen": b["model_label"], "validation": val, "rows": b["n_rows"], "groups": b["n_groups"], "version": "3.0"}
    print(name, "->", b["model_label"], val, flush=True)

summary["_selection"] = summary.get("_selection", {}) | {"v3_rule": "map outputs (spread, burning rate, survive?) -> PI-GP (physics-consistent + input-dependent uncertainty + near-best accuracy); smoke outputs (smoke point, particle size) -> v2 ensemble (most accurate inside the tested range)"}
json.dump(summary, open("model_summary.json", "w"), indent=2, default=str)

# ======================= safe-cabin map + next experiment =======================
fx = joblib.load("flex_extinction.joblib")["model"]; fb = joblib.load("bass2_flame_spread.joblib")["model"]
flex = S["flex_extinction"]["df"]; bass = S["bass2_flame_spread"]["df"]
O2 = np.linspace(12, 34, 90); PR = np.linspace(50, 320, 90); OO, PP = np.meshgrid(O2, PR)
G = pd.DataFrame({"fuel": "Methanol", "pressure_kpa": PP.ravel(), "o2_pct": OO.ravel(), "co2_pct": 0.0, "he_pct": 0.0, "d0_mm": 3.0})
p_surv = 1 - fx.predict_proba(P.flex_features(G))[:, 1]
meth = flex[(flex.fuel == "Methanol")]
Zt = np.c_[(meth.o2_pct - 12) / 22, (meth.pressure_kpa - 50) / 270]; Zg = np.c_[(G.o2_pct - 12) / 22, (G.pressure_kpa - 50) / 270]
dist = np.sqrt(((Zg[:, None, :] - Zt[None, :, :]) ** 2).sum(2)).min(1)
score = p_surv * (1 - p_surv) * np.minimum(dist / 0.15, 1.0)          # most uncertain outcome x far from any tested run
k = int(np.argmax(score)); nxt1 = (float(G.o2_pct[k]), float(G.pressure_kpa[k]), float(p_surv[k]))

F2 = np.linspace(0.4, 7.5, 90); O22 = np.linspace(16.8, 21.0, 90); FF, OB = np.meshgrid(F2, O22)
H = pd.DataFrame({"o2_pct": OB.ravel(), "opposed_flow_cm_s": FF.ravel(), "diameter_cm": 0.64})
mu, sdv = fb.predict_t(P.bass2_X(H)); spread = np.exp(mu); rel = sdv                      # sd in log space = relative uncertainty
k2 = int(np.argmax(rel)); nxt2 = (float(H.o2_pct[k2]), float(H.opposed_flow_cm_s[k2]), float(spread[k2]), float(rel[k2]))

fig, (a, b2) = plt.subplots(1, 2, figsize=(11.5, 4.9))
cs = a.contourf(OO, PP, p_surv.reshape(OO.shape), levels=np.linspace(0, 1, 11), cmap="Blues")
a.contour(OO, PP, p_surv.reshape(OO.shape), levels=[0.5], colors=INK, linewidths=1.4, linestyles="--")
a.scatter(meth.o2_pct, meth.pressure_kpa, s=14, c=np.where(meth.extinguished == 1, SURF, INK), edgecolor=INK, linewidth=0.6, label="NASA FLEX test (white = extinguished)")
a.axhspan(50, 70, color=GRID, alpha=0.6); a.text(13, 58, "below every tested pressure", fontsize=8, color=INK2)
a.plot(nxt1[0], nxt1[1], marker="*", ms=16, color=ORANGE, markeredgecolor=INK, clip_on=False, label=f"next experiment: {nxt1[0]:.0f}% O2, {nxt1[1]:.0f} kPa")
a.set(xlabel="oxygen (%)", ylabel="pressure (kPa)", xlim=(11.5, 34.5), ylim=(45, 325)); a.set_title("Will a 3 mm methanol droplet flame survive?\nshade = P(burns to completion); dashed = 50 % boundary", loc="left", fontsize=10, color=INK)
plt.colorbar(cs, ax=a, fraction=0.046, pad=0.02).set_label("P(flame survives)"); a.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
cs2 = b2.contourf(FF, OB, (100 * (np.exp(rel) - 1)).reshape(FF.shape), levels=10, cmap="Oranges")
cl = b2.contour(FF, OB, spread.reshape(FF.shape), levels=6, colors=INK, linewidths=0.8); b2.clabel(cl, fmt="%.3f", fontsize=7)
t064 = bass[bass.diameter_cm == 0.64]
b2.scatter(bass.opposed_flow_cm_s, bass.o2_pct, s=14, c=np.where(bass.diameter_cm == 0.64, INK, SURF), edgecolor=INK, linewidth=0.6, label="NASA BASS-II test (black = 6.4 mm rod)")
b2.plot(nxt2[1], nxt2[0], marker="*", ms=16, color=BLUE, markeredgecolor=INK, clip_on=False, label=f"next experiment: {nxt2[0]:.1f}% O2, {nxt2[1]:.1f} cm/s")
b2.set(xlabel="opposed airflow (cm/s)", ylabel="oxygen (%)", xlim=(0.2, 7.8), ylim=(16.6, 21.25)); b2.set_title("Flame spread over a 6.4 mm PMMA rod\nlines = spread (mm/s); shade = uncertainty (± %)", loc="left", fontsize=10, color=INK)
plt.colorbar(cs2, ax=b2, fraction=0.046, pad=0.02).set_label("1-sd uncertainty (%)"); b2.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
fig.tight_layout(); fig.savefig("fig_v3_safe_map_next_experiment.png", dpi=170); plt.close()
print("next experiments:", nxt1, nxt2)

# ======================= what if we used a moving average? (BASS-II) =======================
d = bass.copy(); y = d.flame_spread_mm_s.values; g = d.test_id.values
Xb = P.bass2_X(d)[["log_o2", "log_flow", "flow", "log_inv_d"]]
law = TransformedTargetRegressor(make_pipeline(StandardScaler(), Ridge(1e-2)), func=np.log, inverse_func=np.exp)
ma_file = pd.Series(y).rolling(3, center=True, min_periods=1).mean().values                   # across rows in file order (crosses tests)
ma_test = d.assign(y=y).groupby("test_id").y.transform(lambda s: s.rolling(3, center=True, min_periods=1).mean()).values
res_ma = []
for label, ytrain, yscore in [("no smoothing (honest baseline)", y, y),
                              ("moving average over file rows, scored on smoothed values", ma_file, ma_file),
                              ("moving average over file rows, scored on real measurements", ma_file, y),
                              ("moving average within each test, scored on real measurements", ma_test, y)]:
    p = cross_val_predict(law, Xb, ytrain, groups=g, cv=LeaveOneGroupOut())
    res_ma.append({"variant": label, "R2": round(r2_score(yscore, p), 3), "MAE_mm_s": round(mean_absolute_error(yscore, p), 4)})
leak = int((pd.Series(g).shift(1) != pd.Series(g)).sum() - 1)
pd.DataFrame(res_ma).to_csv("v3_moving_average_test.csv", index=False); print(pd.DataFrame(res_ma).to_string(index=False), "\nfile-order windows crossing a test boundary:", leak)

# ======================= large data: how does fitting time grow? =======================
rng = np.random.default_rng(0); scal = []
for n in [250, 500, 1000, 2000]:
    o = rng.uniform(16, 21, n); f = rng.uniform(0.4, 7.5, n); dd = rng.choice([0.64, 0.95, 1.27], n)
    Dn = pd.DataFrame({"o2_pct": o, "opposed_flow_cm_s": f, "diameter_cm": dd}); Xn = P.bass2_X(Dn)
    yn = np.exp(-6.5 + 2.2 * np.log(o) + 0.25 * np.log(f) - 0.05 * f + 0.6 * np.log(1 / dd) + rng.normal(0, 0.15, n))
    t0 = time.time(); PhysicsGPRegressor(mean_cols=["log_o2", "log_flow", "flow", "log_inv_d"], gp_cols=["o2_pct", "log_flow", "inv_d"], log_target=True,
                                          correction=True).fit(Xn, yn, groups=np.arange(n) // 4)
    scal.append({"rows": n, "fit_seconds": round(time.time() - t0, 2)}); print(scal[-1], flush=True)
pd.DataFrame(scal).to_csv("v3_scaling_test.csv", index=False)
json.dump({"next_experiment_flex": {"o2_pct": nxt1[0], "pressure_kpa": nxt1[1], "p_survive": nxt1[2]},
           "next_experiment_bass": {"o2_pct": nxt2[0], "flow_cm_s": nxt2[1], "spread_mm_s": nxt2[2], "sd_log": nxt2[3]},
           "moving_average": res_ma, "ma_windows_crossing_tests": leak, "scaling": scal}, open("v3_side_experiments.json", "w"), indent=1)
