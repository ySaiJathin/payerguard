import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../ui/Card';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../ui/Table';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import {
  DashboardIncidentItem,
  DashboardSeverity,
  DashboardIncidentStatus,
} from '../../data/mockDashboardData';
import {
  ChevronRight,
  ArrowUpRight,
  Search,
  Filter,
  AlertOctagon,
  Clock,
} from 'lucide-react';
import { formatNumber } from '../../utils/formatters';

interface RecentIncidentsTableProps {
  incidents: DashboardIncidentItem[];
}

export const RecentIncidentsTable: React.FC<RecentIncidentsTableProps> = ({
  incidents,
}) => {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter !== 'all' && inc.status !== statusFilter) return false;
    if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesId = inc.id.toLowerCase().includes(q);
      const matchesType = inc.type.toLowerCase().includes(q);
      const matchesPayer = inc.payer.toLowerCase().includes(q);
      if (!matchesId && !matchesType && !matchesPayer) return false;
    }
    return true;
  });

  const getSeverityBadge = (severity: DashboardSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return (
          <Badge variant="danger" size="sm" dot pulse>
            CRITICAL
          </Badge>
        );
      case 'HIGH':
        return (
          <Badge variant="warning" size="sm" dot>
            HIGH
          </Badge>
        );
      case 'MEDIUM':
        return (
          <Badge variant="info" size="sm">
            MEDIUM
          </Badge>
        );
      case 'LOW':
        return (
          <Badge variant="neutral" size="sm">
            LOW
          </Badge>
        );
    }
  };

  const getStatusBadge = (status: DashboardIncidentStatus) => {
    switch (status) {
      case 'Detected':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/70 text-rose-300 border border-rose-800/50">
            Detected
          </span>
        );
      case 'Investigating':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/70 text-amber-300 border border-amber-800/50">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            Investigating
          </span>
        );
      case 'Awaiting Review':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-950/70 text-cyan-300 border border-cyan-800/50">
            Awaiting Review
          </span>
        );
      case 'Resolved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-800/50">
            Resolved
          </span>
        );
    }
  };

  const getSLARiskDisplay = (slaRisk: string, percent: number) => {
    const isBreached = slaRisk.includes('Breached') || percent >= 95;
    const isHigh = percent >= 70;
    const isModerate = percent >= 30;

    return (
      <div className="flex flex-col">
        <span
          className={`font-mono text-xs font-bold ${
            isBreached
              ? 'text-rose-400'
              : isHigh
              ? 'text-amber-400'
              : isModerate
              ? 'text-cyan-300'
              : 'text-emerald-400'
          }`}
        >
          {slaRisk}
        </span>
        <div className="w-20 bg-slate-800 rounded-full h-1 mt-1 overflow-hidden">
          <div
            className={`h-full rounded-full ${
              isBreached
                ? 'bg-rose-500'
                : isHigh
                ? 'bg-amber-500'
                : isModerate
                ? 'bg-cyan-500'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-rose-950/80 border border-rose-800/50 text-rose-400">
              <AlertOctagon className="w-4 h-4" />
            </div>
            <CardTitle>Recent Incidents</CardTitle>
            <Badge variant="neutral" size="sm" className="font-mono">
              {filteredIncidents.length} of {incidents.length}
            </Badge>
          </div>
          <CardDescription className="mt-1">
            Active and remediated healthcare claims defects with SLA exposure and investigation routing
          </CardDescription>
        </div>

        {/* Filter controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search incidents or payers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-cyan-500 w-44 sm:w-56 transition-colors"
            />
          </div>

          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-hidden focus:border-cyan-500 font-mono"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-hidden focus:border-cyan-500 font-mono"
          >
            <option value="all">All Statuses</option>
            <option value="Detected">Detected</option>
            <option value="Investigating">Investigating</option>
            <option value="Awaiting Review">Awaiting Review</option>
            <option value="Resolved">Resolved</option>
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/incidents')}
            rightIcon={<ArrowUpRight className="w-3.5 h-3.5" />}
          >
            All Incidents
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-28">Incident ID</TableHead>
              <TableHead>Incident Type</TableHead>
              <TableHead className="w-32">Affected Claims</TableHead>
              <TableHead className="w-28">Severity</TableHead>
              <TableHead className="w-36">SLA Risk</TableHead>
              <TableHead className="w-36">Status</TableHead>
              <TableHead className="w-24">Time</TableHead>
              <TableHead className="w-20 text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredIncidents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-slate-400">
                  No incidents match the active filter criteria.
                </TableCell>
              </TableRow>
            ) : (
              filteredIncidents.map((incident) => (
                <TableRow
                  key={incident.id}
                  onClick={() => navigate(`/investigation/${incident.id}`)}
                  className="cursor-pointer group hover:bg-slate-850/60 transition-colors"
                >
                  {/* Incident ID */}
                  <TableCell>
                    <span className="font-mono font-bold text-cyan-400 group-hover:text-cyan-300 group-hover:underline">
                      {incident.id}
                    </span>
                  </TableCell>

                  {/* Incident Type */}
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold text-slate-100 group-hover:text-white line-clamp-1">
                        {incident.type}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono flex items-center gap-2 mt-0.5">
                        <span>{incident.payer}</span>
                        <span>·</span>
                        <span className="text-slate-400">{incident.summary}</span>
                      </span>
                    </div>
                  </TableCell>

                  {/* Affected Claims */}
                  <TableCell>
                    <span className="font-mono text-xs font-medium text-slate-200">
                      {formatNumber(incident.affectedClaims)} claims
                    </span>
                  </TableCell>

                  {/* Severity */}
                  <TableCell>
                    {getSeverityBadge(incident.severity)}
                  </TableCell>

                  {/* SLA Risk */}
                  <TableCell>
                    {getSLARiskDisplay(incident.slaRisk, incident.slaRiskPercent)}
                  </TableCell>

                  {/* Status */}
                  <TableCell>
                    {getStatusBadge(incident.status)}
                  </TableCell>

                  {/* Time */}
                  <TableCell>
                    <span className="font-mono text-[11px] text-slate-400">
                      {incident.time}
                    </span>
                  </TableCell>

                  {/* Action */}
                  <TableCell className="text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/investigation/${incident.id}`);
                      }}
                      className="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
                      title="Open Root Cause Investigation"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};
