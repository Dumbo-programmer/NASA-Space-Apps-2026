"use client";

import { useEffect, useRef } from "react";
import { REFERENCE_GEOMETRY } from "@/lib/geometry";
import { clamp, clamp01 } from "@/lib/math";
import type { GeometryState } from "@/lib/types";

export interface MicrogravityFlameCanvasProps {
  /** Predicted diffusion flame length, cm. */
  flameLength: number;
  /** Predicted soot inception height, cm. */
  sootPoint: number;
  /** Predicted smoke mass yield, mg/min. */
  smokeYield: number;
  /** Ambient oxygen concentration, vol %. */
  oxygenPct: number;
  /** Ambient pressure, kPa. */
  pressureKpa: number;
  /** Commanded cabin airflow, cm/s. */
  airflowCms: number;
  /** Predicted heat release rate, W. */
  heatReleaseW: number;
  /** Predicted peak flame temperature, K. */
  flameTempK: number;
  /** Probability the fuel self-extinguishes, 0 - 1. */
  extinctionProb: number;
  /** Active specimen name for the rig label. */
  materialName: string;
  /** Emergency ventilation damper state. */
  isVentilationCut: boolean;
  /** Burner and sample geometry drawn on the rig. */
  geometry: GeometryState;
}

type ParticleKind = "ember" | "soot" | "vapor";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  kind: ParticleKind;
  seed: number;
}

const PARTICLE_CAP = 190;
const REDUCED_PARTICLE_CAP = 40;

/** Seconds for the envelope to collapse when the damper is closed. */
const QUENCH_DECAY_SECONDS = 3;
/** Seconds for the envelope to re-establish when the damper is reopened. */
const RECOVERY_SECONDS = 1.4;

/** Blackbody targets required by the visual spec. */
const OXY_RICH_INNER = "#f97316";
const OXY_RICH_OUTER = "#eab308";
const OXY_POOR_INNER = "#3b82f6";
const OXY_POOR_OUTER = "#06b6d4";

function approach(current: number, target: number, maxDelta: number): number {
  if (current < target) return Math.min(target, current + maxDelta);
  if (current > target) return Math.max(target, current - maxDelta);
  return target;
}

function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ];
}

function mixHex(from: string, to: string, t: number): string {
  const a = hexToRgb(from);
  const b = hexToRgb(to);
  const k = clamp01(t);
  const r = Math.round(a[0] + (b[0] - a[0]) * k);
  const g = Math.round(a[1] + (b[1] - a[1]) * k);
  const bl = Math.round(a[2] + (b[2] - a[2]) * k);
  return `rgb(${r}, ${g}, ${bl})`;
}

