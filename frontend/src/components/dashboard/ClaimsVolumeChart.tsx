import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { DataCaveat } from '../ui/DataState';
import { formatNumber } from '../../utils/formatters';
import { Activity } from 'lucide-react';
import type { VolumeWindow } from '../../types/api';

/**
 * Real claim volume per baseline window.
 *
 * Source: `GET /baseline` -> `volume_baseline.windows`, which is the only
 * genuine volume time series the backend produces. Each point is a window the
 * baseline was actually computed over, with its measured `claim_count`.
 *
 * There is no "flagged" or "clean rate" series to pair with it -- the previous
 * version of this chart showed both, but the backend records anomalies at
 * window grain through a separate benchmark, not as a per-window flagged count
 * alongside volume. Rather than derive a plausible-looking second series, this
 * chart shows the one series that is real.
 */
interface ClaimsVolumeChartProps {
  windows: VolumeWindow[];
  windowDefinition: string;
}

export const ClaimsVolumeChart: React.FC<ClaimsVolumeChartProps> = ({
  windows,
  windowDefinition,
}) => {
  const [hovered, setHovered] = useState<VolumeWindow | null>(null);

  // The baseline can span years; showing every window makes the axis unreadable.
  // Take the most recent 24 so each bar stays legible, and say so in the caption.
  const shown = windows.slice(-24);
  const maxCount = Math.max(...shown.map((w) => w.claim_count), 1);
  const totalShown = shown.reduce((acc, w) => acc + w.claim_count, 0);
  const totalAll = windows.reduce((acc, w) => acc + w.claim_count, 0);

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-cyan-950/80 border border-cyan-800/50 text-cyan-400">
              <Activity className="w-4 h-4" />
            </div>
            <CardTitle>Claim Volume by Baseline Window</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Measured claim counts per window from the current baseline snapshot
          </CardDescription>
        </div>
        <span className="text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded whitespace-nowrap">
          {windowDefinition}
        </span>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Windows</span>
            <span className="text-sm font-bold text-white font-mono">{formatNumber(windows.length)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Claims (all)</span>
            <span className="text-sm font-bold text-cyan-400 font-mono">{formatNumber(totalAll)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Peak Window</span>
            <span className="text-sm font-bold text-emerald-400 font-mono">{formatNumber(maxCount)}</span>
          </div>
        </div>

        <div className="relative pt-4 pb-2">
          <div className="h-6 flex items-center justify-between text-xs font-mono text-slate-400 px-1 mb-2">
            {hovered ? (
              <div className="flex items-center gap-3 text-slate-200">
                <span className="font-bold text-cyan-400">{hovered.start}</span>
                <span className="text-slate-400">to {hovered.end}</span>
                <span>{formatNumber(hovered.claim_count)} claims</span>
              </div>
            ) : (
              <span className="text-slate-400 text-[11px]">
                Hover a bar to inspect that window
              </span>
            )}
          </div>

          <div className="h-44 flex items-end justify-between gap-1.5 sm:gap-2 px-1 border-b border-slate-800">
            {shown.map((w) => {
              const heightPercent = Math.max(4, Math.round((w.claim_count / maxCount) * 100));
              const isHovered = hovered?.window_id === w.window_id;
              return (
                <div
                  key={w.window_id}
                  onMouseEnter={() => setHovered(w)}
                  onMouseLeave={() => setHovered(null)}
                  className="flex-1 flex flex-col items-center gap-1.5 group relative cursor-pointer"
                >
                  <div className="absolute -top-12 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center bg-slate-950 border border-cyan-800/80 text-white text-[11px] px-2.5 py-1 rounded-md shadow-xl z-30 pointer-events-none font-mono whitespace-nowrap">
                    <span className="font-bold text-cyan-300">{formatNumber(w.claim_count)} claims</span>
                    <span className="text-[10px] text-slate-400">{w.start}</span>
                  </div>

                  <div
                    className={`w-full max-w-[32px] rounded-t-sm flex flex-col justify-end overflow-hidden h-36 transition-all duration-200 ${
                      isHovered ? 'ring-1 ring-cyan-400/60 brightness-110' : 'bg-slate-800/40'
                    }`}
                  >
                    <div
                      className="w-full bg-linear-to-t from-cyan-600 via-cyan-500 to-cyan-400 transition-all duration-300"
                      style={{ height: `${heightPercent}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {windows.length > shown.length && (
            <DataCaveat>
              Showing the most recent {shown.length} of {formatNumber(windows.length)} baseline
              windows ({formatNumber(totalShown)} of {formatNumber(totalAll)} claims). Earlier
              windows are omitted from the plot only, not from the totals above.
            </DataCaveat>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
