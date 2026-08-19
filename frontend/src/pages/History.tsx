import React from 'react';
import { useNavigate } from 'react-router-dom';
import { History as HistoryIcon, RefreshCw, Search, ArrowRight, Layers } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { DataState } from '../components/ui/DataState';
import { useAsync } from '../hooks/useAsync';
import { demoApi, incidentsApi } from '../services/api';
import { formatNumber } from '../utils/formatters';
import {
  ALL_INCIDENT_STATUSES,
  bandForScore,
  injectionTypeLabel,
  scoreBandVariant,
  statusDisplay,
  type ScoreBand,
} from '../utils/incidentDisplay';
import type { IncidentAnalysisContext, Incident, IncidentStatus } from '../types/api';

/**
 * Incident history: every incident this installation has ever produced, from
 * every run -- the initial batches, Simulator runs (injected or not) and file
 * uploads alike -- not just the most recent one.
 *
 * This page absorbed what the removed standalone Incidents page used to show.
 * "Investigate" routes to the incident detail view, which is where it always
 * went; only the page that links to it has changed.
 *
 * The run list above the table is the other half of "history": which batches
 * were put through the pipeline, when, and what each produced.
 */

const BANDS: ScoreBand[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

function analysisContext(incident: Incident): IncidentAnalysisContext | null {
  return (incident.evidence_snapshot?.analysis_context as IncidentAnalysisContext | undefined) ?? null;
}

export const History: React.FC = () => {
  const navigate = useNavigate();

  const incidents = useAsync(() => incidentsApi.list(), []);
  const runs = useAsync(() => demoApi.runs(25), []);

  const [query, setQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<IncidentStatus | ''>('');
  const [bandFilter, setBandFilter] = React.useState<ScoreBand | ''>('');

  const all = incidents.data ?? [];

  const rows = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    return all
      .filter((incident) => {
        if (statusFilter && incident.status !== statusFilter) return false;
        const band = bandForScore(incident.severity_result?.severity ?? 0);
        if (bandFilter && band !== bandFilter) return false;
        if (!needle) return true;
        const context = analysisContext(incident);
        return (
          incident.incident_id.toLowerCase().includes(needle) ||
          incident.window_id.toLowerCase().includes(needle) ||
          (context?.batch_label ?? '').toLowerCase().includes(needle) ||
          (context?.detected_anomaly_type ?? '').toLowerCase().includes(needle)
        );
      })
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  }, [all, query, statusFilter, bandFilter]);

  const bandCounts = BANDS.map((band) => ({
    band,
    count: all.filter((incident) => bandForScore(incident.severity_result?.severity ?? 0) === band)
      .length,
  }));

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* ---------------- header ---------------- */}
      <div className="flex flex-col gap-4 pb-2 border-b border-slate-800/80 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white font-heading sm:text-2xl">
              Incident History
            </h1>
            <Badge variant="info" size="sm">
              {formatNumber(all.length)} total
            </Badge>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Every incident across every pipeline run &mdash; batches, simulations and uploads.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            incidents.reload();
            runs.reload();
          }}
          isLoading={incidents.loading || runs.loading}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          Refresh
        </Button>
      </div>

      {/* ---------------- band summary ---------------- */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {bandCounts.map(({ band, count }) => (
          <button
            key={band}
            onClick={() => setBandFilter((current) => (current === band ? '' : band))}
            className={`p-3 rounded-xl border text-left transition-colors ${
              bandFilter === band
                ? 'bg-cyan-600/10 border-cyan-500/40'
                : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">
              {band}
            </span>
            <span className="text-lg font-bold text-white font-mono">{count}</span>
          </button>
        ))}
      </div>

      {/* ---------------- pipeline runs ---------------- */}
      <DataState
        loading={runs.loading}
        error={runs.error}
        notComputed={runs.notComputed}
        label="Pipeline runs"
        producedBy="POST /demo/pipeline/run, POST /demo/simulation/start, POST /demo/upload"
      >
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-slate-900 border border-slate-800 text-cyan-400">
                <Layers className="w-4 h-4" />
              </div>
              <CardTitle>Pipeline runs</CardTitle>
            </div>
            <CardDescription className="mt-1">
              What was ingested, when, and what each run produced.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-left text-slate-400 border-b border-slate-800">
                    <th className="py-2 pr-3 font-semibold">Completed</th>
                    <th className="py-2 pr-3 font-semibold">Batch</th>
                    <th className="py-2 pr-3 font-semibold">Source</th>
                    <th className="py-2 pr-3 font-semibold text-right">Claims</th>
                    <th className="py-2 pr-3 font-semibold text-right">Quality</th>
                    <th className="py-2 pr-3 font-semibold text-right">Detection F1</th>
                    <th className="py-2 font-semibold text-right">Incidents</th>
                  </tr>
                </thead>
                <tbody>
                  {(runs.data ?? []).map((run) => (
                    <tr key={run.run_id} className="border-b border-slate-800/60 last:border-0">
                      <td className="py-2 pr-3 font-mono text-slate-400">
                        {new Date(run.completed_at).toLocaleString()}
                      </td>
                      <td className="py-2 pr-3 text-slate-200">
                        {run.batch_label}
                        {run.injection_applied && (
                          <span className="ml-1.5 text-[10px] text-amber-400">+injected</span>
                        )}
                      </td>
                      <td className="py-2 pr-3 font-mono text-slate-400">{run.source}</td>
                      <td className="py-2 pr-3 text-right font-mono text-slate-300">
                        {formatNumber(run.claims)}
                      </td>
                      <td className="py-2 pr-3 text-right font-mono text-slate-300">
                        {run.quality_composite_score.toFixed(1)}
                      </td>
                      <td className="py-2 pr-3 text-right font-mono text-amber-300">
                        {run.anomaly.f1.toFixed(3)}
                      </td>
                      <td className="py-2 text-right font-mono text-slate-300">
                        {run.incident_ids.length}
                      </td>
                    </tr>
                  ))}
                  {(runs.data ?? []).length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-6 text-center text-slate-500">
                        No pipeline runs recorded yet. Start one from the Simulator.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </DataState>

      {/* ---------------- incident table ---------------- */}
      <DataState
        loading={incidents.loading}
        error={incidents.error}
        notComputed={incidents.notComputed}
        label="Incidents"
        producedBy="the pipeline's incident generation step"
      >
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-rose-950/80 border border-rose-800/50 text-rose-400">
                  <HistoryIcon className="w-4 h-4" />
                </div>
                <CardTitle>All incidents</CardTitle>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search id, window, batch, type"
                    className="pl-7 pr-2 py-1.5 w-56 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-600"
                  />
                </div>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as IncidentStatus | '')}
                  className="py-1.5 px-2 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-200 focus:outline-none focus:border-slate-600"
                >
                  <option value="">All statuses</option>
                  {ALL_INCIDENT_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {statusDisplay(status).label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-left text-slate-400 border-b border-slate-800">
                    <th className="py-2 pr-3 font-semibold">Created</th>
                    <th className="py-2 pr-3 font-semibold">Window</th>
                    <th className="py-2 pr-3 font-semibold">Batch</th>
                    <th className="py-2 pr-3 font-semibold">Detected type</th>
                    <th className="py-2 pr-3 font-semibold text-right">Risk</th>
                    <th className="py-2 pr-3 font-semibold">Severity</th>
                    <th className="py-2 pr-3 font-semibold">Status</th>
                    <th className="py-2 font-semibold" />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((incident) => {
                    const context = analysisContext(incident);
                    const severity = incident.severity_result?.severity ?? 0;
                    const band = bandForScore(severity);
                    const status = statusDisplay(incident.status);
                    return (
                      <tr
                        key={incident.incident_id}
                        className="border-b border-slate-800/60 last:border-0 hover:bg-slate-900/40"
                      >
                        <td className="py-2 pr-3 font-mono text-slate-400">
                          {new Date(incident.created_at).toLocaleString()}
                        </td>
                        <td className="py-2 pr-3 font-mono text-slate-200">{incident.window_id}</td>
                        <td className="py-2 pr-3 text-slate-300">{context?.batch_label ?? '--'}</td>
                        <td className="py-2 pr-3 text-slate-300">
                          {context?.detected_anomaly_type
                            ? injectionTypeLabel(context.detected_anomaly_type)
                            : 'No dominant type'}
                        </td>
                        <td className="py-2 pr-3 text-right font-mono text-slate-200">
                          {incident.risk_score.toFixed(0)}
                        </td>
                        <td className="py-2 pr-3">
                          <Badge variant={scoreBandVariant(band)} size="sm">
                            {severity.toFixed(0)} {band}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3">
                          <Badge variant={status.variant} size="sm">
                            {status.label}
                          </Badge>
                        </td>
                        <td className="py-2 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/investigation/${incident.incident_id}`)}
                            rightIcon={<ArrowRight className="w-3 h-3" />}
                          >
                            Investigate
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-slate-500">
                        {all.length === 0
                          ? 'No incidents yet. Run a batch from the Simulator to produce some.'
                          : 'No incidents match the current filters.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </DataState>
    </div>
  );
};

export default History;
