import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { DataCaveat } from '../ui/DataState';
import { ShieldCheck } from 'lucide-react';
import type { ExpectationCheckResult, QualityScoreResult } from '../../types/api';

/**
 * Great Expectations results grouped by expectation type.
 *
 * This replaces what used to be a quality *trend over time*. The backend keeps
 * one quality run at a time (`GET /quality/results` returns the latest run's
 * score plus its check results) -- there is no history endpoint and no stored
 * series of past composite scores, so a trend line could only have been drawn
 * by inventing prior points. The real, available shape of this data is the
 * PASS / WARNING / CRITICAL split across each expectation type, which is what
 * MVP_CONTEXT.md Section 3.1's bands actually describe.
 */
interface DataQualityTrendChartProps {
  score: QualityScoreResult;
  checks: ExpectationCheckResult[];
}

interface TypeRow {
  type: string;
  pass: number;
  warning: number;
  critical: number;
  total: number;
}

export const DataQualityTrendChart: React.FC<DataQualityTrendChartProps> = ({ score, checks }) => {
  const byType = new Map<string, TypeRow>();
  for (const check of checks) {
    const row =
      byType.get(check.expectation_type) ??
      { type: check.expectation_type, pass: 0, warning: 0, critical: 0, total: 0 };
    if (check.band === 'PASS') row.pass += 1;
    else if (check.band === 'WARNING') row.warning += 1;
    else row.critical += 1;
    row.total += 1;
    byType.set(check.expectation_type, row);
  }

  const rows = [...byType.values()].sort((a, b) => b.total - a.total);
  const failing = checks.filter((c) => c.band !== 'PASS').length;

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-emerald-950/80 border border-emerald-800/50 text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <CardTitle>Quality Checks by Expectation Type</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Composite score and PASS / WARNING / CRITICAL split from the latest validation run
          </CardDescription>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-emerald-500 rounded-xs inline-block" />
            <span className="text-slate-300">Pass</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-amber-500 rounded-xs inline-block" />
            <span className="text-slate-300">Warn</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-rose-500 rounded-xs inline-block" />
            <span className="text-slate-300">Critical</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Composite Score</span>
            <span className="text-sm font-bold text-emerald-400 font-mono">
              {score.composite_score.toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Checks Run</span>
            <span className="text-sm font-bold text-white font-mono">{checks.length}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Not Passing</span>
            <span className={`text-sm font-bold font-mono ${failing > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {failing}
            </span>
          </div>
        </div>

        <div className="space-y-2.5">
          {rows.map((row) => (
            <div key={row.type} className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-200 font-medium">{row.type.replace(/_/g, ' ')}</span>
                <span className="font-mono text-slate-400">
                  {row.pass}/{row.total} pass
                </span>
              </div>
              <div className="h-3 w-full rounded-full overflow-hidden bg-slate-800/60 flex">
                {row.pass > 0 && (
                  <div
                    className="h-full bg-emerald-500/90"
                    style={{ width: `${(row.pass / row.total) * 100}%` }}
                    title={`${row.pass} PASS`}
                  />
                )}
                {row.warning > 0 && (
                  <div
                    className="h-full bg-amber-500/90"
                    style={{ width: `${(row.warning / row.total) * 100}%` }}
                    title={`${row.warning} WARNING`}
                  />
                )}
                {row.critical > 0 && (
                  <div
                    className="h-full bg-rose-500/90"
                    style={{ width: `${(row.critical / row.total) * 100}%` }}
                    title={`${row.critical} CRITICAL`}
                  />
                )}
              </div>
            </div>
          ))}
        </div>

        <DataCaveat>
          One validation run is retained at a time, so this is a snapshot rather than a trend.
          Run id <span className="font-mono text-slate-300">{score.run_id.slice(0, 8)}</span>,
          generated {new Date(score.generated_at).toLocaleString()}.
        </DataCaveat>
      </CardContent>
    </Card>
  );
};
