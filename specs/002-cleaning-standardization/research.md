# Phase 0 Research: Cleaning & Standardization

## Decision: Cleaning reads Phase 1's `column_categories.json` as its schema source of truth

**Decision**: `dtype_conversion.py` loads the categorization artifact produced by Phase 1 (data-profiling-foundation) rather than re-deriving column categories.

**Rationale**: Avoids duplicating categorization logic in two features (violates DRY and risks the two copies drifting apart); Phase 1 already validated categorization against MVP_CONTEXT.md Section 2.3 ground truth.

**Alternatives considered**: Re-implementing categorization inline in the cleaning module — rejected as duplicated logic with drift risk.

## Decision: Duplicates are excluded from the working dataset, never deleted from source

**Decision**: `duplicate_detection.py` flags full-row duplicates and excludes them only from the in-memory/output *cleaned* dataset that downstream phases consume; the raw source file and the audit trail retain the duplicate row's existence.

**Rationale**: MVP_CONTEXT.md Section 4 explicitly states "never silently delete bad records" for the cleaning step; excluding from the analytical dataset while keeping a recoverable trail satisfies both "downstream phases get deduplicated data" and "nothing is silently destroyed."

**Alternatives considered**: Keeping duplicates in the cleaned dataset with a flag column (rejected — would silently double-count claims in every downstream statistic, e.g., baseline volume, unless every single downstream phase remembered to filter, which is fragile); hard-deleting from the raw file (rejected — directly violates the no-silent-deletion rule and Phase 1's read-only guarantee on `data/raw/`).

## Decision: Invalid-value rules are documented, data-derived thresholds — not CMS external code tables

**Decision**: Code-set validity for categorical/diagnosis/procedure columns is defined by the set of values *observed* in Phase 1's profiling output, not an external CMS reference table (none is in scope for this MVP — single dataset only, per constitution "Scope Discipline").

**Rationale**: Introducing an external CMS code-set reference file would exceed the MVP's declared single-dataset scope and risk flagging legitimate-but-rare codes as invalid when they're simply CMS codes this sample happens not to contain. Observed-set membership is a defensible, data-grounded heuristic, and it's explicitly framed in the spec's Assumptions as advisory input to Phase 3's quality score rather than a hard rejection.

**Alternatives considered**: Hardcoding a known CMS code list (rejected — out of scope, and risks becoming a second, unmaintained source of truth that contradicts constitution Principle II if it ever goes stale relative to the real data).

## Decision: Plausible date range derived from observed data range with documented slack

**Decision**: Invalid-date detection uses the observed min/max claim dates from Phase 1's profiling report (2015-04-01 to 2022-10-31) plus a configurable slack window (e.g., ±1 year) as the plausibility bound, rather than a hardcoded calendar range.

**Rationale**: Ties the validity check to the actual data (constitution Principle II) while still catching genuinely implausible values (e.g., a date in 1900 or 2099) that the observed range alone — with zero slack — would over-flag as "invalid" for legitimately late-arriving claims near the boundary.

**Alternatives considered**: Exact observed min/max with zero slack (rejected — would flag legitimate boundary-adjacent claims as invalid); a fixed absolute range like 2000–2030 (rejected — hardcoded, not data-derived, violates Principle II's spirit).

## Decision: Idempotency via deterministic, pure-function cleaning (no in-place mutation of prior output)

**Decision**: Each cleaning run reads only from `data/raw/inpatient.csv` (or the Phase 1 sample) and fully regenerates `data/cleaned/inpatient_cleaned.csv` and `data/reports/quality_issues.json` from scratch, rather than incrementally patching prior output.

**Rationale**: This is the simplest way to guarantee SC-004 (byte-identical output across repeated runs on unmodified input) — incremental/patch-based approaches risk accumulating stale or duplicate audit entries, which FR-009 explicitly forbids.

**Alternatives considered**: Incremental append-only audit log (rejected for this MVP — reintroduces exactly the "duplicate/accumulating audit entries" failure mode the spec's idempotency requirement rules out; could be revisited once Phase 15's continuous-ingestion batching needs incremental processing, at which point batch identity, not full-file identity, becomes the idempotency key).
