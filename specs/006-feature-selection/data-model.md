# Phase 1 Data Model: Feature Selection

## TemporalSplit

| Field | Type | Notes |
|---|---|---|
| `split_id` | string | |
| `train_date_range` | object | `{start, end}` — earliest 70% chronologically |
| `validation_date_range` | object | `{start, end}` — next 15% |
| `test_date_range` | object | `{start, end}` — latest 15%, never touched by selection |
| `train_count` / `validation_count` / `test_count` | integer | Real computed counts |
| `computed_at` | timestamp | |

**Validation rules**: Date ranges are non-overlapping and strictly increasing (train < validation < test) — spec SC-001. Deterministic given unmodified input data.

## FeatureDropDecision

| Field | Type | Notes |
|---|---|---|
| `feature_name` | string | |
| `stage` | enum | `1`, `2`, `3` |
| `reason` | string | Specific, non-generic — e.g., `"constant column (single value across all rows)"`, `"correlation 0.98 with payment_to_charge_ratio, higher missingness, dropped"` |
| `statistic_value` | float \| null | The number that triggered the drop, if applicable (correlation coefficient, variance, importance score) |
| `stage_computed_on` | enum | `train_validation` (always, for Stage 2/3) or `full_dataset` (Stage 1 structural checks, which don't require label/statistical fitting) |

**Validation rules**: Every dropped feature has exactly one record with a non-generic `reason` (spec FR-009, SC-004).

## SelectedFeatureSet

| Field | Type | Notes |
|---|---|---|
| `version_id` | string | |
| `features` | string[] | Final surviving feature names |
| `split_id` | string | References the `TemporalSplit` used |
| `target_used_for_stage3` | string | e.g., `"provisional_deviation_magnitude"` — explicit, per research.md | 
| `stage1_drop_count` / `stage2_drop_count` / `stage3_drop_count` | integer | |
| `generated_at` | timestamp | |

**Validation rules**: `features` excludes every column present in any `FeatureDropDecision` record. Recomputing Stage 2/3 with a corrupted test-split fixture yields an identical `features` list (spec SC-003).

## Relationships

`SelectedFeatureSet` references one `TemporalSplit` and many `FeatureDropDecision` records (one per dropped feature across all stages). Phase 7 and Phase 9 both reference the same `TemporalSplit.split_id` and (optionally) the same `SelectedFeatureSet.version_id` as their modeling input.
