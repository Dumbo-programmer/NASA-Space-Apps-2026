# BASS-II final dataset v1.0
**Main file:** BASS-II_flame_spread_microgravity_v1.0.csv (52 rows, 19 ISS tests)
**Task:** flame-spread regression for black PMMA rods in microgravity, opposed flow.

**Inputs (features):** o2_pct, opposed_flow_cm_s, diameter_cm (+ inv_diameter_per_cm), pmma_color
**Output (target, observed):** flame_spread_mm_s
**IDs / grouping:** test_id (use for grouped CV), flow_step
**Tested range:** O2 16.8-20.9 %, flow 0.41-7.55 cm/s, diameter 0.64/0.95/1.27 cm

**Reference file:** BASS-II_flame_spread_1g_reference_v1.0.csv (46 Earth rows, same rods) for microgravity vs 1g comparison and limiting O2.
**Other files:** gas_response (O2 used, CO2/CO made), test_log_clean (NASA PSI-25 log).

**Sources:** NASA PSI-25 BASS-II Experimental Table; Link et al. (2018) Sci Rep 8:120, Supplementary Tables S1/S2, doi:10.1038/s41598-017-18398-4, CC BY 4.0 (credit required).
**Check:** all 52 rows joined to PSI log by test number; linear fit reproduces the paper's trends (faster spread at higher O2 and thinner rods).
**Known issues:** see 'issues' sheet (P15 O2 mismatch, 3 clear rods, 5 ambiguous 1g rows).
