# Agnishikha — NASA microgravity fire dataset v1.0

**Team:** Agnishikha · **Data Science Lead:** Prachya Biswas · **Built:** November 2026

**Source and licence:** NASA Physical Sciences Informatics (PSI), CC0-1.0 (public domain).

**Verification:**
- Every file taken from NASA was checked with SHA-256 and is byte-identical to NASA's copy.
- 734 random field checks compare the clean files back to the raw data, with 0 errors (`scripts/verify_all.py`).

## Files: what goes in, what comes out

| File | Rows | Inputs (features) | Outputs (targets) | Use |
|---|---|---|---|---|
| `Ignis_mu_unified_master_v1.0.csv` | 850 | gravity, material, configuration, O₂, pressure, airflow, size | `outcome_value` / `outcome_class`, routed by `outcome_type` | Retrieval database (pgvector) and model routing |
| `FLEX_PSI-69_clean_v1.0.csv` | 274 | fuel (methanol/heptane), pressure, O₂/N₂/CO₂/He fractions, initial droplet diameter | `test_end` (Extinction/Completion/Disruption), extinction diameter, burning-rate constant K, burn time | Model 2: extinction classifier (206 usable rows) |
| `SPICE_PSI-107_smoke_points_v1.0.csv` | 55 | fuel, burner diameter, coflow air velocity, fuel flow | `smoke_point_length_mm` (shorter = sootier) | Model 3: smoke-point regression |
| `SAME_PSI-101-102_smoke_particles_v1.0.csv` | 154 | material, heater setting / sample temperature, air velocity, aging time | count-mean and mass-mean particle diameter, number and mass concentration | Model 4: smoke particle size, which drives smoke-detector design (130 usable rows) |
| `BASS_PSI-26_test_log_v1.0.csv` | 121 | material, geometry, flow configuration, O₂, pressure, air settings | `outcome_label` (sustained / brief / no ignition) and NASA crew observations | Retrieval text and a small classifier |
| `SAFFIRE_I-III_PSI-98-100_v1.0.csv` | 13 | material, thickness, flow, flow direction, ignition power | sustained spread (yes/no), burn time, spread rate, 1g comparison | Evidence for the 1g-vs-microgravity comparison |
| `BASS-II_flame_spread_microgravity_v1.0.csv` | 52 | O₂, opposed flow, rod diameter | `flame_spread_mm_s` | Model 1 (already trained) |
| `Ignis_mu_NASA_dataset_v1.0.xlsx` | — | All of the above, plus Data_Map, Row_counts_for_abstract, Data_dictionary and Verification sheets | — | Open this first |

## Rules
1. **Never put the 52 rows of 1g WSTF data into microgravity training.** They are a comparison layer only.
2. **Group cross-validation by test**:
   - FLEX: by `flex_id`
   - SPICE: by `test_point`
   - SAME: by run pair (e.g. `61`/`61a`)
3. **Respect `quality_flags` and `use_for_*` columns** before modelling.
4. **Every number shown in the UI must carry `value_type` and `source_ref`.**

## How each file was obtained
- **FLEX:** the experimental table, downloaded in full.
- **SPICE:** NASA file `Raw Data_SmokePointReview-0g-3.xlsx`, sheet "Smoke Point Datasheet" ("Master Sheets of ISS Tests for SPICE"). The table on the PSI page lists flame conditions only, with no smoke-point results.
  - The data reproduces the published scaling: coflow exponent 0.41, the same as Dotson et al. 2011.
- **SAME / SAME-R:** NASA file `Analyzed Data_SAME, SAME-R_Results.xlsx`, sheet "Reduced data sheet".
- **BASS:** NASA file `Science Documents_As Run_Test Matrix.xlsx`.
  - The outcome label comes from a keyword rule applied to the crew notes. Every non-"sustained" row was checked by hand, and 9 labels were corrected (see the script).
- **SAFFIRE:** the experimental tables. Saffire-II includes the 1g comparison: silicone burned completely in 1g but did not spread in microgravity.

## Known gaps
- **FLEX-2 and CFI:** the tables list test conditions only, with no measured outcomes.
- **SPICE 2012 flight (methane/ethane):** not included.
- **SAFFIRE:** detailed results are only in very large telemetry files.

## Rebuild
```bash
python scripts/build_flex.py raw_from_NASA/PSI-69_Experimental_table_FLEX.csv .
python scripts/build_spice.py raw_from_NASA/PSI-107_SmokePointReview-0g-3_SmokePointDatasheet_extract.csv .
python scripts/build_same.py raw_from_NASA/PSI-101_SAME_SAME-R_Results_ReducedDataSheet_extract.csv .
python scripts/build_bass_saffire.py raw_from_NASA .
python scripts/build_master.py . .
python scripts/verify_all.py raw_from_NASA .
```
