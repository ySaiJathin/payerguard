/**
 * TypeScript mirrors of the backend's real Pydantic schemas.
 *
 * Every type here was transcribed from `backend/app/<module>/schemas.py`,
 * not inferred from the UI. Field names are snake_case because that is what
 * the API actually returns -- renaming them in transit would make it harder
 * to check a component against the endpoint it reads from.
 *
 * Deliberately absent, because the backend has no such concept and the
 * dataset cannot support one (MVP_CONTEXT.md Section 2.4 / 4.1): anything
 * SLA-, turnaround-, EDI-, NPI-, or NCCI-shaped.
 */

// --- quality (app/quality/schemas.py) ---

export type Band = 'PASS' | 'WARNING' | 'CRITICAL';

export type ExpectationType =
  | 'completeness'
  | 'uniqueness'
  | 'validity'
  | 'dtype'
  | 'range'
  | 'code_set'
  | 'freshness'
  | 'missing_rate'
  | 'duplicate_rate';

export interface ExpectationCheckResult {
  check_id: string;
  suite_name: string;
  column_name: string | null;
  expectation_type: ExpectationType;
  computed_rate_or_count: number;
  band: Band;
  threshold_used: Record<string, unknown>;
  run_id: string;
  evaluated_at: string;
}

export interface QualityScoreResult {
  run_id: string;
  batch_source: string;
  composite_score: number;
  weights_used: Record<string, number>;
  contributing_check_ids: string[];
  generated_at: string;
}

/** `GET /quality/results` returns this envelope, not a bare score. */
export interface QualityResultsResponse {
  quality_score_result: QualityScoreResult;
  check_results: ExpectationCheckResult[];
}

// --- baseline (app/baseline/schemas.py) ---

export interface Percentiles {
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  p99: number;
}

export interface VolumeWindow {
  window_id: string;
  start: string;
  end: string;
  claim_count: number;
}

export interface AmountBaseline {
  column_name: string;
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
  percentiles: Percentiles;
}

export interface BaselineSnapshot {
  snapshot_id: string;
  source_file: string;
  source_row_count: number;
  source_date_range: { min_date: string; max_date: string };
  volume_baseline: { window_definition: string; windows: VolumeWindow[] };
  amount_baselines: AmountBaseline[];
  data_health_baseline: {
    historical_missing_rate_by_column: Record<string, number>;
    historical_duplicate_rate: number;
    categorical_distributions: Record<string, Record<string, number>>;
  };
  length_of_stay_baseline: {
    mean: number;
    median: number;
    percentiles: Percentiles;
    claims_included: number;
    claims_excluded_missing_dates: number;
  };
  computed_at: string;
}

// --- anomaly (app/anomaly/schemas.py) ---

export type AnomalyModelType = 'iqr' | 'hbos' | 'isolation_forest' | 'lof';

/**
 * The real five injection types. These replace the previous frontend's
 * npiErrors / codeUnbundling / timelyFiling / modifierIssues categories,
 * which described a different product entirely.
 */
export type InjectionType =
  | 'missing_value_spike'
  | 'amount_spike'
  | 'duplicate_spike'
  | 'volume_drop'
  | 'distribution_shift';

export interface InjectionTypeMetrics {
  precision: number;
  recall: number;
  f1: number;
}

export interface AnomalyBenchmarkResult {
  model_type: AnomalyModelType;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
  detection_latency_ms: number;
  execution_time_s: number;
  measurement_context: {
    hardware: string;
    python_version: string;
    run_timestamp: string;
  };
  per_injection_type_breakdown: Record<string, InjectionTypeMetrics>;
}

export interface AnomalyBenchmarkRunResult {
  benchmark_results: AnomalyBenchmarkResult[];
  production_model_selection: {
    selected_model: AnomalyModelType;
    ranking_rule: string;
    tie_break_applied: boolean;
    benchmark_result_ids: string[];
    selected_at: string;
  };
}

// --- risk benchmark (app/risk/benchmark/schemas.py) ---

export type RiskModelType = 'logistic_regression' | 'random_forest' | 'xgboost';

export interface RiskBenchmarkResult {
  model_type: RiskModelType;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
  calibration_brier_score: number;
  false_negative_rate: number;
  label_distribution_context: Record<string, unknown>;
  risk_dataset_version: string;
  split_id: string;
}

export interface RiskBenchmarkRunResult {
  benchmark_results: RiskBenchmarkResult[];
  production_model_selection: {
    selected_model: RiskModelType;
    ranking_rule: string;
    pr_auc_floor_used: number;
    tie_break_applied: boolean;
    benchmark_result_ids: string[];
    selected_at: string;
  };
  data_scale_warning: string | null;
}

