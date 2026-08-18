# Phase 1 Data Model: Risk Dataset Construction

## RiskDatasetRow

| Field | Type | Notes |
|---|---|---|
| `window_id` | string | Matches Phase 4/5's window definition |
| `window_start` / `window_end` | date | Chronological ordering fields (spec FR-007) |
| `claim_count` | integer | From Phase 5 `WindowFeatures.claim_count` |
| `gx_failure_count` | integer | From Phase 3 `ExpectationCheckResult` CRITICAL (+configured WARNING) count for this window |
| `anomaly_score` / `anomaly_frequency` | float | Derived from Phase 7-enriched `WindowFeatures.anomaly_count` ÷ `claim_count` |
| `affected_claim_pct` | float | Claims flagged by ≥1 GX check or anomaly detection ÷ `claim_count` |
| `volume_deviation` / `amount_deviation` | float | From Phase 5 `WindowFeatures`, carried through unchanged |
| `historical_quality_failure_rate` | float | From Phase 4 `DataHealthBaseline` |
| `investigation_risk_indicator` | float | The computed `IRI` (see research.md) |
| `investigation_risk_label` | integer (0/1) | Thresholded `IRI` — spec FR-003, FR-005, FR-006 |

**Validation rules**: Every field except `investigation_risk_indicator`/`investigation_risk_label` is sourced unchanged from an upstream phase (spec FR-002, SC-001). `investigation_risk_label` is exactly reproducible by re-applying `InvestigationRiskLabelFormula` to the row's own `gx_failure_count`/`anomaly_frequency`/`volume_deviation`/`amount_deviation`-derived inputs (spec SC-002). Zero-claim windows always have `investigation_risk_label = 0` (spec SC-004).

## InvestigationRiskLabelFormula

| Field | Type | Notes |
|---|---|---|
| `formula_version` | string | |
| `weights` | object | `{w_q, w_a, w_d}` |
| `normalization_stats` | object | Per-signal min/max computed on Phase 6 train-split windows only |
| `percentile_threshold` | float | Default 75 |
| `rationale_text` | string | Explicitly references MVP_CONTEXT.md Section 2.4 (spec FR-004, SC-003) |
| `generated_at` | timestamp | |

## LabelDistributionReport

| Field | Type | Notes |
|---|---|---|
| `total_rows` | integer | |
| `investigation_worthy_count` / `investigation_worthy_pct` | integer / float | |
| `not_investigation_worthy_count` / `not_investigation_worthy_pct` | integer / float | |
| `zero_claim_window_count` | integer | Windows contributing a forced `label = 0` |

## Relationships

Every `RiskDatasetRow.investigation_risk_label` is produced by applying the single active `InvestigationRiskLabelFormula` to that row's own fields. `LabelDistributionReport` is computed once per dataset-construction run, over the full set of `RiskDatasetRow` records produced by that run.
