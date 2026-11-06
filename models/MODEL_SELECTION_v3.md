# Model Selection v3: objective first, then model, then preprocessing

**Author:** Prachya Biswas (Data Science Lead, Team AgniShikha)

Mentor feedback on v2 had three parts:
- Choose the model from what we want to do.
- Design the preprocessing for that model.
- Make the preprocessing stronger.

v3 does all three. v2 ([MODEL_SELECTION_v2.md](MODEL_SELECTION_v2.md)) stays as the baseline it is compared against.

## 1. Objective

**Fire-risk envelope.** For given cabin conditions, predict whether a flame survives, how fast it spreads or burns, and how sure the prediction is. The answers build a safe-cabin map and point to where NASA's next ISS experiment would teach the most.

| # | Requirement | How it is measured |
|---|---|---|
| R1 | Accurate on ISS tests never seen | nested grouped CV (whole tests held out) |
| R2 | Honest uncertainty | 90 % interval coverage |
| R3 | Obeys physics | % of NASA rows where moving the key input (O2, airflow, aging) moves the answer the wrong way |
| R4 | Safe outside the data | uncertainty grows away from the data; domain check |
| R5 | Works on 52–256 rows | few learned parameters |
| R6 | Explainable | physics coefficients + exact Shapley |

**Rule, fixed before comparing models:**
- **Map outputs** (survive?, spread rate, burning rate) need R1–R6, so they get the model that meets all six.
- **Smoke outputs** (smoke point, particle size) are read inside the tested range, so they get the most accurate model.

## 2. Model: Physics-Informed Gaussian Process (`pigp.py`)

```
y (physics space) = m(x) physics law  +  f(x) GP correction  +  b_test (ISS test offset)  +  noise
```

- **m(x):** ridge regression on physics terms, which is a power law when the target is log-transformed. The uncertainty of its coefficients is carried into the band.
- **f(x):** a smooth GP (length scale of at least 0.5 sd). It is kept only if grouped inner CV on the training folds shows it beats the physics law on NLPD, a score that punishes both errors and over-confidence. This works like TRACE's parameter-matched control: if the extra part does not earn its place, it is dropped.
- **b_test:** a hierarchical kernel, `same ISS test → correlated`. For a test the model has never seen, this term adds the between-test variance to the band.
- **noise:** starts from the replicate-run noise measured in preprocessing.
- **Band calibration:** a split-conformal-style scale factor, estimated on training folds only.
- Far from the data f(x) → 0, so the model falls back to the physics law by itself. v2 needed a hand-made switch for this.

## 3. Preprocessing v3, designed for the PI-GP (`preprocess_v3.py` → `preprocessing_log_v3.json`)

| Basis | What was done |
|---|---|
| Physics space | logs for power laws; O2 partial pressure; 1/diameter. Flame spread uses log u and u, because in microgravity spread first rises with opposed flow, then falls |
| Clean outcomes | dropped 61 FLEX "Disruption" tests (no outcome), 7 with droplet size or pressure missing, 24 SAME readings with all moments = 0 or '#NUM!', 5 with '??' temperature or missing aging time |
| Groups | ISS test, session, or run pair (fresh and aged reading together) |
| Noise prior | replicate pairs from different tests: 39 BASS-II, 27 FLEX, 16 SPICE, 164 SAME |
| Not done, on purpose | imputing outcomes; SMOTE or oversampling (breaks honest probabilities); moving average (see section 5); merging the five experiments into one table |

## 4. Results: same rows, same outer splits as v2 (`compare_v3.py` → `v3_comparison.csv`, `v3_physics_check.csv`)

| Output | Final model | Nested score | 90 % coverage | Physics violations | v2 on the same tests |
|---|---|---|---|---|---|
| Flame survives? | PI-GP classifier | **AUC 0.867, Brier 0.082**, log-loss 0.270 | – | 2.4 % | AUC 0.833, Brier 0.090, 22.3 % |
| Flame spread | PI-GP (physics law + test offset; inner CV dropped the correction) | R² 0.568, MAE 0.0096 | 86.5 % | **0 %** | R² 0.616, MAE 0.0092, 0 % |
| Burning rate K | PI-GP | R² 0.706, MAE 0.047 | 89.7 % | **0 %** | R² 0.712, MAE 0.045, 0 % |
| Smoke point | v2 ensemble (kept) | R² 0.886 | 87.3 % | 0 % | – |
| Particle size | v2 ensemble (kept) | R² 0.429 | 89.1 % | 43.2 % | – |

**Physics violations of the other tuned models** (% of NASA rows):
- Random forest: 12–79 %
- SVR: 27–90 %
- kNN: 36–87 %
- Gradient boosting: 4–66 %
- GP without a physics mean: up to 100 % on flame spread

**Honest notes:**
- On flame spread, v2 is more accurate (0.62 vs 0.57). The 95 % CIs overlap: PI-GP 0.25–0.73, v2 0.33–0.73.
- PI-GP's 90 % band on flame spread covers 86.5 % of held-out rows, slightly short of 90 %.
- The PI-GP does not help SPICE or SAME. Those keep v2, as the rule says.

## 5. Side experiments (`v3_final.py` → `v3_side_experiments.json`)

**Moving average** (BASS-II, physics law, leave-one-test-out):

| Variant | R² | MAE |
|---|---|---|
| No smoothing | 0.578 | 0.0100 |
| Moving average across file rows, scored on smoothed values | 0.532 | 0.0086 |
| Same, scored on real measurements | 0.527 | 0.0100 |
| Moving average within each test, scored on real measurements | 0.580 | 0.0096 |

- 18 of the 3-row windows cross a test boundary, which leaks one test into another.
- Smoothing makes the error *look* lower but does not improve prediction of real measurements.
- Noise belongs in the model (GP noise term), not removed from the data.

**Scaling:** PI-GP fit time is 0.9 s for 250 rows, 5.4 s for 500, 25 s for 1,000 and 181 s for 2,000 (about n³). For more than a few thousand rows, use a sparse or variational GP (inducing points). For very large multi-experiment data or ESP32 time series, a TRACE-like deep multi-task model becomes reasonable.

**Safe-cabin map and next experiment** (`fig_v3_safe_map_next_experiment.png`):
- 3 mm methanol droplet: the next test should be at about 32 % O2 and 144 kPa. There P(survive) ≈ 0.5, and no tested run is nearby.
- 6.4 mm PMMA rod: uncertainty is highest at 21 % O2 and 7.5 cm/s.
- No FLEX test was run below 70 kPa.

## Run order

```bash
python train_v2.py data      # v2 families, nested CV (about 30 min), v2 bundles also in v2_archive/
python compare_v3.py         # PI-GP vs every v2 family on identical splits + physics check (about 7 min)
python v3_final.py           # final v3 bundles for the three map outputs, map figure, side experiments (about 5 min)
python test_predict.py       # predict() smoke test + physics checks
```
