"use client";

import { useId, useState } from "react";

/** Small "?" that explains a term in one sentence. Works with hover, focus, tap and Esc. */
export function HelpTip({ text, label = "What does this mean?" }: { text: string; label?: string }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block align-middle" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label={label} aria-describedby={open ? id : undefined} aria-expanded={open}
        onClick={() => setOpen((v) => !v)} onBlur={() => setOpen(false)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        className="af-press ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold text-slate-300 ring-1 ring-slate-700 hover:bg-slate-700">?</button>
      {open ? (
        <span id={id} role="tooltip" className="af-enter absolute left-1/2 top-full z-50 mt-2 w-60 -translate-x-1/2 rounded-lg bg-slate-900 p-3 text-left text-xs font-normal leading-relaxed text-slate-200 shadow-xl ring-1 ring-slate-700">
          {text}
        </span>
      ) : null}
    </span>
  );
}

export const GLOSSARY = {
  microgravity: "Near-weightless conditions, like on the International Space Station. Hot gas does not rise, so flames burn as balls.",
  kpa: "A unit of air pressure. Earth air is 101.3 kPa. The planned habitat is 56.5 kPa (8.2 psia).",
  extinction: "The chance a flame goes out by itself before the fuel is used up. Higher means safer.",
  range90: "A range where the true answer should fall 9 times out of 10 on tests the model never saw.",
  shapley: "How much each input pushed the answer up or down.",
  confidence: "How close your conditions are to what NASA actually tested. Far away means more of a guess.",
} as const;
