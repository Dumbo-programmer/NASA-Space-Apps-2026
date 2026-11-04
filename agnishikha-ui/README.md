# Agnishikha // AstraFlame

NASA Space Apps Challenge Mission Control dashboard for **microgravity flammability**.
Single-page, dark-mode, fully interactive. All inference runs client-side against a
mocked PSI telemetry model, so the dashboard is functional before any backend or
ESP32 hardware is wired up.

## Stack

- Next.js 16 (App Router) + React 19
- TypeScript (strict, `noUnusedLocals` / `noUnusedParameters`)
- Tailwind CSS v4 (`@import "tailwindcss"` plus a small `@theme` block that registers the
  animation utilities in `app/globals.css`)
- lucide-react icons

## Run

```bash
npm install
npm run dev        # http://localhost:3000
```

```bash
npm run typecheck  # tsc --noEmit
npm run lint       # eslint
npm run build      # next build
npm start          # serve the production build
```

## Layout

The shell is a single `h-dvh` viewport with `overflow-hidden`, so the page itself never
scrolls. Content is split across four tabs, and the scenario rail is a fixed sidebar on
desktop (`xl`+) or a slide-over drawer below that.

| File | Role |
| --- | --- |
| `app/page.tsx` | Client root. Owns environment + simulation + tab state, memoizes predictor / SHAP / protocol builders, renders the active tab inside the viewport-locked shell. |
| `app/globals.css` | `@theme` keyframes: `rise-in`, `drop-in`, `fade-in`, `ping-slow`, `sweep`, `flicker`; layered console background, slim scrollbars, `:focus-visible` ring, `.range-control` slider skin. All honors `prefers-reduced-motion`. |
| `app/layout.tsx` | Metadata, dark root, body shell. |
| `components/MissionHeader.tsx` | Title, active-case summary, ESP32 status badge, emergency ventilation damper toggle. |
| `components/TabBar.tsx` | Simulation / Risk / Explainability / Protocols tabs plus the mobile controls toggle. |
| `components/ScenarioControls.tsx` | Rail: experiment preset, fuel specimen, cabin atmosphere sliders, rig geometry sliders. |
| `components/MicrogravityFlameCanvas.tsx` | Panel 1. `useRef` + `useEffect` `requestAnimationFrame` canvas: enclosure grid, spherical flame core, blackbody gradient, airflow shear, 3 s quench transient, rig drawn at the commanded geometry. |
| `components/TelemetryCards.tsx` | Panel 2. Five animated metric readouts, in/out-of-domain banner, confidence and risk meters. |
| `components/MaterialRiskScoreboard.tsx` | Panel 3. Sortable registry, active-row highlight, `psi.nasa.gov` source badge per row. |
| `components/RiskMatrix.tsx` | Panel 3b. 5 × 5 likelihood/consequence grid with the live cell highlighted. |
| `components/ShapExplainability.tsx` | Panel 4. Staggered contribution bars, additive `f(base) → f(x)` readout, similar NASA campaigns, model-vs-registry comparison, damper context-switch note. |
| `components/MitigationProtocols.tsx` | Panel 5. Airflow shutdown, suppressant budget, smoke trajectory, each with ordered crew action steps. |
| `components/PanelFrame.tsx` | Shared panel chrome (`className` / `bodyClassName`), `SubCard` nested surface, and `Pill` badge. |
| `hooks/useAnimatedNumber.ts` | Eased numeric readout that snaps instantly under reduced motion. |
| `lib/types.ts` | Shared interfaces (`EnvironmentState`, `GeometryState`, `Telemetry`, `MaterialRecord`). |
| `lib/axes.ts` | Slider limits plus the nominal value used for the off-nominal tick mark. |
| `lib/math.ts` | `clamp`, `clamp01`, `round`, `signed`. |
| `lib/geometry.ts` | Reference geometry, deviation readout, and the geometry scaling factor. |
| `lib/experiments.ts` | Published NASA campaign presets (BASS-II, FLEX, SAFFIRE-I, SAME, custom). |
| `lib/materials.ts` | Flammability registry for PMMA, Nomex, silicone, polyethylene, methanol. |
| `lib/telemetry.ts` | Input envelope, predictor, confidence banding, readiness verdict. |
| `lib/shap.ts` | Global importances + exact ordered-ablation attribution. |
| `lib/protocols.ts` | Mission directive builders. |

