"""
AstraFlame (Team Agnishikha) - the whole data-science pipeline in one command.
Data Science Lead: Prachya Biswas

    python run_pipeline.py              # fast (about 10 min): reuse the cached nested CV, keep the measured scaling timings
    python run_pipeline.py --full       # everything from scratch (about 50 min on 2 CPU cores)
    python run_pipeline.py --only etl validate tests      # any subset of stages, in pipeline order

Stages (fail-fast; each one's time and outcome goes to models/reports/pipeline_manifest.json)
    etl        rebuild data/processed from the verbatim NASA extracts and prove it is byte-for-byte identical
               (734 value checks against NASA inside); --rebuild-data overwrites data/processed instead
    validate   strict data contract: schema, keys, row counts, categories, physics bounds, cross-field consistency, lineage
    train_v2   8 model families, nested grouped CV (group-leak guard on every split), v2 bundles
    noise      replicate-run noise ceilings
    compare    PI-GP vs every tuned family on identical splits: accuracy, 90 % coverage, physics violations
    final      production v3 bundles, safe-cabin map, next-experiment pick, moving-average and scaling tests
    figures    v1 vs v2 figures
    export     real-model answers to agnishikha-ui/public/ignis/ (the dashboard's offline fallback)
    tests      data + model + API test suite (contract, leakage, artifacts, prediction contract, physics, HTTP)
"""
import argparse, hashlib, json, platform, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS, DATA = ROOT / "models", ROOT / "data"
STAGES = ["etl", "validate", "train_v2", "noise", "compare", "final", "figures", "export", "tests"]


def commands(full, rebuild):
    py = sys.executable
    return {
        "etl": ([py, DATA / "scripts" / "build_all.py", "--write" if rebuild else "--check"], ROOT),
        "validate": ([py, DATA / "scripts" / "validate_processed.py"], ROOT),
        "train_v2": ([py, "train_v2.py"] + ([] if full else ["--reuse"]), MODELS),
        "noise": ([py, "noise_ceiling.py"], MODELS),
        "compare": ([py, "compare_v3.py"], MODELS),
        "final": ([py, "v3_final.py"] + ([] if full else ["--no-scaling"]), MODELS),
        "figures": ([py, "make_figures_v2.py"], MODELS),
        "export": ([py, ROOT / "api" / "export_static.py"], ROOT),
        "tests": ([py, ROOT / "tests" / "run_tests.py"], ROOT),
    }


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="recompute the nested CV and the scaling test from scratch")
    ap.add_argument("--rebuild-data", action="store_true", help="overwrite data/processed with the rebuilt files")
    ap.add_argument("--only", nargs="+", choices=STAGES, help="run only these stages")
    a = ap.parse_args()
    stages = [s for s in STAGES if not a.only or s in a.only]
    cmds = commands(a.full, a.rebuild_data)
    manifest = {"mode": "full" if a.full else "fast", "python": platform.python_version(), "stages": []}
    try:
        manifest["git_commit"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        pass
    t_all = time.time()
    for s in stages:
        cmd, cwd = cmds[s]; t0 = time.time()
        print(f"\n=== [{s}] {' '.join(Path(str(c)).name if i < 2 else str(c) for i, c in enumerate(cmd))}", flush=True)
        r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
        tail = [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and "Warning" not in l and not l.startswith("  repeat")][-6:]
        print("\n".join("    " + l for l in tail))
        manifest["stages"].append({"stage": s, "ok": r.returncode == 0, "seconds": round(time.time() - t0, 1)})
        if r.returncode != 0:
            print(f"\nPIPELINE STOPPED: stage '{s}' failed (exit {r.returncode})")
            (MODELS / "reports" / "pipeline_log_failed.txt").write_text(r.stdout + r.stderr)
            break
    manifest["seconds_total"] = round(time.time() - t_all, 1)
    manifest["data_sha256_16"] = {p.name: sha(p) for p in sorted((DATA / "processed").glob("*.csv"))}
    manifest["artifacts_sha256_16"] = {p.name: sha(p) for p in sorted((MODELS / "artifacts").glob("*.joblib"))}
    try:
        import numpy, pandas, sklearn, scipy
        manifest["libraries"] = {m.__name__: m.__version__ for m in (numpy, pandas, scipy, sklearn)}
    except ImportError:
        pass
    (MODELS / "reports" / "pipeline_manifest.json").write_text(json.dumps(manifest, indent=1))
    ok = all(x["ok"] for x in manifest["stages"])
    print(f"\n{'PIPELINE OK' if ok else 'PIPELINE FAILED'} in {manifest['seconds_total']} s - manifest: models/reports/pipeline_manifest.json")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
