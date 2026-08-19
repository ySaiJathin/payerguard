import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { DataCaveat } from '../ui/DataState';
import { formatCurrency } from '../../utils/formatters';
import { DollarSign } from 'lucide-react';
import type { AmountBaseline } from '../../types/api';

/**
 * Claim-amount distribution built from the real baseline percentiles.
 *
 * Buckets are the p25 / p50 / p75 / p95 / p99 boundaries the backend actually
 * computed for the chosen amount column (`GET /baseline` ->
 * `amount_baselines[].percentiles`), so the bucket *edges* are measured values
 * rather than round numbers picked for display.
 *
 * NOTE on the per-bucket anomaly rate that the previous version of this chart
 * showed: it is deliberately absent. Anomaly enrichment is stored at window
 * grain (`WindowAnomalyEnrichment.anomaly_count` keyed by `window_id`), not
 * per claim, so there is no way to attribute an anomaly to an individual
 * claim's amount bucket. Showing a per-bucket rate would require inventing an
 * attribution the data does not support.
 */
interface ClaimAmountDistributionProps {
  amount: AmountBaseline;
  totalClaims: number;
}

export const ClaimAmountDistribution: React.FC<ClaimAmountDistributionProps> = ({
  amount,
  totalClaims,
}) => {
  const p = amount.percentiles;

  // Percentile boundaries imply the share of claims in each band directly:
  // p25 covers the bottom 25%, p25-p50 the next 25%, and so on.
  const buckets = [
    { label: `${formatCurrency(amount.min)} – ${formatCurrency(p.p25)}`, share: 25, band: 'Bottom 25%', color: 'from-sky-600 to-sky-400' },
    { label: `${formatCurrency(p.p25)} – ${formatCurrency(p.p50)}`, share: 25, band: '25th–50th', color: 'from-cyan-600 to-cyan-400' },
    { label: `${formatCurrency(p.p50)} – ${formatCurrency(p.p75)}`, share: 25, band: '50th–75th', color: 'from-emerald-600 to-emerald-400' },
    { label: `${formatCurrency(p.p75)} – ${formatCurrency(p.p95)}`, share: 20, band: '75th–95th', color: 'from-amber-600 to-amber-400' },
    { label: `${formatCurrency(p.p95)} – ${formatCurrency(p.p99)}`, share: 4, band: '95th–99th', color: 'from-orange-600 to-orange-400' },
    { label: `${formatCurrency(p.p99)} – ${formatCurrency(amount.max)}`, share: 1, band: 'Top 1%', color: 'from-rose-600 to-rose-400' },
  ];

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-cyan-950/80 border border-cyan-800/50 text-cyan-400">
            <DollarSign className="w-4 h-4" />
          </div>
          <CardTitle>Claim Amount Distribution</CardTitle>
        </div>
        <CardDescription className="mt-1">
          Percentile bands of <span className="font-mono text-slate-300">{amount.column_name}</span>{' '}
          from the current baseline
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Median</span>
            <span className="text-sm font-bold text-cyan-400 font-mono">{formatCurrency(amount.median)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Mean</span>
            <span className="text-sm font-bold text-white font-mono">{formatCurrency(amount.mean)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Max</span>
            <span className="text-sm font-bold text-rose-400 font-mono">{formatCurrency(amount.max)}</span>
          </div>
        </div>

        <div className="space-y-2.5">
          {buckets.map((bucket) => (
            <div key={bucket.band} className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-200 font-medium">{bucket.band}</span>
                <span className="font-mono text-slate-400">{bucket.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 flex-1 rounded-full overflow-hidden bg-slate-800/60">
                  <div
                    className={`h-full bg-linear-to-r ${bucket.color} transition-all duration-300`}
                    style={{ width: `${(bucket.share / 25) * 100}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono text-slate-400 w-20 text-right">
                  ~{Math.round((bucket.share / 100) * totalClaims).toLocaleString()} claims
                </span>
              </div>
            </div>
          ))}
        </div>

        <DataCaveat>
          Claim counts per band are implied by the percentile definition applied to{' '}
          {totalClaims.toLocaleString()} baseline rows, not separately counted. Mean sits well above
          median because this distribution is heavily right-skewed.
        </DataCaveat>
      </CardContent>
    </Card>
  );
};