## Model notes

`predictTelemetry()` is a deterministic surrogate, not a CFD solve. It couples:

- **combustion vigor** — `((O₂ − material extinction limit) / 8.5)^0.75`, so a low-LOI
  fuel such as methanol is far more ignitable than an aramid at the same 21 % O₂.
- **pressure factor** — parabola peaking just below 1 atm, decaying toward the vacuum
  limit and the high-pressure regime.
- **airflow factor** — forced convection feeds the reaction zone and stretches the
  envelope; above 44 cm/s a blowback penalty raises extinction probability.
- **damper factor** — an open damper starves the flame of convective O₂ (×0.55) and
  is reported separately from the four SHAP regression features.
- **geometry factor** — burner/sample dimensions scale the spread output through an
  explicit operator term in `lib/geometry.ts`, pinned to exactly `1.0` at the BASS-II
  reference geometry so the calibration case is unchanged. It is a stated scaling
  assumption, not a fitted response.

Picking a campaign in the rail loads that experiment's published conditions
(material, O₂, pressure, airflow, reference geometry) rather than an arbitrary
scenario.

`confidenceBand` is `LIMITED` whenever O₂ leaves the 12–25 % NASA validated training
envelope, `HIGH` at ≥ 82 % smoothed confidence inside it, `MODERATE` at ≥ 58 %.

The SHAP panel uses an **ordered ablation**: each feature is relaxed from its
calibration value to the active value in a fixed order and the marginal change in `f`
is recorded as that feature's φ, so the four terms sum exactly to `f(x) − f(base)`.
At the calibration state (PMMA, 21 % O₂, 101.3 kPa, 10 cm/s) the importance shares
render as exactly 42 / 28 / 18 / 12 %.

## What the model does not claim

- The **damper factor is a heuristic context switch**, not a regression feature. The PSI
  target set contains no airflow-dependent measured spread targets, so the suppressed
  rate shown with the damper closed is not experimentally validated. The Explainability
  panel says this inline.
- The **risk matrix is presentational**: it bins the composite risk index against
  propagation front speed. It is not a calibrated FMEA scoring scheme.
- The **"Model vs registry mean"** card compares real PSI campaign means (spread, soot
  yield, peak flame temperature) against the surrogate's prediction for the *active*
  case. Those means were recorded at 21 % O₂ / 101.3 kPa in still air, so the gap is a
  nominal-vs-active delta, not a model validation residual. The two coincide only at
  the calibration case.
- **"Similar NASA campaigns"** ranks the published campaigns by a weighted distance
  across the same four-feature space that sets the importance shares, using each
  campaign's published conditions. 100 % means the active case sits exactly on that
  campaign; the score is model proximity, not experimental agreement.

## Hardware hookup

The header badge reports `Surrogate · offline` — inference is mocked client-side. To bind
live telemetry, replace `environment` / `simulation` in `app/page.tsx` with a WebSocket or
SSE subscription and push incoming samples through the same setters — every panel is a pure
function of that state, and `geometry` rides along on the same payload.

## Accessibility

- Every control is labelled and keyboard reachable; sort headers expose `aria-sort`, range
  inputs expose `aria-valuetext` with units, and material rows are real buttons.
- Tabs use `tablist` / `tab` / `tabpanel` with roving tabindex and arrow-key navigation;
  readiness changes announce through a polite `role="status"` live region.
- The mobile scenario drawer is a `role="dialog"` with `aria-modal`, Escape-to-close and
  namespaced element ids so it never collides with the desktop rail.
- Canvas carries a text `aria-label` describing the active case, and the risk matrix
  mirrors its cell band on the same 0–100 scale screen readers hear.
- All transitions collapse to instant state changes under `prefers-reduced-motion`.
  The canvas `requestAnimationFrame` flame loop is deliberately excluded, since that
  animation carries the combustion physics rather than decoration.
- Panels scroll internally rather than growing the page, so the dashboard stays on one
  screen from laptop to ultrawide.
