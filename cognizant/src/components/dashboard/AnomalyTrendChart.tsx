import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { AnomalyTrendPoint } from '../../data/mockDashboardData';
import { AlertTriangle, Layers } from 'lucide-react';

interface AnomalyTrendChartProps {
  data24h: AnomalyTrendPoint[];
  data7d: AnomalyTrendPoint[];
  activeRange: '24h' | '7d' | '30d';
}

export const AnomalyTrendChart: React.FC<AnomalyTrendChartProps> = ({
  data24h,
  data7d,
  activeRange,
}) => {
  const data = activeRange === '7d' || activeRange === '30d' ? data7d : data24h;
  const [hoveredPoint, setHoveredPoint] = useState<AnomalyTrendPoint | null>(null);

  const maxTotal = Math.max(...data.map((d) => d.total), 1);
  const currentTotalAnomalies = data[data.length - 1]?.total || 12;

  const categories = [
    { key: 'codeUnbundling', label: 'NCCI Unbundling', color: 'bg-amber-500' },
    { key: 'npiErrors', label: 'NPI Checksum', color: 'bg-rose-500' },
    { key: 'duplicateClaims', label: 'Duplicates', color: 'bg-indigo-500' },
    { key: 'modifierIssues', label: 'Modifier 25/59', color: 'bg-cyan-500' },
    { key: 'timelyFiling', label: 'Timely Filing', color: 'bg-rose-400' },
  ] as const;

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-amber-950/80 border border-amber-800/50 text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <CardTitle>Anomaly Trend</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Categorical distribution of claim defects flagged during EDI ingestion stages
          </CardDescription>
        </div>

        <div className="text-right font-mono">
          <span className="text-xs text-slate-400 block">Active Detected</span>
          <span className="text-sm font-bold text-amber-400">{currentTotalAnomalies} anomalies</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        {/* Category Legend */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
          {categories.map((cat) => (
            <div key={cat.key} className="flex items-center gap-1.5 font-medium text-slate-300">
              <span className={`w-2.5 h-2.5 rounded-xs ${cat.color}`} />
              <span>{cat.label}</span>
            </div>
          ))}
        </div>

        {/* Chart Visualization Area */}
        <div className="relative pt-4 pb-1">
          {/* Hover Status */}
          <div className="h-6 flex items-center justify-between text-xs font-mono text-slate-400 px-1 mb-2">
            {hoveredPoint ? (
              <div className="flex items-center gap-3 text-slate-200">
                <span className="font-bold text-amber-400">{hoveredPoint.time}:</span>
                <span>Total: {hoveredPoint.total}</span>
                <span className="text-amber-300">Unbundle: {hoveredPoint.codeUnbundling}</span>
                <span className="text-rose-300">NPI: {hoveredPoint.npiErrors}</span>
                <span className="text-indigo-300">Dup: {hoveredPoint.duplicateClaims}</span>
                <span className="text-cyan-300">Mod: {hoveredPoint.modifierIssues}</span>
              </div>
            ) : (
              <span className="text-slate-400 text-[11px]">Hover over bars to inspect defect breakdown</span>
            )}
          </div>

          {/* Stacked Bars */}
          <div className="h-44 flex items-end justify-between gap-1.5 sm:gap-2 px-1 border-b border-slate-800">
            {data.map((point) => {
              const heightPercent = Math.max(12, Math.round((point.total / maxTotal) * 100));
              const isHovered = hoveredPoint?.time === point.time;

              // Proportions for stack
              const pUnbundle = (point.codeUnbundling / point.total) * 100;
              const pNpi = (point.npiErrors / point.total) * 100;
              const pDup = (point.duplicateClaims / point.total) * 100;
              const pMod = (point.modifierIssues / point.total) * 100;
              const pTime = (point.timelyFiling / point.total) * 100;

              return (
                <div
                  key={point.time}
                  onMouseEnter={() => setHoveredPoint(point)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  className="flex-1 flex flex-col items-center gap-1.5 group relative cursor-pointer"
                >
                  {/* Tooltip */}
                  <div className="absolute -top-16 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center bg-slate-950 border border-amber-800/80 text-white text-[10px] px-2.5 py-1 rounded-md shadow-xl z-30 pointer-events-none font-mono whitespace-nowrap">
                    <span className="font-bold text-amber-300">{point.time} · {point.total} defects</span>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-slate-300 mt-0.5">
                      <span>Unbundling: {point.codeUnbundling}</span>
                      <span>NPI: {point.npiErrors}</span>
                      <span>Duplicates: {point.duplicateClaims}</span>
                      <span>Modifiers: {point.modifierIssues}</span>
                    </div>
                  </div>

                  {/* Stacked Graphic */}
                  <div className={`w-full max-w-[32px] rounded-t-sm flex flex-col justify-end overflow-hidden h-36 transition-all duration-200 ${isHovered ? 'ring-1 ring-amber-400/60 brightness-110' : 'bg-slate-800/40'}`}>
                    <div
                      className="w-full flex flex-col-reverse overflow-hidden transition-all duration-300"
                      style={{ height: `${heightPercent}%` }}
                    >
                      <div className="w-full bg-amber-500" style={{ height: `${pUnbundle}%` }} />
                      <div className="w-full bg-rose-500" style={{ height: `${pNpi}%` }} />
                      <div className="w-full bg-indigo-500" style={{ height: `${pDup}%` }} />
                      <div className="w-full bg-cyan-500" style={{ height: `${pMod}%` }} />
                      <div className="w-full bg-rose-400" style={{ height: `${pTime}%` }} />
                    </div>
                  </div>

                  <span className={`text-[10px] font-mono transition-colors ${isHovered ? 'text-amber-300 font-bold' : 'text-slate-400'}`}>
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
