/**
 * Client for the Agnishikha model API (api/server.py), with a static fallback.
 *
 * Live mode: POST {API}/predict/{model} gives a full answer from the trained bundles for any
 * combination of inputs. API defaults to http://127.0.0.1:8000 and is set with
 * NEXT_PUBLIC_IGNIS_API_URL.
 *
 * Precomputed mode: when the API cannot be reached (for example on a static deploy), answers
 * come from /ignis/*.json, written by api/export_static.py from the same trained models. Those
 * files hold one-input-at-a-time sweeps around NASA reference conditions, so in this mode the
 * panel moves one input at a time and resets the others.
 */

export type Scalar = string | number;
export type Inputs = Record<string, Scalar>;

export interface InputSpec {
  name: string;
  label: string;
  unit: string | null;
  default: Scalar;
  type: "number" | "category";
  options?: Scalar[];
  tested_range?: [number, number] | null;
  tested_range_for_default?: [number, number] | null;
  tested_range_by_category?: Record<string, [number, number]>;
}

export interface ModelCard {
  name: string;
  task: "classification" | "regression";
  target: string;
  unit: string | null;
  model: string;
  version: string | null;
  inputs: InputSpec[];
  explanation_groups: string[];
  training_rows: number | null;
  training_groups: number | null;
  validation: Record<string, unknown>;
  valid_for: string;
  source: string;
  classes?: string[];
  threshold?: number;
  base_rate?: number;
  fallback_model?: string;
}

export interface Prediction {
  model: string;
  task: "classification" | "regression";
  target: string;
  probability?: number;
  predicted_class?: string;
  base_rate?: number;
  note?: string;
  prediction?: number;
  unit?: string;
  interval_90?: [number, number];
  in_domain: boolean;
  confidence: string;
  warnings: string[];
  model_used: string;
  base_value?: number;
  contributions?: Record<string, number>;
  inputs: Inputs;
}

interface SweepPoint extends Partial<Prediction> {
  [field: string]: unknown;
}

interface StaticCase {
  category: Scalar | null;
  reference_inputs: Inputs;
  reference: Prediction;
  sweeps: Record<string, { tested_range: [number, number]; points: SweepPoint[] }>;
}

interface StaticModel {
  model: string;
  by_category: string | null;
  cases: StaticCase[];
}

export type Mode = "live" | "precomputed";

export const API_URL = (
  process.env.NEXT_PUBLIC_IGNIS_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const STATIC_BASE = "/ignis";

async function getJson<T>(url: string, init?: RequestInit, timeoutMs = 4000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const outer = init?.signal;
  outer?.addEventListener("abort", () => controller.abort(), { once: true });
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    const body = (await res.json()) as T & { error?: string };
    if (!res.ok) throw new ApiError(body.error ?? `HTTP ${res.status}`, res.status);
    return body;
  } finally {
    clearTimeout(timer);
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

/** Load the model catalog, preferring the live API. */
export async function loadCatalog(): Promise<{ mode: Mode; models: ModelCard[] }> {
  try {
    const live = await getJson<{ models: ModelCard[] }>(`${API_URL}/models`, undefined, 2500);
    return { mode: "live", models: live.models };
  } catch {
    const pre = await getJson<{ models: ModelCard[] }>(`${STATIC_BASE}/catalog.json`);
    return { mode: "precomputed", models: pre.models };
  }
}

export async function predictLive(
  model: string,
  inputs: Inputs,
  signal?: AbortSignal,
): Promise<Prediction> {
  return getJson<Prediction>(
    `${API_URL}/predict/${model}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(inputs),
      signal,
    },
    15000,
  );
}

const staticCache = new Map<string, Promise<StaticModel>>();

function loadStatic(model: string): Promise<StaticModel> {
  let p = staticCache.get(model);
  if (!p) {
    p = getJson<StaticModel>(`${STATIC_BASE}/${model}.json`, undefined, 15000);
    staticCache.set(model, p);
  }
  return p;
}

function sameScalar(a: Scalar | null | undefined, b: Scalar | null | undefined) {
  if (a === b) return true;
  const x = Number(a);
  const y = Number(b);
  return Number.isFinite(x) && Number.isFinite(y) && Math.abs(x - y) < 1e-9;
}

/**
 * Precomputed answer for the input that changed last. Returns the nearest stored point and the
 * inputs it really used, so the panel can show exactly what was computed.
 */
export async function predictPrecomputed(
  card: ModelCard,
  inputs: Inputs,
  changed: string | null,
): Promise<Prediction> {
  const data = await loadStatic(card.name);
  const byCat = data.by_category;
  const kase =
    data.cases.find((c) => !byCat || sameScalar(c.category, inputs[byCat])) ?? data.cases[0];
  const sweep = changed ? kase.sweeps[changed] : undefined;
  if (!changed || !sweep) return { ...kase.reference, inputs: { ...kase.reference_inputs } };
  const target = Number(inputs[changed]);
  let best = sweep.points[0];
  for (const p of sweep.points) {
    if (Math.abs(Number(p[changed]) - target) < Math.abs(Number(best[changed]) - target)) best = p;
  }
  const used: Inputs = { ...kase.reference_inputs, [changed]: Number(best[changed]) };
  return {
    ...kase.reference,
    ...(best as Partial<Prediction>),
    inputs: used,
  } as Prediction;
}

/** Points along one input, for snapping sliders in precomputed mode. */
export async function precomputedSteps(
  card: ModelCard,
  inputs: Inputs,
  field: string,
): Promise<number[]> {
  const data = await loadStatic(card.name);
  const byCat = data.by_category;
  const kase =
    data.cases.find((c) => !byCat || sameScalar(c.category, inputs[byCat])) ?? data.cases[0];
  return (kase.sweeps[field]?.points ?? []).map((p) => Number(p[field]));
}

/** Tested range of an input for the current category (falls back to the overall range). */
export function testedRange(spec: InputSpec, card: ModelCard, inputs: Inputs) {
  const byCat = spec.tested_range_by_category;
  if (byCat) {
    for (const cat of card.inputs.filter((i) => i.type === "category")) {
      const key = Object.keys(byCat).find((k) => sameScalar(k, inputs[cat.name]));
      if (key) return byCat[key];
    }
  }
  return spec.tested_range ?? null;
}
