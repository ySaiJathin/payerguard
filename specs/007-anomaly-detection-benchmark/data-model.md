# Phase 1 Data Model: Anomaly Detection Benchmark

## AnomalyModelCandidate

| Field | Type | Notes |
|---|---|---|
| `model_type` | enum | `iqr`, `hbos`, `isolation_forest`, `lof` |
| `fitted_on_split` | string | Always `"train"` (spec FR-002) |
| `calibrated_on_split` | string | Always `"validation"` |
| `parameters` | object | Model-specific: IQR bounds, HBOS bin config, Isolation Forest `n_estimators`/`contamination`, LOF `n_neighbors` |
| `calibrated_thresholds` | object | e.g., HBOS 95th/99th percentile bands, per Section 3.1 |
| `artifact_path` | string | e.g., `data/models/anomaly/hbos.pkl` |

## InjectedAnomalyInstance

| Field | Type | Notes |
|---|---|---|
| `synthetic_instance_id` | string | Unique per injected instance |
| `injection_type` | enum | `missing_value_spike`, `amount_spike`, `duplicate_spike`, `volume_drop`, `distribution_shift` |
| `split` | enum | `validation` or `test` — never `train` (spec FR-005) |
| `affected_rows` / `affected_columns` | array | |
| `ground_truth_label` | enum | Always `anomaly` for injected instances |

## BenchmarkResult

| Field | Type | Notes |
|---|---|---|
| `model_type` | enum | Matches `AnomalyModelCandidate.model_type` |
| `precision` / `recall` / `f1` / `fpr` | float | Computed against test-split ground truth (real=normal, injected=anomaly) |
| `detection_latency_ms` | float | Per-instance scoring latency |
| `execution_time_s` | float | Total fit+evaluate time |
| `measurement_context` | object | `{hardware, python_version, run_timestamp}` (spec FR-009) |
| `per_injection_type_breakdown` | object | injection_type → `{precision, recall, f1}` |

## ProductionModelSelection

| Field | Type | Notes |
|---|---|---|
| `selected_model` | enum | The `model_type` that won |
| `ranking_rule` | string | `"F1 primary, FPR tie-break, execution_time second tie-break"` (spec Assumptions/research.md) |
| `tie_break_applied` | boolean | Whether a tie actually occurred |
| `benchmark_result_ids` | string[] | All four `BenchmarkResult` entries this selection was derived from |
| `selected_at` | timestamp | |

**Validation rules**: `selected_model` is verifiably the top-ranked entry in `benchmark_result_ids` under `ranking_rule` (spec SC-004) — a recomputation test applies `ranking_rule` to the referenced results and asserts it reproduces `selected_model`.

## WindowAnomalyEnrichment

| Field | Type | Notes |
|---|---|---|
| `window_id` | string | Matches Phase 5's `WindowFeatures.window_id` |
| `anomaly_count` | integer | Computed from the selected production model against real (non-injected) claims in this window |
| `model_used` | string | `ProductionModelSelection.selected_model` |
| `enriched_at` | timestamp | |

**Validation rules**: Re-running enrichment against unmodified window data and an unchanged `ProductionModelSelection` produces identical `anomaly_count` per window (spec SC-006).

## Relationships

`ProductionModelSelection` references exactly one `BenchmarkResult` per `model_type` (four total) and, once selected, is the sole input to every `WindowAnomalyEnrichment` record. `InjectedAnomalyInstance` records exist only for `validation`/`test` splits and are the ground truth `BenchmarkResult` metrics are computed against.
