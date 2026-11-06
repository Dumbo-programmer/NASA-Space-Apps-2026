# Ignis μ / AgniShikha — ML models v3.0 (trained on NASA ISS data)

**Data Science / ML:** Prachya Biswas · **Data:** NASA PSI, CC0 (see `Ignis_mu_NASA_dataset_v1.0`)

**How the models were chosen (v3):**
1. **Objective.** The fire-risk envelope: will a flame survive, how fast does it spread or burn, and how sure is the answer. It feeds a safe-cabin map and a next-experiment pick.
2. **Model chosen for that objective.** For the three map outputs this is a **physics-informed Gaussian process (PI-GP)**: a physics law, plus a GP correction kept only when the data supports it, plus an ISS-test offset. Far from the data it falls back to physics, and its uncertainty grows there.
3. **Preprocessing designed for the PI-GP.** Inputs are moved into physics space, unclear outcomes are dropped with logged reasons, ISS-test groups are kept, and measured replicate noise is used as the starting noise.
4. **Scoring.** Every model, on the same nested grouped splits, on accuracy, 90 % coverage and physics violations.

Full story: **[MODEL_SELECTION_v3.md](MODEL_SELECTION_v3.md)** (v3) and [MODEL_SELECTION_v2.md](MODEL_SELECTION_v2.md) (v2 nested selection).

## The five models

| # | Model name (`predict(...)`) | Question | Inputs | Final model | Held-out score (nested CV) | Rows |
|---|---|---|---|---|---|---|
| 1 | `bass2_flame_spread` | How fast does flame spread over a PMMA rod? | `o2_pct`, `opposed_flow_cm_s`, `diameter_cm` | PI-GP (power law + test offset) | R² 0.57, 90 % coverage 86.5 %, 0 % physics violations | 52 |
| 2 | `flex_extinction` | Will a fuel-droplet flame go out before the fuel is used up? | `fuel`, `pressure_kpa`, `o2_pct`, `co2_pct`, `he_pct`, `d0_mm` | PI-GP classifier | **ROC-AUC 0.87, Brier 0.082** (base rate 0.114) | 206 |
| 3 | `flex_burning_rate` | How fast does the droplet burn? | same as model 2 | PI-GP | R² 0.71 (noise ceiling ≈ 0.72), coverage 89.7 % | 256 |
| 4 | `spice_smoke_point` | How sooty is a gas flame? | `fuel`, `burner_diameter_mm`, `coflow_air_velocity_cm_s` | v2 ensemble + power-law fallback | R² 0.89, MAE 4.4 mm | 55 |
| 5 | `same_particle_size` | How big are smoke particles from an overheated material? | `material`, `sample_temperature_c`, `air_velocity_cm_s`, `aging_time_s`, `campaign` | v2 ensemble | R² 0.43 | 125 |

Models 1–3 give their own input-dependent 90 % interval. Models 4–5 use the band from the v2 nested residuals.

## What every answer contains
- **The prediction:** `prediction` for regression models, or `probability` + `predicted_class` for the classifier.
- **A 90 % error band:** `interval_90`, taken from the nested held-out errors of the whole procedure.
- **Which model answered:** `model_used` (the ensemble, or the physics-form fallback outside the tested domain).
- **A domain check:** `in_domain` and `warnings`. These flag when the input is outside what NASA tested, including per-fuel and per-material ranges and the nearest-run distance. When this triggers, confidence is reported as "Limited (extrapolation)".
- **Exact Shapley explanations:** `contributions` and `base_value`.
  - One-hot columns, such as `fuel` or `material`, count as one feature.
  - `base_value + sum(contributions) = prediction`.
- **Traceability fields:** `value_type: "ML-predicted"`, `source`, `validation`, `valid_for`, `version`. **Show all of these in the UI.**

## Use in the backend (FastAPI)
```python
from fastapi import FastAPI
from ignis_models import predict
app = FastAPI()

@app.post("/predict/{model_name}")
def run(model_name: str, inputs: dict):
    return predict(model_name, **inputs)
```
Example:
```python
predict("flex_extinction", fuel="Methanol", pressure_kpa=101.3, o2_pct=18, co2_pct=0, he_pct=0, d0_mm=3.0)
predict("spice_smoke_point", fuel="Propylene", burner_diameter_mm=1.6, coflow_air_velocity_cm_s=30)
predict("same_particle_size", material="Kapton", sample_temperature_c=420, air_velocity_cm_s=8.1, aging_time_s=35, campaign="SAME-R")
```
- Run `python test_predict.py` to see all five models plus the physics checks.
- Speed: about 0.1–2 s per call with explanations. Pass `explain=False` for an instant answer.

## Physics checks (all pass)
- **FLEX:** more O₂ means a lower chance of extinction (0.98 → 0.86 from 13 % to 25 %) and faster burning (K 0.35 → 0.58).
- **SPICE:** propylene is the sootiest fuel (smoke point 18 mm vs ethylene's 51 mm); N₂ dilution makes it less sooty (36 mm at 50 %). More coflow raises the smoke point, and a smaller burner raises it too.
- **SAME:** smoke particles grow with aging (0.056 → 0.097 µm) and are larger with no airflow (0.19 µm). Both match NASA's published findings.

## Limits (say these out loud in the demo)
- **The data is small:** 52 to 256 rows per model. Scores are honest held-out numbers, but the error bands are wide.
- **Model 2's base rate:** 87 % of FLEX tests ended in extinction, so read the probability against that base rate. The output includes it.
- **Model 5's inputs:** the two campaigns used different instruments, so `campaign` is an input. Materials outside the five that were tested are rejected.
- **Not modelled:**
  - SAFFIRE has 13 rows, too few for a model. It is used as retrieval evidence.
  - BASS outcomes are mostly "sustained burn", so they are used as retrieval text.
  - FLEX-2 and CFI tables have no measured outcomes.
- **1 g data:** no model was trained on it. WSTF is a comparison layer only.

## Files
| File | Purpose |
|---|---|
| `ignis_models.py` | One entry point, `predict()`, plus feature definitions, Shapley explanations, domain checks and the physics fallback |
| `ml_selection.py` | Model families, hyper-parameter grids, nested grouped CV, selection procedures, bootstrap CIs |
| `train_v2.py` | v2: 8 families, nested CV, all five models (about 30 min; `--reuse` skips the nested CV) |
| `preprocess_v3.py`, `pigp.py` | v3 preprocessing (physics space, logged) and the physics-informed GP |
| `compare_v3.py`, `v3_final.py` | v3 comparison on identical splits + physics check; final v3 bundles, safe-cabin map, side experiments. Run after `train_v2.py` |
| `MODEL_SELECTION_v3.md` | Objective-driven selection, v3 results |
| `MODEL_SELECTION_v2.md` | How the models were selected, and v1 vs v2 |
| `*.joblib` | Trained models. Built with scikit-learn 1.9.1, so pin the same version or retrain |
| `*_v2_nested_cv.csv` | Every family and every selection procedure, scored on held-out tests |
| `*_v2_final_selection.csv` | Inner-CV ranking and tuned hyper-parameters of the final model |
| `*_v2_oof.csv` | Held-out prediction for every row (v2 and v1) |
| `model_summary.json`, `v1_vs_v2.csv`, `noise_ceiling.json` | Scores in one place |
| `fig_v1_vs_v2.png`, `fig_v2_pred_vs_measured.png` | Slide-ready figures |
| `noise_ceiling.py` | Replicate-based estimate of the best possible R² |
| `v1_archive/` | v1 models, scores and scripts, kept for comparison |
| `data/` | The exact training CSVs |
