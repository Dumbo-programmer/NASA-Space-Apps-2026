"""
Ignis mu / AgniShikha - rebuild every processed dataset from the verbatim NASA extracts, in one command.
Data Science Lead: Prachya Biswas

    python data/scripts/build_all.py --check     # rebuild in a temp folder and prove it matches data/processed byte for byte
    python data/scripts/build_all.py --write     # rebuild and overwrite data/processed (+ the Excel deliverable)

Lineage
    raw_from_NASA/PSI-69 ...FLEX.csv                  -> build_flex.py         -> processed/FLEX_PSI-69_clean_v1.0.csv
    raw_from_NASA/PSI-107 ...SmokePoint extract       -> build_spice.py        -> processed/SPICE_PSI-107_smoke_points_v1.0.csv
    raw_from_NASA/PSI-101 ...Results extract          -> build_same.py         -> processed/SAME_PSI-101-102_smoke_particles_v1.0.csv
    raw_from_NASA/PSI-26 + PSI-98/99/100              -> build_bass_saffire.py -> processed/BASS_PSI-26_test_log_v1.0.csv, SAFFIRE_I-III...
    bass2_and_wstf/BASS-II_PSI-25_clean_v0.1.csv      -> build_bass2_final.py  -> processed/BASS-II_flame_spread_microgravity_v1.0.csv
      + Link et al. 2018 Table S1/S2 (typed in script)                          (+ bass2_and_wstf/..._1g_reference_v1.0.csv)
    bass2_and_wstf/BASS-II_PSI-25_clean_v0.1.csv      -> build_gas_response.py -> bass2_and_wstf/BASS-II_gas_response_v0.1.csv
    all of the above + WSTF workbook                  -> build_master.py       -> processed/Ignis_mu_unified_master_v1.0.csv
    then verify_all.py (890 checks against the NASA extracts) and validate_processed.py (schema, physics bounds)
Known gap: BASS-II_PSI-25_clean_v0.1.csv is a frozen intermediate; its NASA source workbook is not stored in the repo.
"""
import argparse, filecmp, hashlib, shutil, subprocess, sys, tempfile
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
RAW, PROC, E, SCRIPTS = DATA / "raw_from_NASA", DATA / "processed", DATA / "bass2_and_wstf", DATA / "scripts"
PROCESSED_CSV = ["FLEX_PSI-69_clean_v1.0.csv", "SPICE_PSI-107_smoke_points_v1.0.csv", "SAME_PSI-101-102_smoke_particles_v1.0.csv",
                 "BASS_PSI-26_test_log_v1.0.csv", "SAFFIRE_I-III_PSI-98-100_v1.0.csv", "BASS-II_flame_spread_microgravity_v1.0.csv",
                 "Ignis_mu_unified_master_v1.0.csv"]
BASS2_OUT = ["BASS-II_flame_spread_1g_reference_v1.0.csv", "BASS-II_gas_response_v0.1.csv"]


def run(args, cwd=None):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(map(str, args))}\n{r.stderr[-2000:]}")
    return r.stdout


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def build(out: Path, work: Path):
    """Run every builder; processed files land in `out`, BASS-II side files in `work`."""
    out.mkdir(parents=True, exist_ok=True)
    for f in E.iterdir():
        shutil.copy(f, work / f.name)
    run([SCRIPTS / "build_flex.py", RAW / "PSI-69_Experimental_table_FLEX.csv", out])
    run([SCRIPTS / "build_spice.py", RAW / "PSI-107_SmokePointReview-0g-3_SmokePointDatasheet_extract.csv", out])
    run([SCRIPTS / "build_same.py", RAW / "PSI-101_SAME_SAME-R_Results_ReducedDataSheet_extract.csv", out])
    run([SCRIPTS / "build_bass_saffire.py", RAW, out])
    run([SCRIPTS / "build_bass2_final.py"], cwd=work)          # reads/writes its working folder
    run([SCRIPTS / "build_gas_response.py"], cwd=work)
    shutil.copy(work / "BASS-II_flame_spread_microgravity_v1.0.csv", out / "BASS-II_flame_spread_microgravity_v1.0.csv")
    run([SCRIPTS / "build_master.py", out, work])
    print(run([SCRIPTS / "verify_all.py", RAW, out]).strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="overwrite data/processed with the rebuilt files")
    ap.add_argument("--check", action="store_true", help="rebuild in a temp folder and compare with data/processed (default)")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        out, work = Path(t) / "out", Path(t) / "work"; work.mkdir()
        build(out, work)
        diffs = [f for f in PROCESSED_CSV if not (PROC / f).exists() or not filecmp.cmp(out / f, PROC / f, shallow=False)]
        diffs += [f"bass2_and_wstf/{f}" for f in BASS2_OUT if not filecmp.cmp(work / f, E / f, shallow=False)]
        if a.write:
            for f in PROCESSED_CSV:
                shutil.copy(out / f, PROC / f)
            for f in BASS2_OUT:
                shutil.copy(work / f, E / f)
            run([SCRIPTS / "package.py", RAW, PROC, E, PROC])          # refresh the Excel deliverable
            print(f"wrote {len(PROCESSED_CSV)} processed files; changed: {diffs or 'none'}")
            for f in PROCESSED_CSV:
                print(f"  {sha(PROC / f)}  {f}")
            return
        if diffs:
            sys.exit(f"NOT REPRODUCIBLE - rebuilt files differ from the committed ones: {diffs}\n"
                     "If the change is intended, run with --write and commit the new files.")
        print(f"reproducible: all {len(PROCESSED_CSV) + len(BASS2_OUT)} files rebuilt byte-for-byte from the NASA extracts")


if __name__ == "__main__":
    main()