// --- risk scoring (app/risk/scoring/schemas.py) ---

export interface SeverityResult {
  quality_failure_severity: number;
  anomaly_magnitude_score: number;
  materiality_score: number;
  weights_used: Record<string, number>;
  severity: number;
  computed_at: string;
}

export interface BusinessImpactComponent {
  name: string;
  value: number | null;
  /** `unavailable` is a first-class outcome, never a zero. Render the reason. */
  status: 'computed' | 'unavailable';
  reason: string | null;
}

export interface BusinessImpactResult {
  components: BusinessImpactComponent[];
  has_unavailable_components: boolean;
  business_impact: number;
  computed_at: string;
}

export interface PriorityResult {
  severity: number;
  risk: number;
  business_impact: number;
  affected_claims_score: number;
  weights_used: Record<string, number>;
  priority: number;
  computed_at: string;
}

// --- incidents (app/incidents/schemas.py) ---

export type IncidentStatus =
  | 'pending_investigation'
  | 'ready_for_review'
  | 'accepted'
  | 'rejected'
  | 'resolved'
  | 'reopened';

export interface EvidenceBundle {
  quality_check_bands: string[];
  anomaly_score_percentile: number;
  affected_claim_pct: number;
  affected_claims_amounts: number[];
  risk_score: number | null;
  baseline_amount_percentiles: Percentiles | null;
  analysis_context?: IncidentAnalysisContext | null;
}

export interface Incident {
  incident_id: string;
  window_id: string;
  quality_score: number;
  anomaly_score: number;
  risk_score: number;
  severity_result: SeverityResult;
  business_impact_result: BusinessImpactResult;
  priority_result: PriorityResult;
  evidence_snapshot: Partial<EvidenceBundle>;
  status: IncidentStatus;
  current_investigation_id: string | null;
  created_at: string;
  updated_at: string;
}

// --- llm (app/llm/schemas.py) ---

export interface LLMInvestigation {
  investigation_id: string;
  incident_id: string;
  evidence_snapshot_id: string;
  summary: string;
  likely_root_cause: string;
  /** When true the model declined to guess -- surface it, don't hide it. */
  insufficient_evidence: boolean;
  evidence: string;
  business_impact_narrative: string;
  recommended_fix: string;
  prevention_recommendation: string;
  model_version: string;
  generated_at: string;
}

export interface InvestigationFailure {
  failure_id: string;
  incident_id: string;
  failure_type: 'api_error' | 'timeout' | 'malformed_response';
  error_detail: string;
  occurred_at: string;
}

/** `GET /llm/investigations/{incident_id}` returns history, not one record. */
export interface InvestigationHistoryResponse {
  investigations: LLMInvestigation[];
  failures: InvestigationFailure[];
}

// --- hitl (app/hitl/schemas.py) ---

export type ReasonCategory =
  | 'incorrect_root_cause'
  | 'insufficient_evidence_disagreement'
  | 'false_positive'
  | 'other';

export interface AcceptRequest {
  reviewer_id: string;
}

export interface RejectRequest {
  reviewer_id: string;
  reason_category: ReasonCategory;
  feedback_text: string;
}

export interface HumanFeedbackRead {
  feedback_id: string;
  incident_id: string;
  investigation_id: string;
  reason_category: string;
  feedback_text: string;
  reviewer_id: string;
  submitted_at: string;
}

export interface RecalculateResponse {
  incident: Incident;
  new_investigation: LLMInvestigation | null;
  evidence_changed: boolean;
}

// --- audit (app/audit/schemas.py) ---

export type PipelineStage =
  | 'cleaning'
  | 'quality'
  | 'anomaly'
  | 'risk'
  | 'severity_scoring'
  | 'llm_investigation'
  | 'incident_status'
  | 'human_feedback'
  | 'remediation'
  | 'revalidation';

export interface AuditTrailEntry {
  entry_id: string;
  entity_type: 'claim' | 'incident' | 'batch';
  entity_id: string;
  pipeline_stage: PipelineStage;
  source_module: string;
  source_record_id: string;
  baseline_snapshot_id_used: string | null;
  sequence_number: number;
  occurred_at: string;
}

export interface HistoryQueryResult {
  entity_type: string;
  entity_id: string;
  entries: AuditTrailEntry[];
  page: number;
  page_size: number;
  total_count: number;
  /** False only when the entity has no history at all -- not for an empty page. */
  found: boolean;
}

