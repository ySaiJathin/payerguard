import React, { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, ChevronRight, AlertOctagon } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { EmptyState } from '../components/ui/EmptyState';
import { DataState } from '../components/ui/DataState';
import { useAsync } from '../hooks/useAsync';
import { incidentsApi } from '../services/api';
import { formatShortDate } from '../utils/formatters';
import {
  ALL_INCIDENT_STATUSES,
  bandForScore,
  scoreBandVariant,
  statusDisplay,
} from '../utils/incidentDisplay';
import type { IncidentStatus } from '../types/api';

/**
 * Real incident queue backed by `GET /incidents`.
 *
 * `status` and `min_priority` are pushed to the backend because the endpoint
 * supports them natively; the free-text search is client-side, since there is
 * no search parameter on that route and inventing one would mean fetching
 * everything anyway.
 *
 * The SLA filter is gone -- see `utils/incidentDisplay.ts` for why the old
 * status vocabulary was not crosswalked onto the backend's.
 */
export const Incidents: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [statusFilter, setStatusFilter] = useState<IncidentStatus | ''>('');
  const [minPriority, setMinPriority] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') ?? '');

  const parsedMinPriority = minPriority === '' ? undefined : Number(minPriority);

  const incidents = useAsync(
    () =>
      incidentsApi.list({
        status: statusFilter || undefined,
        min_priority: Number.isFinite(parsedMinPriority) ? parsedMinPriority : undefined,
      }),
    [statusFilter, minPriority]
  );

  const all = incidents.data ?? [];

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (i) =>
        i.incident_id.toLowerCase().includes(q) ||
        i.window_id.toLowerCase().includes(q)
    );
  }, [all, searchQuery]);

  const readyForReview = all.filter((i) => i.status === 'ready_for_review').length;
  const pending = all.filter((i) => i.status === 'pending_investigation').length;
  const highPriority = all.filter((i) => (i.priority_result?.priority ?? 0) > 60).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Incident Management
            </h1>
            <Badge variant="danger" size="sm" dot>
              {all.length} total
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Window-grain incidents with computed severity, risk, business impact, and priority.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setStatusFilter('');
            setMinPriority('');
            setSearchQuery('');
          }}
        >
          Reset Filters
        </Button>
      </div>

      {/* Summary ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-semibold block">Total Incidents</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">{all.length}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/50">
          <span className="text-[11px] text-amber-300 uppercase font-semibold block">Ready for Review</span>
          <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">{readyForReview}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-sky-950/40 border border-sky-800/50">
          <span className="text-[11px] text-sky-300 uppercase font-semibold block">Pending Investigation</span>
          <span className="text-xl font-bold font-mono text-sky-400 mt-1 block">{pending}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60">
          <span className="text-[11px] text-rose-300 uppercase font-semibold block">Priority &gt; 60</span>
          <span className="text-xl font-bold font-mono text-rose-400 mt-1 block">{highPriority}</span>
        </div>
      </div>

      {/* Filter bar */}
      <Card className="p-4 bg-slate-900/70">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search incident or window id..."
                className="w-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none font-mono"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as IncidentStatus | '')}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="">All statuses</option>
                {ALL_INCIDENT_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {statusDisplay(s).label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Min priority:</span>
              <input
                type="number"
                min={0}
                max={100}
                value={minPriority}
                onChange={(e) => setMinPriority(e.target.value)}
                placeholder="0-100"
                className="w-24 bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          </div>

          <div className="text-xs text-slate-400 font-mono">
            Showing <span className="text-white font-bold">{filtered.length}</span>
          </div>
        </div>
      </Card>

      {/* Table */}
      <DataState
        loading={incidents.loading}
        error={incidents.error}
        notComputed={incidents.notComputed}
        label="Incidents"
        producedBy="POST /incidents"
      >
        <Card>
          <CardContent className="p-0">
            {filtered.length === 0 ? (
              <EmptyState
                icon={<AlertOctagon className="w-6 h-6 text-slate-500" />}
                title={all.length === 0 ? 'No incidents exist yet' : 'No incidents match your filters'}
                description={
                  all.length === 0
                    ? 'Incidents are created from scored windows via POST /incidents. The backend currently has none.'
                    : 'Adjust the status, priority, or search filters to widen the result set.'
                }
                actionLabel={all.length === 0 ? undefined : 'Clear Filters'}
                onAction={
                  all.length === 0
                    ? undefined
                    : () => {
                        setStatusFilter('');
                        setMinPriority('');
                        setSearchQuery('');
                      }
                }
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Incident / Window</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Quality</TableHead>
                    <TableHead>Business Impact</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((incident) => {
                    const priority = incident.priority_result?.priority ?? 0;
                    const status = statusDisplay(incident.status);
                    const impact = incident.business_impact_result;
                    return (
                      <TableRow
                        key={incident.incident_id}
                        className="cursor-pointer hover:bg-slate-850/60"
                        onClick={() => navigate(`/investigation/${incident.incident_id}`)}
                      >
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-mono font-bold text-cyan-400 text-xs">
                              {incident.incident_id.slice(0, 8)}
                            </span>
                            <span className="text-[11px] text-slate-400 font-mono">
                              {incident.window_id}
                            </span>
                          </div>
                        </TableCell>

                        <TableCell>
                          <Badge variant={scoreBandVariant(bandForScore(priority))} size="sm">
                            {priority.toFixed(1)}
                          </Badge>
                        </TableCell>

                        <TableCell className="font-mono text-xs text-slate-200">
                          {(incident.severity_result?.severity ?? 0).toFixed(1)}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-slate-200">
                          {incident.risk_score.toFixed(1)}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-slate-200">
                          {incident.quality_score.toFixed(1)}
                        </TableCell>

                        <TableCell className="font-mono text-xs">
                          <span className="text-slate-200">
                            {(impact?.business_impact ?? 0).toFixed(1)}
                          </span>
                          {impact?.has_unavailable_components && (
                            <span
                              className="text-[10px] text-amber-400 block"
                              title="Some impact components are not computable from this dataset"
                            >
                              partial
                            </span>
                          )}
                        </TableCell>

                        <TableCell>
                          <Badge variant={status.variant} size="sm" title={status.meaning}>
                            {status.label}
                          </Badge>
                        </TableCell>

                        <TableCell className="font-mono text-[11px] text-slate-400">
                          {formatShortDate(incident.created_at)}
                        </TableCell>

                        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="primary"
                            size="xs"
                            onClick={() => navigate(`/investigation/${incident.incident_id}`)}
                            rightIcon={<ChevronRight className="w-3 h-3" />}
                          >
                            Investigate
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </DataState>
    </div>
  );
};

export default Incidents;
