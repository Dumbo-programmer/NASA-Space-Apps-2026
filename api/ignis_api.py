"""
Agnishikha prediction service: transport-independent core.

server.py exposes these functions over HTTP; export_static.py writes them to JSON for a
static deployment; tests/test_api.py calls them directly. Every answer comes from the
trained bundles in models/artifacts through models/ignis_models.predict(), so the
dashboard shows exactly what the validated models say, never a hand-tuned surrogate.
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
if str(MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(MODELS_DIR))

import ignis_models as M  # noqa: E402

API_VERSION = "1.0"
MAX_SWEEP_POINTS = 41


class InputError(ValueError):
    """Raised for a request the API refuses (HTTP 422). The message is shown to the user."""


# Inputs per model, in the order a form should show them. Ranges and categories come from
# the trained bundle (what NASA actually tested), so they can never drift from the model.
INPUTS = {
    "bass2_flame_spread": [
        ("o2_pct", "Oxygen", "% O2", 18.2),
        ("opposed_flow_cm_s", "Opposed airflow", "cm/s", 1.67),
        ("diameter_cm", "PMMA rod diameter", "cm", 0.64),
    ],
    "flex_extinction": [
        ("fuel", "Fuel", None, "Methanol"),
        ("pressure_kpa", "Pressure", "kPa", 101.3),
        ("o2_pct", "Oxygen", "% O2", 21.0),
        ("co2_pct", "CO2 diluent", "%", 0.0),
        ("he_pct", "Helium diluent", "%", 0.0),
        ("d0_mm", "Initial droplet diameter", "mm", 3.0),
    ],
    "flex_burning_rate": [
        ("fuel", "Fuel", None, "Methanol"),
        ("pressure_kpa", "Pressure", "kPa", 101.3),
        ("o2_pct", "Oxygen", "% O2", 21.0),
        ("co2_pct", "CO2 diluent", "%", 0.0),
        ("he_pct", "Helium diluent", "%", 0.0),
        ("d0_mm", "Initial droplet diameter", "mm", 3.0),
    ],
    "spice_smoke_point": [
        ("fuel", "Fuel", None, "Ethylene"),
        ("burner_diameter_mm", "Burner diameter", "mm", 0.8),
        ("coflow_air_velocity_cm_s", "Coflow air velocity", "cm/s", 20.0),
    ],
    "same_particle_size": [
        ("material", "Material", None, "Kapton"),
        ("sample_temperature_c", "Sample temperature", "deg C", 500.0),
        ("air_velocity_cm_s", "Air velocity", "cm/s", 4.0),
        ("aging_time_s", "Smoke aging time", "s", 60.0),
        ("campaign", "Campaign (instrument set)", None, "SAME-R"),
    ],
}
MODEL_NAMES = list(INPUTS)


def jsonable(x):
    """numpy scalars/arrays, tuples and non-finite floats -> plain JSON values."""
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        x = float(x)
        return x if math.isfinite(x) else None
    return x


def _bundle(name):
    if name not in INPUTS:
        raise KeyError(name)
    return M.load(name)


def _categories(b):
    return {k: [jsonable(v) for v in vals] for k, vals in b["domain"].get("categories", {}).items()}


def _range_for(b, field, raw):
    """Tested range of one numeric input, narrowed to the chosen category when the bundle records one."""
    d = b["domain"]
    lo_hi = d["ranges"].get(field)
    pc = d.get("per_category_ranges")
    if pc and raw is not None:
        cat = raw.get(pc["by"])
        table = pc["ranges"].get(cat) or pc["ranges"].get(_coerce_cat(cat, pc["ranges"]))
        if table and field in table:
            lo_hi = table[field]
    return [float(lo_hi[0]), float(lo_hi[1])] if lo_hi is not None else None


def _coerce_cat(value, allowed):
    """Match a category sent as text or number (e.g. diameter '0.64' -> 0.64)."""
    for a in allowed:
        if a == value:
            return a
        try:
            if isinstance(a, (int, float, np.floating)) and math.isclose(float(a), float(value)):
                return a
        except (TypeError, ValueError):
            pass
    return None


def model_card(name):
    b = _bundle(name)
    cats = _categories(b)
    defaults = {f: d for f, _, _, d in INPUTS[name]}
    inputs = []
    for field, label, unit, default in INPUTS[name]:
        item = {"name": field, "label": label, "unit": unit, "default": default}
        if field in cats:
            item.update(type="category", options=cats[field])
        else:
            item.update(type="number", tested_range=_range_for(b, field, None),
                        tested_range_for_default=_range_for(b, field, defaults))
            pc = b["domain"].get("per_category_ranges")
            if pc and any(field in r for r in pc["ranges"].values()):
                item["tested_range_by_category"] = {
                    str(jsonable(cat)): _range_for(b, field, {pc["by"]: cat}) for cat in pc["ranges"]}
        inputs.append(item)
    out = {
        "name": name, "task": b["task"], "target": b["target_label"], "unit": b.get("unit"),
        "model": b["model_label"], "version": b.get("version"), "inputs": inputs,
        "explanation_groups": list(b["groups"]), "training_rows": b.get("n_rows"),
        "training_groups": b.get("n_groups"), "validation": b["validation"],
        "valid_for": b["valid_for"], "source": b["source"],
    }
    if b["task"] == "classification":
        out.update(classes=b["classes"], threshold=b.get("threshold", 0.5), base_rate=b.get("base_rate"))
    if b.get("fallback_label"):
        out["fallback_model"] = b["fallback_label"]
    return jsonable(out)


def catalog():
    return {"api_version": API_VERSION, "models": [model_card(n) for n in MODEL_NAMES]}


def health():
    versions = {}
    for n in MODEL_NAMES:
        versions[n] = jsonable(_bundle(n).get("version"))
    return {"status": "ok", "api_version": API_VERSION, "models": versions}


def clean_inputs(name, body):
    """Validate a request body against the model's inputs. Missing fields take the default."""
    if name not in INPUTS:
        raise KeyError(name)
    if not isinstance(body, dict):
        raise InputError("request body must be a JSON object of inputs")
    b = _bundle(name)
    cats = b["domain"].get("categories", {})
    allowed = {f for f, *_ in INPUTS[name]}
    unknown = sorted(set(body) - allowed - {"explain"})
    if unknown:
        raise InputError(f"unknown input(s) {unknown}; this model takes {sorted(allowed)}")
    raw = {}
    for field, label, unit, default in INPUTS[name]:
        value = body.get(field, default)
        if field in cats:
            match = _coerce_cat(value, cats[field])
            if match is None:
                raise InputError(f"{field}={value!r} was never tested by NASA; choose one of {jsonable(cats[field])}")
            raw[field] = match
        else:
            if isinstance(value, bool) or value is None:
                raise InputError(f"{field} must be a number ({unit})")
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise InputError(f"{field} must be a number ({unit})") from None
            if not math.isfinite(value):
                raise InputError(f"{field} must be a finite number")
            if field in ("pressure_kpa", "d0_mm", "burner_diameter_mm", "coflow_air_velocity_cm_s",
                         "opposed_flow_cm_s") and value <= 0:
                raise InputError(f"{field} must be greater than 0 ({unit})")
            if field.endswith("_pct") and not 0 <= value <= 100:
                raise InputError(f"{field} must be between 0 and 100 %")
            if field in ("aging_time_s", "air_velocity_cm_s") and value < 0:
                raise InputError(f"{field} cannot be negative")
            raw[field] = value
    if {"o2_pct", "co2_pct", "he_pct"} <= raw.keys() and raw["o2_pct"] + raw["co2_pct"] + raw["he_pct"] > 100:
        raise InputError("o2_pct + co2_pct + he_pct cannot exceed 100 %")
    return raw


