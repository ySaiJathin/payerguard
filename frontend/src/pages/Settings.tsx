import React, { useMemo, useState } from 'react';
import { Shield, Server, Lock, Search } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { DataState, DataCaveat } from '../components/ui/DataState';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { useAsync } from '../hooks/useAsync';
import { qualityApi } from '../services/api';
import { BASE_URL } from '../services/apiClient';
import { qualityBandVariant } from '../utils/incidentDisplay';
import type { Band } from '../types/api';

/**
 * Read-only view of the deterministic quality rules that actually ran.
 *
 * ## Why nothing here is editable
 *
 * The previous version let you toggle rules on/off and edit thresholds. The
 * backend has no rule-configuration API at all -- Great Expectations suites
 * are defined in code (`app/quality/`), and there is no endpoint that accepts
 * a rule change. A toggle would have looked like it worked and silently
 * discarded the change on reload. So this page reports the real
 * `ExpectationCheckResult` records from the latest validation run instead, and
 * says plainly that configuration lives in code.
 *
 * The SLA policy tab is gone entirely: this dataset has no turnaround field
 * (MVP_CONTEXT.md Section 2.4), so there was no policy to configure.
 */
type SettingsTab = 'rules' | 'connection';

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('rules');
  const [bandFilter, setBandFilter] = useState<Band | ''>('');
  const [search, setSearch] = useState('');

  const quality = useAsync(() => qualityApi.results(), []);
  const checks = quality.data?.check_results ?? [];

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return checks.filter((c) => {
      if (bandFilter && c.band !== bandFilter) return false;
      if (!q) return true;
      return (
        (c.column_name ?? '').toLowerCase().includes(q) ||
        c.expectation_type.toLowerCase().includes(q) ||
        c.suite_name.toLowerCase().includes(q)
      );
    });
  }, [checks, bandFilter, search]);

  const bandCount = (band: Band) => checks.filter((c) => c.band === band).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Configuration
            </h1>
            <Badge variant="neutral" size="sm">
              Read-only
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Quality rules and backend connection. Nothing on this page is editable — see the note
            below.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto text-xs font-medium">
        {(
          [
            ['rules', 'Data Quality Rules', <Shield key="a" className="w-3.5 h-3.5" />],
            ['connection', 'Backend Connection', <Server key="b" className="w-3.5 h-3.5" />],
          ] as const
        ).map(([key, label, icon]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as SettingsTab)}
            className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
              activeTab === key
                ? 'border-cyan-500 text-cyan-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {icon}
            {label}
            {key === 'rules' && checks.length > 0 && ` (${checks.length})`}
          </button>
        ))}
      </div>

      {activeTab === 'rules' && (
        <DataState
          loading={quality.loading}
          error={quality.error}
          notComputed={quality.notComputed}
          label="Quality validation results"
          producedBy="POST /quality/validate"
        >
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 flex items-start gap-2.5 text-xs">
              <Lock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-slate-300 leading-relaxed">
                <span className="font-semibold text-slate-100">These rules are not editable.</span>{' '}
                Great Expectations suites are defined in backend code and the API exposes no
                rule-configuration endpoint. What follows is the real outcome of the most recent
                validation run, not a settings form.
              </div>
            </div>

            {/* Band summary */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-semibold block">Checks Run</span>
                <span className="text-xl font-bold font-mono text-white mt-1 block">{checks.length}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/50">
                <span className="text-[11px] text-emerald-300 uppercase font-semibold block">Pass</span>
                <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">{bandCount('PASS')}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/50">
                <span className="text-[11px] text-amber-300 uppercase font-semibold block">Warning</span>
                <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">{bandCount('WARNING')}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60">
                <span className="text-[11px] text-rose-300 uppercase font-semibold block">Critical</span>
                <span className="text-xl font-bold font-mono text-rose-400 mt-1 block">{bandCount('CRITICAL')}</span>
              </div>
            </div>

            {/* Filters */}
            <Card className="p-4 bg-slate-900/70">
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="relative w-full sm:w-72">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Filter by column, type, or suite..."
                    className="w-full bg-slate-950/70 border border-slate-800 focus:border-cyan-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none font-mono"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 font-medium">Band:</span>
                  <select
                    value={bandFilter}
                    onChange={(e) => setBandFilter(e.target.value as Band | '')}
                    className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="">All bands</option>
                    <option value="PASS">PASS</option>
                    <option value="WARNING">WARNING</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
                <span className="text-xs text-slate-400 font-mono sm:ml-auto">
                  Showing <span className="text-white font-bold">{filtered.length}</span>
                </span>
              </div>
            </Card>

            {/* Check table */}
            <Card>
              <CardContent className="p-0 max-h-[32rem] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Column</TableHead>
                      <TableHead>Expectation</TableHead>
                      <TableHead>Suite</TableHead>
                      <TableHead>Computed Value</TableHead>
                      <TableHead>Threshold</TableHead>
                      <TableHead>Band</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.slice(0, 300).map((check) => (
                      <TableRow key={check.check_id}>
                        <TableCell className="font-mono text-xs text-cyan-400">
                          {check.column_name ?? <span className="text-slate-500">(dataset)</span>}
                        </TableCell>
                        <TableCell className="text-xs text-slate-200">
                          {check.expectation_type.replace(/_/g, ' ')}
                        </TableCell>
                        <TableCell className="font-mono text-[11px] text-slate-400">
                          {check.suite_name}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-slate-100">
                          {check.computed_rate_or_count.toFixed(4)}
                        </TableCell>
                        <TableCell className="font-mono text-[10px] text-slate-400">
                          {Object.entries(check.threshold_used)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(' ')}
                        </TableCell>
                        <TableCell>
                          <Badge variant={qualityBandVariant(check.band)} size="sm">
                            {check.band}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {filtered.length > 300 && (
              <DataCaveat>
                Showing the first 300 of {filtered.length} matching checks. Narrow the filter to see
                the rest — nothing is aggregated away, only paged.
              </DataCaveat>
            )}
          </div>
        </DataState>
      )}

      {activeTab === 'connection' && (
        <Card>
          <CardHeader>
            <CardTitle>Backend Connection</CardTitle>
            <CardDescription>Where this UI is reading from</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] uppercase text-slate-400 block">API base URL</span>
              <span className="font-mono text-cyan-400">{BASE_URL}</span>
              <p className="text-slate-400 mt-1.5 leading-relaxed">
                Set via <span className="font-mono text-slate-300">VITE_API_BASE_URL</span> in{' '}
                <span className="font-mono text-slate-300">frontend/.env</span>. The backend allows
                this origin through CORS.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] uppercase text-slate-400 block mb-1.5">
                Endpoints this UI consumes
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 font-mono text-[11px] text-slate-300">
                {[
                  'GET /quality/results',
                  'GET /baseline',
                  'GET /anomaly/results',
                  'GET /risk/benchmark/results',
                  'GET /incidents',
                  'GET /llm/investigations/{id}',
                  'GET /history/{type}/{id}',
                  'POST /hitl/{id}/accept',
                  'POST /hitl/{id}/reject',
                  'POST /hitl/{id}/recalculate',
                ].map((ep) => (
                  <span key={ep}>{ep}</span>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Settings;
