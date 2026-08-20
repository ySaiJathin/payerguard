import React from 'react';
import { useNavigate } from 'react-router-dom';

import {
  ArrowRight,
  Search,
  ShieldAlert,
  Wrench,
  Activity,
} from 'lucide-react';

import { Card, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

import {
  bandForScore,
  injectionTypeLabel,
  scoreBandColor,
  scoreBandVariant,
} from '../../utils/incidentDisplay';

import type { Incident, IncidentAnalysisContext } from '../../types/api';

interface IncidentRiskDetailsProps {
  incidents: Incident[];
  limit?: number;
}

/**
 * The four narrative sections of an incident card.
 *
 * These used to be three hardcoded write-ups ("Amount Spike", "Duplicate
 * Claims", "Processing Delay / Volume Drop") cycled by row index, so the
 * first incident on the dashboard always claimed to be an amount spike
 * whatever it actually was, and every number in the prose was invented.
 *
 * They now come from `evidence_snapshot.analysis_context.narrative`, which
 * the pipeline renders per incident from a template chosen by the anomaly
 * type Isolation Forest actually flagged, filled in with that window's real
 * counts, magnitudes and expectation states.
 */
type Insight = {
  type: string;
  riskSummary: string;
  rootCause: string;
  investigation: string;
  fix: string;
};

/** Shown only for an incident that carries no analysis context at all. */
const NO_CONTEXT: Omit<Insight, 'type'> = {
  riskSummary:
    'This incident was created without an analysis context, so there is no recorded description of its risk. Its scores below are real; only the narrative is missing.',
  rootCause:
    'No root-cause analysis was recorded for this incident by the producing pipeline.',
  investigation:
    'No investigation detail was recorded. Open the incident to see its audit trail and evidence snapshot.',
  fix: 'No remediation was recommended, because no root cause was recorded.',
};

function insightFor(incident: Incident): Insight {
  const context = incident.evidence_snapshot?.analysis_context as
    | IncidentAnalysisContext
    | undefined
    | null;

  const type = context?.detected_anomaly_type
    ? injectionTypeLabel(context.detected_anomaly_type)
    : 'Multi-signal quality risk';

  if (!context?.narrative) return { type, ...NO_CONTEXT };

  return {
    type,
    riskSummary: context.narrative.risk_summary,
    rootCause: context.narrative.root_cause,
    investigation: context.narrative.investigation,
    fix: context.narrative.recommended_fix,
  };
}


/**
 * An incident is "implemented" (its fix has been actioned) once it leaves
 * the actionable pipeline. `resolved` is the explicit terminal fixed state;
 * `rejected` means a reviewer decided it needs no fix. Either way it should
 * stop occupying one of the top-priority slots so the next highest-priority
 * open incident moves up -- this is what makes the list dynamic rather than
 * a fixed top 3.
 */
const IMPLEMENTED_STATUSES = new Set([
  'resolved',
  'rejected',
]);

function isOpen(incident: Incident): boolean {
  return !IMPLEMENTED_STATUSES.has(incident.status);
}

/** P1 = highest computed priority among open incidents, P2 = next, etc. */
function priorityLabel(rank: number): string {
  return `P${rank + 1}`;
}

const PRIORITY_BADGE_STYLE: Record<string, string> = {
  P1: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  P2: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  P3: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40',
};

export const IncidentRiskDetails: React.FC<
  IncidentRiskDetailsProps
> = ({
  incidents,
  limit = 3,
}) => {

  const navigate = useNavigate();

  /*
   * Ranked by the actual composite Priority score (`priority_result.priority`
   * -- Severity/Risk/Business Impact/Affected Claims, see MVP_CONTEXT.md
   * §3.3), not just risk_score, since that's the number the system defines
   * as "priority." Incidents already resolved or rejected are excluded, so
   * as soon as one of today's top 3 is implemented the next-highest-priority
   * open incident automatically fills its slot on the next data refresh.
   */
  const rows = incidents
    .filter(isOpen)
    .slice()
    .sort(
      (a, b) =>
        (b.priority_result?.priority ?? 0) -
        (a.priority_result?.priority ?? 0)
    )
    .slice(0, limit)
    .map((incident, index) => ({
      incident,
      insight: insightFor(incident),
      priorityLabel: priorityLabel(index),
    }));


  return (
    <div className="space-y-4">

      {rows.length === 0 ? (

        <Card>

          <CardContent className="py-12 text-center">

            <ShieldAlert className="mx-auto mb-3 h-8 w-8 text-slate-600" />

            <p className="text-sm font-medium text-slate-300">
              No open priority incidents
            </p>

            <p className="mt-1 text-xs text-slate-500">
              Every incident is resolved or rejected, or none have been
              scored yet. New incidents will appear here after risk scoring.
            </p>

          </CardContent>

        </Card>

      ) : (

        rows.map(({ incident, insight, priorityLabel: pLabel }) => {

          const risk =
            incident.risk_score ?? 0;

          const band =
            bandForScore(risk);

          const priority =
            incident.priority_result?.priority ?? 0;


          return (

            <Card
              key={incident.incident_id}
              className="overflow-hidden"
            >

              <CardContent className="p-0">


                {/* =================================================
                    INCIDENT HEADER
                ================================================= */}

                <div className="flex flex-col gap-4 border-b border-slate-800 bg-slate-900/70 p-5 sm:flex-row sm:items-center sm:justify-between">


                  <div>

                    <div className="flex flex-wrap items-center gap-2">

                      <span
                        className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-bold tracking-wide ${
                          PRIORITY_BADGE_STYLE[pLabel] ??
                          PRIORITY_BADGE_STYLE.P3
                        }`}
                        title={`Rank ${pLabel} by computed priority score (${priority.toFixed(
                          0
                        )}/100) among open incidents`}
                      >
                        {pLabel}
                      </span>

                      <span className="font-mono text-[11px] font-semibold text-cyan-400">
                        {incident.incident_id}
                      </span>

                      <Badge
                        variant={scoreBandVariant(band)}
                        size="sm"
                      >
                        {band}
                      </Badge>

                    </div>


                    <h3 className="mt-2 text-base font-semibold text-white">
                      {insight.type}
                    </h3>


                    <p className="mt-1 text-[11px] text-slate-500">
                      Processing window: {incident.window_id}
                    </p>

                  </div>


                  {/* RISK SCORE */}

                  <div className="flex items-center gap-4">

                    <div className="flex h-12 w-12 items-center justify-center rounded-full border border-slate-700 bg-slate-950">

                      <Activity
                        className={`h-5 w-5 ${scoreBandColor(
                          band
                        )}`}
                      />

                    </div>


                    <div>

                      <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                        Risk Score
                      </p>


                      <p
                        className={`mt-0.5 text-3xl font-bold font-mono ${scoreBandColor(
                          band
                        )}`}
                      >

                        {risk.toFixed(0)}

                        <span className="text-sm text-slate-500">
                          /100
                        </span>

                      </p>


                      <p className="text-[10px] text-slate-500">
                        {band} risk
                      </p>

                    </div>

                  </div>

                </div>


                {/* =================================================
                    WHAT IS THE RISK
                ================================================= */}

                <div className="border-b border-slate-800 px-5 py-4">

                  <div className="mb-2 flex items-center gap-2">

                    <ShieldAlert className="h-4 w-4 text-rose-400" />

                    <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-300">
                      What is the Risk?
                    </h4>

                  </div>


                  <p className="max-w-5xl text-sm leading-relaxed text-slate-300">
                    {insight.riskSummary}
                  </p>

                </div>


                {/* =================================================
                    ROOT CAUSE + INVESTIGATION
                ================================================= */}

                <div className="grid grid-cols-1 divide-y divide-slate-800 md:grid-cols-2 md:divide-x md:divide-y-0">


                  {/* ROOT CAUSE */}

                  <div className="p-5">

                    <div className="mb-3 flex items-center gap-2">

                      <Search className="h-4 w-4 text-purple-400" />

                      <h4 className="text-xs font-semibold uppercase tracking-wider text-purple-300">
                        Root Cause
                      </h4>

                    </div>


                    <p className="text-sm leading-relaxed text-slate-300">
                      {insight.rootCause}
                    </p>

                  </div>


                  {/* INVESTIGATION */}

                  <div className="p-5">

                    <div className="mb-3 flex items-center gap-2">

                      <Activity className="h-4 w-4 text-cyan-400" />

                      <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-300">
                        Investigation
                      </h4>

                    </div>


                    <p className="text-sm leading-relaxed text-slate-300">
                      {insight.investigation}
                    </p>

                  </div>

                </div>


                {/* =================================================
                    RECOMMENDED FIX
                ================================================= */}

                <div className="border-t border-slate-800 bg-emerald-950/10 p-5">

                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">


                    <div className="flex gap-3">


                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-800/50 bg-emerald-950/40">

                        <Wrench className="h-4 w-4 text-emerald-400" />

                      </div>


                      <div>

                        <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-300">
                          Recommended Fix
                        </h4>


                        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-slate-300">
                          {insight.fix}
                        </p>

                      </div>

                    </div>


                    <Button
                      variant="outline"
                      size="xs"
                      onClick={() =>
                        navigate(
                          `/investigation/${incident.incident_id}`
                        )
                      }
                      rightIcon={
                        <ArrowRight className="h-3 w-3" />
                      }
                    >
                      Investigate
                    </Button>


                  </div>

                </div>


              </CardContent>

            </Card>

          );

        })

      )}

    </div>
  );
};

export default IncidentRiskDetails;