import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { ClaimAmountBracket } from '../../data/mockDashboardData';
import { formatCurrency, formatNumber } from '../../utils/formatters';
import { DollarSign, AlertCircle } from 'lucide-react';

interface ClaimAmountDistributionProps {
  brackets: ClaimAmountBracket[];
}

export const ClaimAmountDistribution: React.FC<ClaimAmountDistributionProps> = ({ brackets }) => {
  const maxCount = Math.max(...brackets.map((b) => b.count));
  const totalBilled = brackets.reduce((acc, b) => acc + b.totalAmount, 0);

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-cyan-950/80 border border-cyan-800/50 text-cyan-400">
              <DollarSign className="w-4 h-4" />
            </div>
            <CardTitle>Claim Amount Distribution</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Billed dollar bands cross-referenced with defect frequency and financial exposure
          </CardDescription>
        </div>

        <div className="text-right font-mono">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Aggregate Exposure</span>
          <span className="text-sm font-bold text-cyan-300">{formatCurrency(totalBilled)}</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-3.5 pt-1">
        {brackets.map((bracket) => {
          const widthPercent = (bracket.count / maxCount) * 100;
          return (
            <div key={bracket.range} className="space-y-1.5 group">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors">
                  {bracket.range}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-slate-400">
                    <span className="text-slate-200 font-bold">{formatNumber(bracket.count)}</span> ({bracket.percentage}%)
                  </span>
                  <span className="text-slate-500">|</span>
                  <span className="text-cyan-300 font-semibold">{formatCurrency(bracket.totalAmount)}</span>
                  <span
                    className={`inline-flex items-center gap-1 text-[11px] px-1.5 py-0.2 rounded font-medium ${
                      bracket.anomalyRate > 10
                        ? 'bg-rose-950 text-rose-300 border border-rose-800/50'
                        : bracket.anomalyRate > 4
                        ? 'bg-amber-950 text-amber-300 border border-amber-800/50'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {bracket.anomalyRate}% Anomaly
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden p-0.5 border border-slate-800/80">
                <div
                  className={`h-full rounded-full bg-linear-to-r ${bracket.color} transition-all duration-500`}
                  style={{ width: `${widthPercent}%` }}
                />
              </div>
            </div>
          );
        })}

        <div className="mt-3 pt-2.5 border-t border-slate-800/70 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 text-slate-300">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
            High-dollar tier (&gt;$50k) carries 14.8% anomaly rate (18x baseline)
          </span>
          <span className="font-mono text-cyan-400">6 Financial Tiers Audited</span>
        </div>
      </CardContent>
    </Card>
  );
};
