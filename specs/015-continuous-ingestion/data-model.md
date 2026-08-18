# Phase 1 Data Model: Continuous Ingestion

## IngestedBatch

| Field | Type | Notes |
|---|---|---|
| `batch_id` | string | |
| `filename` | string | Informational only, not the dedup key |
| `content_hash` | string | SHA-256, the dedup key (spec FR-004) |
| `ingestion_method` | enum | `manual_upload`, `watched_folder` |
| `row_count` | integer | |
| `date_range` | object | `{min_date, max_date}` computed from the batch |
| `processing_status` | enum | `rejected_malformed`, `rejected_empty`, `rejected_duplicate`, `processing`, `completed`, `failed` |
| `overlap_flag_id` | string \| null | Set if `DateRangeOverlapFlag` was raised (spec FR-007) |
| `ingested_at` | timestamp | |

**Validation rules**: `content_hash` is unique among non-rejected batches — a match against an existing hash produces `processing_status: "rejected_duplicate"` unless an explicit force-reprocess override is supplied (spec FR-004).

## BatchProcessingResult

| Field | Type | Notes |
|---|---|---|
| `batch_id` | string | |
| `cleaning_run_id` / `quality_run_id` / `feature_run_id` / `anomaly_scores_ref` / `risk_scores_ref` | string | References to the exact Phase 2/3/5/7/9 outputs produced for this batch — not duplicated data |
| `incidents_created` | string[] | `Incident` IDs created via Phase 12, if any |
| `completed_at` | timestamp | |

## DateRangeOverlapFlag

| Field | Type | Notes |
|---|---|---|
| `flag_id` | string | |
| `batch_id` | string | The new, overlapping batch |
| `overlapping_batch_ids` | string[] | Existing batch(es) it overlaps with |
| `overlap_date_range` | object | The intersecting date span |
| `reviewed` | boolean | Defaults false — pending explicit review |

## ProcessedFileManifestEntry

| Field | Type | Notes |
|---|---|---|
| `file_path` | string | Watched-folder relative path |
| `content_hash` | string | |
| `first_seen_at` | timestamp | |

**Validation rules**: Prevents reprocessing on watcher restart (spec FR-006).

## Relationships

`IngestedBatch` is 1:1 with a `BatchProcessingResult` once processing completes successfully, and 0-or-1 with a `DateRangeOverlapFlag`. `ProcessedFileManifestEntry` exists only for `watched_folder`-sourced batches and is the watcher's own idempotency record, separate from (but consistent with) `IngestedBatch.content_hash`-based dedup.
