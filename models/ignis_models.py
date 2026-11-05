"""
Ignis mu / AgniShikha - shared model utilities + one prediction entry point for the backend.

    from ignis_models import predict
    predict("flex_extinction", fuel="Methanol", pressure_kpa=101.3, o2_pct=18, co2_pct=0, he_pct=0, d0_mm=3.0)
    predict("bass2_flame_spread", o2_pct=18.2, opposed_flow_cm_s=1.67, diameter_cm=0.64)

v2: every bundle is built by train_v2.py (nested grouped model selection, see MODEL_SELECTION_v2.md).

Every answer carries: prediction, uncertainty band, in_domain + warnings, exact Shapley contributions,
value_type = "ML-predicted", the NASA source and the model's validation scores.
"""
import itertools, os
from math import factorial
import numpy as np, pandas as pd, joblib

HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE = {}

# ---------- feature definitions: ONE place, used by training and by prediction ----------
SPICE_FUELS = ["Ethylene", "Propane", "Propylene", "Propylene/N2 50%", "Propylene/N2 75%"]
SAME_MATERIALS = ["Kapton", "Lampwick (cotton)", "Pyrell", "Silicone", "Teflon"]

def flex_features(df):
    return pd.DataFrame({
        "is_heptane": (df["fuel"].str.lower() == "heptane").astype(float),
        "pressure_kpa": df["pressure_kpa"].astype(float),
        "o2_pct": df["o2_pct"].astype(float),
        "co2_pct": df["co2_pct"].astype(float),
        "he_pct": df["he_pct"].astype(float),
        "d0_mm": df["d0_mm"].astype(float)})

def spice_features(df):
    X = pd.DataFrame({"log_burner_d": np.log(df["burner_diameter_mm"].astype(float)),
                      "log_coflow": np.log(df["coflow_air_velocity_cm_s"].astype(float))})
    for f in SPICE_FUELS[1:]:
        X[f"fuel_{f}"] = (df["fuel"] == f).astype(float)
    return X

def same_features(df):
    X = pd.DataFrame({"sample_temperature_c": df["sample_temperature_c"].astype(float),
                      "air_velocity_cm_s": df["air_velocity_cm_s"].astype(float),
                      "log_aging_s": np.log1p(df["aging_time_s"].astype(float)),
                      "same_r_campaign": (df["campaign"] == "SAME-R").astype(float)})
    for m in SAME_MATERIALS[1:]:
        X[f"mat_{m}"] = (df["material"] == m).astype(float)
    return X


# ---- v2 feature sets (same raw inputs as v1, plus physics-informed terms) ----
def flex2_features(df):
    p, o2 = df["pressure_kpa"].astype(float), df["o2_pct"].astype(float)
    return pd.DataFrame({
        "is_heptane": (df["fuel"].str.lower() == "heptane").astype(float),
        "log_pressure": np.log(p),
        "o2_pct": o2,
        "o2_partial_kpa": o2 / 100 * p,                       # oxygen actually available to the flame
        "co2_pct": df["co2_pct"].astype(float),
        "he_pct": df["he_pct"].astype(float),
        "d0_mm": df["d0_mm"].astype(float)})

def same2_features(df):
    X = same_features(df)
    X.insert(2, "no_flow", (df["air_velocity_cm_s"].astype(float) == 0).astype(float))
    return X

def bass2_features(df):
    flow = df["opposed_flow_cm_s"].astype(float)
    return pd.DataFrame({"o2_pct": df["o2_pct"].astype(float),
                         "opposed_flow_cm_s": flow,
                         "log_flow": np.log(flow),
                         "inv_diameter_per_cm": 1.0 / df["diameter_cm"].astype(float)})   # thin-rod spread ~ 1/d

FEATURE_FNS = {"flex": flex_features, "spice": spice_features, "same": same_features,
               "flex2": flex2_features, "spice2": spice_features, "same2": same2_features, "bass2": bass2_features}

def inverse(kind, y):
    return np.exp(y) if kind == "log" else np.asarray(y, dtype=float)

def band(spec, y):
    kind, q = spec
    return (max(0.0, y - q), y + q) if kind == "additive" else (y / q, y * q)

def load(name):
    import sys
    if HERE not in sys.path:
        sys.path.insert(0, HERE)        # bundles reference ml_selection / sklearn objects
    if name not in _CACHE:
        _CACHE[name] = joblib.load(os.path.join(HERE, f"{name}.joblib"))
    return _CACHE[name]

