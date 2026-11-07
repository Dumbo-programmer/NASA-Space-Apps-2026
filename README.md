<h1 align="center">AstraFlame — AI Fire-Safety Insights from NASA Microgravity Combustion Data</h1>

<p align="center">
  <strong>850 real NASA experiments. Five trained models. Every number traceable to its NASA source.</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#my-role">My Role</a> •
  <a href="#features">Features</a> •
  <a href="#nasa-data">NASA Data</a> •
  <a href="#models">Models</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#project-structure">Structure</a>
</p>

---

## Overview

**AstraFlame** is Team **Agnishikha**'s project for the **NASA Space Apps Challenge 2026** (Dhaka), challenge **"Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"**.

In microgravity, fire does not rise. It burns as a sphere, can survive at lower oxygen, and does not follow the rules we learn on Earth. NASA has run hundreds of fire experiments on the International Space Station and on unmanned Cygnus vehicles. That knowledge is spread across separate investigations, file formats and papers.

AstraFlame brings those experiments together. You give it a condition: oxygen level, pressure, airflow and material. It answers with:

- how fast a fire will spread,
- whether a flame will go out,
- how sooty or smoky it will be,
- how large the smoke particles will be.

Every answer comes with an error band, the NASA evidence behind it, and an honest warning when NASA never tested that condition.

## My Role

I'm the **Data Science Lead** on Team Agnishikha.

**Data.** I built the project's dataset from NASA's Physical Sciences Informatics (PSI) repository.
- I found the files that hold the measured results, not just the test settings.
- I verified every extract byte-for-byte against NASA's copy.
- I cleaned and documented ten sources into one 850-row table.

**Models.** I trained and validated the five machine-learning models in `models/`.
- I chose each model from the project's objective (a fire-risk envelope with honest uncertainty), not by score alone.
- I designed the preprocessing for the chosen model: physics space, logged cleaning, test groups and measured noise.
- Every candidate was scored with **nested grouped cross-validation** on ISS tests it never saw.
- Each model is checked against a simple baseline and a replicate-based noise ceiling.

**Interface.** I wrote the single `predict()` interface, the model API in `api/` that serves it, and the dashboard's **NASA Models** tab that calls it.

The dashboard UI in `agnishikha-ui/` was built by our UI & Software Lead, **Tawhid Bin Omar**.

This repo is my copy of the project, kept here alongside my other work.

---

## Features

| Category | Details |
|---|---|
| **Verified NASA dataset** | 850 rows from 9 ISS/Cygnus investigations (798 microgravity runs) plus 52 rows of 1g ground reference. Every extract was checked against NASA's file, and 890 field-level checks found 0 errors |
| **Five trained models** | Flame spread, flame extinction, droplet burning rate, smoke point and smoke particle size, all trained on NASA ISS data |
| **Honest validation** | Grouped cross-validation holds out whole test series or sessions, and every model is compared against a baseline |
| **Explainability** | Exact Shapley values for every prediction: how much each input pushed the answer up or down |
| **Domain check** | Warns when an input is outside what NASA tested, including per-fuel and per-material ranges and nearest-experiment distance |
| **Traceability** | Every prediction carries `value_type`, the NASA source and the model's validation scores |
| **Model API** | `api/server.py`: JSON endpoints for every model (`/models`, `/predict/{model}`, `/sweep/{model}`), strict input validation, no extra dependencies |
| **Mission-control dashboard** | Next.js dashboard with a microgravity flame visualizer, telemetry, risk matrix, explainability, crew protocols, and a **NASA Models** tab that shows the trained models' answers live |
| **Beginner notebook** | A step-by-step notebook (with Bangla explanations) that rebuilds the flame-spread model from scratch |

---

## NASA Data

