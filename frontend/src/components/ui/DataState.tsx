import React from 'react';
import { AlertTriangle, PlugZap, Hourglass } from 'lucide-react';
import { LoadingState } from './LoadingState';

/**
 * Renders the three non-success outcomes of a backend read, so no page has to
 * decide independently what to show when data is missing.
 *
 * The important case is `notComputed`. PayerGuard's pipeline stages are run
 * explicitly, so an endpoint can correctly report that its artifact does not
 * exist yet (no anomaly benchmark has been run, no incidents created). That is
 * shown as its own state, quoting the backend's own explanation, instead of
 * being flattened into an error or -- worse -- into zeroes on a chart.
 */
export interface DataStateProps {
  loading: boolean;
  error: string | null;
  notComputed: string | null;
  /** What the user would have seen, named for the "not computed" message. */
  label: string;
  /** How to produce the missing artifact, e.g. "POST /anomaly/benchmark". */
  producedBy?: string;
  children: React.ReactNode;
}

export const DataState: React.FC<DataStateProps> = ({
  loading,
  error,
  notComputed,
  label,
  producedBy,
  children,
}) => {
  if (loading) {
    return <LoadingState message={`Loading ${label}...`} />;
  }

  if (error) {
    return (
      <div className="p-5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs">
        <div className="flex items-center gap-2 text-rose-300 font-semibold">
          <PlugZap className="w-4 h-4 shrink-0" />
          Could not load {label}
        </div>
        <p className="text-rose-200/80 mt-1.5 font-mono text-[11px] break-words">{error}</p>
      </div>
    );
  }

  if (notComputed) {
    return (
      <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 text-xs">
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <Hourglass className="w-4 h-4 shrink-0 text-amber-400" />
          {label} has not been computed yet
        </div>
        <p className="text-slate-400 mt-1.5 leading-relaxed">{notComputed}</p>
        {producedBy && (
          <p className="text-slate-400 mt-2 font-mono text-[11px]">
            Produced by: <span className="text-cyan-400">{producedBy}</span>
          </p>
        )}
        <p className="text-slate-500 mt-2 text-[11px] italic">
          Nothing is shown here rather than a placeholder value.
        </p>
      </div>
    );
  }

  return <>{children}</>;
};

/** Inline note for a value that is real but carries a caveat worth stating. */
export const DataCaveat: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="flex items-start gap-1.5 text-[11px] text-slate-400 mt-2 leading-relaxed">
    <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5 text-amber-500/80" />
    <span>{children}</span>
  </p>
);
