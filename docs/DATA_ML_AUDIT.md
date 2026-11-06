# Data and ML pipeline audit (November 2026)

**Owner:** Prachya Biswas, Data Science Lead · **Scope:** `data/`, `models/`, `tests/`, `run_pipeline.py`

Each finding below was checked by running the code. A one-command run (`python run_pipeline.py`) now reproduces the processed data byte for byte and every reported score.

## Findings and fixes

| # | Finding | Risk | Fix |
|---|---|---|---|
| 1 | Four training CSVs existed twice: `models/data/` and `data/processed/` | The model could silently train on a stale copy | `models/data/` removed. `models/config.py` is the only path definition, and `data/processed/` is the single source of truth (`IGNIS_DATA_DIR` can override it for tests) |
| 2 | Three figures existed twice (`docs/` and `models/`); the map code existed in two scripts | Copies drift apart | One copy each, under `models/figures/`. The map code lives only in `v3_final.py` |
| 3 | `models/` held about 45 files in one folder (bundles, tables, figures, scripts) | Hard to audit or deploy | `artifacts/` (production bundles, `archive/v1`, `archive/v2`), `reports/`, `figures/`; scripts stay in `models/` |
| 4 | No single command rebuilt the data; two builders depended on the working folder | Not reproducible by others | `data/scripts/build_all.py --check` rebuilds all 9 files from the NASA extracts and proves byte-for-byte equality (`--write` to overwrite) |
| 5 | `package.py` copied the raw extracts and scripts *into* `data/processed/` when run there | Duplicated raw data | It now copies them only when building a standalone bundle folder |
| 6 | No data contract | Bad values reach training unnoticed | `validate_processed.py`: 130 checks covering schema, keys, row counts, categories, physics bounds, cross-field consistency and lineage. Exit code 1 on any error |
| 7 | **The contract found a real error:** SAME run 57 (lampwick, heater on) recorded at 0 °C. NASA's sheet uses 0 as a blank | Wrong temperature in the published dataset | `build_same.py` now treats it as missing and flags it (dataset v1.0.1). It was already excluded from training (missing aging time), so no model changed |
| 8 | Leakage was prevented by design but never *checked* | A later edit could leak a test across folds unnoticed | `checked_splits()` asserts that no ISS test, session or run sits on both sides of any outer or inner split. `check_no_target_leak()` refuses any feature that copies the target |
| 9 | No pinned environment; bundles need scikit-learn 1.9.1 | Bundles fail to load elsewhere | `requirements.txt` with exact versions; `requirements-dev.txt` adds pytest |
| 10 | No automated tests | Regressions go unseen | `tests/`, 12 tests: contract on clean and corrupted data, reproducible ETL, leakage guards, artifact integrity, scores match their tables, prediction contract, exact Shapley additivity, out-of-domain warning with a wider band, physics directions |
| 11 | No end-to-end runner | Steps run by hand, in an order only the author knows | `run_pipeline.py`: etl → validate → train_v2 → noise → compare → final → figures → tests. Fail-fast, and it writes `models/reports/pipeline_manifest.json` (stage times, git commit, library versions, data and artifact hashes) |
| 12 | No CI | Nobody notices a broken pipeline | `.github/workflows/ml-pipeline.yml` runs ETL check + contract + tests on every change to `data/`, `models/` or `tests/` |
| 13 | A stale cache path would have silently re-run the 30-minute nested CV in "fast" mode | Wasted time; the cache could be overwritten by a partial run | Every cache path goes through `config.py` |

## Verification

- `python run_pipeline.py`: all 8 stages pass, in about 10 minutes.
- The rebuilt `v3_comparison.csv`, `v3_physics_check.csv`, `v1_vs_v2.csv`, `v2_procedure_ranks.csv`, `noise_ceiling.json` and `preprocessing_log_v3.json` are **identical** to the versions committed before the refactor. Every reported score is unchanged.
- `python tests/run_tests.py`: 12 passed, 0 failed.

## Still open (not in this scope)

- `data/bass2_and_wstf/BASS-II_PSI-25_clean_v0.1.csv` is a frozen intermediate. Its NASA PSI-25 workbook is not stored in the repository.
- A REST API around `predict()` for the dashboard, which is still on a placeholder model, is the next step and is shared with the UI lead.
- The full mode (`--full`, about 50 min) was not re-run after the refactor. Fast mode reuses the cached nested CV, whose results are the ones committed.
- CI has not run yet. The workflow is written for GitHub Actions, and the pinned versions are the ones tested locally (Python 3.13).
