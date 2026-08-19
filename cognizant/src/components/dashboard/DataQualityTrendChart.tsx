import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { DQTrendPoint } from '../../data/mockDashboardData';
import { ShieldCheck, CheckCircle2, TrendingUp } from 'lucide-react';

interface DataQualityTrendChartProps {
  data24h: DQTrendPoint[];
  data7d: DQTrendPoint[];
  activeRange: '24h' | '7d' | '30d';
}

export const DataQualityTrendChart: React.FC<DataQualityTrendChartProps> = ({
  data24h,
  data7d,
  activeRange,
}) => {
  const data = activeRange === '7d' || activeRange === '30d' ? data7d : data24h;
  const [hoveredPoint, setHoveredPoint] = useState<DQTrendPoint | null>(null);

  const currentScore = data[data.length - 1]?.score || 94.2;
  const minScore = 90.0;
  const maxScore = 96.0;

  // Calculate SVG polyline points
  const points = data.map((d, index) => {
    const x = (index / (data.length - 1)) * 100;
    const y = 100 - ((d.score - minScore) / (maxScore - minScore)) * 100;
    return `${x},${y}`;
  }).join(' ');

  const targetY = 100 - ((95.0 - minScore) / (maxScore - minScore)) * 100;

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-emerald-950/80 border border-emerald-800/50 text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <CardTitle>Data Quality Trend</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Automated composite DQ index tracking syntactic, semantic, and NCCI compliance
          </CardDescription>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full inline-block" />
            <span className="text-slate-300">DQ Score ({currentScore}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 border-t-2 border-dashed border-amber-400 inline-block" />
            <span className="text-slate-400">Target (95.0%)</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        {/* Dimension Breakdown Bar */}
        <div className="grid grid-cols-4 gap-2 bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80 text-center font-mono">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Completeness</span>
            <span className="text-xs font-bold text-emerald-400">
              {hoveredPoint ? `${hoveredPoint.completeness}%` : '99.6%'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Validity</span>
            <span className="text-xs font-bold text-cyan-400">
              {hoveredPoint ? `${hoveredPoint.validity}%` : '96.5%'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Accuracy</span>
            <span className="text-xs font-bold text-indigo-300">
              {hoveredPoint ? `${hoveredPoint.accuracy}%` : '94.3%'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Timeliness</span>
            <span className="text-xs font-bold text-emerald-400">
              {hoveredPoint ? `${hoveredPoint.timeliness}%` : '99.9%'}
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
                <linearGradient id="dqGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Horizontal Grid lines */}
              <line x1="0" y1="0" x2="100" y2="0" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
              <line x1="0" y1="50" x2="100" y2="50" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
              <line x1="0" y1="100" x2="100" y2="100" stroke="#334155" strokeWidth="0.5" />

              {/* Target Benchmark Line (95.0%) */}
              <line
                x1="0"
                y1={targetY}
                x2="100"
                y2={targetY}
                stroke="#f59e0b"
                strokeWidth="1.2"
                strokeDasharray="3,3"
              />

              {/* Area fill */}
              <polygon
                points={`0,100 ${points} 100,100`}
                fill="url(#dqGradient)"
              />

              {/* Line stroke */}
              <polyline
                fill="none"
                stroke="#34d399"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
              />

              {/* Data points */}
              {data.map((d, index) => {
                const x = (index / (data.length - 1)) * 100;
                const y = 100 - ((d.score - minScore) / (maxScore - minScore)) * 100;
                const isHovered = hoveredPoint?.time === d.time;
                return (
                  <g key={d.time}>
                    <circle
                      cx={x}
                      cy={y}
                      r={isHovered ? '4' : '2.5'}
                      fill="#10b981"
                      stroke="#022c22"
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
                    ? 'text-emerald-400 font-bold'
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
