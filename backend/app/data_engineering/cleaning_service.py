"""Orchestrates: schema validation -> duplicate detection -> missing-value
flagging -> dtype/date conversion -> invalid-value detection, producing a
CleanedClaimLine dataset plus the QualityIssueRecord audit trail.

Duplicate detection runs first (on the raw, as-read values) so that an
excluded duplicate occurrence never also contributes missing-value/date/
invalid-value records under the same row_identifier as the kept occurrence.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.audit.aggregation_service import append_entries
from app.data_engineering.duplicate_detection import detect_and_exclude_duplicates
from app.data_engineering.dtype_conversion import (
    CategoriesUnavailableError,
    convert_dtypes,
    load_column_categories,
)
from app.data_engineering.invalid_value_detection import build_reference_stats, detect_invalid_values
from app.data_engineering.paths import cleaned_dir, raw_inpatient_csv, reports_dir, sampled_dir
from app.data_engineering.profiling_service import ProfilingError, load_source_csv
from app.data_engineering.quality_issue_log import write_cleaning_run_summary, write_quality_issues
from app.data_engineering.sampling_service import SAMPLE_FILENAME
from app.data_engineering.schemas import CleaningRunSummary, QualityIssue, QualityIssueRecord, SchemaValidationResult

__all__ = [
    "CategoriesUnavailableError",
    "SchemaValidationError",
    "CleaningError",
    "run_cleaning",
]

CLEANED_OUTPUT_FILENAME = "inpatient_cleaned.csv"
CLM_ID_COLUMN = "CLM_ID"
CLM_LINE_NUM_COLUMN = "CLM_LINE_NUM"


class CleaningError(ValueError):
    """Source file missing/unreadable."""


class SchemaValidationError(ValueError):
    def __init__(self, result: SchemaValidationResult):
        self.result = result
        super().__init__(
            f"Schema validation failed: expected {result.expected_column_count} columns, "
            f"got {result.actual_column_count}; missing={result.missing_columns}; "
            f"unexpected={result.unexpected_columns}"
        )


def _resolve_source_path(source: str) -> Path:
    if source == "raw":
        return raw_inpatient_csv()
    if source == "sampled":
        return sampled_dir() / SAMPLE_FILENAME
    raise CleaningError(f"Unknown source '{source}' -- expected 'raw' or 'sampled'.")


def _validate_schema(df: pd.DataFrame, categories: dict) -> SchemaValidationResult:
    expected_columns = set(categories.keys())
    actual_columns = set(df.columns)
    missing = sorted(expected_columns - actual_columns)
    unexpected = sorted(actual_columns - expected_columns)
    passed = not missing and not unexpected and len(df.columns) == len(categories)
    return SchemaValidationResult(
        passed=passed,
        expected_column_count=len(categories),
        actual_column_count=len(df.columns),
        missing_columns=missing,
        unexpected_columns=unexpected,
    )


def _row_id_map(df: pd.DataFrame) -> dict[int, str]:
    """Plain dict (row index -> row_identifier) -- see dtype_conversion
    .convert_dtypes for why this dataset's scale rules out per-cell
    `pd.Series.loc[idx]` lookups.
    """
    return (df[CLM_ID_COLUMN].astype(str) + ":" + df[CLM_LINE_NUM_COLUMN].astype(str)).to_dict()


def _missing_value_records(df: pd.DataFrame, row_id_map: dict[int, str]) -> list[QualityIssueRecord]:
    now = datetime.now(timezone.utc)
    records = []
    for column in df.columns:
        missing_idx = df.index[df[column].isna()].to_numpy()
        records.extend(
            QualityIssueRecord.model_construct(
                row_identifier=row_id_map[idx],
                column_name=column,
                original_value=None,
                cleaned_value=None,
                quality_issue=QualityIssue.MISSING_VALUE,
                detected_at=now,
            )
            for idx in missing_idx
        )
    return records


def _append_cleaning_audit_entries(db: "Session", records: list[QualityIssueRecord]) -> None:
    """One audit entry per affected claim (Phase 16 FR-001, US1 scenario 1).

    Granularity is deliberately per-claim, not per-`QualityIssueRecord`.
    The real 58,066-row x 197-column file produces on the order of
    millions of individual records (a missing cell is one record), and one
    audit row each would dwarf the rest of the trail by orders of
    magnitude while answering no question the claim-level entry doesn't.
    US1's acceptance scenario asks that querying *a claim* surfaces its
    cleaning correction, which per-claim granularity satisfies:
    `source_record_id` is the claim's `row_identifier`, and every
    individual record for it remains resolvable in the same run's
    `quality_issues.json` by that key -- so nothing is lost, only indexed
    at the level history is actually queried by.
    """
    seen: dict[str, datetime] = {}
    for record in records:
        # Keep the earliest correction time per claim -- that is when the
        # claim first entered cleaning, which is what the trail orders by.
        existing = seen.get(record.row_identifier)
        if existing is None or record.detected_at < existing:
            seen[record.row_identifier] = record.detected_at

    append_entries(
        db,
        [
            {
                "entity_type": "claim",
                "entity_id": row_identifier,
                "pipeline_stage": "cleaning",
                "source_module": "data_engineering",
                "source_record_id": row_identifier,
                "occurred_at": detected_at,
            }
            for row_identifier, detected_at in seen.items()
        ],
    )


def run_cleaning(
    source: str = "raw",
    source_path: Path | None = None,
    categories_dir: Path | None = None,
    reference_path: Path | None = None,
    output_dir: Path | None = None,
    reports_out_dir: Path | None = None,
    db: Session | None = None,
) -> CleaningRunSummary:
    """Runs the full cleaning pipeline.

    `source`/`source_path`/`categories_dir`/`reference_path`/`output_dir`/
    `reports_out_dir` default to the real project paths (used by the
    router); tests override them to point at fixtures/tmp_path so the
    pipeline can be exercised without touching real project data.

    `db` is optional (Phase 16): when supplied -- the router passes it --
    one audit entry per affected claim is appended. It defaults to `None`
    so every existing direct-call test keeps working unchanged, and so
    cleaning remains runnable without a database at all.
    """
    categories = load_column_categories(categories_dir)  # raises CategoriesUnavailableError if Phase 1 hasn't run

    resolved_source_path = source_path or _resolve_source_path(source)
    try:
        raw_df = load_source_csv(resolved_source_path, expected_column_count=None)
    except ProfilingError as exc:
        raise CleaningError(str(exc)) from exc

    validation = _validate_schema(raw_df, categories)
    if not validation.passed:
        raise SchemaValidationError(validation)

    rows_in = len(raw_df)
    row_ids_all = _row_id_map(raw_df)

    deduped_df, dup_records = detect_and_exclude_duplicates(raw_df, row_ids_all)
    row_id_map = _row_id_map(deduped_df)

    missing_records = _missing_value_records(deduped_df, row_id_map)

    converted_df, date_records = convert_dtypes(deduped_df, categories, row_id_map)

    if source == "raw" and source_path is None and reference_path is None:
        reference_df = raw_df
    else:
        ref_path = reference_path or raw_inpatient_csv()
        reference_df = load_source_csv(ref_path, expected_column_count=None)
    reference_stats = build_reference_stats(reference_df, categories)
    invalid_records = detect_invalid_values(converted_df, categories, row_id_map, reference_stats)

    all_records = dup_records + missing_records + date_records + invalid_records

    out_dir = reports_out_dir or reports_dir()
    write_quality_issues(all_records, out_dir)

    out_data_dir = output_dir or cleaned_dir()
    out_data_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_data_dir / CLEANED_OUTPUT_FILENAME
    converted_df.to_csv(output_path, index=False)

    if db is not None:
        _append_cleaning_audit_entries(db, all_records)

    summary = CleaningRunSummary(
        source_file=str(resolved_source_path),
        output_file=str(output_path),
        rows_in=rows_in,
        rows_out=len(converted_df),
        duplicate_rows_excluded=len(dup_records),
        quality_issue_count=len(all_records),
        generated_at=datetime.now(timezone.utc),
    )
    write_cleaning_run_summary(summary, out_dir)
    return summary
