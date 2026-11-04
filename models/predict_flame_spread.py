"""
AgniShikha / Ignis mu  -  predict BASS-II microgravity flame spread (PMMA rod, opposed flow)

Use from Python (e.g. FastAPI /predict):
    from predict_flame_spread import predict
    predict(o2_pct=19.5, opposed_flow_cm_s=3.0, diameter_cm=0.95)

Use from terminal:
    python predict_flame_spread.py 19.5 3.0 0.95
"""
import sys, itertools
from math import factorial
import os
import numpy as np, pandas as pd, joblib

_B = joblib.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bass2_flame_spread_model.joblib"))

def _features(o2, flow, dia):
    return pd.DataFrame({"o2_pct": [float(o2)], "opposed_flow_cm_s": [float(flow)],
                         "inv_diameter_per_cm": [1.0 / float(dia)]})

def _domain_check(o2, flow, dia, X):
    dom, reasons = _B["domain"], []
    lo, hi = dom["o2_pct"];            (o2 < lo or o2 > hi) and reasons.append(f"O2 {o2}% outside tested {lo}-{hi}%")
    lo, hi = dom["opposed_flow_cm_s"]; (flow < lo or flow > hi) and reasons.append(f"flow {flow} cm/s outside tested {lo}-{hi} cm/s")
    if not any(abs(dia - v) < 1e-6 for v in dom["diameter_cm"]):
        reasons.append(f"diameter {dia} cm not tested (tested: {dom['diameter_cm']})")
    mu, sd = pd.Series(dom["z_mean"]), pd.Series(dom["z_std"])
    Z = ((_B["background"] - mu) / sd).values
    z = ((X.iloc[0] - mu) / sd).values
    nn = float(np.sqrt(((Z - z) ** 2).sum(1)).min())
    if nn > dom["nn_distance_limit"]:
        reasons.append("combination of inputs is far from every tested ISS run")
    return len(reasons) == 0, reasons

def _shapley(x_row):
    model, bg, feats = _B["model"], _B["background"], _B["features"]; n = len(feats); phi = np.zeros(n)
    def v(S):
        Bk = bg.copy()
        for j in S: Bk[feats[j]] = x_row[feats[j]]
        return model.predict(Bk).mean()
    for i in range(n):
        others = [j for j in range(n) if j != i]
        for k in range(n):
            for S in itertools.combinations(others, k):
                w = factorial(len(S)) * factorial(n - len(S) - 1) / factorial(n)
                phi[i] += w * (v(S + (i,)) - v(S))
    return {f: round(float(p), 5) for f, p in zip(feats, phi)}

def predict(o2_pct, opposed_flow_cm_s, diameter_cm, explain=True):
    X = _features(o2_pct, opposed_flow_cm_s, diameter_cm)
    y = float(_B["model"].predict(X)[0]); q = _B["q90_abs_error"]
    in_domain, reasons = _domain_check(o2_pct, opposed_flow_cm_s, diameter_cm, X)
    out = {
        "flame_spread_mm_s": round(y, 4),
        "interval_90_mm_s": [round(max(0.0, y - q), 4), round(y + q, 4)],
        "in_domain": in_domain,
        "confidence": "Moderate" if in_domain else "Limited (extrapolation)",
        "warnings": reasons,
        "value_type": "ML-predicted",
        "model": f"Extra Trees v{_B['version']} trained on {_B['n_rows']} runs / {_B['n_tests']} ISS tests",
        "valid_for": _B["domain"]["valid_for"],
        "source": _B["source"],
    }
    if explain:
        out["base_value_mm_s"] = round(_B["base_value"], 4)
        out["contributions_mm_s"] = _shapley(X.iloc[0])   # base + sum(contributions) = prediction
    return out

if __name__ == "__main__":
    import json
    a = [float(v) for v in sys.argv[1:4]] if len(sys.argv) >= 4 else [19.5, 3.0, 0.95]
    print(json.dumps(predict(*a), indent=2))
