# Phase 1 Data Model: Batch File Ingestion

## IngestedBatch

| Field | Type | Notes |
|---|---|---|
| `batch_id` | string | Generated at upload time; independent identity even for a repeated filename/content (spec FR-005) |
| `filename` | string | As supplied by the uploader |
| `stored_path` | string | Where the raw bytes were persisted (`data/raw/uploads/`) |
| `uploaded_at` | timestamp | |
| `row_count` | integer \| null | Null only if rejected before the file could be parsed at all |
| `status` | enum | `rejected`, `accepted`, `processing`, `completed`, `failed` (spec FR-007) |
| `rejection_reason` | string \| null | Set only when `status = rejected`; references a `BatchUploadRejection` |
| `pipeline_stage_reached` | string \| null | Last pipeline stage that completed successfully — lets `failed` report *where* it stopped, not just that it stopped |
| `quality_result_id` | string \| null | Phase 3's `run_id` for this batch's validation, once reached |
| `anomaly_result_id` | string \| null | Which production anomaly model enriched this batch's windows (Phase 7 has no per-run id of its own to reference — recorded honestly as "which model," not a fabricated run id) |
| `risk_result_id` | string \| null | Marker that this batch's windows were scored against the production risk model (Phase 9 likewise has no per-window persisted-result id to reference) |
| `incident_ids` | string[] | Any incidents created from this batch (Phase 12) |

**Validation rules**: `status` only ever advances forward (`rejected`/`accepted` → `processing` → `completed`/`failed`) — never silently reverted or skipped (spec FR-007, SC-004). `batch_id` is unique per upload attempt regardless of `filename`/content repetition (spec FR-005, SC-003). Every reference field points at something real (a persisted record's id, or an honest "which model" marker where no persisted-per-run id exists upstream) — never a fabricated identifier (constitution Principle II).

**Implementation note (see tasks.md Post-Implementation Finding A)**: only the raw upload gets durable, batch-scoped storage. Downstream Phase 3/5/7 results are read/written through each phase's existing shared, single-current-batch state (unchanged by this feature) because Phase 7's enrichment has no per-batch override at all — so `quality_result_id`/`anomaly_result_id`/`risk_result_id` are reliable only until a *later* batch's run supersedes that shared state, not permanently resolvable independent of it.

## BatchUploadRejection

| Field | Type | Notes |
|---|---|---|
| `batch_id` | string | The `IngestedBatch` this rejection belongs to |
| `reason_code` | enum | `wrong_delimiter`, `missing_columns`, `unexpected_columns`, `empty_file`, `below_min_rows`, `above_max_size`, `unparseable` |
| `detail` | string | Human-readable specifics (e.g., which columns are missing) — spec FR-002 |

## BatchListing

| Field | Type | Notes |
|---|---|---|
| `batches` | IngestedBatch[] | Ordered newest-first (spec FR-006) |
| `page` / `page_size` / `total_count` | integer | Pagination metadata |

## Relationships

`IngestedBatch` is the entry point every downstream Phase 2–12 record traces back to for data that arrived through this feature — `quality_result_id`/`anomaly_result_id`/`risk_result_id`/`incident_ids` are references into those phases' own tables, never copies. Each accepted or rejected `IngestedBatch` also produces exactly one `audit.AuditTrailEntry` with `pipeline_stage = ingestion` (Phase 16's registry, re-entered per research.md's last decision), and every subsequent stage the batch reaches produces its own `AuditTrailEntry` the same way every other upload path already does — this feature adds no second audit-writing mechanism.
