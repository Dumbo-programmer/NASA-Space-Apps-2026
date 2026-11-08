# Novelty changes (Nov 8, 2026)

**Claim:** NASA's microgravity fire data covers none of the proposed habitat atmosphere (56.5 kPa, 34% O2). AstraFlame maps what is known, what is extrapolated and what is unknown, and recommends the tests that close the gap. ("First" is unverified; use "to our knowledge" or drop it.)

## Findings from the master table (`models/reports/habitat_map.json` → `coverage`)
- 0 of 798 microgravity rows are at or below 70 kPa (lowest 70.2 kPa, 13.7 kPa above the habitat).
- 24 rows reach 30% O2, all FLEX droplets. 0 solids; microgravity solids max out at 22.7% O2.
- 0 rows in the box 30–36% O2 × 45–70 kPa. FLEX methanol model at the habitat point: P(flame goes out) 0.18, flagged as extrapolation.
- Material card: 22 materials, 12 burn at 21% O2, 20 at 34% (headline limit = median of each material's WSTF tests; the 20 holds under min, median, mean and max). Only the two PVC sheets resist 34%.

## Ideas implemented
| Idea | What changed |
|---|---|
| 1 Habitat fire map | New `models/habitat_map.py`; new **Habitat Map** tab (`agnishikha-ui/components/HabitatMapPanel.tsx`) with heat map, NASA test dots, ISS and habitat markers |
| 2 Hardware → model live | `POST /habitat/locate` (`api/ignis_api.py::habitat_locate`) returns the real FLEX answer, distance to nearest NASA test and in/out of range. The tab can poll an ESP32 feed set by `NEXT_PUBLIC_CHAMBER_URL` (JSON `{"pressure_kpa","o2_pct"}`), "Live chamber" button |
| 3 Next-experiment panel | Top 5 recommended tests inside the habitat envelope (O2 ≥ 21%, 45–101 kPa), shown as stars on the map and as a list |
| 4 Material safety card | Table of 22 materials: limit, margin at 34%, burns yes/no, with caveat |
| 5 Scenario switch | ISS / Habitat / Custom (sliders) / Live chamber buttons move the "you are here" dot and re-query the model |
Ideas 6–9 not done (see brief).

## Files
- **New:** `models/habitat_map.py`, `models/reports/habitat_map.json`, `models/reports/material_safety_card.csv`, `agnishikha-ui/components/HabitatMapPanel.tsx`, `agnishikha-ui/public/ignis/habitat_map.json`, this file.
- **Edited:** `api/ignis_api.py` (+`habitat_map`, `habitat_locate`), `api/server.py` (+`GET /habitat`, `POST /habitat/locate`), `api/export_static.py` (copies `habitat_map.json`), `run_pipeline.py` (+`habitat` step), `tests/test_api.py` (+`test_habitat_map_and_locate`), `agnishikha-ui/lib/ignisApi.ts` (+`loadHabitat`, `locateLive`, `readChamber`), `agnishikha-ui/components/TabBar.tsx` and `app/page.tsx` (new tab, footer text), `README.md` (habitat section, **Use of AI** line).

## Verified / not verified
- Verified: `python tests/run_tests.py` → 19 passed (18 existing + 1 new). `habitat_map.py` runs end to end.
- NOT verified: the Next.js UI was not built or run (no node_modules, no network here). Run `npm install && npm run build` in `agnishikha-ui` and fix any type error. The static `habitat_map.json` is ~88 KB.

## Caveats (keep in the video and abstract)
- Heat map = FLEX methanol droplets in microgravity; material markers/card = 1g solids at 70–101 kPa. Different data on shared axes; labelled in the UI.
- 56.5 kPa is below both datasets: first estimate only. "20 of 22 at 8.2 psia" must read "20 of 22 at 34% O2 in 1g, pressure extrapolated" (Purno's approval).
- Next-test rule is uncertainty × distance, not Bayesian design; methanol only.
- Do not physically enrich the chamber with O2; use sensing and the simulated slider.
- Not touched: the old notebook rename, abstract date, video script (open tasks in the brief).