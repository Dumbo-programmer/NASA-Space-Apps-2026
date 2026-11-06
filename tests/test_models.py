"""Model layer: leakage guards, artifact integrity, prediction contract, physics behaviour, out-of-domain handling."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "models"))
import config as C                                                     # noqa: E402
from ignis_models import predict, load                                 # noqa: E402
from ml_selection import checked_splits, LeakageError                  # noqa: E402
import preprocess_v3 as P                                              # noqa: E402

EXAMPLES = {
    "bass2_flame_spread": dict(o2_pct=18.2, opposed_flow_cm_s=1.67, diameter_cm=0.64),
    "flex_extinction": dict(fuel="Methanol", pressure_kpa=101.3, o2_pct=21, co2_pct=0, he_pct=0, d0_mm=2.5),
    "flex_burning_rate": dict(fuel="Heptane", pressure_kpa=101.3, o2_pct=21, co2_pct=0, he_pct=0, d0_mm=3.0),
    "spice_smoke_point": dict(fuel="Ethylene", burner_diameter_mm=1.6002, coflow_air_velocity_cm_s=40),
    "same_particle_size": dict(material="Silicone", sample_temperature_c=380, air_velocity_cm_s=8.1, aging_time_s=45, campaign="SAME-R"),
}
CONTRACT_KEYS = {"model", "task", "target", "in_domain", "confidence", "warnings", "value_type", "model_used", "valid_for", "validation", "source", "version"}


# ---------------------------------------------------------------- leakage guards
def test_leakage_guard_rejects_random_split_and_accepts_grouped():
    from sklearn.model_selection import KFold, GroupKFold
    X = pd.DataFrame({"a": np.arange(40.0)}); y = np.arange(40.0); g = np.repeat(np.arange(10), 4)
    try:
        checked_splits(KFold(5, shuffle=True, random_state=0), X, y, g, "test")
        raise AssertionError("random KFold should leak groups")
    except LeakageError:
        pass
    assert len(checked_splits(GroupKFold(5), X, y, g, "test")) == 5


def test_target_leak_guard():
    spec = P.all_specs()["bass2_flame_spread"]
    spec = dict(spec, X=spec["X"].assign(copy_of_target=np.log(spec["y"])))
    try:
        P.check_no_target_leak(spec)
        raise AssertionError("a copy of the target must be refused")
    except AssertionError as e:
        assert "target leakage" in str(e)


def test_training_rows_match_documented_counts():
    S = P.all_specs()
    assert {k: len(v["y"]) for k, v in S.items()} == {"bass2_flame_spread": 52, "flex_extinction": 206, "flex_burning_rate": 256,
                                                       "spice_smoke_point": 55, "same_particle_size": 125}


# ---------------------------------------------------------------- artifacts
def test_every_production_artifact_loads_and_is_versioned():
    for name in C.MODEL_NAMES:
        b = load(name)
        assert b["version"] in ("2.0", "3.0") and "validation" in b and "domain" in b and "source" in b
    assert load("bass2_flame_spread")["version"] == "3.0" and load("spice_smoke_point")["version"] == "2.0"


def test_reported_scores_match_comparison_tables():
    s = json.loads(C.report("model_summary.json").read_text()); t = pd.read_csv(C.report("v3_comparison.csv"))
    pigp = t[t.model == "PI-GP (proposed)"].set_index("model_task")
    assert abs(s["flex_extinction"]["validation"]["ROC_AUC"] - pigp.loc["flex_extinction", "ROC_AUC"]) < 1e-3
    assert abs(s["bass2_flame_spread"]["validation"]["R2"] - pigp.loc["bass2_flame_spread", "R2"]) < 1e-3


# ---------------------------------------------------------------- prediction contract
def test_prediction_contract_and_exact_shapley():
    for name, kw in EXAMPLES.items():
        r = predict(name, **kw)
        assert CONTRACT_KEYS <= set(r), f"{name}: missing {CONTRACT_KEYS - set(r)}"
        assert r["in_domain"] and r["value_type"] == "ML-predicted"
        out = r["probability"] if "probability" in r else r["prediction"]
        assert np.isclose(r["base_value"] + sum(r["contributions"].values()), out, atol=2e-3), f"{name}: Shapley not additive"
        if "probability" in r:
            assert 0 <= r["probability"] <= 1
        else:
            lo, hi = r["interval_90"]
            assert lo <= r["prediction"] <= hi and lo > 0


def test_out_of_domain_is_flagged_and_band_widens():
    inside = predict("bass2_flame_spread", explain=False, o2_pct=17.5, opposed_flow_cm_s=1.67, diameter_cm=0.64)
    outside = predict("bass2_flame_spread", explain=False, o2_pct=24, opposed_flow_cm_s=10, diameter_cm=0.64)
    assert inside["in_domain"] and not outside["in_domain"] and outside["warnings"]
    w = lambda r: np.log(r["interval_90"][1] / r["interval_90"][0])
    assert w(outside) > w(inside)


# ---------------------------------------------------------------- physics behaviour
def _seq(name, key, values, **kw):
    out = []
    for v in values:
        r = predict(name, explain=False, **{**kw, key: v})
        out.append(r["probability"] if "probability" in r else r["prediction"])
    return np.array(out)


def test_physics_directions():
    assert np.all(np.diff(_seq("flex_extinction", "o2_pct", [13, 18, 21, 25], fuel="Methanol", pressure_kpa=101.3, co2_pct=0, he_pct=0, d0_mm=3.0)) <= 1e-9)
    assert np.all(np.diff(_seq("flex_burning_rate", "o2_pct", [13, 18, 21, 25], fuel="Methanol", pressure_kpa=101.3, co2_pct=0, he_pct=0, d0_mm=3.0)) > 0)
    assert np.all(np.diff(_seq("bass2_flame_spread", "o2_pct", [16.8, 17.5, 18.5], opposed_flow_cm_s=2.0, diameter_cm=0.64)) > 0)
    assert np.all(np.diff(_seq("spice_smoke_point", "coflow_air_velocity_cm_s", [10, 30, 50], fuel="Propylene", burner_diameter_mm=1.6002)) > 0)
    fresh, aged = _seq("same_particle_size", "aging_time_s", [35, 560], material="Kapton", sample_temperature_c=420, air_velocity_cm_s=8.1, campaign="SAME-R")
    assert aged > fresh
