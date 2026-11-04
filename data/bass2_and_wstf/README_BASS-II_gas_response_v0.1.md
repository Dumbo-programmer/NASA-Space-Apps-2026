# BASS-II_gas_response_v0.1.csv
**Built from:** BASS-II_PSI-25_clean_v0.1.csv with build_gas_response.py
**Question:** how much does a burning material change cabin air in microgravity?

**IDs (not features):** record_id, psi_id, source_row, pi_group (use as CV group), test_id, sample_no
**Inputs (features):** material_family, material_inferred, geometry, thickness_mm, diameter_mm, width_cm, rod_color, burning_sides, flow_restrictor, o2_initial_pct, co2_background_pct, co_background_ppm, air_setting_initial, air_setting_steps, flow_reduced_to_extinction, frames_shot_duration_proxy
**Outputs (targets, observed):** delta_o2_pct, delta_co2_pct, delta_co_ppm
**Physics-derived:** co2_per_o2_ratio (theory: PMMA 0.83, cellulose 1.0), co_to_co2_ratio, delta_co2_per_frame (proxy rate)
**Use rules:** use_for_o2_co2 (119 rows), use_for_co (115 rows); drop small_material_group = True
**Check result:** PMMA median CO2/O2 = 0.80 vs theory 0.83 → sensors consistent.
**Caution:** burn duration not recorded; raw deltas mostly reflect how long it burned. Prefer rate targets.
