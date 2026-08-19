import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { SeverityDistributionItem } from '../../data/mockDashboardData';
import { formatCurrency, formatNumber } from '../../utils/formatters';
import { AlertOctagon, ShieldAlert } from 'lucide-react';
import { Badge } from '../ui/Badge';

interface IncidentSeverityDistributionProps {
  distribution: SeverityDistributionItem[];
}

export const IncidentSeverityDistribution: React.FC<IncidentSeverityDistributionProps> = ({
  distribution,
}) => {
  const totalIncidents = distribution.reduce((acc, item) => acc + item.count, 0);
  const totalValueAtRisk = distribution.reduce((acc, item) => acc + item.valueAtRisk, 0);

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-rose-950/80 border border-rose-800/50 text-rose-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <CardTitle>Incident Severity Distribution</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Categorized triage breakdown and active financial liability by severity tier
          </CardDescription>
        </div>

        <div className="text-right font-mono">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Total Active</span>
          <span className="text-sm font-bold text-rose-300">{totalIncidents} Incidents</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-1">
        {/* Multi-segment distribution bar */}
        <div className="w-full bg-slate-950 rounded-lg h-4 overflow-hidden p-0.5 border border-slate-800 flex gap-0.5">
          {distribution.map((item) => (
            <div
              key={item.severity}
              className={`h-full ${item.color} first:rounded-l-md last:rounded-r-md transition-all duration-300 relative group cursor-pointer`}
              style={{ width: `${item.percentage}%` }}
            >
              <div className="absolute -top-9 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center bg-slate-950 border border-slate-700 text-white text-[10px] px-2 py-0.5 rounded shadow-lg z-20 pointer-events-none font-mono whitespace-nowrap">
                <span>{item.severity}: {item.count} ({item.percentage}%)</span>
              </div>
            </div>
          ))}
        </div>

        {/* Severity Cards List */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {distribution.map((item) => (
            <div
              key={item.severity}
              className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all duration-150"
            >
              <div className="flex items-center justify-between">
                <Badge variant={item.badgeVariant} size="sm" dot>
                  {item.severity}
                </Badge>
                <span className="font-mono text-xs font-bold text-white">
                  {item.count} <span className="text-slate-400 font-normal">({item.percentage}%)</span>
                </span>
              </div>

              <div className="mt-2.5 grid grid-cols-2 gap-1 text-[11px] font-mono border-t border-slate-800/60 pt-2">
                <div>
                  <span className="text-slate-400 block text-[10px]">Claims Affected</span>
                  <span className="text-slate-200 font-medium">{formatNumber(item.affectedClaims)}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Value at Risk</span>
                  <span className="text-rose-300 font-semibold">{formatCurrency(item.valueAtRisk)}</span>
                </div>
              </div>

              <div className="mt-1.5 text-[10px] text-slate-400 flex items-center justify-between">
                <span>SLA Target:</span>
                <span className="text-slate-300 font-mono font-medium">{item.avgResolutionTime}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-2 pt-2.5 border-t border-slate-800/70 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Aggregate Value at Risk:</span>
          <span className="text-rose-400 font-bold">{formatCurrency(totalValueAtRisk)}</span>
        </div>
      </CardContent>
    </Card>
  );
};
