import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export type PanelAccent = "orange" | "cyan" | "violet" | "emerald" | "amber";

export interface PanelFrameProps {
  index: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  accent?: PanelAccent;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

const ACCENT_GLOW: Record<PanelAccent, string> = {
  orange: "bg-orange-500/10 text-orange-300 ring-orange-500/30",
  cyan: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/30",
  violet: "bg-violet-500/10 text-violet-300 ring-violet-500/30",
  emerald: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  amber: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
};

/** Hairline that rides the top edge of the panel in the panel's accent color. */
const ACCENT_EDGE: Record<PanelAccent, string> = {
  orange: "from-orange-500/70 via-orange-400/30 to-transparent",
  cyan: "from-cyan-500/70 via-cyan-400/30 to-transparent",
  violet: "from-violet-500/70 via-violet-400/30 to-transparent",
  emerald: "from-emerald-500/70 via-emerald-400/30 to-transparent",
  amber: "from-amber-500/70 via-amber-400/30 to-transparent",
};

export function PanelFrame({
  index,
  title,
  subtitle,
  icon: Icon,
  accent = "orange",
  actions,
  children,
  className = "",
  bodyClassName = "",
}: PanelFrameProps) {
  return (
    <section
      className={`relative flex flex-col overflow-hidden rounded-xl border border-slate-800/80 bg-slate-900/40 shadow-lg shadow-black/30 ring-1 ring-white/[0.03] backdrop-blur-sm transition-colors duration-300 hover:border-slate-700/80 ${className}`}
    >
      <span
        className={`pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r ${ACCENT_EDGE[accent]}`}
        aria-hidden="true"
      />

      <header className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-800/80 bg-gradient-to-b from-slate-900/80 to-slate-900/40 px-3 py-2">
        <div className="flex min-w-0 items-start gap-2.5">
          <span
            className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md ring-1 ${ACCENT_GLOW[accent]}`}
          >
            <Icon className="size-3.5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h2 className="flex items-center gap-1.5 text-[13px] font-semibold tracking-tight text-slate-100">
              <span className="font-mono text-[10px] text-slate-400">{index}</span>
              {title}
            </h2>
            <p className="truncate text-[11px] text-slate-400" title={subtitle}>
              {subtitle}
            </p>
          </div>
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </header>

      <div className={`min-h-0 flex-1 p-3 ${bodyClassName}`}>{children}</div>
    </section>
  );
}

export function SubCard({
  children,
  className = "",
  interactive = false,
}: {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border border-slate-800/80 bg-slate-950/40 ring-1 ring-white/[0.02] transition-colors duration-200 ${
        interactive ? "hover:border-slate-700/80 hover:bg-slate-900/60" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function Pill({
  children,
  tone = "slate",
  className = "",
}: {
  children: ReactNode;
  tone?: "slate" | "orange" | "emerald" | "amber" | "red" | "cyan" | "violet";
  className?: string;
}) {
  const tones: Record<string, string> = {
    slate: "bg-slate-800/80 text-slate-300 ring-slate-700",
    orange: "bg-orange-500/10 text-orange-300 ring-orange-500/30",
    emerald: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
    amber: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
    red: "bg-red-500/10 text-red-300 ring-red-500/30",
    cyan: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/30",
    violet: "bg-violet-500/10 text-violet-300 ring-violet-500/30",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider ring-1 transition-colors ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
