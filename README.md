<h1 align="center">AstraFlame — AI Fire-Safety Insights from NASA Microgravity Combustion Data</h1>

<p align="center">
  <strong>850 verified NASA records. Five trained models. One habitat fire map. Every number traceable to its NASA source.</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#nasa-data">NASA Data</a> •
  <a href="#models">Models</a> •
  <a href="#habitat-fire-map">Habitat Fire Map</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#project-structure">Structure</a> •
  <a href="#team-agnishikha">Team</a>
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

Every answer comes with an error band, the NASA evidence behind it, and a warning when the condition is outside the NASA data used here.

It also draws a **habitat fire map**: where the NASA data has tests, where the model is estimating, where it is extrapolating, and which experiments would close the gap for the proposed Moon-habitat atmosphere (8.2 psia, 34 % O₂).

---

## Features

| Category | Details |
|---|---|
| **Verified NASA dataset** | 850 rows: 798 microgravity runs from 9 ISS/Cygnus investigations and 52 rows of 1g ground reference. Every extract was checked against NASA's file, and 890 field-level checks found 0 errors |
| **Five trained models** | Flame spread, flame extinction, droplet burning rate, smoke point and smoke particle size, all trained on NASA ISS data |
| **Honest validation** | Grouped cross-validation holds out whole test series or sessions, and every model is compared against a baseline |
| **Explainability** | Exact Shapley values for every prediction: how much each input pushed the answer up or down |
| **Domain check** | Warns when an input is outside the NASA data used, including per-fuel and per-material ranges and nearest-experiment distance |
| **Traceability** | Every prediction carries `value_type`, the NASA source and the model's validation scores |
| **Habitat fire map** | One map of oxygen against pressure: every NASA microgravity test in the data, the extinction model's estimate, the ISS and habitat points, a 22-material safety card and the five most useful next tests |
| **Live chamber reading** | `POST /habitat/locate` places a live reading from the ESP32 chamber on the map and returns the model's answer, the distance to the nearest NASA test and whether the point is inside the data |
| **Model API** | `api/server.py`: JSON endpoints for every model (`/models`, `/predict/{model}`, `/sweep/{model}`, `/habitat`, `/habitat/locate`), strict input validation, no extra dependencies |
| **Mission-control dashboard** | Next.js dashboard with a **NASA Models** tab and a **Habitat Map** tab that show the trained models' answers live, a guided tour, light and dark themes, and illustrative tabs for the flame visualizer, telemetry, risk matrix, explainability and crew protocols |
| **One-command run** | `docker compose up --build` starts the API and the dashboard together |

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

The models were chosen from the objective. The fire-risk envelope asks three things: will a flame survive, how fast does it spread or burn, and how sure is the answer. For the three outputs that feed the safe-cabin map, the project uses a **physics-informed Gaussian process (PI-GP)**. The two smoke outputs keep the most accurate v2 ensemble. All scores come from nested grouped cross-validation on identical held-out ISS tests. Full method: [models/MODEL_SELECTION_v3.md](models/MODEL_SELECTION_v3.md).

| # | Model | Question | Final model | Score | Physics violations | v2 on same tests |
|---|---|---|---|---|---|---|
| 1 | `bass2_flame_spread` | How fast does flame spread over a PMMA rod? | PI-GP | R² 0.57, 90 % coverage 86.5 % | 0 % | R² 0.62 |
| 2 | `flex_extinction` | Will a fuel-droplet flame go out? | PI-GP classifier | ROC-AUC **0.87**, Brier **0.082**, balanced accuracy **0.78**, macro F1 0.70 | 2.4 % | AUC 0.83, Brier 0.090, 22 % violations |
| 3 | `flex_burning_rate` | How fast does the droplet burn? | PI-GP | R² **0.71** (ceiling ≈ 0.72), coverage 89.7 % | 0 % | R² 0.71 |
| 4 | `spice_smoke_point` | How sooty is a gas flame? | v2 ensemble | R² **0.89**, MAE 4.4 mm | 0 % | — |
| 5 | `same_particle_size` | How large are smoke particles? | v2 ensemble | R² 0.43 | 43 % | — |

