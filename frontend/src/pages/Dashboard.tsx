import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Activity,
  Layers,
  RefreshCw,
  Database,
} from 'lucide-react';
import { KPICard } from '../components/ui/KPICard';
import { Button } from '../components/ui/Button';
import { DataState } from '../components/ui/DataState';
import { SystemStatusSection, type StageStatus } from '../components/dashboard/SystemStatusSection';
import { ClaimsVolumeChart } from '../components/dashboard/ClaimsVolumeChart';
import { DataQualityTrendChart } from '../components/dashboard/DataQualityTrendChart';
import { AnomalyTrendChart } from '../components/dashboard/AnomalyTrendChart';
import { ClaimAmountDistribution } from '../components/dashboard/ClaimAmountDistribution';
import { IncidentSeverityDistribution } from '../components/dashboard/IncidentSeverityDistribution';
import { RecentIncidentsTable } from '../components/dashboard/RecentIncidentsTable';
import { useAsync } from '../hooks/useAsync';
import { anomalyApi, baselineApi, incidentsApi, qualityApi, riskApi } from '../services/api';
import { formatNumber } from '../utils/formatters';

/**
 * Composed from five independent endpoints -- the backend has no aggregate
 * dashboard endpoint, so each panel loads and fails on its own. A stage that
 * has not been run yet renders as "not computed", never as a zero.
 */
