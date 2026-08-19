/**
 * Presentation helpers for the backend's real incident vocabulary.
 *
 * ## Why there is no old-status -> new-status mapping table
 *
 * The previous frontend had `open | investigating | resolved | escalated |
 * false_positive`. The backend has `pending_investigation | ready_for_review |
 * accepted | rejected | resolved | reopened`. Forcing a 1:1 crosswalk was
 * rejected because two of the old values have no backend counterpart at all,
 * and one of them turns out not to be a status in the first place:
 *
 * - `escalated` has no equivalent. Nothing in the backend escalates an
 *   incident to a third party; the workflow ends at a human decision.
 *   Inventing a status to hold it would create a state no endpoint can ever
 *   produce or transition out of.
 * - `false_positive` is not a status -- it is a *reject reason*. It lives in
 *   `ReasonCategory` on the reject payload (`app/hitl/schemas.py`). An
 *   incident a reviewer judged a false positive has `status: 'rejected'` and
 *   `reason_category: 'false_positive'`. Modelling it as a status would lose
 *   that distinction and duplicate a field that already exists.
 * - `open` and `investigating` collapse ambiguously: the backend splits the
 *   pre-decision phase by *who is waiting* (`pending_investigation` = waiting
 *   on the LLM, `ready_for_review` = waiting on a human), which is a more
 *   useful split than the old pair and not recoverable from it.
 *
 * So the backend's six values are the canonical set and the UI adopts them
 * directly. What the UI adds is a `phase` grouping, purely for filtering and
 * colour -- it is a view over the real statuses, not a second vocabulary.
 */

import type { Band, IncidentStatus, ReasonCategory } from '../types/api';

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple';

/** Coarse workflow phase, derived from status for grouping/filtering only. */
export type IncidentPhase = 'awaiting_ai' | 'awaiting_human' | 'decided' | 'closed';

interface StatusDisplay {
  label: string;
  variant: BadgeVariant;
  phase: IncidentPhase;
  /** Plain-language explanation of what the system is waiting on. */
  meaning: string;
}

export const INCIDENT_STATUS_DISPLAY: Record<IncidentStatus, StatusDisplay> = {
  pending_investigation: {
    label: 'Pending Investigation',
    variant: 'info',
    phase: 'awaiting_ai',
    meaning: 'Created and scored; waiting on an LLM investigation.',
  },
  ready_for_review: {
    label: 'Ready for Review',
    variant: 'warning',
    phase: 'awaiting_human',
    meaning: 'Investigation complete; waiting on a human accept/reject decision.',
  },
  accepted: {
    label: 'Accepted',
    variant: 'success',
    phase: 'decided',
    meaning: 'A reviewer accepted the recommendation; remediation may proceed.',
  },
  rejected: {
    label: 'Rejected',
    variant: 'danger',
    phase: 'decided',
    meaning: 'A reviewer rejected the recommendation and recorded feedback.',
  },
  resolved: {
    label: 'Resolved',
    variant: 'success',
    phase: 'closed',
    meaning: 'Remediation was revalidated and the finding no longer reproduces.',
  },
  reopened: {
    label: 'Reopened',
    variant: 'danger',
    phase: 'closed',
    meaning: 'Revalidation still reproduced the finding after remediation.',
  },
};

export const ALL_INCIDENT_STATUSES: IncidentStatus[] = [
  'pending_investigation',
  'ready_for_review',
  'accepted',
  'rejected',
  'resolved',
  'reopened',
];

export function statusDisplay(status: IncidentStatus): StatusDisplay {
  return (
    INCIDENT_STATUS_DISPLAY[status] ?? {
      label: status,
      variant: 'neutral' as BadgeVariant,
      phase: 'decided' as IncidentPhase,
      meaning: 'Unrecognised status returned by the backend.',
    }
  );
}

/** Where `false_positive` actually lives, now that it is not a status. */
export const REASON_CATEGORY_LABELS: Record<ReasonCategory, string> = {
  incorrect_root_cause: 'Incorrect root cause',
  insufficient_evidence_disagreement: 'Disagreed on insufficient evidence',
  false_positive: 'False positive',
  other: 'Other',
};

/**
 * Display-only banding of a 0-100 score.
 *
 * Thresholds are MVP_CONTEXT.md Section 3.1's documented risk-classification
 * bands (0-30 LOW / 31-60 MEDIUM / 61-80 HIGH / 81-100 CRITICAL). The backend
 * stores severity and priority as raw numbers and has no severity enum, so
 * this banding exists to colour a number the API already computed -- it never
 * originates a value. The numeric score is always shown alongside the band.
 */
export type ScoreBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export function bandForScore(score: number): ScoreBand {
  if (score > 80) return 'CRITICAL';
  if (score > 60) return 'HIGH';
  if (score > 30) return 'MEDIUM';
  return 'LOW';
}

export function scoreBandVariant(band: ScoreBand): BadgeVariant {
  switch (band) {
    case 'CRITICAL':
      return 'danger';
    case 'HIGH':
      return 'warning';
    case 'MEDIUM':
      return 'warning';
    case 'LOW':
      return 'info';
  }
}

export function scoreBandColor(band: ScoreBand): string {
  switch (band) {
    case 'CRITICAL':
      return 'text-rose-400';
    case 'HIGH':
      return 'text-amber-400';
    case 'MEDIUM':
      return 'text-yellow-400';
    case 'LOW':
      return 'text-sky-400';
  }
}

/** Great Expectations band -> badge variant. */
export function qualityBandVariant(band: Band): BadgeVariant {
  switch (band) {
    case 'PASS':
      return 'success';
    case 'WARNING':
      return 'warning';
    case 'CRITICAL':
      return 'danger';
  }
}

/** Human-readable label for the real anomaly injection types. */
export const INJECTION_TYPE_LABELS: Record<string, string> = {
  missing_value_spike: 'Missing-value spike',
  amount_spike: 'Amount spike',
  duplicate_spike: 'Duplicate spike',
  volume_drop: 'Volume drop',
  distribution_shift: 'Distribution shift',
};

export function injectionTypeLabel(key: string): string {
  return INJECTION_TYPE_LABELS[key] ?? key.replace(/_/g, ' ');
}

/** Pipeline-stage labels for the audit trail. */
export const PIPELINE_STAGE_LABELS: Record<string, string> = {
  cleaning: 'Cleaning',
  quality: 'Quality validation',
  anomaly: 'Anomaly detection',
  risk: 'Risk scoring',
  severity_scoring: 'Severity / impact / priority',
  llm_investigation: 'LLM investigation',
  incident_status: 'Incident status change',
  human_feedback: 'Human feedback',
  remediation: 'Remediation',
  revalidation: 'Revalidation',
};

export function pipelineStageLabel(stage: string): string {
  return PIPELINE_STAGE_LABELS[stage] ?? stage.replace(/_/g, ' ');
}