// --- demo: synthetic batches, pipeline runs, simulator (app/demo/schemas.py) ---

export interface InjectionPlanSummary {
  rates: Partial<Record<InjectionType, number>>;
  clusters: { name: string; rates: Partial<Record<InjectionType, number>>; density: number }[];
  background_density: number;
}

export interface BatchSpec {
  batch_id: string;
  label: string;
  description: string;
  claim_count: number;
  start_date: string;
  end_date: string;
  seed: number;
  amount_scale: number;
  amount_spread: number;
  extra_missing_pct: number;
  duplicate_rate: number;
  injection_plan: InjectionPlanSummary;
}

export interface BatchManifestEntry {
  batch_id: string;
  label: string;
  description: string;
  file: string;
  ground_truth_file: string;
  rows: number;
  claims: number;
  injected_rows: number;
  injected_counts: Record<string, number>;
  date_from: string;
  date_to: string;
  clm_pmt_amt_sum: number;
  clm_pmt_amt_median: number;
  duplicate_rows: number;
  missing_cell_pct: number;
  generated_at: string;
  spec: BatchSpec;
}

/** The ten distinct risk signal types the XGBoost model consumes. */
export interface SubScores {
  missing_data_risk: number;
  null_risk: number;
  duplicate_risk: number;
  sla_timeliness_risk: number;
  range_risk: number;
  dtype_risk: number;
  validity_risk: number;
  uniqueness_risk: number;
  freshness_risk: number;
  anomaly_risk: number;
}

export interface AnomalyEvaluation {
  model_type: string;
  train_rows: number;
  eval_rows: number;
  injected_eval_rows: number;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
  per_injection_type: Record<string, { precision: number; recall: number; f1: number }>;
  threshold: number;
  detection_latency_ms: number;
  execution_time_s: number;
  feature_columns: string[];
  parameters: Record<string, unknown>;
}

export interface WindowRiskAssessment {
  window_id: string;
  window_start: string;
  window_end: string;
  claim_count: number;
  sub_scores: SubScores;
  risk_score: number;
  severity_band: string;
  anomaly_claim_count: number;
  dominant_injection_type: string | null;
  affected_claim_pct: number;
  affected_claims_amounts: number[];
  anomaly_score_percentile: number;
  quality_check_bands: string[];
  deviation_pct: number;
}

export interface PipelineRunResult {
  run_id: string;
  source: string;
  batch_id: string;
  batch_label: string;
  injection_applied: boolean;
  rows: number;
  claims: number;
  quality_run_id: string;
  quality_composite_score: number;
  quality_band_counts: Record<string, number>;
  quality_type_band_counts: Record<string, Record<string, number>>;
  anomaly: AnomalyEvaluation;
  risk_model_type: string;
  windows: WindowRiskAssessment[];
  incident_ids: string[];
  incident_severity_counts: Record<string, number>;
  /** The exact LLMInvestigation record logged for each incident created in
   * this run -- same shape/content GET /llm/investigations/{id} returns,
   * included directly so a caller doesn't need a follow-up fetch per
   * incident just to see what narrative.to_investigation() produced. */
  investigations: LLMInvestigation[];
  started_at: string;
  completed_at: string;
}

export type SimulationState = 'queued' | 'ingesting' | 'analyzing' | 'complete' | 'failed';

export interface SimulationStatus {
  run_id: string;
  batch_id: string;
  batch_label: string;
  inject_anomalies: boolean;
  state: SimulationState;
  chunk_index: number;
  chunk_total: number;
  chunk_interval_seconds: number;
  claims_ingested: number;
  claims_total: number;
  current_window: string | null;
  message: string;
  started_at: string;
  updated_at: string;
  result: PipelineRunResult | null;
  error: string | null;
}

/**
 * What the demo pipeline records on an incident's `evidence_snapshot`:
 * which window, which detected anomaly type, the ten risk sub-scores, and
 * the rendered narrative. Optional because incidents created by other
 * producers (or before this feature) do not carry it.
 */
export interface IncidentAnalysisContext {
  batch_id: string;
  batch_label: string;
  source: string;
  injection_applied: boolean;
  window_start: string;
  window_end: string;
  claim_count: number;
  anomaly_claim_count: number;
  detected_anomaly_type: string | null;
  deviation_pct: number;
  risk_model: string;
  risk_score: number;
  severity_band: string;
  sub_scores: SubScores;
  narrative: {
    risk_summary: string;
    root_cause: string;
    investigation: string;
    recommended_fix: string;
    prevention: string;
  };
}