export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const quality = useAsync(() => qualityApi.results(), []);
  const baseline = useAsync(() => baselineApi.current(), []);
  const anomaly = useAsync(() => anomalyApi.results(), []);
  const risk = useAsync(() => riskApi.benchmarkResults(), []);
  const incidents = useAsync(() => incidentsApi.list(), []);

  const reloadAll = () => {
    quality.reload();
    baseline.reload();
    anomaly.reload();
    risk.reload();
    incidents.reload();
  };

  const anyLoading =
    quality.loading || baseline.loading || anomaly.loading || risk.loading || incidents.loading;

  // --- KPI inputs, each straight from a real response ---
  const compositeScore = quality.data?.quality_score_result.composite_score ?? null;
  const checks = quality.data?.check_results ?? [];
  const failingChecks = checks.filter((c) => c.band !== 'PASS').length;
  const criticalChecks = checks.filter((c) => c.band === 'CRITICAL').length;
  const baselineRows = baseline.data?.source_row_count ?? null;
  const windowCount = baseline.data?.volume_baseline.windows.length ?? null;
  const incidentList = incidents.data ?? [];
  const selectedAnomalyModel = anomaly.data?.production_model_selection.selected_model ?? null;
  const selectedRiskModel = risk.data?.production_model_selection.selected_model ?? null;

  const stages: StageStatus[] = [
    {
      name: 'Quality validation',
      state: quality.loading ? 'loading' : quality.error ? 'error' : quality.notComputed ? 'not_computed' : 'ready',
      detail: quality.data
        ? `Composite ${quality.data.quality_score_result.composite_score.toFixed(2)} across ${checks.length} checks`
        : quality.notComputed ?? quality.error ?? 'Checking /quality/results',
      computedAt: quality.data?.quality_score_result.generated_at,
    },
    {
      name: 'Historical baseline',
      state: baseline.loading ? 'loading' : baseline.error ? 'error' : baseline.notComputed ? 'not_computed' : 'ready',
      detail: baseline.data
        ? `${formatNumber(baseline.data.source_row_count)} rows, ${baseline.data.volume_baseline.windows.length} windows`
        : baseline.notComputed ?? baseline.error ?? 'Checking /baseline',
      computedAt: baseline.data?.computed_at,
    },
    {
      name: 'Anomaly benchmark',
      state: anomaly.loading ? 'loading' : anomaly.error ? 'error' : anomaly.notComputed ? 'not_computed' : 'ready',
      detail: anomaly.data
        ? `Production model: ${anomaly.data.production_model_selection.selected_model}`
        : anomaly.notComputed ?? anomaly.error ?? 'Checking /anomaly/results',
      computedAt: anomaly.data?.production_model_selection.selected_at,
    },
    {
      name: 'Risk benchmark',
      state: risk.loading ? 'loading' : risk.error ? 'error' : risk.notComputed ? 'not_computed' : 'ready',
      detail: risk.data
        ? `Production model: ${risk.data.production_model_selection.selected_model}`
        : risk.notComputed ?? risk.error ?? 'Checking /risk/benchmark/results',
      computedAt: risk.data?.production_model_selection.selected_at,
    },
    {
      name: 'Incidents',
      state: incidents.loading ? 'loading' : incidents.error ? 'error' : 'ready',
      detail: incidents.error ?? `${incidentList.length} incident(s) recorded`,
      computedAt: null,
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
            PayerGuard Operations Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Claims quality, anomaly, and investigation-risk monitoring over the CMS Medicare
            inpatient extract. Every figure below is computed by the backend or reported as not
            yet computed.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={reloadAll}
            isLoading={anyLoading}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate('/incidents')}>
            View Incidents
          </Button>
        </div>
      </div>

      {/* Pipeline stage status */}
      <SystemStatusSection stages={stages} />

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KPICard
          title="Data Quality Score"
          value={compositeScore !== null ? compositeScore.toFixed(1) : '--'}
          subtext={compositeScore !== null ? 'Composite, 0-100' : 'No validation run yet'}
          status={compositeScore === null ? 'neutral' : compositeScore >= 90 ? 'good' : 'warning'}
          icon={<ShieldCheck className="w-5 h-5 text-emerald-400" />}
        />
        <KPICard
          title="Checks Not Passing"
          value={quality.data ? failingChecks : '--'}
          unit={quality.data ? `of ${checks.length}` : undefined}
          subtext={quality.data ? `${criticalChecks} critical` : 'No validation run yet'}
          status={failingChecks > 0 ? 'warning' : 'good'}
          icon={<AlertTriangle className="w-5 h-5 text-amber-400" />}
        />
        <KPICard
          title="Baseline Claims"
          value={baselineRows !== null ? formatNumber(baselineRows) : '--'}
          subtext={baseline.data ? `Source: ${baseline.data.source_file.split(/[\\/]/).pop()}` : 'No baseline yet'}
          status="info"
          icon={<Database className="w-5 h-5 text-cyan-400" />}
        />
        <KPICard
          title="Baseline Windows"
          value={windowCount !== null ? formatNumber(windowCount) : '--'}
          subtext={baseline.data?.volume_baseline.window_definition ?? 'No baseline yet'}
          status="info"
          icon={<Layers className="w-5 h-5 text-cyan-400" />}
        />
        <KPICard
          title="Open Incidents"
          value={incidents.data ? incidentList.length : '--'}
          subtext={
            incidents.data
              ? `${incidentList.filter((i) => i.status === 'ready_for_review').length} ready for review`
              : 'Unavailable'
          }
          status={incidentList.length > 0 ? 'warning' : 'good'}
          icon={<AlertOctagon className="w-5 h-5 text-rose-400" />}
        />
        <KPICard
          title="Production Models"
          value={selectedAnomalyModel ?? '--'}
          subtext={selectedRiskModel ? `Risk: ${selectedRiskModel}` : 'Risk benchmark not run'}
          status="info"
          icon={<Activity className="w-5 h-5 text-purple-400" />}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DataState
          loading={baseline.loading}
          error={baseline.error}
          notComputed={baseline.notComputed}
          label="Claim volume baseline"
          producedBy="POST /baseline/compute"
        >
          {baseline.data && (
            <ClaimsVolumeChart
              windows={baseline.data.volume_baseline.windows}
              windowDefinition={baseline.data.volume_baseline.window_definition}
            />
          )}
        </DataState>

        <DataState
          loading={quality.loading}
          error={quality.error}
          notComputed={quality.notComputed}
          label="Quality validation results"
          producedBy="POST /quality/validate"
        >
          {quality.data && (
            <DataQualityTrendChart
              score={quality.data.quality_score_result}
              checks={quality.data.check_results}
            />
          )}
        </DataState>

        <DataState
          loading={anomaly.loading}
          error={anomaly.error}
          notComputed={anomaly.notComputed}
          label="Anomaly benchmark"
          producedBy="POST /anomaly/benchmark"
        >
          {anomaly.data && <AnomalyTrendChart result={anomaly.data} />}
        </DataState>

        <DataState
          loading={baseline.loading}
          error={baseline.error}
          notComputed={baseline.notComputed}
          label="Claim amount baseline"
          producedBy="POST /baseline/compute"
        >
          {baseline.data && baseline.data.amount_baselines.length > 0 && (
            <ClaimAmountDistribution
              amount={baseline.data.amount_baselines[0]}
              totalClaims={baseline.data.source_row_count}
            />
          )}
        </DataState>
      </div>

      {/* Incident distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DataState
          loading={incidents.loading}
          error={incidents.error}
          notComputed={incidents.notComputed}
          label="Incidents"
          producedBy="POST /incidents"
        >
          <IncidentSeverityDistribution incidents={incidentList} />
        </DataState>

        <DataState
          loading={risk.loading}
          error={risk.error}
          notComputed={risk.notComputed}
          label="Risk model benchmark"
          producedBy="POST /risk/benchmark"
        >
          {risk.data && <RiskBenchmarkPanel result={risk.data} />}
        </DataState>
      </div>

      {/* Recent incidents */}
      <DataState
        loading={incidents.loading}
        error={incidents.error}
        notComputed={incidents.notComputed}
        label="Incidents"
        producedBy="POST /incidents"
      >
        <RecentIncidentsTable incidents={incidentList} />
      </DataState>
    </div>
  );
};

