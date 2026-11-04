"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Eases a displayed number toward a new target so telemetry readouts and risk
 * meters animate instead of snapping when a slider moves. Resolves to the
 * target immediately when the operator has reduced-motion enabled.
 *
 * The target is only ever committed from inside a rAF callback, never
 * synchronously in the effect body, to avoid cascading renders.
 */
export function useAnimatedNumber(
  target: number,
  decimals = 1,
  durationMs = 420,
): number {
  const [display, setDisplay] = useState(target);
  const currentRef = useRef(target);
  const frameRef = useRef(0);

  useEffect(() => {
    if (!Number.isFinite(target)) return;

    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const from = reduced ? target : currentRef.current;
    const start = performance.now();

    const tick = (now: number) => {
      const progress = reduced ? 1 : Math.min(1, (now - start) / durationMs);
      const eased = 1 - (1 - progress) ** 3;
      const next = from + (target - from) * eased;
      currentRef.current = next;
      setDisplay(next);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      } else {
        currentRef.current = target;
      }
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, decimals, durationMs]);

  return display;
}