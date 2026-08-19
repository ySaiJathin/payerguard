import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertOctagon,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Filter,
  Search,
  ChevronRight,
  Shield,
  User,
  ArrowUpDown,
  FileCheck
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { EmptyState } from '../components/ui/EmptyState';
import { mockIncidents } from '../data/mockIncidents';
import { Incident, IncidentSeverity, IncidentStatus, SLAStatus } from '../types';
import { formatCurrency, formatShortDate, getIncidentStatusBadge, getSeverityColor, getSLAStatusBadge } from '../utils/formatters';

export const Incidents: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialSearch = searchParams.get('search') || '';

  const [incidents, setIncidents] = useState<Incident[]>(mockIncidents);
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [slaFilter, setSlaFilter] = useState<string>('all');

  const filteredIncidents = incidents.filter((inc) => {
    if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
    if (statusFilter !== 'all' && inc.status !== statusFilter) return false;
    if (slaFilter !== 'all' && inc.slaStatus !== slaFilter) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = inc.id.toLowerCase().includes(q) || inc.claimNumber.toLowerCase().includes(q);
      const matchTitle = inc.title.toLowerCase().includes(q) || inc.description.toLowerCase().includes(q);
      const matchPayer = inc.payer.toLowerCase().includes(q);
      if (!matchId && !matchTitle && !matchPayer) return false;
    }

    return true;
  });

  const criticalCount = incidents.filter((i) => i.severity === 'critical').length;
  const atRiskCount = incidents.filter((i) => i.slaStatus === 'at_risk').length;
  const breachedCount = incidents.filter((i) => i.slaStatus === 'breached').length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Data Quality & SLA Incident Management
            </h1>
            <Badge variant="danger" size="sm" pulse dot>
              {incidents.length} Active Tickets
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Triaged queue for EDI validation breaches, statutory SLA timeouts, and AI-flagged anomaly root-cause remediation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSearchQuery('');
              setSeverityFilter('all');
              setStatusFilter('all');
              setSlaFilter('all');
            }}
          >
            Reset Filters
          </Button>
        </div>
      </div>

      {/* Incident Status Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-semibold block">Total Open Incidents</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">{incidents.length}</span>
        </div>

        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/50">
          <span className="text-[11px] text-rose-300 uppercase font-semibold block">Critical Severity</span>
          <span className="text-xl font-bold font-mono text-rose-400 mt-1 block">{criticalCount}</span>
        </div>

        <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/50">
          <span className="text-[11px] text-amber-300 uppercase font-semibold block">SLA At Risk (&lt;30m)</span>
          <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">{atRiskCount}</span>
        </div>

        <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-700/60">
          <span className="text-[11px] text-rose-200 uppercase font-semibold block">SLA Breached</span>
          <span className="text-xl font-bold font-mono text-rose-300 mt-1 block">{breachedCount}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="p-4 bg-slate-900/70">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search Incident ID, Claim #, Title..."
                className="w-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none font-mono"
              />
            </div>

            {/* Severity Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            {/* SLA Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">SLA:</span>
              <select
                value={slaFilter}
                onChange={(e) => setSlaFilter(e.target.value)}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All SLA States</option>
                <option value="at_risk">At Risk (&lt;30m)</option>
                <option value="breached">Breached</option>
                <option value="on_track">On Track</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Ticket:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Statuses</option>
                <option value="open">Open</option>
                <option value="investigating">Investigating</option>
                <option value="escalated">Escalated</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </div>

          <div className="text-xs text-slate-400 font-mono">
            Showing <span className="text-white font-bold">{filteredIncidents.length}</span> tickets
          </div>
        </div>
      </Card>

      {/* Incidents Table */}
      <Card>
        <CardContent className="p-0">
          {filteredIncidents.length === 0 ? (
            <EmptyState
              title="No incidents found"
              description="No data quality or SLA incident tickets match your search filters."
              actionLabel="Clear Filters"
              onAction={() => {
                setSearchQuery('');
                setSeverityFilter('all');
                setStatusFilter('all');
                setSlaFilter('all');
              }}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Incident ID & Title</TableHead>
                  <TableHead>Payer & Claim #</TableHead>
                  <TableHead>Severity & Category</TableHead>
                  <TableHead>SLA Countdown</TableHead>
                  <TableHead>Assignee</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredIncidents.map((incident) => {
                  const sevColor = getSeverityColor(incident.severity);
                  const statusBadge = getIncidentStatusBadge(incident.status);
                  const slaBadge = getSLAStatusBadge(incident.slaStatus);
                  const isBreached = incident.slaStatus === 'breached';

                  return (
                    <TableRow
                      key={incident.id}
                      className="cursor-pointer hover:bg-slate-850/60"
                      onClick={() => navigate(`/investigation/${incident.id}`)}
                    >
                      <TableCell>
                        <div className="flex flex-col">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-cyan-400">{incident.id}</span>
                            <span className="text-xs font-semibold text-slate-100">{incident.title}</span>
                          </div>
                          <span className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                            {incident.description}
                          </span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-col font-mono text-xs">
                          <span className="text-slate-200 font-semibold">{incident.payer}</span>
                          <span className="text-[11px] text-slate-400">{incident.claimNumber}</span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <Badge variant={sevColor.badge} size="sm">
                            {incident.severity.toUpperCase()}
                          </Badge>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {incident.category.replace('_', ' ')}
                          </span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-col">
                          <Badge
                            variant={slaBadge.variant}
                            size="sm"
                            dot
                            pulse={isBreached || incident.slaStatus === 'at_risk'}
                          >
                            {isBreached ? 'Breached (-120m)' : `${incident.slaRemainingMinutes}m remaining`}
                          </Badge>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-cyan-300">
                            {incident.assignee.avatar || 'AU'}
                          </div>
                          <span className="text-xs text-slate-300">{incident.assignee.name}</span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <Badge variant={statusBadge.variant} size="sm">
                          {statusBadge.label}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="primary"
                          size="xs"
                          onClick={() => navigate(`/investigation/${incident.id}`)}
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
    </div>
  );
};
