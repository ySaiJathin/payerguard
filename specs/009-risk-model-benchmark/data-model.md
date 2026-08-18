# Phase 1 Data Model: Risk Model Benchmark

## RiskModelCandidate

| Field | Type | Notes |
|---|---|---|
| `model_type` | enum | `logistic_regression`, `random_forest`, `xgboost` |
| `fitted_on_split` | string | Always `"train"` |
| `tuned_on_split` | string | Always `"validation"` |
| `hyperparameters` | object | Model-specific, tuned on validation |
| `artifact_path` | string | e.g., `data/models/risk/xgboost.pkl` |

## RiskBenchmarkResult

| Field | Type | Notes |
|---|---|---|
| `model_type` | enum | Matches `RiskModelCandidate.model_type` |
| `accuracy` / `precision` / `recall` / `f1` | float | On test split |
| `roc_auc` / `pr_auc` | float | On test split |
| `calibration_brier_score` | float | Lower is better calibrated |
| `false_negative_rate` | float | |
| `label_distribution_context` | object | From Phase 8's `LabelDistributionReport`, carried through for interpretability |
| `risk_dataset_version` / `split_id` | string | Versioning keys (research.md) |

## ProductionRiskModelSelection

| Field | Type | Notes |
|---|---|---|
| `selected_model` | enum | The `model_type` that won |
| `ranking_rule` | string | `"PR-AUC floor gate, then rank by recall, Brier score tie-break, FNR final tie-break"` |
| `pr_auc_floor_used` | float | The documented minimum floor applied |
| `tie_break_applied` | boolean | |
| `benchmark_result_ids` | string[] | All three `RiskBenchmarkResult` entries |
| `selected_at` | timestamp | |

**Validation rules**: `selected_model` is verifiably the top-ranked survivor of the `ranking_rule` applied to `benchmark_result_ids` (spec SC-003) — a recomputation test enforces this. Row-to-split assignment underlying every `RiskBenchmarkResult` matches Phase 6's `TemporalSplit` boundaries exactly (spec SC-006).

## Relationships

`ProductionRiskModelSelection` references exactly one `RiskBenchmarkResult` per `model_type` (three total). Every `RiskBenchmarkResult` is computed against Phase 8's `RiskDatasetRow` set, split per Phase 6's `TemporalSplit` — neither dataset nor split is recomputed within this feature.
