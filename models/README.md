# Ignis μ / AgniShikha — ML models v2.0 (trained on NASA ISS data)

**Data Science / ML:** Prachya Biswas · **Data:** NASA PSI, CC0 (see `Ignis_mu_NASA_dataset_v1.0`)

**How the models were chosen and scored (v2):**
- **Nested grouped cross-validation.** Whole ISS test series or sessions are held out in the outer loop. All tuning and model choice happens only in the inner loop, so the scores below were never used to pick the model.
- **8 model families** (7 for the classifier) were tuned and compared for every model.
- **One selection procedure for all five models:** the average of the top-3 tuned families, with a physics-form fallback when an input is outside the tested domain.
- The full story, with v1 vs v2 on the same splits and the noise ceilings, is in **[MODEL_SELECTION_v2.md](MODEL_SELECTION_v2.md)**.

## The five models

| # | Model name (`predict(...)`) | Question it answers | Inputs | Output | Held-out score (nested CV) | Rows |
|---|---|---|---|---|---|---|
| 1 | `bass2_flame_spread` | How fast does flame spread over a plastic (PMMA) rod? | `o2_pct`, `opposed_flow_cm_s`, `diameter_cm` | mm/s | R² **0.62**, MAE 0.009 mm/s (v1: 0.53; noise ceiling ≈ 0.68) | 52 |
| 2 | `flex_extinction` | Will a fuel-droplet flame go out before the fuel is used up? | `fuel` (Methanol/Heptane), `pressure_kpa`, `o2_pct`, `co2_pct`, `he_pct`, `d0_mm` | probability + class | ROC-AUC **0.83**, Brier **0.090** (base rate 0.114), log-loss 0.299 | 206 |
| 3 | `flex_burning_rate` | How fast does the droplet burn? | same as model 2 | K, mm²/s | R² **0.71**, MAE 0.045 (9 % of mean; noise ceiling ≈ 0.72) | 256 |
| 4 | `spice_smoke_point` | How sooty / smoky is a gas flame? (shorter smoke point = more smoke) | `fuel`, `burner_diameter_mm`, `coflow_air_velocity_cm_s` | mm | R² **0.89**, MAE 4.4 mm, MAPE 11 % | 55 |
| 5 | `same_particle_size` | How big are the smoke particles from an overheated material? (smoke-detector design) | `material`, `sample_temperature_c`, `air_velocity_cm_s`, `aging_time_s`, `campaign` | µm | R² 0.43, MAPE 26 % | 125 |

95 % group-bootstrap confidence intervals, tuned hyper-parameters and the inner-CV ranking of every family are in `model_summary.json` and `*_v2_final_selection.csv`.

### What each final model is
- **Model 1:** average of a log-target ridge (a power law), SVR and ridge with interactions. Outside the tested domain the power law alone answers.
- **Model 2:** average of logistic regression with interactions, an RBF SVM and extra trees. Outside the tested domain plain logistic regression answers.
- **Model 3:** average of SVR, a Gaussian process and linear ridge. Linear ridge is the fallback.
- **Model 4:** average of a Gaussian process, SVR and the physics power law. The power law alone, L_sp ∝ d^−0.76 · u_air^0.41 (matching Dotson et al. 2011), is the fallback.
- **Model 5:** average of SVR, extra trees and random forest. No physics fallback, because no physical law links particle size to these inputs; out-of-domain inputs are still flagged.

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
| `train_v2.py` | Retrains all five models: `python train_v2.py data` (about 30 min on 2 cores; `--reuse` skips the nested CV) |
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
