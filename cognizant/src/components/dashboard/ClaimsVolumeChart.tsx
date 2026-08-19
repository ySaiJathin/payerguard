import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { VolumeTrendPoint } from '../../data/mockDashboardData';
import { formatNumber } from '../../utils/formatters';
import { Activity, ArrowUpRight } from 'lucide-react';

interface ClaimsVolumeChartProps {
  data24h: VolumeTrendPoint[];
  data7d: VolumeTrendPoint[];
  activeRange: '24h' | '7d' | '30d';
}

export const ClaimsVolumeChart: React.FC<ClaimsVolumeChartProps> = ({
  data24h,
  data7d,
  activeRange,
}) => {
  const data = activeRange === '7d' || activeRange === '30d' ? data7d : data24h;
  const [hoveredPoint, setHoveredPoint] = useState<VolumeTrendPoint | null>(null);

  const maxVolume = Math.max(...data.map((d) => d.processed), 1);
  const totalVolume = data.reduce((acc, curr) => acc + curr.processed, 0);
  const avgCleanRate = (
    data.reduce((acc, curr) => acc + curr.cleanRate, 0) / data.length
  ).toFixed(1);

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-cyan-950/80 border border-cyan-800/50 text-cyan-400">
              <Activity className="w-4 h-4" />
            </div>
            <CardTitle>Claims Volume Trend</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Throughput volume of EDI 837/CMS-1500 claims processed vs. anomalies flagged
          </CardDescription>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-cyan-500 rounded-xs inline-block" />
            <span className="text-slate-300">Volume</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-rose-500 rounded-xs inline-block" />
            <span className="text-slate-300">Flagged</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        {/* Metric highlights */}
        <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Total Ingested</span>
            <span className="text-sm font-bold text-white font-mono">{formatNumber(totalVolume)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Peak Ingestion</span>
            <span className="text-sm font-bold text-cyan-400 font-mono">{formatNumber(maxVolume)}/pt</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Clean Pass Avg</span>
            <span className="text-sm font-bold text-emerald-400 font-mono">{avgCleanRate}%</span>
          </div>
        </div>

        {/* Chart Visualization Area */}
        <div className="relative pt-6 pb-2">
          {/* Active Hover Inspection Banner */}
          <div className="h-6 flex items-center justify-between text-xs font-mono text-slate-400 px-1 mb-2">
            {hoveredPoint ? (
              <div className="flex items-center gap-3 text-slate-200">
                <span className="font-bold text-cyan-400">{hoveredPoint.time}:</span>
                <span>{formatNumber(hoveredPoint.processed)} processed</span>
                <span className="text-rose-400 font-semibold">{hoveredPoint.flagged} flagged</span>
                <span className="text-emerald-400">{hoveredPoint.cleanRate}% clean</span>
                <span className="text-slate-400">({hoveredPoint.latencyMs}ms)</span>
              </div>
            ) : (
              <span className="text-slate-400 text-[11px]">Hover over bars to inspect hourly telemetry</span>
            )}
          </div>

          {/* Bar Columns Container */}
          <div className="h-44 flex items-end justify-between gap-1.5 sm:gap-2 px-1 border-b border-slate-800">
            {data.map((point) => {
              const heightPercent = Math.max(12, Math.round((point.processed / maxVolume) * 100));
              const flaggedPercent = Math.min(25, Math.max(4, Math.round((point.flagged / point.processed) * 100 * 3)));
              const isHovered = hoveredPoint?.time === point.time;

              return (
                <div
                  key={point.time}
                  onMouseEnter={() => setHoveredPoint(point)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  className="flex-1 flex flex-col items-center gap-1.5 group relative cursor-pointer"
                >
                  {/* Tooltip on hover */}
                  <div className="absolute -top-14 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center bg-slate-950 border border-cyan-800/80 text-white text-[11px] px-2.5 py-1 rounded-md shadow-xl z-30 pointer-events-none font-mono whitespace-nowrap">
                    <span className="font-bold text-cyan-300">{point.time} · {formatNumber(point.processed)} claims</span>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-emerald-400">{point.cleanRate}% Clean</span>
                      <span className="text-rose-400">{point.flagged} Flagged</span>
                    </div>
                  </div>

                  {/* Dual Bar Graphic */}
                  <div className={`w-full max-w-[32px] rounded-t-sm flex flex-col justify-end overflow-hidden h-36 transition-all duration-200 ${isHovered ? 'ring-1 ring-cyan-400/60 brightness-110' : 'bg-slate-800/40'}`}>
                    <div
                      className="w-full bg-linear-to-t from-cyan-600 via-cyan-500 to-cyan-400 relative transition-all duration-300"
                      style={{ height: `${heightPercent}%` }}
                    >
                      {/* Flagged top segment indicator */}
                      <div
                        className="w-full bg-rose-500/90 absolute top-0 left-0 right-0 border-b border-rose-600/40"
                        style={{ height: `${flaggedPercent}%` }}
                      />
                    </div>
                  </div>

                  <span className={`text-[10px] font-mono transition-colors ${isHovered ? 'text-cyan-300 font-bold' : 'text-slate-400'}`}>
                    {point.time}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
