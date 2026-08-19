import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { DataCaveat } from '../ui/DataState';
import { AlertTriangle } from 'lucide-react';
import { injectionTypeLabel } from '../../utils/incidentDisplay';
import type { AnomalyBenchmarkRunResult } from '../../types/api';

/**
 * Detection performance of the selected production model, per injection type.
 *
 * The categories here are the backend's real five synthetic injection types
 * (`InjectionType` in `app/anomaly/schemas.py`): missing-value spike, amount
 * spike, duplicate spike, volume drop, distribution shift. They replace the
 * previous NPI-error / code-unbundling / timely-filing / modifier-issue
 * categories, which belonged to a different product and have no backend or
 * dataset equivalent here.
 *
 * This is a per-injection-type breakdown, not a time series. `GET
 * /anomaly/results` returns benchmark results -- precision/recall/F1 measured
 * once per model against injected anomalies -- and the backend stores no
 * per-interval anomaly counts, so there is no honest trend to plot.
 */
interface AnomalyTrendChartProps {
  result: AnomalyBenchmarkRunResult;
}

type Metric = 'recall' | 'precision' | 'f1';

export const AnomalyTrendChart: React.FC<AnomalyTrendChartProps> = ({ result }) => {
  const [metric, setMetric] = useState<Metric>('recall');

  const selected = result.production_model_selection.selected_model;
  const winner =
    result.benchmark_results.find((r) => r.model_type === selected) ?? result.benchmark_results[0];

  const breakdown = Object.entries(winner?.per_injection_type_breakdown ?? {});

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-amber-950/80 border border-amber-800/50 text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <CardTitle>Anomaly Detection by Injection Type</CardTitle>
          </div>
          <CardDescription className="mt-1">
            Benchmark performance of the selected production model against each injected anomaly type
          </CardDescription>
        </div>

        <div className="bg-slate-900 p-1 rounded-lg border border-slate-800 flex items-center text-[11px] shrink-0">
          {(['recall', 'precision', 'f1'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                metric === m ? 'bg-slate-800 text-amber-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2 flex-1 flex flex-col justify-between">
        <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Production Model</span>
            <span className="text-sm font-bold text-amber-400 font-mono">{selected}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Overall F1</span>
            <span className="text-sm font-bold text-white font-mono">{winner?.f1.toFixed(3) ?? '--'}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">False-Positive Rate</span>
            <span className="text-sm font-bold text-rose-400 font-mono">{winner?.fpr.toFixed(3) ?? '--'}</span>
          </div>
        </div>

        <div className="space-y-2.5">
          {breakdown.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">
              The benchmark recorded no per-injection-type breakdown for this model.
            </p>
          ) : (
            breakdown.map(([type, metrics]) => {
              const value = metrics[metric];
              const pct = Math.max(0, Math.min(1, value)) * 100;
              return (
                <div key={type} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-200 font-medium">{injectionTypeLabel(type)}</span>
                    <span className="font-mono text-amber-300">{value.toFixed(3)}</span>
                  </div>
                  <div className="h-3 w-full rounded-full overflow-hidden bg-slate-800/60">
                    <div
                      className="h-full bg-linear-to-r from-amber-600 to-amber-400 transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>

        <DataCaveat>
          Measured on injected anomalies in the validation/test splits only -- training data is
          never contaminated with injections. Selection rule:{' '}
          <span className="font-mono text-slate-300">
            {result.production_model_selection.ranking_rule}
          </span>
          .
        </DataCaveat>
      </CardContent>
    </Card>
  );
};
