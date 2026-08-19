/**
 * Every backend call the UI makes, grouped by the module that owns it.
 *
 * Paths were read off the routers in `backend/app/<module>/router.py`, so the
 * prefixes here are the real ones -- note `/audit/baseline` rather than
 * `/baseline` for the audit pass-through (Phase 4's router already owns
 * `/baseline`, so Phase 16 mounted its copy elsewhere), and `/history/...`
 * with no prefix at all.
 */

import { apiGet, apiPost } from './apiClient';
import type {
  AcceptRequest,
  AnomalyBenchmarkRunResult,
  BaselineSnapshot,
  HistoryQueryResult,
  HumanFeedbackRead,
  Incident,
  IncidentStatus,
  InvestigationHistoryResponse,
  QualityResultsResponse,
  RecalculateResponse,
  RejectRequest,
  RiskBenchmarkRunResult,
} from '../types/api';

// --- quality ---

export const qualityApi = {
  results: (params?: { band?: string; category?: string }) =>
    apiGet<QualityResultsResponse>('/quality/results', params),
  check: (checkId: string) => apiGet('/quality/checks/' + encodeURIComponent(checkId)),
};

// --- baseline ---

export const baselineApi = {
  current: () => apiGet<BaselineSnapshot>('/baseline'),
};

// --- anomaly ---

export const anomalyApi = {
  /** 404s (as NotComputedError) until `POST /anomaly/benchmark` has been run. */
  results: () => apiGet<AnomalyBenchmarkRunResult>('/anomaly/results'),
};

// --- risk ---

export const riskApi = {
  /** 404s (as NotComputedError) until `POST /risk/benchmark` has been run. */
  benchmarkResults: () => apiGet<RiskBenchmarkRunResult>('/risk/benchmark/results'),
};

// --- incidents ---

export const incidentsApi = {
  list: (params?: { status?: IncidentStatus | ''; min_priority?: number }) =>
    apiGet<Incident[]>('/incidents', params),
  get: (incidentId: string) => apiGet<Incident>('/incidents/' + encodeURIComponent(incidentId)),
};

// --- llm ---

export const llmApi = {
  investigations: (incidentId: string) =>
    apiGet<InvestigationHistoryResponse>('/llm/investigations/' + encodeURIComponent(incidentId)),
};

// --- hitl ---

export const hitlApi = {
  accept: (incidentId: string, body: AcceptRequest) =>
    apiPost<Incident>(`/hitl/${encodeURIComponent(incidentId)}/accept`, body),
  /** The backend requires all three fields; there is no "reject with no reason". */
  reject: (incidentId: string, body: RejectRequest) =>
    apiPost<Incident>(`/hitl/${encodeURIComponent(incidentId)}/reject`, body),
  recalculate: (incidentId: string) =>
    apiPost<RecalculateResponse>(`/hitl/${encodeURIComponent(incidentId)}/recalculate`, {}),
  feedback: (incidentId: string) =>
    apiGet<HumanFeedbackRead[]>(`/hitl/${encodeURIComponent(incidentId)}/feedback`),
};

// --- audit / history ---

export const auditApi = {
  /**
   * Returns 200 even when the entity has no trail -- `found: false` is the
   * signal, not a 404 (backend router documents this deliberately).
   */
  history: (
    entityType: 'claim' | 'incident' | 'batch',
    entityId: string,
    params?: { page?: number; page_size?: number; stage?: string }
  ) =>
    apiGet<HistoryQueryResult>(
      `/history/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
      params
    ),
  baseline: () => apiGet<BaselineSnapshot>('/audit/baseline'),
};
