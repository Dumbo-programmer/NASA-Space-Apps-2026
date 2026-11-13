# Changelog: habitat fire map and dashboard redesign

The NASA microgravity fire data used in this project covers none of the proposed habitat atmosphere (56.5 kPa, 34 % O2). These changes add a map of what is known, what is estimated and what is extrapolated, and a list of the tests that would close the gap.

## What the data shows

From `models/reports/habitat_map.json`, section `coverage`:

- 0 of 798 microgravity rows are at or below 70 kPa. The lowest is 70.2 kPa, which is 13.7 kPa above the habitat pressure.
- 24 rows reach 30 % O2, and all are FLEX droplets. Microgravity solids stop at 22.7 % O2.
- 0 rows fall in the box 30–36 % O2 by 45–70 kPa.
- At the habitat point the FLEX methanol model gives P(flame goes out) = 0.18, flagged as an extrapolation.
- Material card: 22 materials, of which 12 burn at 21 % O2 and 20 at 34 % O2. The limit used is the median of each material's WSTF tests; the count of 20 holds under the minimum, median, mean and maximum. Only the two PVC sheets resist 34 % O2.

These counts describe the dataset used here. Saffire V and VI flew reduced-pressure, oxygen-enriched tests that are not in it.

## What was added

| Feature | What changed |
|---|---|
| Habitat fire map | New `models/habitat_map.py`. New **Habitat Map** tab (`agnishikha-ui/components/HabitatMapPanel.tsx`) with a heat map, NASA test dots, and ISS and habitat markers |
| Live chamber reading | `POST /habitat/locate` (`api/ignis_api.py::habitat_locate`) returns the FLEX answer, the distance to the nearest NASA test and whether the point is inside the data. The tab can poll an ESP32 feed set by `NEXT_PUBLIC_CHAMBER_URL` (JSON `{"pressure_kpa", "o2_pct"}`) |
| Next-experiment panel | The five recommended tests inside the habitat envelope (O2 ≥ 21 %, 45–101 kPa), shown on the map and as a list |
| Material safety card | Table of 22 materials: oxygen limit, margin at 34 % O2, burns or not, with the caveat below |
| Scenario switch | ISS, Habitat, Custom (sliders) and Live chamber buttons move the selected point and query the model again |
| Guided tour | A first-run tour of the dashboard, with help tips for the technical terms |
| Themes | Light and dark themes with a switch |
| Docker | Images for the API and the dashboard, `docker-compose.yml`, a development override and `.env.example` |

## Files

- **New:** `models/habitat_map.py`, `models/reports/habitat_map.json`, `models/reports/material_safety_card.csv`, `agnishikha-ui/components/HabitatMapPanel.tsx`, `GuidedTour.tsx`, `HelpTip.tsx`, `ThemeToggle.tsx`, `agnishikha-ui/lib/tourSteps.ts`, `agnishikha-ui/app/theme.css`, `agnishikha-ui/public/ignis/habitat_map.json`, `agnishikha-ui/UI_INVENTORY.md`, `api/Dockerfile`, `agnishikha-ui/Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`.
- **Edited:** `api/ignis_api.py` (`habitat_map`, `habitat_locate`), `api/server.py` (`GET /habitat`, `POST /habitat/locate`), `api/export_static.py` (copies `habitat_map.json`), `run_pipeline.py` (`habitat` step), `tests/test_api.py` (`test_habitat_map_and_locate`), `agnishikha-ui/lib/ignisApi.ts` (`loadHabitat`, `locateLive`, `readChamber`), `agnishikha-ui/components/TabBar.tsx` and `app/page.tsx` (new tab, footer text), `README.md`.

## Dashboard redesign

- `PanelFrame.tsx`: shared card style and readable headings.
- `ScenarioControls.tsx`: restyled control groups, labels, selects and sliders, with 40 px controls.
- `RiskMatrix.tsx`: removed the active-cell glow and added a staggered card grid.
- `ShapExplainability.tsx`: staggered entrance and readable labels.
- `MitigationProtocols.tsx`: removed the critical-card glow and aligned protocol cards and text.
- `NasaModelPanel.tsx`: loading skeleton, a Retry action when the API is offline, restyled tabs and cards, help tips kept.
- `MaterialRiskScoreboard.tsx`: 40 px sort and select controls and consistent table labels.
- `TelemetryCards.tsx`: shared card style, staggered metric cards, alert glow removed.

No new dependencies.

## Checks

- `python tests/run_tests.py`: 19 passed (18 existing and 1 new).
- `models/habitat_map.py` runs end to end and reproduces `habitat_map.json`.
- Guided tour: opens on first load; Next, Back and Skip work; arrow keys and Escape work; keyboard focus stays inside the tour card; steps 3 to 7 switch to the Habitat Map tab; "Take the tour" restarts it; skipping stops it reopening after a reload; at 360 px the card docks to the bottom; reduced-motion settings turn the animation off.
- Every item in `agnishikha-ui/UI_INVENTORY.md` is still present. The mobile Scenario drawer works with no horizontal overflow at 360 px.

## Caveats

- The heat map comes from FLEX methanol droplets in microgravity. The material markers and card come from solids in Earth gravity at 70–101 kPa. They are different data on shared axes, and the dashboard labels them as such.
- 56.5 kPa is below both datasets, so answers there are a first estimate only. "20 of 22" refers to 34 % O2 in Earth gravity, with the pressure extrapolated.
- The next-test rule is uncertainty times distance, not a Bayesian design, and covers methanol only.
- The chamber is never enriched with oxygen. Oxygen is sensed or set with the slider.