function mulberry32(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Radial gradient stops derived from ambient oxygen.
 *
 * > 21 % O2  -> hot orange core into yellow envelope (oxidizer enriched)
 * < 16 % O2  -> dim blue / cyan diffusion core (oxygen starved)
 * between    -> continuous blackbody crossfade through the stoich transition
 */
function flamePalette(oxygenPct: number): {
  inner: string;
  outer: string;
  core: string;
  glow: string;
  intensity: number;
} {
  if (oxygenPct >= 21) {
    const enrichment = clamp01((oxygenPct - 21) / 9);
    return {
      inner: OXY_RICH_INNER,
      outer: mixHex(OXY_RICH_OUTER, "#fde047", enrichment),
      core: mixHex("#fff7ed", "#fffbeb", enrichment),
      glow: "rgba(249, 115, 22, 0.30)",
      intensity: 0.86 + 0.14 * enrichment,
    };
  }
  if (oxygenPct <= 16) {
    const starvation = clamp01((16 - oxygenPct) / 4);
    return {
      inner: mixHex("#60a5fa", OXY_POOR_INNER, starvation),
      outer: mixHex("#22d3ee", OXY_POOR_OUTER, starvation),
      core: mixHex("#e0f2fe", "#cffafe", starvation),
      glow: "rgba(6, 182, 212, 0.26)",
      intensity: 0.5 + 0.34 * (1 - starvation),
    };
  }
  const t = clamp01((oxygenPct - 16) / 5);
  return {
    inner: mixHex(OXY_POOR_INNER, OXY_RICH_INNER, t),
    outer: mixHex(OXY_POOR_OUTER, OXY_RICH_OUTER, t),
    core: mixHex("#e0f2fe", "#fff7ed", t),
    glow: `rgba(${Math.round(59 + 190 * t)}, ${Math.round(
      130 - 15 * t,
    )}, ${Math.round(246 - 200 * t)}, 0.28)`,
    intensity: 0.62 + 0.22 * t,
  };
}

export function MicrogravityFlameCanvas({
  flameLength,
  sootPoint,
  smokeYield,
  oxygenPct,
  pressureKpa,
  airflowCms,
  heatReleaseW,
  flameTempK,
  extinctionProb,
  materialName,
  isVentilationCut,
  geometry,
}: MicrogravityFlameCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const latestProps = useRef({
    flameLength,
    sootPoint,
    smokeYield,
    oxygenPct,
    pressureKpa,
    airflowCms,
    heatReleaseW,
    flameTempK,
    extinctionProb,
    materialName,
    isVentilationCut,
    geometry,
  });

  useEffect(() => {
    latestProps.current = {
      flameLength,
      sootPoint,
      smokeYield,
      oxygenPct,
      pressureKpa,
      airflowCms,
      heatReleaseW,
      flameTempK,
      extinctionProb,
      materialName,
      isVentilationCut,
      geometry,
    };
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const particleCap = prefersReducedMotion ? REDUCED_PARTICLE_CAP : PARTICLE_CAP;

    let width = 640;
    let height = 360;
    let frameHandle = 0;
    let lastTime = 0;
    let quench = latestProps.current.isVentilationCut ? 1 : 0;
    let spawnAccumulator = 0;
    const random = mulberry32(0x41535452);

    const particles: Particle[] = [];

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(240, rect.width);
      height = Math.max(220, rect.height);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();

    const spawnParticle = (
      coreX: number,
      coreY: number,
      radiusX: number,
      radiusY: number,
      smokeFactor: number,
      airflowNorm: number,
    ) => {
      const roll = random();
      const kind: ParticleKind =
        roll < 0.34 ? "ember" : roll < 0.34 + 0.42 * smokeFactor ? "soot" : "vapor";
      const angle = random() * Math.PI * 2;
      const radial = Math.sqrt(random());
      const maxLife = kind === "ember" ? 0.5 + random() * 0.7 : 1.6 + random() * 2.6;
      particles.push({
        x: coreX + Math.cos(angle) * radiusX * radial,
        y: coreY + Math.sin(angle) * radiusY * radial * 0.55,
        vx: 6 + airflowNorm * 40 * (0.4 + random()),
        vy: -6 - random() * 16,
        life: maxLife,
        maxLife,
        size:
          kind === "ember"
            ? 0.9 + random() * 1.5
            : kind === "soot"
              ? 1.6 + random() * 3.2
              : 5 + random() * 9,
        kind,
        seed: random() * Math.PI * 2,
      });
    };

    const drawEnclosure = () => {
      ctx.fillStyle = "#03060e";
      ctx.fillRect(0, 0, width, height);

      const cell = 32;
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.05)";
      ctx.beginPath();
      for (let x = cell; x < width; x += cell) {
        ctx.moveTo(x + 0.5, 0);
        ctx.lineTo(x + 0.5, height);
      }
      for (let y = cell; y < height; y += cell) {
        ctx.moveTo(0, y + 0.5);
        ctx.lineTo(width, y + 0.5);
      }
      ctx.stroke();

      ctx.strokeStyle = "rgba(148, 163, 184, 0.16)";
      ctx.strokeRect(width * 0.08 + 0.5, height * 0.1 + 0.5, width * 0.84, height * 0.78);

      ctx.strokeStyle = "rgba(148, 163, 184, 0.1)";
      ctx.beginPath();
      for (let x = width * 0.08; x <= width * 0.92; x += width * 0.14) {
        ctx.moveTo(x + 0.5, height * 0.1);
        ctx.lineTo(x + 0.5, height * 0.88);
      }
      ctx.stroke();

      const horizon = height * 0.74;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.09)";
      ctx.beginPath();
      for (let i = -6; i <= 6; i += 1) {
        ctx.moveTo(width / 2, horizon);
        ctx.lineTo(width / 2 + i * width * 0.16, height);
      }
      for (let i = 1; i <= 5; i += 1) {
        const y = horizon + (height - horizon) * (i / 5) ** 1.7;
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();

      ctx.strokeStyle = "rgba(148, 163, 184, 0.28)";
      ctx.lineWidth = 1.5;
      const bracket = 16;
      ctx.beginPath();
      ctx.moveTo(12, 12 + bracket);
      ctx.lineTo(12, 12);
      ctx.lineTo(12 + bracket, 12);
      ctx.moveTo(width - 12 - bracket, 12);
      ctx.lineTo(width - 12, 12);
      ctx.lineTo(width - 12, 12 + bracket);
      ctx.moveTo(12, height - 12 - bracket);
      ctx.lineTo(12, height - 12);
      ctx.lineTo(12 + bracket, height - 12);
      ctx.moveTo(width - 12 - bracket, height - 12);
      ctx.lineTo(width - 12, height - 12);
      ctx.lineTo(width - 12, height - 12 - bracket);
      ctx.stroke();
    };

    /** Reference burner (25 mm) is drawn 46 px wide, so this is px per mm. */
    const PX_PER_MM = 1.84;

    const drawRig = (anchorY: number) => {
      const g = latestProps.current.geometry ?? REFERENCE_GEOMETRY;
      const rigWidth = Math.min(width * 0.46, 320);
      const rigLeft = width / 2 - rigWidth / 2;

      ctx.fillStyle = "rgba(30, 41, 59, 0.9)";
      ctx.fillRect(rigLeft, anchorY, rigWidth, 10);
      ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
      ctx.lineWidth = 1;
      ctx.strokeRect(rigLeft + 0.5, anchorY + 0.5, rigWidth, 10);

      const burnerWidth = clamp(g.burnerDiameterMm * PX_PER_MM, 12, width * 0.4);
      ctx.fillStyle = "rgba(71, 85, 105, 0.95)";
      ctx.fillRect(width / 2 - burnerWidth / 2, anchorY + 10, burnerWidth, height * 0.1);
      ctx.strokeRect(
        width / 2 - burnerWidth / 2 + 0.5,
        anchorY + 10.5,
        burnerWidth,
        height * 0.1,
      );

      ctx.fillStyle = "rgba(248, 250, 252, 0.06)";
      ctx.fillRect(rigLeft + 6, anchorY - 3, rigWidth - 12, 3);

      // Free-floating sample, drawn at the commanded geometry and orientation.
      const sampleW = clamp(g.sampleWidthMm * PX_PER_MM, 14, width * 0.5);
      const sampleH = clamp(g.sampleThicknessMm * PX_PER_MM, 4, 44);
      ctx.save();
      ctx.translate(width / 2, anchorY - sampleH / 2 - 1);
      ctx.rotate((-g.orientationDeg * Math.PI) / 180);
      ctx.fillStyle = "rgba(251, 191, 36, 0.28)";
      ctx.strokeStyle = "rgba(251, 191, 36, 0.7)";
      ctx.lineWidth = 1;
      ctx.fillRect(-sampleW / 2, -sampleH / 2, sampleW, sampleH);
      ctx.strokeRect(-sampleW / 2 + 0.5, -sampleH / 2 + 0.5, sampleW, sampleH);
      ctx.restore();

      ctx.font = "600 10px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillStyle = "rgba(148, 163, 184, 0.85)";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(
        `SAMPLE: ${latestProps.current.materialName.toUpperCase()}`,
        width / 2,
        anchorY + 16 + height * 0.1,
      );

      ctx.font = "500 9px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
      ctx.textBaseline = "bottom";
      ctx.fillText(
        `burner ${g.burnerDiameterMm.toFixed(0)} mm · sample ${g.sampleWidthMm.toFixed(0)}×${g.sampleThicknessMm.toFixed(1)} mm · ${g.orientationDeg.toFixed(0)}°`,
        width / 2,
        anchorY - 4,
      );
    };

    const drawAirflow = (airflowNorm: number, suppressed: number) => {
      if (airflowNorm <= 0.01) return;
      const alpha = (0.05 + 0.22 * airflowNorm) * (1 - suppressed);
      ctx.strokeStyle = `rgba(167, 139, 250, ${alpha})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = 0; i < 7; i += 1) {
        const y = height * 0.16 + i * ((height * 0.52) / 6);
        const startX = width * (0.08 + (i % 2) * 0.02);
        const length = width * 0.3 * (0.6 + airflowNorm);
        ctx.moveTo(startX, y);
        ctx.lineTo(Math.min(startX + length, width * 0.42), y + 2);
      }
      ctx.stroke();

      ctx.font = "500 9px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillStyle = `rgba(167, 139, 250, ${0.35 + 0.4 * airflowNorm})`;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(
        suppressed > 0.5 ? "DAMPER CLOSED" : `FORCED CONVECTION ${(airflowNorm * 50).toFixed(1)} cm/s`,
        width * 0.09,
        height * 0.12,
      );
    };

    const drawFlame = (
      coreX: number,
      anchorY: number,
      radiusX: number,
      radiusY: number,
      palette: ReturnType<typeof flamePalette>,
      presence: number,
    ) => {
      const coreY = anchorY - radiusY * 0.92;

      ctx.save();
      ctx.globalCompositeOperation = "lighter";

      const glowRadius = radiusX * 3.1;
      const glow = ctx.createRadialGradient(
        coreX,
        coreY,
        radiusX * 0.15,
        coreX,
        coreY,
        glowRadius,
      );
      glow.addColorStop(0, palette.glow);
      glow.addColorStop(0.45, palette.glow.replace(/[\d.]+\)$/, "0.08)"));
      glow.addColorStop(1, "rgba(2, 6, 23, 0)");
      ctx.globalAlpha = presence * 0.85;
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(coreX, coreY, glowRadius, 0, Math.PI * 2);
      ctx.fill();

      const envelope = ctx.createRadialGradient(
        coreX,
        coreY,
        0,
        coreX,
        coreY,
        Math.max(radiusX, 1),
      );
      envelope.addColorStop(0, palette.core);
      envelope.addColorStop(0.28, palette.inner);
      envelope.addColorStop(0.72, palette.outer);
      envelope.addColorStop(1, "rgba(15, 23, 42, 0)");
      ctx.globalAlpha = presence * palette.intensity;
      ctx.fillStyle = envelope;
      ctx.beginPath();
      ctx.ellipse(coreX, coreY, Math.max(radiusX, 0.5), Math.max(radiusY, 0.5), 0, 0, Math.PI * 2);
      ctx.fill();

      const coreRadius = Math.max(radiusX * 0.34, 0.5);
      const core = ctx.createRadialGradient(
        coreX,
        coreY - radiusY * 0.12,
        0,
        coreX,
        coreY - radiusY * 0.12,
        coreRadius,
      );
      core.addColorStop(0, "#ffffff");
      core.addColorStop(0.6, palette.core);
      core.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.globalAlpha = presence * clamp01(palette.intensity + 0.12);
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.ellipse(
        coreX,
        coreY - radiusY * 0.12,
        coreRadius,
        coreRadius * 0.86,
        0,
        0,
        Math.PI * 2,
      );
      ctx.fill();

      ctx.restore();

      ctx.font = "500 10px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillStyle = `rgba(226, 232, 240, ${0.35 + 0.4 * presence})`;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(
        `${latestProps.current.flameLength.toFixed(1)} cm`,
        coreX + radiusX + 12,
        coreY,
      );
    };

    const drawParticles = (
      dt: number,
      airflowNorm: number,
      time: number,
    ) => {
      ctx.save();
      for (let i = particles.length - 1; i >= 0; i -= 1) {
        const p = particles[i];
        const freeStream = 12 + airflowNorm * 150;
        p.vx += (freeStream - p.vx) * 1.6 * dt;
        p.vy += (-5 - p.vy) * 0.5 * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt + Math.sin(p.seed + time * 0.0016) * 6 * dt;
        p.life -= dt;

        if (p.life <= 0 || p.x > width + 40 || p.y < -40 || p.y > height + 40) {
          particles.splice(i, 1);
          continue;
        }

        const decay = clamp01(p.life / p.maxLife);
        if (p.kind === "ember") {
          ctx.globalCompositeOperation = "lighter";
          ctx.fillStyle = `rgba(253, 224, 71, ${0.55 * decay})`;
        } else if (p.kind === "soot") {
          ctx.globalCompositeOperation = "source-over";
          ctx.fillStyle = `rgba(30, 34, 44, ${0.5 * decay})`;
        } else {
          ctx.globalCompositeOperation = "source-over";
          ctx.fillStyle = `rgba(120, 132, 152, ${0.14 * decay})`;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    };

    const drawHud = (
      anchorY: number,
      radiusY: number,
      palette: ReturnType<typeof flamePalette>,
      presence: number,
    ) => {
      const p = latestProps.current;
      ctx.font = "500 10px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";

      const lines = [
        `O₂ ${p.oxygenPct.toFixed(1)} %`,
        `P ${p.pressureKpa.toFixed(1)} kPa`,
        `T ${p.flameTempK} K`,
        `HRR ${p.heatReleaseW.toFixed(1)} W`,
        `SMOKE ${p.smokeYield.toFixed(1)} mg/min`,
      ];
      ctx.fillStyle = "rgba(148, 163, 184, 0.8)";
      lines.forEach((line, index) => {
        ctx.fillText(line, width * 0.09, height * 0.86 + index * 13);
      });

      const sootCm = p.sootPoint.toFixed(1);
      ctx.textAlign = "right";
      ctx.fillStyle = "rgba(203, 213, 225, 0.75)";
      ctx.fillText(`SOOT INCEPTION ${sootCm} cm`, width * 0.91, height * 0.86);

      const margin = 16;
      const scaleTop = anchorY - radiusY * 2.1;
      const scaleBottom = anchorY - radiusY * 0.2;
      ctx.strokeStyle = "rgba(148, 163, 184, 0.45)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(width * 0.91 - margin, scaleTop);
      ctx.lineTo(width * 0.91 - margin, scaleBottom);
      ctx.moveTo(width * 0.91 - margin - 4, scaleTop);
      ctx.lineTo(width * 0.91 - margin + 4, scaleTop);
      ctx.moveTo(width * 0.91 - margin - 4, scaleBottom);
      ctx.lineTo(width * 0.91 - margin + 4, scaleBottom);
      ctx.stroke();

      ctx.save();
      ctx.translate(width * 0.91 - margin - 9, (scaleTop + scaleBottom) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(148, 163, 184, 0.85)";
      ctx.font = "500 9px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillText(
        `${p.flameLength.toFixed(1)} cm ENVELOPE`,
        0,
        0,
      );
      ctx.restore();

      const status =
        p.isVentilationCut && presence < 0.35
          ? { label: "FLAME QUENCHED", color: "rgba(248, 250, 252, 0.92)" }
          : p.extinctionProb > 0.6
            ? { label: "NO IGNITION · BELOW EXTINCTION LIMIT", color: "rgba(125, 211, 252, 0.92)" }
            : p.extinctionProb > 0.3
              ? { label: "MARGINAL FLAME · SELF-EXTINGUISHING", color: "rgba(252, 211, 77, 0.92)" }
              : { label: "PROPAGATING DIFFUSION FLAME", color: "rgba(134, 239, 172, 0.92)" };

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = "700 11px ui-monospace, SFMono-Regular, Menlo, monospace";
      const badgeWidth = ctx.measureText(status.label).width + 22;
      ctx.fillStyle = "rgba(2, 6, 23, 0.72)";
      ctx.fillRect(width / 2 - badgeWidth / 2, height * 0.055, badgeWidth, 20);
      ctx.strokeStyle = palette.outer.replace("rgb", "rgba").replace(")", ", 0.35)");
      ctx.strokeRect(width / 2 - badgeWidth / 2 + 0.5, height * 0.055 + 0.5, badgeWidth, 20);
      ctx.fillStyle = status.color;
      ctx.fillText(status.label, width / 2, height * 0.055 + 11);
    };

    const drawQuenchOverlay = (coreX: number, coreY: number) => {
      if (quench <= 0.02) return;

      ctx.save();
      ctx.fillStyle = `rgba(2, 6, 23, ${0.5 * quench})`;
      ctx.fillRect(0, 0, width, height);

      if (quench > 0.42) {
        const fade = clamp01((quench - 0.42) / 0.4);
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.font = "800 20px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillStyle = `rgba(248, 250, 252, ${0.15 + 0.8 * fade})`;
        ctx.fillText("FLAME QUENCHED", coreX, coreY - 8);

        ctx.font = "600 12px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillStyle = `rgba(253, 186, 116, ${0.1 + 0.75 * fade})`;
        ctx.fillText("PASSIVE EXTINCTION", coreX, coreY + 14);

        ctx.strokeStyle = `rgba(248, 250, 252, ${0.12 * fade})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(coreX - 120, coreY + 3);
        ctx.lineTo(coreX + 120, coreY + 3);
        ctx.stroke();

        ctx.font = "500 10px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillStyle = `rgba(148, 163, 184, ${0.1 + 0.6 * fade})`;
        ctx.fillText(
          "O₂ DELIVERY TO FLAME ZONE SUSPENDED · T < 900 K",
          coreX,
          coreY + 30,
        );
      }
      ctx.restore();
    };

    const frame = (time: number) => {
      frameHandle = window.requestAnimationFrame(frame);

      const dt = lastTime === 0 ? 1 / 60 : Math.min((time - lastTime) / 1000, 0.05);
      lastTime = time;

      const p = latestProps.current;
      const activeAirflow = p.isVentilationCut ? 0 : p.airflowCms;
      const airflowNorm = clamp01(activeAirflow / 50);
      const smokeFactor = clamp01(p.smokeYield / 80);
      const palette = flamePalette(p.oxygenPct);

      // Quench transient: 3 s collapse, faster re-establishment on restore.
      const target = p.isVentilationCut ? 1 : 0;
      const rate =
        target > quench
          ? dt / QUENCH_DECAY_SECONDS
          : dt / RECOVERY_SECONDS;
      quench = approach(quench, target, rate);

      const presence =
        clamp01(1 - p.extinctionProb * 0.85) * (1 - 0.92 * quench);

      const anchorY = height * 0.74;
      const o2Norm = clamp01((p.oxygenPct - 12) / 9);
      const lengthNorm = clamp(p.flameLength / 12, 0, 2.2);
      const flicker = prefersReducedMotion
        ? 1
        : 1 +
          0.06 * Math.sin(time * 0.011) +
          0.04 * Math.sin(time * 0.0071 + 1.7) +
          0.03 * Math.sin(time * 0.0179 + 0.4);

      const baseRadius =
        height *
        0.14 *
        (0.45 + 0.55 * o2Norm) *
        (0.35 + 0.65 * lengthNorm) *
        flicker;

      const stretch = 1 + airflowNorm * 1.6;
      const lift = 1 + airflowNorm * 0.35;

      const radiusX = clamp(baseRadius * stretch * (1 - 0.97 * quench), 0, width * 0.46);
      const radiusY = clamp(baseRadius * lift * (1 - 0.97 * quench), 0, height * 0.46);
      const coreX = width / 2;
      const coreY = anchorY - radiusY * 0.92;

      // Full frame clear prevents frame-buffer accumulation and stale trails.
      ctx.clearRect(0, 0, width, height);
      drawEnclosure();
      drawAirflow(airflowNorm, quench);
      drawRig(anchorY);

      if (radiusX > 0.6 && radiusY > 0.6) {
        drawFlame(coreX, anchorY, radiusX, radiusY, palette, presence);
      }

      const spawnRate = 70 * presence * (0.35 + 0.65 * smokeFactor);
      spawnAccumulator += spawnRate * dt;
      while (spawnAccumulator >= 1 && particles.length < particleCap) {
        spawnAccumulator -= 1;
        spawnParticle(
          coreX,
          coreY,
          Math.max(radiusX, 2),
          Math.max(radiusY, 2),
          smokeFactor,
          airflowNorm,
        );
      }
      if (particles.length > particleCap) {
        particles.splice(0, particles.length - particleCap);
      }

      drawParticles(dt, airflowNorm, time);
      drawHud(anchorY, Math.max(radiusY, 4), palette, presence);
      drawQuenchOverlay(coreX, anchorY - height * 0.16);
    };

    frameHandle = window.requestAnimationFrame(frame);

    return () => {
      window.cancelAnimationFrame(frameHandle);
      observer.disconnect();
      particles.length = 0;
    };
  }, []);

