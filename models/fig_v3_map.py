"""Safe-cabin map + next-experiment figure (also produced inside v3_final.py)."""
import json, numpy as np, pandas as pd, joblib, warnings
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import preprocess_v3 as P
warnings.filterwarnings("ignore")
S = P.all_specs("data")
BLUE, ORANGE, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF})
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