# ---------- exact interventional Shapley over feature GROUPS (one-hot columns count as one group) ----------
def shapley(f, x_row, background, groups):
    names = list(groups); n = len(names); phi = dict.fromkeys(names, 0.0); memo = {}
    def v(S):
        key = frozenset(S)
        if key not in memo:
            B = background.copy()
            for g in S:
                for col in groups[g]:
                    B[col] = x_row[col]
            memo[key] = float(np.mean(f(B)))
        return memo[key]
    for i, g in enumerate(names):
        others = [h for h in names if h != g]
        for k in range(n):
            for S in itertools.combinations(others, k):
                w = factorial(len(S)) * factorial(n - len(S) - 1) / factorial(n)
                phi[g] += w * (v(S + (g,)) - v(S))
    return {g: round(p, 5) for g, p in phi.items()}, round(v(()), 5)

# ---------- domain check: per-feature ranges (optionally per category) + nearest-neighbour distance ----------
def domain_check(bundle, raw, X):
    d, reasons = bundle["domain"], []
    for col, (lo, hi) in d["ranges"].items():
        val = raw.get(col)
        if val is not None and not (lo - 1e-9 <= float(val) <= hi + 1e-9):
            reasons.append(f"{col}={val} outside tested range {lo}-{hi}")
    for col, allowed in d.get("categories", {}).items():
        if raw.get(col) not in allowed:
            reasons.append(f"{col}='{raw.get(col)}' was never tested (tested: {allowed})")
    if "per_category_ranges" in d:
        cat = d["per_category_ranges"]["by"]; table = d["per_category_ranges"]["ranges"].get(raw.get(cat), {})
        for col, (lo, hi) in table.items():
            val = raw.get(col)
            if val is not None and not (lo - 1e-9 <= float(val) <= hi + 1e-9):
                reasons.append(f"for {raw.get(cat)}, {col}={val} outside its tested range {lo}-{hi}")
    mu, sd = pd.Series(d["z_mean"]), pd.Series(d["z_std"]).replace(0, 1)
    Z = ((bundle["background"][mu.index] - mu) / sd).values
    z = ((X.iloc[0][mu.index] - mu) / sd).values
    if float(np.sqrt(((Z - z) ** 2).sum(1)).min()) > d["nn_limit"]:
        reasons.append("this combination of inputs is far from every tested NASA run")
    return len(reasons) == 0, reasons

# ---------- the single entry point ----------
def predict(model_name, explain=True, **raw):
    b = load(model_name)
    raw = {**b.get("defaults", {}), **raw}
    X = FEATURE_FNS[b["feature_fn"]](pd.DataFrame([raw]))
    in_domain, warnings = domain_check(b, raw, X)
    out = {"model": model_name, "task": b["task"], "target": b["target_label"]}
    model = b["model"]
    if not in_domain and b.get("fallback_model") is not None:
        model = b["fallback_model"]                     # physics-form model extrapolates more safely than the ensemble
        warnings = warnings + [f"outside the tested domain: answer comes from the physics-form model ({b['fallback_label']}), not the ensemble"]
    if b["task"] == "classification":
        p = float(model.predict_proba(X[b["features"]])[0, 1])
        out.update(probability=round(p, 3), predicted_class=b["classes"][int(p >= b.get("threshold", 0.5))],
                   base_rate=round(b.get("base_rate", 0.5), 3), note=b["prob_note"])
        f = lambda B: model.predict_proba(B[b["features"]])[:, 1]
    else:
        y = float(inverse(b["target_transform"], model.predict(X[b["features"]]))[0])
        lo, hi = band(b["band"], y)
        out.update(prediction=round(y, 4), unit=b["unit"], interval_90=[round(lo, 4), round(hi, 4)])
        f = lambda B: inverse(b["target_transform"], model.predict(B[b["features"]]))
    out.update(in_domain=in_domain, confidence="Moderate" if in_domain else "Limited (extrapolation)",
               warnings=warnings, value_type="ML-predicted", model_used=(b.get("fallback_label") if model is not b["model"] else b["model_label"]), valid_for=b["valid_for"],
               validation=b["validation"], source=b["source"], version=b["version"])
    if explain:
        contrib, base = shapley(f, X.iloc[0], b["background"], b["groups"])
        out.update(base_value=base, contributions=contrib)
    return out
