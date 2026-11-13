# AstraFlame UI inventory

Checklist for the visible UI before the redesign steps.

## Header

- [x] Product name: AstraFlame
- [x] Product mark: Agnishikha
- [x] Mission context: ISS Columbus · µg
- [x] Training envelope: envelope 21–36 % O₂
- [x] Data status: PSI surrogate v2.4 · offline
- [x] Status pill: Surrogate · offline
- [x] Status pill: KB2 · TEGEL · 30 Hz
- [x] Specimen label and active material name
- [x] Button: Cut ventilation
- [x] Alternate button label: Ventilation isolated · restore

## Tabs

- [x] Button: Scenario
- [x] Tab: Simulation (short label: Flame)
- [x] Tab: Risk Matrix (short label: Risk)
- [x] Tab: Explainability (short label: Why)
- [x] Tab: NASA Models (short label: Models)
- [x] Tab: Habitat Map (short label: Map)
- [x] Tab: Protocols (short label: Action)
- [x] Keyboard navigation: ArrowLeft and ArrowRight move between tabs

## Left controls panel

- [x] Scenario controls heading
- [x] Experiment selector and experiment names
- [x] Material selector and material names
- [x] Oxygen slider and percentage readout
- [x] Pressure slider and kPa readout
- [x] Airflow slider and cm/s readout
- [x] Geometry controls and geometry factor
- [x] Droplet diameter / geometry readouts
- [x] Ventilation control
- [x] Mobile button: Scenario
- [x] Mobile drawer button: Close scenario controls
- [x] Warning or out-of-domain messages for values outside the training envelope

## Simulation tab

- [x] Panel: Microgravity Flame Visualizer
- [x] Subtitle: Canvas rAF loop · 190-particle envelope · model-driven
- [x] Status: Damper open / Damper closed
- [x] Panel: Required Metric Telemetry
- [x] Subtitle: Five PSI-traceable readouts · surrogate inference
- [x] Status: In-domain / Out-of-domain
- [x] Telemetry readouts: flame length, soot point, smoke yield, heat release, flame temperature, extinction probability
- [x] Units: mm, mg/min, W, K, %, cm/s

## Risk Matrix tab

- [x] Panel: Material Flammability Risk Scoreboard
- [x] Subtitle: Traceable registry · sortable · active specimen highlighted
- [x] Sortable material table
- [x] Columns: material, spread rate, extinction limit, smoke yield, peak flame temperature, pyrolysis heat, fuel load
- [x] Units: mm/s, %, mg/min, K
- [x] Panel: Risk Matrix
- [x] Subtitle: Likelihood vs consequence
- [x] Axes: likelihood and consequence
- [x] Risk bands: LOW, GUARDED, MODERATE, HIGH, SEVERE
- [x] Values: Likelihood, Consequence, Band, Risk index, percentage
- [x] Warning/caveat: presentational mapping of the surrogate, not a calibrated FMEA scoring scheme
- [x] Panel: Specimen Engineering Note
- [x] Subtitle: Registry note for the active fuel

## Explainability tab

- [x] Panel: AI SHAP Explainability
- [x] Subtitle: Feature contribution drivers · exact additive attribution
- [x] Dominant driver badges
- [x] Feature contribution chart and values
- [x] Units: mm/s
- [x] Explanation: nominal-vs-active delta, not a validation residual
- [x] Footer labels: Exact additive · ordered ablation; Shares sum 100 %

## NASA Models tab

- [x] Panel: NASA-trained models
- [x] Subtitle: Real predictions with 90% ranges, tested-range warnings and exact Shapley values
- [x] Status: 5 models · 4 ISS investigations
- [x] API status: Live · Python API / Precomputed · same trained models
- [x] Status: computing
- [x] Loading state: skeleton for NASA-trained models
- [x] Offline warning: API error, startup instruction, and Retry button
- [x] Model cards, model names, predictions, 90% ranges, confidence and tested-range warnings
- [x] Model card label and Valid for text
- [x] Button: Retry

## Habitat Map tab

- [x] Panel: Habitat fire map
- [x] Subtitle: The NASA tests in our data, what the model says, where the habitat sits, what to test next
- [x] Status: Real FLEX model · WSTF limits
- [x] Heading: 1. Pick an atmosphere
- [x] Buttons: ISS, Habitat, Custom, Live chamber
- [x] Oxygen and pressure sliders with values
- [x] Status: No chamber connected yet.
- [x] Heading: 2. See where it sits on the map
- [x] Map labels: Lowest test in our data, Space Station, Habitat, selected
- [x] Axis labels: Oxygen in the air (%), Air pressure (kPa)
- [x] Legend: Flame goes out by itself; Flame keeps burning; Faded: far from any NASA test (a guess); A past NASA space test; A–E: best next tests
- [x] Caveat: map colors are methanol-droplet model data; material results are Earth-gravity data
- [x] Heading: 3. What should NASA test next?
- [x] Recommended tests A–E with oxygen, pressure and flame-out probability
- [x] Material safety table: Material, Stops burning below (% oxygen), Result at 34%
- [x] Live answer and extrapolation/in-domain status

## Protocols tab

- [x] Panel: Mission Fire Mitigation Protocols
- [x] Subtitle: Actionable crew directives generated from the active case
- [x] Status: Crew-facing · advisory only
- [x] Protocol severity/status labels
- [x] Crew directives and rationale
- [x] Fan reduction percentage
- [x] Envelope decay seconds
- [x] Advisory/warning text

## Footer

- [x] Text: Team Agnishikha · AstraFlame · NASA Space Apps 2026
- [x] Text: NASA Models and Habitat Map tabs: trained on NASA PSI data
- [x] Text: other tabs: client-side surrogate
- [x] Link: NASA PSI (`https://psi.nasa.gov`)
- [x] Link labels and external-link icon