How the models were chosen:

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
- **Decision threshold for extinction.** 87 % of the ISS droplet tests ended in extinction, so accuracy alone is misleading (always answering "goes out" scores 0.87). The yes/no threshold is chosen by balanced accuracy on grouped out-of-fold predictions (0.67 in production). Scored with the threshold chosen inside each training set, 72 % of the rare "burns to completion" tests are caught (35 % at a 0.5 threshold).
- **Honest limits.** v2 is slightly more accurate on flame spread (0.62 vs 0.57, overlapping CIs). Flame spread and burning rate sit near their replicate noise ceilings (≈ 0.68 and 0.72), so new experiments, not new models, would improve them.

<p align="center">
  <img src="models/figures/fig_v3_safe_map_next_experiment.png" alt="Safe-cabin map and next experiment" width="760" />
</p>

**Where NASA should test next.** The models know where they are unsure. Combining that uncertainty with the distance from every existing test, they recommend the next ISS experiments. Searched over the whole tested range, the rule picks a 3 mm methanol droplet at **32 % O₂, 144 kPa** (the outcome there is a coin toss) and flame spread over a 6.4 mm rod at **21 % O₂, 7.5 cm/s** airflow (the largest uncertainty). Searched inside the habitat envelope only, it picks the five tests listed under [Habitat Fire Map](#habitat-fire-map). This is a simple rule, not a full Bayesian experimental design.

**The problem in numbers.** Of the 22 materials whose oxygen limits NASA measured (Hirsch et al. 2011), **20 would keep burning in the 34 % oxygen proposed for Moon habitats** (12 already do in Earth air). These limits come from Earth-gravity tests at 70–101 kPa, so this is a first estimate for 8.2 psia.

<p align="center">
  <img src="models/figures/fig_v1_vs_v2.png" alt="v1 vs v2 held-out scores and noise ceilings" width="760" />
</p>

---

## Habitat Fire Map

The proposed exploration atmosphere for Moon habitats is 8.2 psia (56.5 kPa) with 34 % O₂. The map answers one question: what does the NASA data say about fire in that air, and what should be tested next?

**The gap in the data.** Of the 798 microgravity runs, 501 record both oxygen and pressure.

- None is below 70.2 kPa, which is 13.7 kPa above the habitat pressure.
- 24 runs reach 30 % O₂ or more, and all are FLEX droplets. Microgravity solids in the data stop at 22.7 % O₂.
- No run falls in the box 30–36 % O₂ by 45–70 kPa.

**What the map holds.** `models/habitat_map.py` writes `models/reports/habitat_map.json` with five layers:

- the FLEX extinction model's probability that a 3 mm methanol droplet flame goes out, on a grid of 12–36 % O₂ by 40–320 kPa, with the distance to the nearest test;
- the 501 NASA test points;
- the ISS point (101.3 kPa, 21 % O₂) and the habitat point;
- a safety card for the 22 WSTF materials: 12 burn at 21 % O₂ and 20 at 34 % O₂ in Earth gravity;
- the five recommended next tests.

At the habitat point the model gives a 0.18 probability that the flame goes out, and flags the answer as an extrapolation.

**The five next tests.** Score = P(1 − P) × min(distance / 0.15, 1), searched over O₂ ≥ 21 % and 45–101.3 kPa, with picks kept apart so they are not near-duplicates.

| Test | O₂ (%) | Pressure (kPa) | P(flame goes out) | Position against the data |
|---|---|---|---|---|
| A | 27.2 | 49.3 | 0.57 | Below the lowest pressure in the data: an extrapolation |
| B | 27.2 | 86.7 | 0.68 | Inside the tested range |
| C | 32.8 | 100.7 | 0.31 | Inside the tested range |
| D | 36.0 | 100.7 | 0.22 | Above the highest oxygen in the data (34 %): an extrapolation |
| E | 32.0 | 49.3 | 0.24 | Below the lowest pressure in the data: an extrapolation |

**Where to see it.** API: `GET /habitat` and `POST /habitat/locate`. Dashboard: the **Habitat Map** tab, which can also place a live reading from the ESP32 chamber on the map (set `NEXT_PUBLIC_CHAMBER_URL` to the chamber's JSON feed). The chamber holds no flame and no added oxygen.

**Limits of the map.**

- **"No test" means no test in the data used here.** NASA has flown fire tests in reduced-pressure, oxygen-enriched air that are not in this dataset: Saffire V at about 71 kPa and 26 % O₂ ([Urban et al., ICES-2021-266](https://ntrs.nasa.gov/api/citations/20210011521/downloads/ICES%202021-266%200503-2021%20final.pdf)) and Saffire VI at about 54–55 kPa and 29–31 % O₂ ([ICES-2024-365](https://ntrs.nasa.gov/api/citations/20240002981/downloads/Saffire-ICES-2024-ICES-365-accepted%20final.pdf)). Adding those results is the first next step.
- **The layers are different data.** The probability grid comes from methanol droplets in microgravity. The material card comes from solids in Earth gravity at 70–101 kPa. They share axes for context only.
- **The next-test rule covers methanol droplets only.**
- The map is decision support, not certification.

---

## Architecture

```
 NASA PSI repository (CC0)
          |
          v
 data/scripts  ->  verified extracts  ->  unified master table (850 rows)
                                                 |
                       +-------------------------+--------------------------+
                       v                                                    v
          models/ (5 trained models)                          models/habitat_map.py
          predict(model_name, **inputs)                       (habitat fire map, next tests)
                       |                                                    |
                       +-------------> model API (api/server.py) <----------+
                                                   ^
                                                   |  /predict, /sweep, /habitat, /habitat/locate
                                                   v
          ESP32 chamber  ---------------->  agnishikha-ui (Next.js dashboard)
          (live reading, optional)          NASA Models and Habitat Map tabs
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

### 3. Run the API and the dashboard with Docker Compose

```bash
docker compose up --build
```

- Dashboard: http://localhost:3000 (open the **NASA Models** or **Habitat Map** tab)
- Model API: http://localhost:8000 (`GET /health`, `GET /models`, `GET /habitat`)

Ports and the API address can be changed by copying `.env.example` to `.env`. For live reloading during development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

To run the tests inside the API container:

```bash
docker compose run --rm api python tests/run_tests.py
```

### 4. Or run them by hand

```bash
python api/server.py                     # http://127.0.0.1:8000  (GET /models, POST /predict/{model}, GET /habitat)
curl -X POST localhost:8000/predict/flex_extinction -d '{"fuel": "Heptane", "co2_pct": 20}'
curl -X POST localhost:8000/habitat/locate -d '{"pressure_kpa": 56.5, "o2_pct": 34}'

cd agnishikha-ui
npm install
npm run dev                              # http://localhost:3000, open the "NASA Models" or "Habitat Map" tab
```

The tabs call the API at `NEXT_PUBLIC_IGNIS_API_URL` (default `http://127.0.0.1:8000`). Without the API, for example on a static deploy, they use `public/ignis/*.json`: answers precomputed by `api/export_static.py` from the same trained models, one input at a time around NASA reference conditions, and labelled as precomputed.

To rebuild the habitat map after retraining:

```bash
cd models && python habitat_map.py       # writes models/reports/habitat_map.json and material_safety_card.csv
```

### 5. Rebuild and check the dataset from NASA's files

```bash
python data/scripts/build_all.py --check      # rebuild every processed file and prove it is byte-for-byte identical
python data/scripts/validate_processed.py     # strict data contract: schema, physics bounds, consistency, lineage
```

---

## Project Structure

```
NASA-Space-Apps-2026/
├── agnishikha-ui/            # Next.js mission-control dashboard (Tawhid Bin Omar); NASA Models tab (Prachya Biswas)
│   ├── components/           # HabitatMapPanel, NasaModelPanel, GuidedTour, ThemeToggle and the illustrative tabs
│   └── public/ignis/         # Precomputed answers and habitat_map.json for offline use
├── api/                      # Model API: server.py, ignis_api.py (validation, sweeps, habitat), export_static.py, Dockerfile
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
│   ├── habitat_map.py        # Habitat fire map: coverage, extinction grid, material card, next tests
│   ├── artifacts/            # Production model bundles (+ archive/v1, archive/v2)
│   ├── reports/              # Scores, comparisons, logs, pipeline manifest, habitat_map.json, material_safety_card.csv
│   ├── figures/              # Figures
│   └── MODEL_SELECTION_v3.md, MODEL_SELECTION_v2.md, README.md
├── tests/                    # Data contract, reproducibility, leakage guards, prediction contract, physics behaviour, API
├── run_pipeline.py           # One command: ETL -> validation -> training -> evaluation -> habitat map -> export -> tests
├── docker-compose.yml        # API + dashboard in one command (docker-compose.dev.yml for live reload, .env.example for ports)
├── requirements.txt          # Pinned versions
├── notebooks/                # Full results notebook + Colab notebook for model selection v2
└── docs/                     # ML design notes, abstract draft, data and ML audit, changelog
```

---

## Status and Limits

- **Dashboard:** the NASA Models and Habitat Map tabs show the trained models. The Simulation, Risk Matrix, Explainability and Protocols tabs are illustrative: they use a client-side surrogate for the live scenario and say so in the footer and in the guided tour.
- **Scope of "not tested":** every statement that a condition has no test refers to the NASA data used here. Saffire IV–VI results, including reduced-pressure and oxygen-enriched burns, are not in the dataset yet.
- **Droplets, not cabin materials:** the extinction model and the habitat map's probability grid describe fuel-droplet flames. They are a first indicator for habitat air, not a prediction for solid cabin materials.
- **Hosting the API:** it must run on a Python host for free input combinations; a static deploy gets the precomputed answers only.
- **Data size:** 52–256 rows per model. The scores are honest held-out numbers, but the error bands are wide (95 % CIs are in `models/reports/model_summary.json`). For flame spread and burning rate the remaining error is mostly run-to-run noise, so more ISS experiments, not more modelling, would improve them.
- **High oxygen:** extinction errors rise above 21 % O₂, the conditions closest to the habitat air, because NASA ran few tests there (see the notebook's error analysis).
- **1g data:** the WSTF ground reference is a comparison layer and is never used to train microgravity models.
- **Missing outcomes:** the FLEX-2 and Cool Flames Investigation tables list test conditions only, so they are not modelled.

---

## Team Agnishikha

AstraFlame is a team project. The table lists who built each part.

| Member | Role | Contribution |
|---|---|---|
| Apurbo Kumar | Team Lead & Project Manager | Project planning, coordination and submission |
| [Prachya Biswas](https://github.com/prachyabiswas) | Data Science Lead | NASA dataset: collection, verification against NASA's files and the 850-row master table. The five models and their validation. The `predict()` interface, the model API and the NASA Models tab. The results notebook |
| [Samyo Pramanik](https://github.com/SamyoPramanik) | AI Lead | Docker setup for the API and the dashboard. Dashboard layout fixes |
| Purno | Physics & Technical Lead | Physics review of the models and of the habitat-atmosphere claims |
| [Tawhid Bin Omar](https://github.com/Dumbo-programmer) | UI & Software Lead | The dashboard in `agnishikha-ui/`. The habitat fire map: `models/habitat_map.py`, its API endpoints and the Habitat Map tab. The guided tour and themes |
| Mahib Al Mamun | Hardware & Embedded Lead | The ESP32 chamber and its live sensor feed |

Change notes for the habitat map and the dashboard redesign are in [docs/CHANGELOG.md](docs/CHANGELOG.md).

---

## Use of AI

AI assistants (Claude) were used to help write code, tests and documentation. All data is NASA public-domain data; results were checked by the team against the NASA sources. The project videos use AI-assisted animation and AI-generated music and sound effects, which are credited in the videos and on the project page.

---

## License

NASA source data is public domain (CC0-1.0) from NASA Physical Sciences Informatics. Code was written by Team Agnishikha for the NASA Space Apps Challenge 2026.

---

<p align="center">
  Built by Team Agnishikha for NASA Space Apps Challenge 2026 — <a href="https://github.com/prachyabiswas">Prachya Biswas</a> · <a href="https://github.com/Dumbo-programmer">Tawhid Bin Omar</a> · <a href="https://github.com/SamyoPramanik">Samyo Pramanik</a> · Apurbo Kumar · Purno · Mahib Al Mamun
</p>
