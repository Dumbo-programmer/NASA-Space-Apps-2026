"""
Write real-model answers to static JSON for a dashboard deployed without a Python server.

    python api/export_static.py            # -> agnishikha-ui/public/ignis/

For every model and every tested category (fuel, rod size, material), each numeric input is
swept across its NASA-tested range (and 15 % beyond, to show the out-of-range warning) with
the other inputs at their reference values. Every point is a full predict() answer from the
trained bundles, Shapley breakdown included. The dashboard uses these files only when the
live API cannot be reached, and labels them as precomputed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ignis_api as A  # noqa: E402

OUT = A.ROOT / "agnishikha-ui" / "public" / "ignis"
POINTS = 17
EXTEND = 0.15


def model_sweeps(name):
    card = A.model_card(name)
    cats = [i for i in card["inputs"] if i["type"] == "category"]
    nums = [i["name"] for i in card["inputs"] if i["type"] == "number"]
    defaults = {i["name"]: i["default"] for i in card["inputs"]}
    primary = cats[0]["name"] if cats else None
    out = {"model": name, "points_per_sweep": POINTS, "extend": EXTEND, "by_category": primary, "cases": []}
    options = cats[0]["options"] if cats else [None]
    for opt in options:
        base = dict(defaults)
        if primary:
            base[primary] = opt
        ref = A.predict(name, base, explain=True)
        case = {"category": opt, "reference_inputs": ref["inputs"], "reference": ref, "sweeps": {}}
        for field in nums:
            s = A.sweep(name, {"inputs": base, "vary": field, "points": POINTS, "extend": EXTEND, "explain": True})
            s["points"] = [p for p in s["points"] if "error" not in p]
            case["sweeps"][field] = {"tested_range": s["tested_range"], "points": s["points"]}
        out["cases"].append(case)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--only", nargs="*", default=A.MODEL_NAMES)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cat = A.catalog()
    cat["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    cat["mode"] = "precomputed"
    (out / "catalog.json").write_text(json.dumps(cat, separators=(",", ":"), allow_nan=False))
    for n in a.only:
        t = time.time()
        data = model_sweeps(n)
        (out / f"{n}.json").write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
        npts = sum(len(s["points"]) for c in data["cases"] for s in c["sweeps"].values())
        print(f"{n}: {len(data['cases'])} case(s), {npts} predictions, {time.time() - t:.0f}s")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
