"""
AstraFlame (Team Agnishikha) - one place for every path the ML pipeline reads or writes.
Data Science Lead: Prachya Biswas

Layout
    data/raw_from_NASA/   verbatim NASA PSI extracts (never edited)
    data/processed/       clean, verified datasets  <- the ONLY place models read data from
    models/artifacts/     production model bundles (*.joblib) + caches; archive/ holds v1 and v2 bundles
    models/reports/       every table, score and log the pipeline writes (csv / json)
    models/figures/       every figure the pipeline draws (png)

Override the data folder with the environment variable IGNIS_DATA_DIR (e.g. for a test copy).
"""
import os
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODELS_DIR.parent
DATA_DIR = Path(os.environ.get("IGNIS_DATA_DIR", REPO_ROOT / "data" / "processed"))
RAW_DIR = REPO_ROOT / "data" / "raw_from_NASA"
ARTIFACTS = MODELS_DIR / "artifacts"
ARCHIVE = ARTIFACTS / "archive"
REPORTS = MODELS_DIR / "reports"
FIGURES = MODELS_DIR / "figures"

MODEL_NAMES = ["bass2_flame_spread", "flex_extinction", "flex_burning_rate", "spice_smoke_point", "same_particle_size"]

DATASETS = {                                   # model -> processed file it trains on
    "bass2_flame_spread": "BASS-II_flame_spread_microgravity_v1.0.csv",
    "flex_extinction": "FLEX_PSI-69_clean_v1.0.csv",
    "flex_burning_rate": "FLEX_PSI-69_clean_v1.0.csv",
    "spice_smoke_point": "SPICE_PSI-107_smoke_points_v1.0.csv",
    "same_particle_size": "SAME_PSI-101-102_smoke_particles_v1.0.csv",
}


def data(name):
    """path of a processed dataset"""
    return DATA_DIR / name


def artifact(name):
    ARTIFACTS.mkdir(parents=True, exist_ok=True); return ARTIFACTS / name


def archived(version, name):
    p = ARCHIVE / version; p.mkdir(parents=True, exist_ok=True); return p / name


def report(name):
    REPORTS.mkdir(parents=True, exist_ok=True); return REPORTS / name


def figure(name):
    FIGURES.mkdir(parents=True, exist_ok=True); return FIGURES / name
