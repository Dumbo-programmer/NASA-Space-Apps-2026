"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { TOUR_STEPS, type TourStep } from "@/lib/tourSteps";
import type { TabKey } from "@/components/TabBar";

const KEY = "astraflame-tour-seen";
const PAD = 8;

/** Hook: auto-opens once for first-time visitors; start() reopens it any time. */
export function useTour() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let seen = false;
    try { seen = localStorage.getItem(KEY) === "1"; } catch { /* storage blocked: show once per load */ }
    if (!seen) { const id = setTimeout(() => setOpen(true), 600); return () => clearTimeout(id); }
  }, []);
  const close = useCallback(() => { setOpen(false); try { localStorage.setItem(KEY, "1"); } catch { /* ignore */ } }, []);
  return { open, start: () => setOpen(true), close };
}

interface Rect { top: number; left: number; width: number; height: number }

export function GuidedTour({ open, onClose, onSelectTab, steps = TOUR_STEPS }: {
  open: boolean; onClose: () => void; onSelectTab: (tab: TabKey) => void; steps?: TourStep[];
}) {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const [vw, setVw] = useState(1024);
  const card = useRef<HTMLDivElement>(null);
  const step = steps[i];
  const last = i === steps.length - 1;

  useEffect(() => { if (open) setI(0); }, [open]);

  const measure = useCallback(() => {
    setVw(window.innerWidth);
    const el = step ? document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`) : null;
    if (!el) { setRect(null); return; }
    const r = el.getBoundingClientRect();
    setRect({ top: r.top - PAD, left: r.left - PAD, width: r.width + 2 * PAD, height: r.height + 2 * PAD });
  }, [step]);

  // switch tab if the step needs one, wait for it to render, scroll the target into view, measure it
  useEffect(() => {
    if (!open || !step) return;
    if (step.tab) onSelectTab(step.tab);
    const t = setTimeout(() => {
      const el = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      el?.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
      setTimeout(measure, reduce ? 0 : 320);
    }, 260);
    return () => clearTimeout(t);
  }, [open, step, onSelectTab, measure]);

  useEffect(() => {
    if (!open) return;
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => { window.removeEventListener("resize", measure); window.removeEventListener("scroll", measure, true); };
  }, [open, measure]);

  useLayoutEffect(() => { if (open) card.current?.focus(); }, [open, i]);

  const next = () => (last ? onClose() : setI((n) => n + 1));
  const back = () => setI((n) => Math.max(0, n - 1));

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { e.preventDefault(); onClose(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); next(); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); back(); }
    else if (e.key === "Tab") { // keep focus inside the card
      const f = card.current?.querySelectorAll<HTMLElement>("button");
      if (!f?.length) return;
      const first = f[0], lastEl = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastEl.focus(); }
      else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); first.focus(); }
    }
  };

  if (!open || !step) return null;
  const mobile = vw < 640;
  const CW = Math.min(360, vw - 24);
  let style: React.CSSProperties;
  if (mobile) style = { left: 12, right: 12, bottom: 12, width: "auto" };
  else if (!rect) style = { top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: CW };
  else {
    const below = rect.top + rect.height + 12 + 220 < window.innerHeight;
    style = { width: CW, left: Math.min(Math.max(12, rect.left), vw - CW - 12),
      top: below ? rect.top + rect.height + 12 : Math.max(12, rect.top - 12 - 200) };
  }

  return (
    <>
      <div className="fixed inset-0 z-[69]" aria-hidden onClick={onClose} />
      {rect ? <div className="af-spot" style={rect} aria-hidden />
            : <div className="fixed inset-0 z-[70] bg-slate-950/60" aria-hidden />}
      <div ref={card} role="dialog" aria-modal="true" aria-labelledby="tour-title" tabIndex={-1} onKeyDown={onKey}
        className="af-tourcard af-enter rounded-2xl bg-slate-900 p-5 text-slate-100 shadow-2xl ring-1 ring-slate-700 outline-none" style={style}>
        <p className="text-xs font-medium text-slate-400" aria-live="polite">Step {i + 1} of {steps.length}</p>
        <h2 id="tour-title" className="mt-1 text-lg font-semibold">{step.title}</h2>
        <p className="mt-1 text-[15px] leading-relaxed text-slate-300">{step.body}</p>
        <div className="mt-3 flex gap-1.5" aria-hidden>
          {steps.map((_, k) => <span key={k} className={`h-1.5 rounded-full transition-all ${k === i ? "w-5 bg-violet-500" : "w-1.5 bg-slate-600"}`} />)}
        </div>
        <div className="mt-4 flex items-center justify-between gap-2">
          <button type="button" onClick={onClose} className="af-press h-10 rounded-lg px-3 text-sm text-slate-400 hover:text-slate-200">Skip</button>
          <div className="flex gap-2">
            <button type="button" onClick={back} disabled={i === 0} className="af-press h-10 rounded-lg bg-slate-800 px-4 text-sm font-medium disabled:opacity-40">Back</button>
            <button type="button" onClick={next} className="af-press h-10 rounded-lg bg-violet-600 px-4 text-sm font-semibold text-white hover:bg-violet-500">{last ? "Finish" : "Next"}</button>
          </div>
        </div>
      </div>
    </>
  );
}
