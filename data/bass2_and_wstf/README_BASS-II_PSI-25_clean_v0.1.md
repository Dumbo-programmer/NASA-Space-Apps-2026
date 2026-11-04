# BASS-II_PSI-25_clean_v0.1 (CSV / XLSX)
**Source:** NASA PSI-25, BASS-II Experimental Table (ISS, 2014). 129 tests, 6 PI groups.
**What it is:** cleaned test log. Raw text kept; parsed columns added; quality flags added.

**Inputs available:** PI, test/sample IDs, material (parsed + raw), geometry, thickness_mm, width_cm, diameter_mm, rod_color, burning_sides, flow_restrictor, air/fan settings (raw + first value), O2 / CO2 / CO before and after.
**Outputs available:** none as a model target. Derived deltas (O2 used, CO2/CO made) are in the gas-response file.
**Missing:** flame spread rate, measured extinction flow, flame length, pressure, units of air/fan settings.
**Where to get missing outputs:** see Ignis_mu_Data_Map_v0.1.xlsx → Missing_Sources (Link et al. 2018 Table S1 first).
**Value type:** observed (test log). Rows with `quality_flags` must be checked before use.