All source data is public domain (**CC0-1.0**) from [NASA Physical Sciences Informatics](https://psi.nasa.gov).

| Investigation | PSI record | What was measured | Rows used |
|---|---|---|---|
| **FLEX** — Flame Extinguishment Experiment | [PSI-69](https://psi.nasa.gov/physci/repo/data/investigations/PSI-69) · DOI 10.60555/mbq8-0451 | Droplet flame extinction, burning rate | 274 |
| **SPICE** — Smoke Point In Co-flow Experiment | [PSI-107](https://psi.nasa.gov/physci/repo/data/investigations/PSI-107) · DOI 10.60555/9kbh-e962 | Smoke point of gas-jet flames | 55 |
| **SAME / SAME-R** — Smoke Aerosol Measurement | [PSI-102](https://psi.nasa.gov/physci/repo/data/investigations/PSI-102), [PSI-101](https://psi.nasa.gov/physci/repo/data/investigations/PSI-101) | Smoke particle size and concentration | 154 |
| **BASS** — Burning and Suppression of Solids | [PSI-26](https://psi.nasa.gov/physci/repo/data/investigations/PSI-26) | Burn outcome and crew observations | 121 |
| **BASS-II** | [PSI-25](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25) + Link et al. 2018, *Sci. Rep.* 8:120 | Flame spread over PMMA rods, gas response | 181 |
| **Saffire I–III** — Spacecraft Fire Experiment | [PSI-98](https://psi.nasa.gov/physci/repo/data/investigations/PSI-98), [PSI-99](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99), [PSI-100](https://psi.nasa.gov/physci/repo/data/investigations/PSI-100) | Large-scale flame spread, with a 1g comparison | 13 |
| **WSTF 1g reference** | Hirsch et al. 2011, NTRS 20110008636 | Maximum oxygen concentration on Earth | 52 (comparison only) |

**A finding worth seeing:** in Saffire-II, silicone burned completely in 1g but **did not spread at all in microgravity**. Earth-based fire rules do not transfer directly to space.

Full documentation is in `data/README.md` (layout, lineage, data contract, changelog), `data/README_dataset_v1.0.md` and the workbook `data/processed/Ignis_mu_NASA_dataset_v1.0.xlsx`. Start with its *Data_Map* sheet.

---

## Models

The models were chosen from the objective. The fire-risk envelope asks three things: will a flame survive, how fast does it spread or burn, and how sure is the answer. For the three outputs that feed the safe-cabin map, I use a **physics-informed Gaussian process (PI-GP)**. The two smoke outputs keep the most accurate v2 ensemble. All scores come from nested grouped cross-validation on identical held-out ISS tests. Full method: [models/MODEL_SELECTION_v3.md](models/MODEL_SELECTION_v3.md).

| # | Model | Question | Final model | Score | Physics violations | v2 on same tests |
|---|---|---|---|---|---|---|
| 1 | `bass2_flame_spread` | How fast does flame spread over a PMMA rod? | PI-GP | R² 0.57, 90 % coverage 86.5 % | 0 % | R² 0.62 |
| 2 | `flex_extinction` | Will a fuel-droplet flame go out? | PI-GP classifier | ROC-AUC **0.87**, Brier **0.082** | 2.4 % | AUC 0.83, Brier 0.090, 22 % violations |
| 3 | `flex_burning_rate` | How fast does the droplet burn? | PI-GP | R² **0.71** (ceiling ≈ 0.72), coverage 89.7 % | 0 % | R² 0.71 |
| 4 | `spice_smoke_point` | How sooty is a gas flame? | v2 ensemble | R² **0.89**, MAE 4.4 mm | 0 % | — |
| 5 | `same_particle_size` | How large are smoke particles? | v2 ensemble | R² 0.43 | 43 % | — |

How I chose the models:

- **Objective first.** Map outputs must be accurate, follow physics and give uncertainty that grows outside NASA's data. Smoke outputs are read inside the tested range, so accuracy decides there. This rule was set before the comparison.
- **PI-GP = physics law + GP correction + ISS-test offset.**
  - The correction is kept only when grouped inner CV shows it beats the physics law alone. For flame spread it was dropped.
  - Far from data the model returns to physics by itself.
  - Its uncertainty points to the next most useful ISS experiment.
- **Preprocessing designed for the model.**
  - Physics space: log transforms, O₂ partial pressure, 1/diameter.
  - Unclear outcomes removed, with every reason logged.
  - ISS-test groups kept.
  - Replicate-measured noise used as the prior.
- **Physics stays in.** SPICE recovers the published scaling of Dotson et al. (2011): smoke-point length ∝ burner diameter^−0.76 × coflow velocity^0.41.
- **Honest limits.** v2 is slightly more accurate on flame spread (0.62 vs 0.57, overlapping CIs). Flame spread and burning rate sit near their replicate noise ceilings (≈ 0.68 and 0.72), so new experiments, not new models, would improve them.

<p align="center">
  <img src="models/figures/fig_v3_safe_map_next_experiment.png" alt="Safe-cabin map and next experiment" width="760" />
</p>

<p align="center">
  <img src="models/figures/fig_v1_vs_v2.png" alt="v1 vs v2 held-out scores and noise ceilings" width="760" />
</p>

---

## Architecture

```
 NASA PSI repository (CC0)                         ESP32 sensor rig (O2, pressure, airflow)
          |                                                     |
          v                                                     v
 data/scripts  ->  verified extracts  ->  unified master table (850 rows)
                                                 |
                       +-------------------------+--------------------------+
                       v                                                    v
          models/ (5 trained models)                          evidence retrieval
          predict(model_name, **inputs)                       (NASA record behind each answer)
                       |                                                    |
                       +-------------> model API (api/server.py) <----------+
                                                   |
                                                   v
                                 agnishikha-ui (Next.js dashboard, NASA Models tab)
                                 offline fallback: agnishikha-ui/public/ignis/*.json
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Data pipeline** | Python 3, pandas, NumPy, openpyxl |
| **Machine learning** | scikit-learn 1.9.1: physics-informed Gaussian process, tuned ensembles, nested grouped CV, exact Shapley explanations; one-command pipeline with data contract and tests |
| **Model API** | Python standard library HTTP server (`api/server.py`) calling `models/ignis_models.py`; precomputed JSON fallback for static hosting |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, lucide-react |
| **Hardware** | ESP32 with O2, pressure, temperature and airflow sensors |
| **Data source** | NASA Physical Sciences Informatics (PSI) |

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/prachyabiswas/NASA-Space-Apps-2026.git
cd NASA-Space-Apps-2026
```

### 2. Run the data-science pipeline

```bash
pip install -r requirements.txt          # pinned versions; scikit-learn 1.9.1 is required by the model files
python run_pipeline.py                   # about 10 min: reproducible ETL -> data contract -> training -> evaluation -> tests
python run_pipeline.py --full            # everything from scratch, about 50 min
python tests/run_tests.py                # test suite only (or: pytest tests)
```

```python
import sys; sys.path.insert(0, "models")
from ignis_models import predict
predict("flex_extinction", fuel="Methanol", pressure_kpa=101.3, o2_pct=18, co2_pct=0, he_pct=0, d0_mm=3.0)
predict("spice_smoke_point", fuel="Propylene", burner_diameter_mm=1.6, coflow_air_velocity_cm_s=30)
```

### Full results notebook

[`notebooks/AstraFlame_Full_ML_Pipeline.ipynb`](notebooks/AstraFlame_Full_ML_Pipeline.ipynb) runs the whole data-science part in one place (about 15 minutes on a laptop): data checks, preprocessing, the grouped train/validation/test design, noise ceilings, every model on identical held-out ISS tests (R², MAE, coverage, ROC-AUC, Brier, accuracy, balanced accuracy, F1, confusion matrix), the improvements tried, the physics check and the final results. It is saved with its outputs, so the results can be read on GitHub without running it.

### Or run everything in Google Colab

Open [`notebooks/Ignis_mu_Model_Selection_v2.ipynb`](notebooks/Ignis_mu_Model_Selection_v2.ipynb) in Colab ([open in Colab](https://colab.research.google.com/github/prachyabiswas/NASA-Space-Apps-2026/blob/main/notebooks/Ignis_mu_Model_Selection_v2.ipynb)) and choose `Runtime → Run all`. The notebook then:
- rebuilds all five models from the NASA data, including the objective-driven v3 (PI-GP) models
- shows the leakage demo, the noise ceilings and the nested selection
- runs the physics checks

It needs no login and takes about 30 minutes.

### 3. Run the model API and the dashboard

```bash
python api/server.py                     # http://127.0.0.1:8000  (GET /models, POST /predict/{model})
curl -X POST localhost:8000/predict/flex_extinction -d '{"fuel": "Heptane", "co2_pct": 20}'

cd agnishikha-ui
npm install
npm run dev                              # http://localhost:3000, open the "NASA Models" tab
```

The tab calls the API at `NEXT_PUBLIC_IGNIS_API_URL` (default `http://127.0.0.1:8000`). Without the API, for example on a static deploy, it uses `public/ignis/*.json`: answers precomputed by `api/export_static.py` from the same trained models, one input at a time around NASA reference conditions, and labelled as precomputed.

### 4. Rebuild and check the dataset from NASA's files

```bash
python data/scripts/build_all.py --check      # rebuild every processed file and prove it is byte-for-byte identical
python data/scripts/validate_processed.py     # strict data contract: schema, physics bounds, consistency, lineage
```

---

## Project Structure

```
NASA-Space-Apps-2026/
├── agnishikha-ui/            # Next.js mission-control dashboard (Tawhid Bin Omar); NASA Models tab (Prachya Biswas)
├── api/                      # Model API: server.py, ignis_api.py (validation, sweeps), export_static.py
├── data/                     # see data/README.md
│   ├── raw_from_NASA/        # Verbatim NASA PSI extracts (never edited)
│   ├── processed/            # Single source of truth: clean datasets, master table, Excel workbook
│   ├── bass2_and_wstf/       # BASS-II intermediates, WSTF 1g reference
│   └── scripts/              # build_all.py (one-command rebuild), builders, verify_all.py, validate_processed.py
├── models/                   # see models/README.md
│   ├── config.py             # Every path the pipeline uses
│   ├── ignis_models.py       # predict(): domain checks, exact Shapley, physics fallback
│   ├── preprocess_v3.py, pigp.py, ml_selection.py
│   ├── train_v2.py, compare_v3.py, v3_final.py, noise_ceiling.py
│   ├── artifacts/            # Production model bundles (+ archive/v1, archive/v2)
│   ├── reports/              # Scores, comparisons, logs, pipeline manifest
│   ├── figures/              # Figures
│   └── MODEL_SELECTION_v3.md, MODEL_SELECTION_v2.md, README.md
├── tests/                    # Data contract, reproducibility, leakage guards, prediction contract, physics behaviour, API
├── run_pipeline.py           # One command: ETL -> validation -> training -> evaluation -> export -> tests
├── requirements.txt          # Pinned versions
├── notebooks/                # Colab notebook for model selection v2 + beginner flame-spread notebook
└── docs/                     # ML design notes, abstract draft, verification guide
```

---

## Status and Limits

- **Dashboard:** the NASA Models tab shows the trained models. The Simulation, Risk Matrix, Explainability and Protocols tabs still use a client-side surrogate for the live scenario and say so in the footer.
- **Hosting the API:** it must run on a Python host for free input combinations; a static deploy gets the precomputed answers only.
- **Data size:** 52–256 rows per model. The scores are honest held-out numbers, but the error bands are wide (95 % CIs are in `models/reports/model_summary.json`). For flame spread and burning rate the remaining error is mostly run-to-run noise, so more ISS experiments, not more modelling, would improve them.
- **1g data:** the WSTF ground reference is a comparison layer and is never used to train microgravity models.
- **Missing outcomes:** the FLEX-2 and Cool Flames Investigation tables list test conditions only, so they are not modelled.

---

## Team Agnishikha

| Member | Role |
|---|---|
| Apurbo Kumar | Team Lead & Project Manager |
| Prachya Biswas | Data Science Lead |
| Samyo Pramanik | AI Lead |
| Purno | Physics & Technical Lead |
| Tawhid Bin Omar | UI & Software Lead |
| Mahib Al Mamun | Hardware & Embedded Lead |
---

## License

NASA source data is public domain (CC0-1.0) from NASA Physical Sciences Informatics. Code was written by Team Agnishikha for the NASA Space Apps Challenge 2026.

---

<p align="center">
  Built by Team Agnishikha for NASA Space Apps Challenge 2026 — Data Science & ML: <a href="https://github.com/prachyabiswas">Prachya Biswas</a> · UI: <a href="https://github.com/Dumbo-programmer">Tawhid Bin Omar</a>
</p>
