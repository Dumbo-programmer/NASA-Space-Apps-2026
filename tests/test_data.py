"""Data layer: reproducible ETL and a strict data contract that actually catches bad data."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "data" / "scripts"


def _validate(data_dir):
    env = dict(os.environ, IGNIS_DATA_DIR=str(data_dir), IGNIS_VALIDATION_REPORT=str(Path(tempfile.mkdtemp()) / "report.json"))
    return subprocess.run([sys.executable, str(SCRIPTS / "validate_processed.py")], env=env, capture_output=True, text=True)


def _corrupted_copy(edit):
    tmp = Path(tempfile.mkdtemp())
    for f in (ROOT / "data" / "processed").glob("*.csv"):
        shutil.copy(f, tmp / f.name)
    edit(tmp)
    return tmp


def test_contract_passes_on_committed_data():
    r = _validate(ROOT / "data" / "processed")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 errors" in r.stdout


def test_contract_catches_heated_sample_at_zero_celsius():
    def edit(d):
        f = d / "SAME_PSI-101-102_smoke_particles_v1.0.csv"; s = pd.read_csv(f)
        s.loc[s.index[0], "sample_temperature_c"] = 0.0; s.to_csv(f, index=False)
    r = _validate(_corrupted_copy(edit))
    assert r.returncode == 1 and "0 C" in r.stdout


def test_contract_catches_duplicate_key_and_impossible_oxygen():
    def edit(d):
        f = d / "FLEX_PSI-69_clean_v1.0.csv"; x = pd.read_csv(f)
        x.loc[1, "record_id"] = x.loc[0, "record_id"]; x.loc[2, "o2_pct"] = 140.0; x.to_csv(f, index=False)
    r = _validate(_corrupted_copy(edit))
    assert r.returncode == 1
    assert "record_id present and unique" in r.stdout and "o2_pct within" in r.stdout


def test_etl_rebuilds_processed_data_byte_for_byte():
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_all.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "byte-for-byte" in r.stdout
