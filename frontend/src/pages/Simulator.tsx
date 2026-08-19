import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Cpu,
  Play,
  Zap,
  AlertTriangle,
  FileSpreadsheet,
  Clock,
  ShieldAlert,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Sliders,
  Sparkles,
  Layers
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { PayerName } from '../types';
import { generateRandomClaim } from '../services/streamSimulatorService';
import { claimsService } from '../services/claimsService';
import { incidentService } from '../services/incidentService';
import { formatCurrency } from '../utils/formatters';

interface SimulationScenario {
  id: string;
  name: string;
  category: string;
  severity: 'critical' | 'high' | 'medium';
  description: string;
  targetRule: string;
  expectedResult: string;
  anomalyKey: string;
}

const SCENARIOS: SimulationScenario[] = [
  {
    id: 'SCEN-01',
    name: 'Invalid Billing NPI Checksum Failure',
    category: 'NPI Registry Check',
    severity: 'critical',
    description: 'Generates a batch with provider NPI 0000000000 failing the Luhn checksum and missing from the NPPES registry.',
    targetRule: 'DQ_ERR_INVALID_BILLING_NPI',
    expectedResult: 'Immediate hard flag in Loop 2010AA, Anomaly score > 0.90, raised to Critical Incident Queue.',
    anomalyKey: 'missing_npi',
  },
  {
    id: 'SCEN-02',
    name: 'CMS NCCI Mutually Exclusive Unbundling',
    category: 'Coding Accuracy',
    severity: 'high',
    description: 'Generates an encounter with concurrent unbundled procedural line items (e.g. CPT 93000 and 93010) violating Column 1 / Column 2 edits.',
    targetRule: 'DQ_ERR_NCCI_MUTUALLY_EXCLUSIVE',
    expectedResult: 'Flagged line item 2 in Loop 2400 SV1, auto-remediation suggested: CPT 93000 Global.',
    anomalyKey: 'ncci_unbundling',
  },
  {
    id: 'SCEN-03',
    name: 'Same-Day Duplicate Service Line Submission',
    category: 'Duplicate Detection',
    severity: 'high',
    description: 'Injects identical CPT codes on the same patient and service date without required repeat procedure modifiers (76/77).',
    targetRule: 'DQ_ERR_SAME_DAY_DUPLICATE_CPT',
    expectedResult: 'Flagged duplicate encounter line, potential overpayment prevented.',
    anomalyKey: 'duplicate_cpt',
  },
  {
    id: 'SCEN-04',
    name: 'High-Dollar Statistical Charge Outlier (> $145,000)',
    category: 'Outlier Anomaly',
    severity: 'medium',
    description: 'Submits an outpatient surgical claim with billed charges exceeding the regional 99th percentile benchmark by 3.8 standard deviations.',
    targetRule: 'DQ_ERR_HIGH_DOLLAR_CHARGE_OUTLIER',
    expectedResult: 'Trigger automatic clinical audit hold and chargemaster review.',
    anomalyKey: 'high_dollar',
  },
  {
    id: 'SCEN-05',
    name: 'Payer Timely Filing Limit Breach (>365 Days)',
    category: 'Timely Filing SLA',
    severity: 'critical',
    description: 'Submits a claim with service date 465 days in the past, exceeding statutory Medicare / Commercial timely filing windows.',
    targetRule: 'DQ_ERR_TIMELY_FILING_LIMIT_EXCEEDED',
    expectedResult: 'Auto-rejection with CARC Code 29 (Timely filing expired).',
    anomalyKey: 'timely_filing',
  },
];

