"""
AgniShikha / Ignis mu  -  Model 1: BASS-II microgravity flame-spread regressor
Data Science Lead: Prachya Biswas

Input : BASS-II_flame_spread_microgravity_v1.0.csv  (52 rows, 19 ISS tests, PMMA rods, opposed flow)
Output: bass2_flame_spread_model.joblib, cv_results.csv, oof_predictions.csv, figures, model_summary.xlsx

Validation: Leave-One-Test-Out (19 folds). All rows from one ISS test are held out together,
so the score shows how well the model predicts a test it has never seen.
Run: python train_bass2_flame_spread.py
"""
import json, itertools, warnings
import numpy as np, pandas as pd, joblib
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
warnings.filterwarnings("ignore")

DATA = "BASS-II_flame_spread_microgravity_v1.0.csv"
TARGET = "flame_spread_mm_s"
INPUTS = ["o2_pct", "opposed_flow_cm_s", "diameter_cm"]          # what the UI / API sends
SOURCE = "Link et al. 2018, Sci Rep 8:120, doi:10.1038/s41598-017-18398-4 (Table S1); NASA PSI-25"

def make_features(df):
    """Raw inputs -> model features. 1/d because thin-rod spread scales roughly with 1/diameter."""
    return pd.DataFrame({"o2_pct": df["o2_pct"].astype(float),
                         "opposed_flow_cm_s": df["opposed_flow_cm_s"].astype(float),
                         "inv_diameter_per_cm": 1.0 / df["diameter_cm"].astype(float)})

def linear_features(df):
    X = make_features(df); X["flow_sq"] = X["opposed_flow_cm_s"] ** 2; return X

d = pd.read_csv(DATA)
y = d[TARGET].values
groups = d["test_id"].values
X = make_features(d)
logo = LeaveOneGroupOut()

# ---------------- 1. Compare models with grouped CV ----------------
candidates = {
    "Mean baseline (predicts average)": (X, DummyRegressor()),
    "Linear + flow^2 (transparent reference)": (linear_features(d), LinearRegression()),
    "Extra Trees (final)": (X, ExtraTreesRegressor(n_estimators=300, min_samples_leaf=3, random_state=42)),
}
rows, oof = [], {}
for name, (Xc, model) in candidates.items():
    p = cross_val_predict(model, Xc, y, groups=groups, cv=logo)
    oof[name] = p
    rows.append({"model": name, "MAE_mm_s": mean_absolute_error(y, p),
                 "RMSE_mm_s": mean_squared_error(y, p) ** 0.5, "R2": r2_score(y, p),
                 "MAE_pct_of_mean": 100 * mean_absolute_error(y, p) / y.mean()})
cv = pd.DataFrame(rows)
cv.to_csv("cv_results.csv", index=False)
print(cv.round(4).to_string(index=False))

final_name = "Extra Trees (final)"
p_final = oof[final_name]
resid = y - p_final
q90 = float(np.quantile(np.abs(resid), 0.90))      # out-of-fold 90% error band (approximate interval)

# ---------------- 2. Fit final model on all 52 rows ----------------
final = ExtraTreesRegressor(n_estimators=300, min_samples_leaf=3, random_state=42).fit(X, y)
lin = LinearRegression().fit(linear_features(d), y)

# ---------------- 3. Domain of validity ----------------
mu, sd = X.mean(), X.std(ddof=0)
Z = ((X - mu) / sd).values
nn = []
for i in range(len(Z)):
    dist = np.sqrt(((Z - Z[i]) ** 2).sum(1)); dist[i] = np.inf; nn.append(dist.min())
domain = {
    "o2_pct": [float(d.o2_pct.min()), float(d.o2_pct.max())],
    "opposed_flow_cm_s": [float(d.opposed_flow_cm_s.min()), float(d.opposed_flow_cm_s.max())],
    "diameter_cm": sorted(d.diameter_cm.unique().tolist()),
    "nn_distance_limit": float(np.max(nn)),
    "z_mean": mu.to_dict(), "z_std": sd.to_dict(),
    "valid_for": "PMMA rods, opposed flow, microgravity (ISS BASS-II), ~1 atm",
}

# ---------------- 4. Exact Shapley contributions (3 features -> 8 coalitions) ----------------
background = X.copy()
def shapley(model, x_row):
    feats = list(X.columns); n = len(feats); phi = np.zeros(n)
    def v(S):
        B = background.copy()
        for j in S: B[feats[j]] = x_row[feats[j]]
        return model.predict(B).mean()
    from math import factorial
    for i in range(n):
        others = [j for j in range(n) if j != i]
        for k in range(len(others) + 1):
            for S in itertools.combinations(others, k):
                w = factorial(len(S)) * factorial(n - len(S) - 1) / factorial(n)
                phi[i] += w * (v(S + (i,)) - v(S))
    return dict(zip(feats, phi)), v(())

base_value = float(final.predict(background).mean())
shap_rows = []
for i in range(len(X)):
    phi, _ = shapley(final, X.iloc[i]); shap_rows.append(phi)
shap_df = pd.DataFrame(shap_rows)
global_imp = shap_df.abs().mean().sort_values(ascending=False)
print("\nGlobal importance (mean |Shapley|, mm/s):\n", global_imp.round(5))