return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div
        ref={containerRef}
        className="relative min-h-0 w-full flex-1 overflow-hidden rounded-lg border border-slate-800/80 bg-slate-950 shadow-inner shadow-black/50"
      >
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={`Microgravity flame visualization for ${materialName}: predicted flame length ${flameLength.toFixed(1)} centimetres, soot inception at ${sootPoint.toFixed(1)} centimetres, ${oxygenPct.toFixed(1)} percent oxygen, ${airflowCms.toFixed(1)} centimeters per second airflow, ${flameTempK.toFixed(0)} kelvin${isVentilationCut ? ", ventilation damper isolated" : ""}`}
          className="block h-full w-full"
        />
        {isVentilationCut ? (
          <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-center">
            <span className="animate-drop-in mt-2 rounded-full border border-red-500/60 bg-red-600/20 px-3 py-0.5 font-mono text-[10px] font-bold uppercase tracking-widest text-red-200 backdrop-blur-sm">
              Ventilation Isolated
            </span>
          </div>
        ) : null}
      </div>
      <p className="shrink-0 font-mono text-[10px] leading-relaxed text-slate-400">
        Radius scales with predicted envelope length and ambient O₂. Radial gradient
        follows blackbody targets: orange→yellow above 21 % O₂, blue→cyan below 16 %
        O₂. Particles shear along +X with commanded airflow; the emergency damper
        drives a 3 s collapse to passive extinction.
      </p>
    </div>
  );
}
