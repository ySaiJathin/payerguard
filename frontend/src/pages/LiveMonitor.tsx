import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  Pause,
  Trash2,
  Filter,
  Search,
  Activity,
  Zap,
  Clock,
  AlertOctagon,
  ShieldCheck,
  Eye,
  SlidersHorizontal,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { StatusIndicator } from '../components/ui/StatusIndicator';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { useLiveStream } from '../hooks/useLiveStream';
import { mockClaims } from '../data/mockClaims';
import { ClaimRecord, PayerName } from '../types';
import { formatCurrency, formatShortDate, getClaimStatusBadge, getSLAStatusBadge } from '../utils/formatters';

export const LiveMonitor: React.FC = () => {
  const navigate = useNavigate();

  // Use the live stream hook with initial claims
  const {
    claims,
    isRunning,
    speed,
    stats,
    setSpeed,
    toggleRunning,
    clearStream,
    injectAnomaly,
  } = useLiveStream({
    autoStart: true,
    intervalMs: 2500,
    maxStoredClaims: 80,
    initialClaims: mockClaims,
  });

  // Local filter states
  const [payerFilter, setPayerFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedClaim, setSelectedClaim] = useState<ClaimRecord | null>(null);

  // Filtered claims list
  const filteredClaims = claims.filter((claim) => {
    if (payerFilter !== 'all' && claim.payer !== payerFilter) return false;
    if (statusFilter === 'clean' && claim.status !== 'clean') return false;
    if (statusFilter === 'flagged' && claim.status !== 'flagged') return false;
    if (statusFilter === 'rejected' && claim.status !== 'rejected') return false;
    if (statusFilter === 'sla_risk' && claim.slaStatus === 'on_track') return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesId = claim.id.toLowerCase().includes(q) || claim.claimNumber.toLowerCase().includes(q);
      const matchesPatient = claim.patientName.toLowerCase().includes(q);
      const matchesProvider = claim.providerName.toLowerCase().includes(q) || claim.providerNpi.includes(q);
      if (!matchesId && !matchesPatient && !matchesProvider) return false;
    }

    return true;
  });

  const speedOptions = [
    { label: '0.5x (Slow)', value: 4000 },
    { label: '1x (Normal)', value: 2500 },
    { label: '2x (Fast)', value: 1200 },
    { label: '5x (Turbo)', value: 500 },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Stream Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Live Claims Ingestion & SLA Monitor
            </h1>
            <StatusIndicator
              status={isRunning ? 'operational' : 'inactive'}
              label={isRunning ? 'Streaming Live' : 'Paused'}
              size="sm"
            />
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Continuous real-time evaluation of EDI 837/CMS-1500 payloads across connected health plans and clearinghouse gateways.
          </p>
        </div>

        {/* Live Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant={isRunning ? 'secondary' : 'primary'}
            size="sm"
            onClick={toggleRunning}
            leftIcon={isRunning ? <Pause className="w-3.5 h-3.5 text-amber-400" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
          >
            {isRunning ? 'Pause Stream' : 'Resume Stream'}
          </Button>

          {/* Speed Selector */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-1 flex items-center gap-1 text-xs">
            {speedOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSpeed(opt.value)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-all ${
                  speed === opt.value
                    ? 'bg-slate-800 text-cyan-300 shadow-xs'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={clearStream}
            leftIcon={<Trash2 className="w-3.5 h-3.5 text-slate-400" />}
          >
            Clear
          </Button>

          <Button
            variant="subtle"
            size="sm"
            onClick={() => injectAnomaly('missing_npi')}
            leftIcon={<Sparkles className="w-3.5 h-3.5 text-cyan-400" />}
          >
            Inject Anomaly
          </Button>
        </div>
      </div>

      {/* Live Telemetry Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[11px] uppercase font-semibold text-slate-400 block">
              Stream Throughput
            </span>
            <span className="text-xl font-bold font-mono text-white mt-1 block">
              {stats.throughputPerSec} <span className="text-xs text-slate-400 font-normal">claims/sec</span>
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800/80 text-cyan-400">
            <Zap className="w-5 h-5" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[11px] uppercase font-semibold text-slate-400 block">
              Avg Validation Latency
            </span>
            <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">
              {stats.avgLatencyMs} <span className="text-xs text-slate-400 font-normal">ms</span>
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[11px] uppercase font-semibold text-slate-400 block">
              Total Streamed (Session)
            </span>
            <span className="text-xl font-bold font-mono text-white mt-1 block">
              {claims.length} <span className="text-xs text-slate-400 font-normal">records</span>
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800/80 text-indigo-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[11px] uppercase font-semibold text-slate-400 block">
              Anomalies Flagged
            </span>
            <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">
              {claims.filter((c) => c.status !== 'clean').length} <span className="text-xs text-slate-400 font-normal">flagged</span>
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-amber-950/60 text-amber-400 border border-amber-800/40">
            <AlertOctagon className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
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
                placeholder="Filter by Claim ID, Patient, NPI..."
                className="w-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none font-mono"
              />
            </div>

            {/* Payer Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Payer:</span>
              <select
                value={payerFilter}
                onChange={(e) => setPayerFilter(e.target.value)}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Payers</option>
                <option value="Medicare CMS">Medicare CMS</option>
                <option value="UnitedHealthcare">UnitedHealthcare</option>
                <option value="Anthem BlueCross">Anthem BlueCross</option>
                <option value="Aetna Health">Aetna Health</option>
                <option value="Cigna Healthcare">Cigna Healthcare</option>
                <option value="Humana">Humana</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Quality:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Statuses</option>
                <option value="clean">Clean First-Pass</option>
                <option value="flagged">DQ Flagged</option>
                <option value="rejected">Rejected</option>
                <option value="sla_risk">SLA At Risk / Breached</option>
              </select>
            </div>
          </div>

          <div className="text-xs text-slate-400 font-mono self-end md:self-center">
            Showing <span className="text-white font-bold">{filteredClaims.length}</span> of {claims.length} claims
          </div>
        </div>
      </Card>

      {/* Streaming Claims Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Live Ingestion Feed
            </CardTitle>
            <CardDescription>
              Real-time transaction stream with automated anomaly confidence scoring
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {filteredClaims.length === 0 ? (
            <EmptyState
              title="No claims matching filter"
              description="Try adjusting your payer or quality filter criteria, or click Inject Anomaly to simulate incoming traffic."
              actionLabel="Reset Filters"
              onAction={() => {
                setPayerFilter('all');
                setStatusFilter('all');
                setSearchQuery('');
              }}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Claim ID & Timestamp</TableHead>
                  <TableHead>Payer & Standard</TableHead>
                  <TableHead>Patient & Provider</TableHead>
                  <TableHead>Billed Amount</TableHead>
                  <TableHead>Anomaly Score</TableHead>
                  <TableHead>DQ & SLA Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredClaims.map((claim, idx) => {
                  const statusBadge = getClaimStatusBadge(claim.status);
                  const slaBadge = getSLAStatusBadge(claim.slaStatus);
                  const isHighAnomaly = claim.anomalyScore > 0.6;

                  return (
                    <TableRow
                      key={`${claim.id}-${idx}`}
                      className={idx === 0 && isRunning ? 'bg-cyan-950/20 transition-colors duration-500' : ''}
                    >
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-mono font-bold text-slate-100">{claim.id}</span>
                          <span className="text-[10px] text-slate-400 font-mono">{formatShortDate(claim.receivedAt)}</span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-col">
                          <span className="text-slate-200 font-medium">{claim.payer}</span>
                          <span className="text-[10px] text-slate-400 font-mono">{claim.ediStandard}</span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-col">
                          <span className="text-slate-200">{claim.patientName}</span>
                          <span className="text-[11px] text-slate-400 font-mono truncate max-w-[180px]">
                            {claim.providerName}
                          </span>
                        </div>
                      </TableCell>

                      <TableCell className="font-mono font-semibold text-slate-200">
                        {formatCurrency(claim.billedAmount)}
                      </TableCell>

                      <TableCell>
                        <div className="flex items-center gap-2 font-mono">
                          <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full ${isHighAnomaly ? 'bg-rose-500' : claim.anomalyScore > 0.2 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                              style={{ width: `${claim.anomalyScore * 100}%` }}
                            />
                          </div>
                          <span className={`text-xs font-bold ${isHighAnomaly ? 'text-rose-400' : 'text-slate-300'}`}>
                            {claim.anomalyScore.toFixed(2)}
                          </span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <Badge variant={statusBadge.variant} size="sm">
                            {statusBadge.label}
                          </Badge>
                          <span className={`text-[10px] font-mono ${slaBadge.color}`}>
                            {slaBadge.label}
                          </span>
                        </div>
                      </TableCell>

                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => setSelectedClaim(claim)}
                            leftIcon={<Eye className="w-3 h-3" />}
                          >
                            Inspect
                          </Button>
                          {claim.violations.length > 0 && (
                            <Button
                              variant="danger"
                              size="xs"
                              onClick={() => navigate(`/investigation/INC-${claim.id.replace('CLM-2026-', '')}`)}
                            >
                              Audit
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Claim Detail Modal */}
      {selectedClaim && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedClaim(null)}
          title={`EDI Claim Inspector: ${selectedClaim.id}`}
          description={`Payer: ${selectedClaim.payer} | Format: ${selectedClaim.ediStandard} | Billed: ${formatCurrency(selectedClaim.billedAmount)}`}
          size="xl"
          footer={
            <>
              <Button variant="secondary" size="sm" onClick={() => setSelectedClaim(null)}>
                Close
              </Button>
              {selectedClaim.violations.length > 0 && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    setSelectedClaim(null);
                    navigate(`/investigation/INC-${selectedClaim.id.replace('CLM-2026-', '')}`);
                  }}
                  rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
                >
                  Proceed to Investigation Room
                </Button>
              )}
            </>
          }
        >
          <div className="space-y-4 text-xs">
            {/* Meta header */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div>
                <span className="text-slate-400 block text-[10px]">Patient</span>
                <span className="font-semibold text-slate-200">{selectedClaim.patientName}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Billing Provider NPI</span>
                <span className="font-mono text-slate-200 font-semibold">{selectedClaim.providerNpi}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Primary Diagnosis</span>
                <span className="font-mono text-slate-200">{selectedClaim.primaryDiagnosis}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">SLA Status</span>
                <Badge variant={getSLAStatusBadge(selectedClaim.slaStatus).variant} size="sm">
                  {getSLAStatusBadge(selectedClaim.slaStatus).label}
                </Badge>
              </div>
            </div>

            {/* Violations notice */}
            {selectedClaim.violations.length > 0 ? (
              <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 space-y-2">
                <div className="flex items-center gap-2 text-rose-300 font-semibold">
                  <AlertOctagon className="w-4 h-4" />
                  <span>{selectedClaim.violations.length} Data Quality Violations Flagged</span>
                </div>
                {selectedClaim.violations.map((v, i) => (
                  <div key={i} className="pl-6 text-[11px] text-rose-200/90 space-y-0.5">
                    <p className="font-semibold text-rose-300">• {v.ruleName} ({v.ruleCode})</p>
                    <p className="text-slate-300">{v.message}</p>
                    <p className="text-cyan-300 font-mono">Remediation: {v.remediationSuggestion}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/50 flex items-center gap-2 text-emerald-300">
                <ShieldCheck className="w-4 h-4" />
                <span>Zero Data Quality or Coding Violations. 100% Clean Pass.</span>
              </div>
            )}

            {/* Line items */}
            <div>
              <span className="font-semibold text-slate-300 block mb-2">Service Line Items (Loop 2400)</span>
              <div className="border border-slate-800 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-2">Line</th>
                      <th className="p-2">CPT / HCPCS</th>
                      <th className="p-2">Units</th>
                      <th className="p-2">Charge</th>
                      <th className="p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {selectedClaim.lineItems.map((item) => (
                      <tr key={item.lineNumber} className="hover:bg-slate-800/30">
                        <td className="p-2 text-slate-400">#{item.lineNumber}</td>
                        <td className="p-2 text-slate-200">
                          {item.cptCode}
                          {item.modifiers && <span className="text-cyan-400 ml-1">-{item.modifiers.join(',-')}</span>}
                        </td>
                        <td className="p-2 text-slate-400">{item.units}</td>
                        <td className="p-2 font-semibold text-white">{formatCurrency(item.charge)}</td>
                        <td className="p-2">
                          <Badge variant={item.status === 'valid' ? 'success' : 'danger'} size="sm">
                            {item.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
