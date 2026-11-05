"""Figures for the v2 model-selection report: v1 vs v2 (same outer splits) + noise ceiling, and nested predicted-vs-measured."""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

BLUE, ORANGE, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF})
cmp = pd.read_csv("v1_vs_v2.csv"); ceil = json.load(open("noise_ceiling.json")); summ = json.load(open("model_summary.json"))
NAMES = {"bass2_flame_spread": "1 BASS-II\nflame spread", "flex_burning_rate": "3 FLEX\nburning rate K",
         "spice_smoke_point": "4 SPICE\nsmoke point", "same_particle_size": "5 SAME\nparticle size"}

fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [2.3, 1]})
r2 = cmp[cmp.metric == "R2"].set_index("model").loc[list(NAMES)]
xs = np.arange(len(NAMES)); w = 0.34
a.bar(xs - w / 2 - 0.01, r2.v1_on_same_outer_splits, w, color=ORANGE, label="v1 model (same held-out tests)")
a.bar(xs + w / 2 + 0.01, r2.v2_nested, w, color=BLUE, label="v2 nested selection (honest)")
for i, m in enumerate(NAMES):
    c = ceil[m]["max_R2_possible"]
    a.plot([i - 0.42, i + 0.42], [c, c], color=INK, lw=1.6, ls=(0, (3, 2)))
    a.text(i, c + 0.02, f"noise ceiling ~{c:.2f}", ha="center", va="bottom", fontsize=7.5, color=INK2)
    for dx, v in ((-w / 2, r2.v1_on_same_outer_splits.iloc[i]), (w / 2, r2.v2_nested.iloc[i])):
        a.text(i + dx, v - 0.025, f"{v:.2f}", ha="center", va="top", fontsize=8.5, color="white", fontweight="bold")
a.set_xticks(xs, NAMES.values()); a.set_ylim(0, 1.1); a.set_ylabel("R² on held-out ISS tests")
a.yaxis.grid(True, color=GRID, lw=0.8); a.set_axisbelow(True)
a.legend(frameon=False, loc="upper left", fontsize=8, bbox_to_anchor=(0, 1.0))
a.set_title("Regression models: held-out R² vs. replicate noise ceiling", loc="left", fontsize=10, color=INK)

f = cmp[cmp.model == "flex_extinction"].set_index("metric")
mets = ["Brier", "log_loss"]; xs2 = np.arange(len(mets))
b.bar(xs2 - w / 2 - 0.01, f.loc[mets, "v1_on_same_outer_splits"], w, color=ORANGE)
b.bar(xs2 + w / 2 + 0.01, f.loc[mets, "v2_nested"], w, color=BLUE)
for i, m in enumerate(mets):
    for dx, v in ((-w / 2, f.loc[m, "v1_on_same_outer_splits"]), (w / 2, f.loc[m, "v2_nested"])):
        b.text(i + dx, v + 0.006, f"{v:.3f}", ha="center", fontsize=8, color=INK)
b.set_xticks(xs2, ["Brier score", "Log-loss"]); b.set_ylabel("lower is better")
b.yaxis.grid(True, color=GRID, lw=0.8); b.set_axisbelow(True)
auc1, auc2 = f.loc["ROC_AUC", "v1_on_same_outer_splits"], f.loc["ROC_AUC", "v2_nested"]
b.set_title(f"2 FLEX extinction (classifier)\nAUC v1 {auc1:.2f} -> v2 {auc2:.2f}", loc="left", fontsize=10, color=INK)
fig.tight_layout(); fig.savefig("fig_v1_vs_v2.png", dpi=170); plt.close()

# nested predicted vs measured, all four regressions
fig, axs = plt.subplots(1, 4, figsize=(13, 3.4))
cols = {"bass2_flame_spread": "flame_spread_mm_s", "flex_burning_rate": "burning_rate_K_mm2_s",
        "spice_smoke_point": "smoke_point_length_mm", "same_particle_size": "count_mean_diameter_um"}
units = {"bass2_flame_spread": "mm/s", "flex_burning_rate": "mm²/s", "spice_smoke_point": "mm", "same_particle_size": "µm"}
for ax, (m, c) in zip(axs, cols.items()):
    o = pd.read_csv(f"{m}_v2_oof.csv"); y, p = o[c], o.pred_nested
    lim = [0, max(y.max(), p.max()) * 1.08]
    ax.plot(lim, lim, color=INK2, lw=1, ls=(0, (3, 2)))
    ax.scatter(y, p, s=22, color=BLUE, edgecolor=SURF, linewidth=1)
    v = summ[m]["validation"]
    ax.set(xlim=lim, ylim=lim, xlabel=f"measured ({units[m]})", ylabel="predicted, test held out" if ax is axs[0] else "")
    ax.set_title(f"{NAMES[m].replace(chr(10), ' ')}\nR² {v['R2']:.2f} · MAE {v['MAE']:.3g}", loc="left", fontsize=9, color=INK)
fig.tight_layout(); fig.savefig("fig_v2_pred_vs_measured.png", dpi=170); plt.close()
print("figures written")