/** Small inline panel: the risk benchmark's real per-model metrics. */
const RiskBenchmarkPanel: React.FC<{
  result: import('../types/api').RiskBenchmarkRunResult;
}> = ({ result }) => {
  const selected = result.production_model_selection.selected_model;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 h-full">
      <div className="flex items-center gap-2 mb-1">
        <Activity className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-white">Risk Model Benchmark</h3>
      </div>
      <p className="text-xs text-slate-400 mb-4">
        Ranked on recall and PR-AUC -- false negatives are the costly error
      </p>

      <div className="space-y-2.5">
        {result.benchmark_results.map((r) => (
          <div
            key={r.model_type}
            className={`p-3 rounded-lg border ${
              r.model_type === selected
                ? 'bg-purple-950/40 border-purple-700/60'
                : 'bg-slate-950/60 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-slate-100 font-mono">{r.model_type}</span>
              {r.model_type === selected && (
                <span className="text-[10px] font-mono text-purple-300 bg-purple-950 border border-purple-800/60 px-1.5 py-0.5 rounded">
                  PRODUCTION
                </span>
              )}
            </div>
            <div className="grid grid-cols-4 gap-2 text-[11px] font-mono">
              <div>
                <span className="text-slate-500 block text-[10px]">Recall</span>
                <span className="text-slate-200">{r.recall.toFixed(3)}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">PR-AUC</span>
                <span className="text-slate-200">{r.pr_auc.toFixed(3)}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">F1</span>
                <span className="text-slate-200">{r.f1.toFixed(3)}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">FN rate</span>
                <span className="text-rose-300">{r.false_negative_rate.toFixed(3)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {result.data_scale_warning && (
        <p className="mt-3 text-[11px] text-amber-300 bg-amber-950/40 border border-amber-800/50 rounded-lg p-2.5 leading-relaxed">
          {result.data_scale_warning}
        </p>
      )}
    </div>
  );
};

export default Dashboard;
