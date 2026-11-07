# data/ — AstraFlame NASA microgravity fire dataset

**Owner:** Prachya Biswas (Data Science Lead) · **Licence:** NASA source data is CC0-1.0 (NASA Physical Sciences Informatics)

`data/processed/` is the **single source of truth**. Every model, notebook and test reads its data from there, through `models/config.py`, and no other copy of a dataset exists in the repository.

## Layout

| Folder | What it holds | Edited by hand? |
|---|---|---|
| `raw_from_NASA/` | Verbatim extracts of NASA PSI files (SHA-256 checked when they were extracted) | Never |
| `bass2_and_wstf/` | BASS-II (PSI-25) intermediate tables and the WSTF 1 g reference workbook | Never (rebuilt by scripts) |
| `processed/` | Clean, verified datasets and the Excel deliverable | Never (rebuilt by scripts) |
| `scripts/` | Builders, verifier, data contract, one-command rebuild | Code |
| `validation_report.json` | Result of the last data-contract run | Generated |

## Rebuild and check, in one command each

```bash
python data/scripts/build_all.py --check      # rebuild from NASA extracts in a temp folder; prove byte-for-byte equality
python data/scripts/build_all.py --write      # rebuild and overwrite data/processed (+ refresh the Excel file)
python data/scripts/validate_processed.py     # strict data contract (130 checks); exit 1 on any error
python run_pipeline.py --only etl validate    # both, from the repository root
```

## Lineage

| Processed file | Built by | From | Rows |
|---|---|---|---|
| `FLEX_PSI-69_clean_v1.0.csv` | `build_flex.py` | `raw_from_NASA/PSI-69_Experimental_table_FLEX.csv` | 274 |
| `SPICE_PSI-107_smoke_points_v1.0.csv` | `build_spice.py` | `raw_from_NASA/PSI-107_SmokePointReview-0g-3_SmokePointDatasheet_extract.csv` | 55 |
| `SAME_PSI-101-102_smoke_particles_v1.0.csv` | `build_same.py` | `raw_from_NASA/PSI-101_SAME_SAME-R_Results_ReducedDataSheet_extract.csv` | 154 |
| `BASS_PSI-26_test_log_v1.0.csv` | `build_bass_saffire.py` | `raw_from_NASA/PSI-26_AsRunTestMatrix_*.csv` | 121 |
| `SAFFIRE_I-III_PSI-98-100_v1.0.csv` | `build_bass_saffire.py` | `raw_from_NASA/PSI-98/99/100_Experimental_table_*.csv` | 13 |
| `BASS-II_flame_spread_microgravity_v1.0.csv` | `build_bass2_final.py` | Link et al. 2018, *Sci Rep* 8:120, Table S1 + `bass2_and_wstf/BASS-II_PSI-25_clean_v0.1.csv` | 52 |
| `Ignis_mu_unified_master_v1.0.csv` | `build_master.py` | all of the above + the WSTF 1 g workbook | 850 |

`verify_all.py` re-checks 890 values against the NASA extracts on every rebuild (734 sampled values plus all 52 WSTF rows × MOC, ULOI and pressure).

## Data contract (`scripts/validate_processed.py`)

| Check | Example |
|---|---|
| Schema | required columns exist; numeric columns are numeric |
| Identity | `record_id` / `experiment_id` present and unique; frozen row counts |
| Categories | fuel ∈ {Methanol, Heptane}; `test_end` ∈ {Extinction, Completion, Disruption}; known PSI ids |
| Physics bounds | O₂ 0–100 %; mole fractions 0–1; droplet 0.1–10 mm; K 0–3 mm²/s; heated sample 20–1000 °C |
| Consistency | mole fractions sum to 1 ± 0.03; kPa = mmHg × 0.1333; o2_pct = 100·x_O₂; extinction label agrees with `test_end`; extinction diameter ≤ initial diameter; one O₂ per BASS-II test |
| Lineage | every master-table row links to an existing record in its source file; exactly 52 rows of 1 g reference |

Leakage is checked where it can happen:
- **Group leakage:** the same ISS test, session or run appearing on both sides of a CV split. Every split is checked in `models/ml_selection.py`.
- **Target leakage:** a feature that is (almost) the target. Checked in `models/preprocess_v3.py`.

## Changelog

- **v1.0.2 (Nov 7, 2026).** All 52 WSTF 1 g rows (Hirsch et al. 2011, NTRS 20110008636, Tables 2–9) were checked against the paper: every MOC, ULOI and test pressure matches. The transcription is kept as `raw_from_NASA/NTRS-20110008636_Hirsch2011_Tables2-9_transcribed.csv`, and `verify_all.py` now re-checks it on every rebuild. Row WSTF11-T8-02 is renamed **Delrin polyoxymethylene**: the paper's Table 1 lists Acetron GP only as a 1/8-in rod and Delrin as a 0.054-in plastic, so the 1/2-in sheet result is Delrin (Table 9's label). The two POM entries are different products, not duplicates. The rows' quality flag now reads "verified" instead of "verification pending". No model input changed.
- **v1.0.1 (Nov 2026).** The new data contract found that SAME run 57 (lampwick, heater on, Rt/R0 = 1.25) was recorded at **0 °C**: NASA's sheet uses 0 as a blank there.
  - `build_same.py` now treats a 0 °C value on a heated sample as missing, and flags it.
  - Exactly one value changed in the SAME file and in the master table. File names keep `v1.0`.
  - No model changed, because that run was already excluded (its aging time is missing).
- **v1.0 (Nov 2026).** First verified release: 850 rows, 10 sources.

## Known gap

`bass2_and_wstf/BASS-II_PSI-25_clean_v0.1.csv` is a frozen intermediate. The NASA PSI-25 workbook it was cleaned from is not stored in this repository, so this one table cannot be rebuilt from raw here. Every table downstream of it can.
