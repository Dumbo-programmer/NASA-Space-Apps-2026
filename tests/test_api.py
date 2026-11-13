"""API layer: input validation, parity with the models, HTTP contract, and the static export the dashboard falls back to."""
import json, math, sys, threading, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "models"))
import ignis_api as A                                                  # noqa: E402
import ignis_models as M                                               # noqa: E402


def _raises(fn, *args):
    try:
        fn(*args)
    except A.InputError as e:
        return str(e)
    raise AssertionError(f"expected InputError for {args}")


def test_catalog_defaults_are_inside_nasa_tested_conditions():
    cat = A.catalog()
    assert [m["name"] for m in cat["models"]] == A.MODEL_NAMES
    for card in cat["models"]:
        defaults = {i["name"]: i["default"] for i in card["inputs"]}
        r = A.predict(card["name"], defaults, explain=False)
        assert r["in_domain"], (card["name"], r["warnings"])
        assert card["training_rows"] > 0 and card["validation"]
        json.dumps(card, allow_nan=False)


def test_api_answers_equal_direct_model_answers():
    raw = dict(fuel="Heptane", pressure_kpa=101.3, o2_pct=21.0, co2_pct=20.0, he_pct=0.0, d0_mm=3.0)
    via_api = A.predict("flex_extinction", raw)
    direct = M.predict("flex_extinction", **raw)
    assert via_api["probability"] == direct["probability"]
    assert via_api["contributions"] == direct["contributions"]


def test_invalid_inputs_are_refused_with_a_clear_message():
    assert "never tested" in _raises(A.predict, "flex_extinction", {"fuel": "Diesel"})
    assert "unknown input" in _raises(A.predict, "flex_extinction", {"temperature": 3})
    assert "number" in _raises(A.predict, "flex_extinction", {"o2_pct": "abc"})
    assert "finite" in _raises(A.predict, "flex_extinction", {"o2_pct": float("nan")})
    assert "exceed 100" in _raises(A.predict, "flex_extinction", {"o2_pct": 60, "co2_pct": 50})
    assert "greater than 0" in _raises(A.predict, "flex_extinction", {"pressure_kpa": 0})
    assert "vary must be" in _raises(A.sweep, "flex_extinction", {"vary": "fuel"})
    assert "points" in _raises(A.sweep, "flex_extinction", {"vary": "co2_pct", "points": 500})
    try:
        A.predict("no_such_model", {})
        raise AssertionError("unknown model should raise KeyError")
    except KeyError:
        pass


def test_sweep_flags_points_beyond_the_tested_range():
    s = A.sweep("bass2_flame_spread", {"vary": "o2_pct", "points": 9, "extend": 0.25,
                                       "inputs": {"diameter_cm": 0.64}})
    lo, hi = s["tested_range"]
    assert (lo, hi) == (16.8, 18.9)
    for p in s["points"]:
        inside = lo - 1e-9 <= p["o2_pct"] <= hi + 1e-9
        if inside:
            assert p["in_domain"], p
        else:
            assert not p["in_domain"]
            assert p["interval_90"][1] > p["interval_90"][0]


def _serve():
    srv = A_server.make_server("127.0.0.1", 0, quiet=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _call(url, data=None, method=None):
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


import server as A_server                                              # noqa: E402


def test_http_contract():
    srv, base = _serve()
    try:
        code, _, body = _call(base + "/health")
        assert code == 200 and json.loads(body)["status"] == "ok"
        code, _, body = _call(base + "/models")
        assert code == 200 and len(json.loads(body)["models"]) == 5
        code, headers, body = _call(base + "/predict/flex_burning_rate", json.dumps({"fuel": "Heptane"}).encode())
        r = json.loads(body)
        assert code == 200 and r["interval_90"][0] < r["prediction"] < r["interval_90"][1]
        assert headers.get("Access-Control-Allow-Origin") == "*"
        assert _call(base + "/predict/flex_extinction", b'{"fuel": "Diesel"}')[0] == 422
        assert _call(base + "/predict/flex_extinction", b"{not json")[0] == 400
        assert _call(base + "/predict/unknown", b"{}")[0] == 404
        assert _call(base + "/nowhere")[0] == 404
        assert _call(base + "/predict/flex_extinction", b"x" * (A_server.MAX_BODY + 1))[0] == 413
        code, headers, _ = _call(base + "/predict/flex_extinction", method="OPTIONS")
        assert code == 204 and "POST" in headers.get("Access-Control-Allow-Methods", "")
        code, _, body = _call(base + "/sweep/flex_extinction", json.dumps({"vary": "he_pct", "points": 5}).encode())
        assert code == 200 and len(json.loads(body)["points"]) == 5
    finally:
        srv.shutdown()


def test_habitat_map_and_locate():
    hm = A.habitat_map()
    assert hm["coverage"]["rows_at_or_below_70kpa"] == 0           # the evidence gap the project claims
    assert hm["materials"]["n"] == 22 and hm["materials"]["burn_at_34"] == 20
    r = A.habitat_locate({"pressure_kpa": 56.5, "o2_pct": 34})
    assert r["prediction"]["in_domain"] is False and "extrapolation" in r["status"]
    r2 = A.habitat_locate({"pressure_kpa": 101.3, "o2_pct": 21})
    assert r2["distance_to_nearest_nasa_test"] < r["distance_to_nearest_nasa_test"] + 0.2
    assert "required" in _raises(A.habitat_locate, {"o2_pct": 21})
    srv, base = _serve()
    try:
        code, _, body = _call(base + "/habitat")
        assert code == 200 and "grid" in json.loads(body)
        code, _, body = _call(base + "/habitat/locate", json.dumps({"pressure_kpa": 80, "o2_pct": 25}).encode())
        assert code == 200 and "prediction" in json.loads(body)
        assert _call(base + "/habitat/other", b"{}")[0] == 404
    finally:
        srv.shutdown()


def test_static_export_matches_the_live_models():
    out = ROOT / "agnishikha-ui" / "public" / "ignis"
    cat = json.loads((out / "catalog.json").read_text())
    assert [m["name"] for m in cat["models"]] == A.MODEL_NAMES
    for name in A.MODEL_NAMES:
        data = json.loads((out / f"{name}.json").read_text())
        for case in data["cases"]:
            live = A.predict(name, case["reference_inputs"])
            ref = case["reference"]
            key = "probability" if live["task"] == "classification" else "prediction"
            assert math.isclose(live[key], ref[key], rel_tol=1e-9), (name, case["category"], live[key], ref[key])
            assert set(case["sweeps"]) == {i["name"] for i in A.model_card(name)["inputs"] if i["type"] == "number"}
