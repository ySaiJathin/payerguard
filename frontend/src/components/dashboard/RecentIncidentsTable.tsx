import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../ui/Table';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { EmptyState } from '../ui/EmptyState';
import { ChevronRight, AlertOctagon } from 'lucide-react';
import { formatShortDate } from '../../utils/formatters';
import { bandForScore, scoreBandVariant, statusDisplay } from '../../utils/incidentDisplay';
import type { Incident } from '../../types/api';

/**
 * The most recent real incidents, newest first.
 *
 * Every column maps to a field the backend actually returns: window id,
 * computed priority/severity/risk, and the real status vocabulary. There is no
 * payer, claim number, or assignee column -- the backend models incidents at
 * *window* grain and has no assignment concept, so those columns had nothing
 * behind them.
 */
interface RecentIncidentsTableProps {
  incidents: Incident[];
  limit?: number;
}

export const RecentIncidentsTable: React.FC<RecentIncidentsTableProps> = ({
  incidents,
  limit = 8,
}) => {
  const navigate = useNavigate();

  const recent = [...incidents]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-rose-950/80 border border-rose-800/50 text-rose-400">
            <AlertOctagon className="w-4 h-4" />
          </div>
          <CardTitle>Recent Incidents</CardTitle>
        </div>
        <CardDescription className="mt-1">
          Newest scored windows escalated into incidents
        </CardDescription>
      </CardHeader>

      <CardContent className="p-0">
        {recent.length === 0 ? (
          <EmptyState
            title="No incidents yet"
            description="Incidents are created from scored windows. None exist in the backend right now."
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
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((incident) => {
                const priority = incident.priority_result?.priority ?? 0;
                const severity = incident.severity_result?.severity ?? 0;
                const status = statusDisplay(incident.status);
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
                      {severity.toFixed(1)}
                    </TableCell>

                    <TableCell className="font-mono text-xs text-slate-200">
                      {incident.risk_score.toFixed(1)}
                    </TableCell>

                    <TableCell className="font-mono text-xs text-slate-200">
                      {incident.quality_score.toFixed(1)}
                    </TableCell>

                    <TableCell>
                      <Badge variant={status.variant} size="sm">
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
  );
};
