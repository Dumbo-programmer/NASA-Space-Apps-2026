import json, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve
S = json.load(open("model_summary.json"))
fig, ax = plt.subplots(2, 2, figsize=(10, 9))
o = pd.read_csv("flex_extinction_oof.csv"); o = o[o.test_end.isin(["Extinction", "Completion"])]
y = (o.test_end == "Extinction").astype(int); fpr, tpr, _ = roc_curve(y, o.p_extinction_oof)
ax[0, 0].plot(fpr, tpr, color="#C2410C", lw=2, label=f"Extra trees, AUC {S['flex_extinction']['validation']['ROC_AUC']:.2f}")
ax[0, 0].plot([0, 1], [0, 1], "--", color="grey", lw=1, label="guessing (AUC 0.50)")
ax[0, 0].set(title="Model 2 - FLEX: will the droplet flame go out?\n(206 ISS tests, whole test series held out)", xlabel="false alarm rate", ylabel="extinctions caught"); ax[0, 0].legend(fontsize=8)
for a, f, col, unit, title, key in [
    (ax[0, 1], "flex_burning_rate_oof.csv", "burning_rate_K_mm2_s", "mm²/s", "Model 3 - FLEX burning-rate constant K", "flex_burning_rate"),
    (ax[1, 0], "spice_smoke_point_oof.csv", "smoke_point_length_mm", "mm", "Model 4 - SPICE smoke point (power law)", "spice_smoke_point"),
    (ax[1, 1], "same_particle_size_oof.csv", "count_mean_diameter_um", "µm", "Model 5 - SAME smoke particle size", "same_particle_size")]:
    d = pd.read_csv(f); lim = [0, max(d[col].max(), d.pred_oof.max()) * 1.08]
    a.scatter(d[col], d.pred_oof, s=18, color="#1F3A5F", alpha=.75, edgecolor="white", lw=.4); a.plot(lim, lim, "--", color="grey", lw=1)
    v = S[key]["validation"]; r2 = v.get("R2")
    a.set(xlim=lim, ylim=lim, xlabel=f"measured ({unit})", ylabel=f"predicted, held out ({unit})", title=f"{title}\nR² {r2:.2f} · {S[key]['rows']} rows")
for a in ax.flat: a.grid(alpha=.25)
fig.suptitle("Ignis μ - models trained on NASA ISS data (grouped cross-validation)", fontweight="bold")
fig.tight_layout(); fig.savefig("fig_models_overview.png", dpi=160)