# ---------------- 5. Save model bundle ----------------
bundle = {"model": final, "linear_reference": lin, "features": list(X.columns), "inputs": INPUTS,
          "target": TARGET, "unit": "mm/s", "q90_abs_error": q90, "domain": domain,
          "base_value": base_value, "background": background, "source": SOURCE,
          "cv": cv.to_dict("records"), "n_rows": int(len(d)), "n_tests": int(d.test_id.nunique()),
          "version": "1.0"}
joblib.dump(bundle, "bass2_flame_spread_model.joblib")

# ---------------- 6. OOF table ----------------
out = d[["record_id", "test_id", "o2_pct", "opposed_flow_cm_s", "diameter_cm", "pmma_color", TARGET]].copy()
out["pred_extra_trees_oof"] = p_final.round(5)
out["pred_linear_oof"] = oof["Linear + flow^2 (transparent reference)"].round(5)
out["abs_error_extra_trees"] = np.abs(resid).round(5)
for c in shap_df.columns: out[f"shap_{c}"] = shap_df[c].round(5)
out.to_csv("oof_predictions.csv", index=False)

# ---------------- 7. Figures ----------------
fig, ax = plt.subplots(figsize=(5.2, 5))
lim = [0, max(y.max(), p_final.max()) * 1.1]
ax.plot(lim, lim, "--", color="grey", lw=1)
ax.fill_between(lim, [l - q90 for l in lim], [l + q90 for l in lim], color="tab:orange", alpha=.12, label="±90% error band")
for col, mk in [("black", "o"), ("clear", "s")]:
    m = d.pmma_color == col
    ax.scatter(y[m], p_final[m], marker=mk, s=36, edgecolor="k", lw=.4,
               color="tab:orange" if col == "black" else "white", label=f"{col} PMMA")
ax.set(xlim=lim, ylim=lim, xlabel="Measured flame spread (mm/s)", ylabel="Predicted, test held out (mm/s)",
       title=f"Extra Trees, leave-one-test-out\nMAE {cv.MAE_mm_s[2]:.4f} mm/s · R² {cv.R2[2]:.2f}")
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig("fig_pred_vs_actual.png", dpi=160); plt.close()

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
flows = np.linspace(domain["opposed_flow_cm_s"][0], domain["opposed_flow_cm_s"][1], 60)
o2s = np.linspace(domain["o2_pct"][0], domain["o2_pct"][1], 60)
for dia, c in zip([0.64, 0.95, 1.27], ["tab:red", "tab:orange", "tab:blue"]):
    G = pd.DataFrame({"o2_pct": 20.9, "opposed_flow_cm_s": flows, "diameter_cm": dia})
    axes[0].plot(flows, final.predict(make_features(G)), color=c, label=f"d = {dia} cm")
    G = pd.DataFrame({"o2_pct": o2s, "opposed_flow_cm_s": 3.0, "diameter_cm": dia})
    axes[1].plot(o2s, final.predict(make_features(G)), color=c, label=f"d = {dia} cm")
for dia, c in zip([0.64, 0.95, 1.27], ["tab:red", "tab:orange", "tab:blue"]):
    m = d.diameter_cm == dia
    axes[0].scatter(d.opposed_flow_cm_s[m], y[m], color=c, s=14, alpha=.6)
    axes[1].scatter(d.o2_pct[m], y[m], color=c, s=14, alpha=.6)
axes[0].set(xlabel="Opposed flow (cm/s)", ylabel="Flame spread (mm/s)", title="Effect of airflow (O₂ = 20.9%)")
axes[1].set(xlabel="O₂ (%)", ylabel="Flame spread (mm/s)", title="Effect of oxygen (flow = 3 cm/s)")
for a in axes: a.legend(fontsize=8); a.grid(alpha=.25)
fig.tight_layout(); fig.savefig("fig_effects.png", dpi=160); plt.close()

fig, ax = plt.subplots(figsize=(5.5, 2.8))
labels = {"o2_pct": "O₂ (%)", "opposed_flow_cm_s": "Opposed flow (cm/s)", "inv_diameter_per_cm": "Rod size (1/diameter)"}
gi = global_imp[::-1]
ax.barh([labels[k] for k in gi.index], gi.values, color="tab:purple")
ax.set(xlabel="Mean |Shapley value| (mm/s)", title="What drives the prediction (exact Shapley)")
fig.tight_layout(); fig.savefig("fig_importance.png", dpi=160); plt.close()

# ---------------- 8. Excel summary ----------------
with pd.ExcelWriter("bass2_flame_spread_model_summary.xlsx") as xw:
    cv.round(5).to_excel(xw, sheet_name="cv_results", index=False)
    out.to_excel(xw, sheet_name="oof_predictions", index=False)
    global_imp.rename("mean_abs_shapley_mm_s").round(5).to_frame().to_excel(xw, sheet_name="importance")
    pd.DataFrame([{"input": k, "min_or_values": str(v)} for k, v in domain.items() if k in INPUTS]).to_excel(xw, sheet_name="domain", index=False)
json.dump({k: v for k, v in domain.items()}, open("domain.json", "w"), indent=2)
print(f"\nq90 abs error = {q90:.4f} mm/s; base value = {base_value:.4f}; NN limit = {domain['nn_distance_limit']:.2f}")