export const Simulator: React.FC = () => {
  const navigate = useNavigate();

  const [selectedScenario, setSelectedScenario] = useState<SimulationScenario>(SCENARIOS[0]);
  const [targetPayer, setTargetPayer] = useState<PayerName>('Medicare CMS');
  const [batchVolume, setBatchVolume] = useState<number>(5);
  const [isRunning, setIsRunning] = useState(false);
  const [executionLogs, setExecutionLogs] = useState<Array<{ timestamp: string; text: string; type: 'info' | 'warn' | 'error' | 'success' }>>([]);
  const [lastGeneratedIncidentId, setLastGeneratedIncidentId] = useState<string | null>(null);

  const handleRunSimulation = () => {
    setIsRunning(true);
    setExecutionLogs([]);
    setLastGeneratedIncidentId(null);

    const now = () => new Date().toLocaleTimeString();

    // Step 1: Initialize
    setExecutionLogs((prev) => [
      ...prev,
      { timestamp: now(), text: `Initializing stress test scenario: ${selectedScenario.name}`, type: 'info' },
      { timestamp: now(), text: `Target Payer: ${targetPayer} | Injection count: ${batchVolume} payloads`, type: 'info' },
    ]);

    // Step 2: Generating synthetic payload
    setTimeout(() => {
      setExecutionLogs((prev) => [
        ...prev,
        { timestamp: now(), text: `Synthesizing ANSI ASC X12N 837 transaction envelopes...`, type: 'info' },
      ]);
    }, 400);

    // Step 3: Rule engine trigger
    setTimeout(() => {
      const anomalousClaim = generateRandomClaim(selectedScenario.anomalyKey);
      anomalousClaim.payer = targetPayer;
      claimsService.addClaim(anomalousClaim);

      const incidentId = `INC-${anomalousClaim.id.replace('CLM-2026-', '')}`;
      setLastGeneratedIncidentId(incidentId);

      setExecutionLogs((prev) => [
        ...prev,
        { timestamp: now(), text: `Ingested ${anomalousClaim.id} into high-speed validation pipeline`, type: 'info' },
        { timestamp: now(), text: `[RULE ENGINE] Rule ${selectedScenario.targetRule} triggered violation on Loop 2010/2400`, type: 'warn' },
        { timestamp: now(), text: `Anomaly Confidence Score calculated: ${(anomalousClaim.anomalyScore * 100).toFixed(0)}%`, type: 'error' },
        { timestamp: now(), text: `Created active Data Quality Incident ${incidentId} with SLA countdown`, type: 'success' },
      ]);

      setIsRunning(false);
    }, 1200);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Anomaly & SLA Stress-Testing Simulator
            </h1>
            <Badge variant="purple" size="sm">
              Diagnostic Engine
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Inject synthetic EDI data defects, simulate prompt-pay SLA violations, and benchmark automated pipeline defense responses.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Scenario Picker & Parameters */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                Select Stress Scenario
              </CardTitle>
              <CardDescription>
                Choose an adversarial pattern to evaluate platform detection heuristics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {SCENARIOS.map((scenario) => {
                const isSelected = selectedScenario.id === scenario.id;
                return (
                  <div
                    key={scenario.id}
                    onClick={() => setSelectedScenario(scenario)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-cyan-950/30 border-cyan-500/60 ring-1 ring-cyan-500/40 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-100">{scenario.name}</span>
                          <Badge
                            variant={scenario.severity === 'critical' ? 'danger' : scenario.severity === 'high' ? 'warning' : 'info'}
                            size="sm"
                          >
                            {scenario.severity.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                          {scenario.description}
                        </p>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-1 rounded bg-slate-900 text-slate-300 border border-slate-800 shrink-0">
                        {scenario.category}
                      </span>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex flex-wrap items-center justify-between text-[11px] gap-2">
                      <span className="font-mono text-cyan-300">Target Rule: {scenario.targetRule}</span>
                      <span className="text-slate-400 text-right">{scenario.expectedResult}</span>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Configuration Parameters */}
          <Card>
            <CardHeader>
              <CardTitle>Simulation Parameters</CardTitle>
              <CardDescription>Configure target health plan and volume parameters</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Target Health Plan</label>
                  <select
                    value={targetPayer}
                    onChange={(e) => setTargetPayer(e.target.value as PayerName)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Medicare CMS">Medicare CMS (Part B)</option>
                    <option value="UnitedHealthcare">UnitedHealthcare (Commercial/Inpatient)</option>
                    <option value="Anthem BlueCross">Anthem BlueCross</option>
                    <option value="Aetna Health">Aetna Health</option>
                    <option value="Cigna Healthcare">Cigna Healthcare</option>
                    <option value="Humana">Humana Medicare Advantage</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    Synthetic Payload Count ({batchVolume} claims)
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={25}
                    value={batchVolume}
                    onChange={(e) => setBatchVolume(Number(e.target.value))}
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500 mt-2"
                  />
                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>1 Claim</span>
                    <span>10 Claims</span>
                    <span>25 Claims</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleRunSimulation}
                  isLoading={isRunning}
                  leftIcon={<Play className="w-4 h-4 text-white fill-current" />}
                >
                  Execute Stress Scenario
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right 1 Col: Execution Terminal & Output */}
        <div className="space-y-6">
          <Card className="bg-slate-950 border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                <CardTitle className="text-xs font-mono uppercase text-slate-300">
                  Pipeline Execution Terminal
                </CardTitle>
              </div>
              <span className="text-[10px] font-mono text-slate-400">Live Console</span>
            </CardHeader>
            <CardContent className="pt-3">
              <div className="h-80 overflow-y-auto space-y-2 font-mono text-xs p-2 rounded-lg bg-slate-900/90 border border-slate-850">
                {executionLogs.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-400">
                    <Sparkles className="w-6 h-6 text-slate-500 mb-2" />
                    <span>Select a scenario and click Execute to view real-time rule engine execution telemetry.</span>
                  </div>
                ) : (
                  executionLogs.map((log, idx) => {
                    const color =
                      log.type === 'error'
                        ? 'text-rose-400'
                        : log.type === 'warn'
                        ? 'text-amber-400'
                        : log.type === 'success'
                        ? 'text-emerald-400 font-bold'
                        : 'text-slate-300';
                    return (
                      <div key={idx} className="flex items-start gap-2 leading-relaxed">
                        <span className="text-[10px] text-slate-400 shrink-0">[{log.timestamp}]</span>
                        <span className={color}>{log.text}</span>
                      </div>
                    );
                  })
                )}
              </div>

              {lastGeneratedIncidentId && (
                <div className="mt-4 p-3 rounded-lg bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-white">Incident Created: {lastGeneratedIncidentId}</span>
                    <span className="text-[11px] text-cyan-300">Ready for forensic audit</span>
                  </div>
                  <Button
                    variant="primary"
                    size="xs"
                    onClick={() => navigate(`/investigation/${lastGeneratedIncidentId}`)}
                    rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                  >
                    Investigate
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Info */}
          <Card className="bg-slate-900/60">
            <CardHeader>
              <CardTitle className="text-xs font-semibold uppercase text-slate-400">
                Why Simulator Matters
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-400 space-y-2 leading-relaxed">
              <p>
                Healthcare claims data flows at hundreds of transactions per second. Stress testing enables continuous validation of SLA monitors, prevents catastrophic batch rejections, and verifies prompt-pay compliance before high-volume SFTP transmissions.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
