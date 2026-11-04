# Ignis μ / AgniShikha — ML models v1.0 (trained on NASA ISS data)

**Data Science / ML:** Prachya Biswas · **Data:** NASA PSI, CC0 (see `Ignis_mu_NASA_dataset_v1.0`)

**How the models were scored:**
- Every score below comes from **grouped cross-validation**. Whole test series or sessions are held out together, so the scores measure performance on unseen experiments.
- Each model is compared with a simple baseline before it is chosen.

## The five models

| # | Model name (`predict(...)`) | Question it answers | Inputs | Output | Held-out score | Rows |
|---|---|---|---|---|---|---|
| 1 | `bass2_flame_spread` | How fast does flame spread over a plastic (PMMA) rod? | `o2_pct`, `opposed_flow_cm_s`, `diameter_cm` | mm/s | R² 0.53, MAE 0.009 mm/s (mean baseline R² −0.11) | 52 |
| 2 | `flex_extinction` | Will a fuel-droplet flame go out before the fuel is used up? | `fuel` (Methanol/Heptane), `pressure_kpa`, `o2_pct`, `co2_pct`, `he_pct`, `d0_mm` | probability + class | ROC-AUC **0.84** (guessing 0.50); Brier 0.092 (base rate 0.115) | 206 |
| 3 | `flex_burning_rate` | How fast does the droplet burn? | same as model 2 | K, mm²/s | R² **0.72**, MAE 0.047 (9% of mean) | 256 |
| 4 | `spice_smoke_point` | How sooty / smoky is a gas flame? (shorter smoke point = more smoke) | `fuel`, `burner_diameter_mm`, `coflow_air_velocity_cm_s` | mm | R² **0.85**, MAPE 16% | 55 |
| 5 | `same_particle_size` | How big are the smoke particles from an overheated material? (smoke-detector design) | `material`, `sample_temperature_c`, `air_velocity_cm_s`, `aging_time_s`, `campaign` | µm | R² 0.50, MAPE 26% | 125 |

### How each model was chosen
- **Model 2:** among the candidates whose probabilities beat the base rate, it had the best AUC. Class-balanced versions were rejected because they distort the probabilities.
- **Models 3 and 4:** a linear model and a physics power law beat the tree models, so the simpler model was kept.
- **Model 4's fitted law:** L_sp ∝ d^−0.76 · u_air^0.41. This matches Dotson et al. 2011, which reported a coflow exponent of 0.41.

## What every answer contains
- **The prediction:** `prediction` for regression models, or `probability` + `predicted_class` for the classifier.
- **A 90 % error band:** `interval_90`, taken from the held-out errors.
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
- **FLEX:** more O₂ means a lower chance of extinction (0.99 → 0.83 from 13 % to 25 %) and faster burning (K 0.35 → 0.57).
- **SPICE:** propylene is the sootiest fuel (smoke point 18 mm vs ethylene's 55 mm). More coflow raises the smoke point, and a smaller burner raises it too.
- **SAME:** smoke particles grow with aging (0.058 → 0.094 µm) and are larger with no airflow (0.16 µm). Both match NASA's published findings.

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
| `ignis_models.py` | One entry point, `predict()`, plus feature definitions, Shapley explanations and domain checks |
| `*.joblib` | Trained models. Built with scikit-learn 1.9.1, so pin the same version or retrain |
| `train_all.py` | Retrains models 2–5: `python train_all.py data/` |
| `train_bass2_flame_spread.py`, `predict_flame_spread.py` | Model 1 |
| `*_cv_results.csv` | Comparison of every candidate model |
| `*_oof.csv` | Held-out prediction for every row |
| `model_summary.json` | Scores in one file |
| `fig_models_overview.png` | Slide-ready figure |
| `data/` | The exact training CSVs |
