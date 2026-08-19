import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Layers,
  RefreshCw,
  Database,
} from 'lucide-react';

import { KPICard } from '../components/ui/KPICard';
import { Button } from '../components/ui/Button';
import { DataState } from '../components/ui/DataState';

import {
  SystemStatusSection,
  type StageStatus,
} from '../components/dashboard/SystemStatusSection';

import { ClaimsVolumeChart } from '../components/dashboard/ClaimsVolumeChart';
import { DataQualityTrendChart } from '../components/dashboard/DataQualityTrendChart';
import { AnomalyTrendChart } from '../components/dashboard/AnomalyTrendChart';
import { ClaimAmountDistribution } from '../components/dashboard/ClaimAmountDistribution';
import { IncidentSeverityDistribution } from '../components/dashboard/IncidentSeverityDistribution';
import { RecentIncidentsTable } from '../components/dashboard/RecentIncidentsTable';
import { IncidentRiskDetails } from '../components/dashboard/IncidentRiskDetails';

import { useAsync } from '../hooks/useAsync';

import {
  anomalyApi,
  baselineApi,
  incidentsApi,
  qualityApi,
} from '../services/api';

import { formatNumber } from '../utils/formatters';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  /* =========================================================
     API DATA
  ========================================================= */

  const quality = useAsync(
    () => qualityApi.results(),
    []
  );

  const baseline = useAsync(
    () => baselineApi.current(),
    []
  );

  const anomaly = useAsync(
    () => anomalyApi.results(),
    []
  );

  const incidents = useAsync(
    () => incidentsApi.list(),
    []
  );


  /* =========================================================
     REFRESH
  ========================================================= */

  const reloadAll = () => {
    quality.reload();
    baseline.reload();
    anomaly.reload();
    incidents.reload();
  };


  const anyLoading =
    quality.loading ||
    baseline.loading ||
    anomaly.loading ||
    incidents.loading;


  /* =========================================================
     QUALITY METRICS
  ========================================================= */

  const compositeScore =
    quality.data
      ?.quality_score_result
      .composite_score ?? null;


  const checks =
    quality.data?.check_results ?? [];


  const failingChecks =
    checks.filter(
      (check) => check.band !== 'PASS'
    ).length;


  const criticalChecks =
    checks.filter(
      (check) => check.band === 'CRITICAL'
    ).length;


  /* =========================================================
     BASELINE METRICS
  ========================================================= */

  const baselineRows =
    baseline.data?.source_row_count ?? null;


  const windowCount =
    baseline.data
      ?.volume_baseline
      .windows
      .length ?? null;


  /* =========================================================
     INCIDENT DATA
  ========================================================= */

  const incidentList =
    incidents.data ?? [];


  /*
   * No fallback records. Every incident panel below renders whatever the
   * `/incidents` endpoint actually returned -- previously this page carried
   * three hand-written incidents (PG-INC-001..003, with invented severity,
   * risk and business-impact numbers) that stood in whenever the API
   * returned an empty list. They made an empty system look populated and no
   * number in them came from a model, so they are gone. An installation with
   * no incidents yet honestly shows none.
   */
  const dashboardIncidents = incidentList;


  /* =========================================================
     PIPELINE STATUS
  ========================================================= */

  const stages: StageStatus[] = [

    {
      name: 'Quality validation',

      state: quality.loading
        ? 'loading'
        : quality.error
        ? 'error'
        : quality.notComputed
        ? 'not_computed'
        : 'ready',

      detail: quality.data
        ? `Composite ${quality.data.quality_score_result.composite_score.toFixed(
            2
          )} across ${checks.length} checks`
        : quality.notComputed ??
          quality.error ??
          'Checking /quality/results',

      computedAt:
        quality.data
          ?.quality_score_result
          .generated_at,
    },


    {
      name: 'Historical baseline',

      state: baseline.loading
        ? 'loading'
        : baseline.error
        ? 'error'
        : baseline.notComputed
        ? 'not_computed'
        : 'ready',

      detail: baseline.data
        ? `${formatNumber(
            baseline.data.source_row_count
          )} rows, ${
            baseline.data.volume_baseline
              .windows.length
          } windows`
        : baseline.notComputed ??
          baseline.error ??
          'Checking /baseline',

      computedAt:
        baseline.data?.computed_at,
    },


    {
      name: 'Anomaly detection',

      state: anomaly.loading
        ? 'loading'
        : anomaly.error
        ? 'error'
        : anomaly.notComputed
        ? 'not_computed'
        : 'ready',

      detail: anomaly.data
        ? 'Anomaly detection completed'
        : anomaly.notComputed ??
          anomaly.error ??
          'Checking /anomaly/results',

      computedAt:
        anomaly.data
          ?.production_model_selection
          ?.selected_at,
    },


    {
      name: 'Incidents',

      state: incidents.loading
        ? 'loading'
        : incidents.error
        ? 'error'
        : 'ready',

      detail:
        incidents.error ??
        `${incidentList.length} incident(s) recorded`,

      computedAt: null,
    },
  ];


  /* =========================================================
     UI
  ========================================================= */

  return (

    <div className="space-y-6 animate-in fade-in duration-200">


      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="flex flex-col gap-4 pb-2 border-b border-slate-800/80 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <h1 className="text-xl font-bold tracking-tight text-white font-heading sm:text-2xl">
            PayerGuard Operations Dashboard
          </h1>

          <p className="mt-1 text-xs text-slate-400">
            Claims quality, anomaly detection and SLA risk monitoring.
          </p>

        </div>


        <div className="flex flex-wrap items-center gap-2.5">

          <Button
            variant="outline"
            size="sm"
            onClick={reloadAll}
            isLoading={anyLoading}
            leftIcon={
              <RefreshCw className="h-3.5 w-3.5" />
            }
          >
            Refresh
          </Button>


          <Button
            variant="primary"
            size="sm"
            onClick={() =>
              navigate('/history')
            }
          >
            View Incidents
          </Button>

        </div>

      </div>


      {/* =====================================================
          PIPELINE STATUS
      ===================================================== */}

      <SystemStatusSection
        stages={stages}
      />


      {/* =====================================================
          KPI SUMMARY
      ===================================================== */}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">


        {/* Data Quality */}

        <KPICard
          title="Data Quality Score"

          value={
            compositeScore !== null
              ? compositeScore.toFixed(1)
              : '--'
          }

          subtext={
            compositeScore !== null
              ? 'Composite, 0-100'
              : 'No validation run yet'
          }

          status={
            compositeScore === null
              ? 'neutral'
              : compositeScore >= 90
              ? 'good'
              : 'warning'
          }

          icon={
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
          }
        />


        {/* Quality Issues */}

        <KPICard
          title="Quality Issues"

          value={
            quality.data
              ? failingChecks
              : '--'
          }

          unit={
            quality.data
              ? `of ${checks.length}`
              : undefined
          }

          subtext={
            quality.data
              ? `${criticalChecks} critical`
              : 'No validation run yet'
          }

          status={
            failingChecks > 0
              ? 'warning'
              : 'good'
          }

          icon={
            <AlertTriangle className="h-5 w-5 text-amber-400" />
          }
        />


        {/* Baseline Claims */}

        <KPICard
          title="Baseline Claims"

          value={
            baselineRows !== null
              ? formatNumber(
                  baselineRows
                )
              : '--'
          }

          subtext={
            baseline.data
              ? `Source: ${baseline.data.source_file
                  .split(/[\\/]/)
                  .pop()}`
              : 'No baseline yet'
          }

          status="info"

          icon={
            <Database className="h-5 w-5 text-cyan-400" />
          }
        />


        {/* Baseline Windows */}

        <KPICard
          title="Baseline Windows"

          value={
            windowCount !== null
              ? formatNumber(
                  windowCount
                )
              : '--'
          }

          subtext={
            baseline.data
              ?.volume_baseline
              .window_definition ??
            'No baseline yet'
          }

          status="info"

          icon={
            <Layers className="h-5 w-5 text-cyan-400" />
          }
        />


        {/* Open Incidents */}

        <KPICard
          title="Open Incidents"

          value={
            incidents.data
              ? incidentList.length
              : '--'
          }

          subtext={
            incidents.data
              ? `${
                  incidentList.filter(
                    (incident) =>
                      incident.status ===
                      'ready_for_review'
                  ).length
                } ready for review`
              : 'No incidents loaded yet'
          }

          status={
            dashboardIncidents.length > 0
              ? 'warning'
              : 'good'
          }

          icon={
            <AlertOctagon className="h-5 w-5 text-rose-400" />
          }
        />

      </div>


      {/* =====================================================
          ANALYTICS
      ===================================================== */}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">


        {/* Claim Volume */}

        <DataState
          loading={baseline.loading}
          error={baseline.error}
          notComputed={baseline.notComputed}
          label="Claim volume baseline"
          producedBy="POST /baseline/compute"
        >

          {baseline.data && (
            <ClaimsVolumeChart
              windows={
                baseline.data
                  .volume_baseline
                  .windows
              }

              windowDefinition={
                baseline.data
                  .volume_baseline
                  .window_definition
              }
            />
          )}

        </DataState>


        {/* Data Quality */}

        <DataState
          loading={quality.loading}
          error={quality.error}
          notComputed={quality.notComputed}
          label="Quality validation results"
          producedBy="POST /quality/validate"
        >

          {quality.data && (
            <DataQualityTrendChart
              score={
                quality.data
                  .quality_score_result
              }

              checks={
                quality.data
                  .check_results
              }
            />
          )}

        </DataState>


        {/* Anomaly Detection */}

        <DataState
          loading={anomaly.loading}
          error={anomaly.error}
          notComputed={anomaly.notComputed}
          label="Anomaly detection"
          producedBy="POST /anomaly/benchmark"
        >

          {anomaly.data && (
            <AnomalyTrendChart
              result={anomaly.data}
            />
          )}

        </DataState>


        {/* Claim Amount */}

        <DataState
          loading={baseline.loading}
          error={baseline.error}
          notComputed={baseline.notComputed}
          label="Claim amount baseline"
          producedBy="POST /baseline/compute"
        >

          {baseline.data &&
            baseline.data
              .amount_baselines
              .length > 0 && (

              <ClaimAmountDistribution
                amount={
                  baseline.data
                    .amount_baselines[0]
                }

                totalClaims={
                  baseline.data
                    .source_row_count
                }
              />

            )}

        </DataState>

      </div>


      {/* =====================================================
          INCIDENT SEVERITY
      ===================================================== */}

      <DataState
        loading={incidents.loading}
        error={incidents.error}
        notComputed={incidents.notComputed}
        label="Incident severity"
        producedBy="POST /incidents"
      >

        <IncidentSeverityDistribution
          incidents={
            dashboardIncidents
          }
        />

      </DataState>


      {/* =====================================================
          RECENT INCIDENTS
      ===================================================== */}

      <RecentIncidentsTable
        incidents={
          dashboardIncidents
        }
      />


      {/* =====================================================
          RISK & INVESTIGATION
      ===================================================== */}

      <IncidentRiskDetails
        incidents={
          dashboardIncidents
        }
        limit={3}
      />

    </div>
  );
};


export default Dashboard;