import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { DataCaveat } from '../ui/DataState';
import { formatCurrency } from '../../utils/formatters';
import { AlertOctagon } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { bandForScore, scoreBandVariant, type ScoreBand } from '../../utils/incidentDisplay';
import type { Incident } from '../../types/api';

/**
 * Real incidents grouped into severity bands.
 *
 * The backend has no severity *enum* -- `severity_result.severity` is a
 * computed 0-100 number (MVP_CONTEXT.md Section 3.3). Bands here are the
 * documented Section 3.1 thresholds applied for display only; the underlying
 * numbers are shown so the banding never stands in for the real value.
 *
 * The previous version showed an `avgResolutionTime` per band. That is not
 * derived here: it would need incident open/close durations, and while
 * `created_at`/`updated_at` exist, `updated_at` moves on any edit rather than
 * only on closure, so a duration computed from it would not mean what the
 * label claims. Dollar exposure, by contrast, is real -- it comes from the
 * incident's own `evidence_snapshot.affected_claims_amounts`.
 */
interface IncidentSeverityDistributionProps {
  incidents: Incident[];
}

const BANDS: ScoreBand[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

const BAND_BAR: Record<ScoreBand, string> = {
  CRITICAL: 'from-rose-600 to-rose-400',
  HIGH: 'from-amber-600 to-amber-400',
  MEDIUM: 'from-yellow-600 to-yellow-400',
  LOW: 'from-sky-600 to-sky-400',
};

export const IncidentSeverityDistribution: React.FC<IncidentSeverityDistributionProps> = ({
  incidents,
}) => {
  const rows = BANDS.map((band) => {
    const inBand = incidents.filter((i) => bandForScore(i.severity_result?.severity ?? 0) === band);
    const exposure = inBand.reduce(
      (acc, i) => acc + (i.evidence_snapshot?.affected_claims_amounts ?? []).reduce((a, b) => a + b, 0),
      0
    );
    const avgSeverity =
      inBand.length > 0
        ? inBand.reduce((acc, i) => acc + (i.severity_result?.severity ?? 0), 0) / inBand.length
        : 0;
    return { band, count: inBand.length, exposure, avgSeverity };
  });

  const total = incidents.length;
  const maxCount = Math.max(...rows.map((r) => r.count), 1);

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-rose-950/80 border border-rose-800/50 text-rose-400">
            <AlertOctagon className="w-4 h-4" />
          </div>
          <CardTitle>Incident Severity Distribution</CardTitle>
        </div>
        <CardDescription className="mt-1">
          Computed severity scores across {total} incident{total === 1 ? '' : 's'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {total === 0 ? (
          <p className="text-xs text-slate-400 py-6 text-center">
            No incidents exist yet. Incidents are created from scored windows via{' '}
            <span className="font-mono text-cyan-400">POST /incidents</span>.
          </p>
        ) : (
          <>
            <div className="space-y-3">
              {rows.map((row) => (
                <div key={row.band} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant={scoreBandVariant(row.band)} size="sm">
                        {row.band}
                      </Badge>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {row.count} incident{row.count === 1 ? '' : 's'}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-300">
                      {row.count > 0 ? `avg ${row.avgSeverity.toFixed(1)}` : '--'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="h-3 flex-1 rounded-full overflow-hidden bg-slate-800/60">
                      <div
                        className={`h-full bg-linear-to-r ${BAND_BAR[row.band]} transition-all duration-300`}
                        style={{ width: `${(row.count / maxCount) * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 w-24 text-right">
                      {row.exposure > 0 ? formatCurrency(row.exposure) : '--'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <DataCaveat>
              Bands are display groupings of the computed 0-100 severity score (Section 3.1
              thresholds). Exposure is the sum of each incident's own affected-claim amounts.
            </DataCaveat>
          </>
        )}
      </CardContent>
    </Card>
  );
};