@lru_cache(maxsize=4096)
def _predict_cached(name, frozen, explain):
    return jsonable(M.predict(name, explain=explain, **dict(frozen)))


def predict(name, body, explain=None):
    raw = clean_inputs(name, body)
    if explain is None:
        explain = bool(body.get("explain", True)) if isinstance(body, dict) else True
    out = dict(_predict_cached(name, tuple(sorted(raw.items())), bool(explain)))
    out["inputs"] = jsonable(raw)
    return out


def sweep(name, body):
    """Vary one numeric input across its tested range (optionally a bit beyond) with the rest fixed.

    body = {"vary": "co2_pct", "inputs": {...}, "points": 21, "extend": 0.15, "explain": false}
    Returns one prediction per point, so a slider or a chart can show the real model's response.
    """
    if not isinstance(body, dict):
        raise InputError("request body must be a JSON object")
    base = clean_inputs(name, body.get("inputs", {}))
    vary = body.get("vary")
    numeric = [f for f, *_ in INPUTS[name] if f not in _bundle(name)["domain"].get("categories", {})]
    if vary not in numeric:
        raise InputError(f"vary must be one of {numeric}")
    try:
        n = int(body.get("points", 21))
        extend = float(body.get("extend", 0.0))
    except (TypeError, ValueError):
        raise InputError("points must be an integer and extend a number") from None
    if not 2 <= n <= MAX_SWEEP_POINTS:
        raise InputError(f"points must be between 2 and {MAX_SWEEP_POINTS}")
    if not 0 <= extend <= 1:
        raise InputError("extend must be between 0 and 1 (fraction of the tested range)")
    lo, hi = _range_for(_bundle(name), vary, base)
    span = hi - lo
    lo, hi = lo - extend * span, hi + extend * span
    if vary.endswith("_pct") or vary in ("aging_time_s", "air_velocity_cm_s"):
        lo = max(lo, 0.0)
    if vary in ("pressure_kpa", "d0_mm", "burner_diameter_mm", "coflow_air_velocity_cm_s", "opposed_flow_cm_s"):
        lo = max(lo, 1e-3)
    explain = bool(body.get("explain", False))
    points = []
    for v in np.linspace(lo, hi, n):
        inputs = {**base, vary: round(float(v), 6)}
        try:
            r = predict(name, inputs, explain=explain)
        except InputError as e:            # e.g. diluents summing past 100 % at the far end
            points.append({vary: round(float(v), 6), "error": str(e)})
            continue
        keep = ("probability", "predicted_class", "prediction", "interval_90", "in_domain", "warnings",
                "model_used", "contributions", "base_value")
        points.append({vary: round(float(v), 6), **{k: r[k] for k in keep if k in r}})
    tested = _range_for(_bundle(name), vary, base)
    return {"model": name, "vary": vary, "inputs": jsonable(base), "tested_range": tested, "points": points}
