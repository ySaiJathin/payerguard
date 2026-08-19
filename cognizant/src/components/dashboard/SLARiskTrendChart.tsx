import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { SLARiskTrendPoint } from '../../data/mockDashboardData';
import { Clock, AlertOctagon, TrendingDown } from 'lucide-react';

interface SLARiskTrendChartProps {
  data24h: SLARiskTrendPoint[];
  data7d: SLARiskTrendPoint[];
  activeRange: '24h' | '7d' | '30d';
}

export const SLARiskTrendChart: React.FC<SLARiskTrendChartProps> = ({
  data24h,
  data7d,
  activeRange,
}) => {
  const data = activeRange === '7d' || activeRange === '30d' ? data7d : data24h;
  const [hoveredPoint, setHoveredPoint] = useState<SLARiskTrendPoint | null>(null);

  const currentRisk = data[data.length - 1]?.riskScore || 18;
  const minRisk = 0;
  const maxRisk = 40;

  // Calculate SVG Polyline Points
  const points = data.map((d, index) => {
    const x = (index / (data.length - 1)) * 100;
    const y = 100 - ((d.riskScore - minRisk) / (maxRisk - minRisk)) * 100;
    return `${x},${y}`;
  }).join(' ');

  const warningThresholdY = 100 - ((25 - minRisk) / (maxRisk - minRisk)) * 100;

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-rose-950/80 border border-rose-800/50 text-rose-400">
              <Clock className="w-4 h-4" />
            </div>
            <CardTitle>SLA Risk Trend</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Prompt-pay statutory compliance risk percentage and turnaround velocity
          </CardDescription>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-rose-400 rounded-full inline-block" />
            <span className="text-slate-300">Risk Score ({currentRisk}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 border-t-2 border-dashed border-rose-500 inline-block" />
            <span className="text-rose-400 font-semibold">Alert Zone (&gt;25%)</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        {/* SLA Telemetry Metrics Bar */}
        <div className="grid grid-cols-3 gap-2 bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80 text-center font-mono">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Current Risk</span>
            <span className="text-xs font-bold text-amber-400">
              {hoveredPoint ? `${hoveredPoint.riskScore}%` : `${currentRisk}%`}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Claims at Risk</span>
            <span className="text-xs font-bold text-rose-400">
              {hoveredPoint ? `${hoveredPoint.atRiskCount} (<30m)` : '2 (<30m)'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Avg Turnaround</span>
            <span className="text-xs font-bold text-emerald-400">
              {hoveredPoint ? `${hoveredPoint.avgTurnaroundMins}m` : '18.2m'}
            </span>
          </div>
        </div>

        {/* SVG Curve Chart Area */}
        <div className="relative pt-3 pb-1">
          <div className="h-44 w-full relative">
            <svg
              className="w-full h-full overflow-visible"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
            >
              <defs>
                <linearGradient id="slaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              <line x1="0" y1="0" x2="100" y2="0" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
              <line x1="0" y1="50" x2="100" y2="50" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
              <line x1="0" y1="100" x2="100" y2="100" stroke="#334155" strokeWidth="0.5" />

              {/* Warning Threshold Line (>25%) */}
              <line
                x1="0"
                y1={warningThresholdY}
                x2="100"
                y2={warningThresholdY}
                stroke="#f43f5e"
                strokeWidth="1.2"
                strokeDasharray="3,3"
              />

              {/* Area fill */}
              <polygon
                points={`0,100 ${points} 100,100`}
                fill="url(#slaGradient)"
              />

              {/* Line stroke */}
              <polyline
                fill="none"
                stroke="#f43f5e"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
              />

              {/* Data points */}
              {data.map((d, index) => {
                const x = (index / (data.length - 1)) * 100;
                const y = 100 - ((d.riskScore - minRisk) / (maxRisk - minRisk)) * 100;
                const isHovered = hoveredPoint?.time === d.time;
                return (
                  <g key={d.time}>
                    <circle
                      cx={x}
                      cy={y}
                      r={isHovered ? '4' : '2.5'}
                      fill="#f43f5e"
                      stroke="#4c0519"
                      strokeWidth="1.5"
                      className="cursor-pointer transition-all duration-150 hover:r-5"
                    />
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Interactive node hover triggers */}
          <div className="flex justify-between items-center px-1 mt-2 border-t border-slate-800 pt-1">
            {data.map((d) => (
              <button
                key={d.time}
                onMouseEnter={() => setHoveredPoint(d)}
                onMouseLeave={() => setHoveredPoint(null)}
                className={`text-[10px] font-mono transition-colors ${
                  hoveredPoint?.time === d.time
                    ? 'text-rose-400 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {d.time}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
