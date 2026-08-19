import React from 'react';
import { CheckCircle2, XCircle, Hourglass, Loader2 } from 'lucide-react';

/**
 * Presence/recency check per pipeline stage.
 *
 * This is deliberately modest: it reports whether each stage's endpoint
 * currently returns an artifact, and how old that artifact is. It is not a
 * health probe, an uptime figure, or a latency measurement -- the backend
 * exposes none of those, and the previous version's "99.4% / 42ms" style
 * readouts had nothing behind them.
 */
export type StageState = 'ready' | 'not_computed' | 'error' | 'loading';

export interface StageStatus {
  name: string;
  state: StageState;
  /** Real detail: a count, a score, or the backend's own explanation. */
  detail: string;
  /** ISO timestamp of the artifact, when the endpoint reports one. */
  computedAt?: string | null;
}

interface SystemStatusSectionProps {
  stages: StageStatus[];
}

const STATE_STYLE: Record<StageState, { label: string; chip: string; icon: React.ReactNode }> = {
  ready: {
    label: 'Ready',
    chip: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/50',
    icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
  },
  not_computed: {
    label: 'Not computed',
    chip: 'bg-amber-950/50 text-amber-300 border-amber-800/50',
    icon: <Hourglass className="w-3.5 h-3.5 text-amber-400" />,
  },
  error: {
    label: 'Unreachable',
    chip: 'bg-rose-950/60 text-rose-300 border-rose-800/50',
    icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
  },
  loading: {
    label: 'Checking',
    chip: 'bg-slate-800 text-slate-300 border-slate-700',
    icon: <Loader2 className="w-3.5 h-3.5 text-slate-400 animate-spin" />,
  },
};

function relativeAge(iso?: string | null): string | null {
  if (!iso) return null;
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return null;
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export const SystemStatusSection: React.FC<SystemStatusSectionProps> = ({ stages }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
    {stages.map((stage) => {
      const style = STATE_STYLE[stage.state];
      const age = relativeAge(stage.computedAt);
      return (
        <div
          key={stage.name}
          className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col gap-2"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-100">{stage.name}</span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded border flex items-center gap-1 whitespace-nowrap ${style.chip}`}
            >
              {style.icon}
              {style.label}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">{stage.detail}</p>
          {age && <span className="text-[10px] font-mono text-slate-500">computed {age}</span>}
        </div>
      );
    })}
  </div>
);
