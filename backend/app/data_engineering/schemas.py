"""Pydantic models for the data profiling foundation feature.

See specs/001-data-profiling-foundation/data-model.md for field definitions
and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ColumnCategory(str, Enum):
    IDENTIFIER = "identifier"
    DATE = "date"
    AMOUNT = "amount"
    UTILIZATION_DURATION = "utilization_duration"
    CATEGORICAL_CODE = "categorical_code"
    DIAGNOSIS_PROCEDURE_CODE = "diagnosis_procedure_code"


class ValueCount(BaseModel):
    value: str
    count: int = Field(ge=0)


class NumericStats(BaseModel):
    mean: float
    median: float
    std: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float


class ColumnProfile(BaseModel):
    column_name: str
    category: ColumnCategory
    dtype_observed: str
    missing_count: int = Field(ge=0)
    missing_pct: float = Field(ge=0, le=100)
    cardinality: int = Field(ge=0)
    numeric_stats: NumericStats | None = None
    categorical_top_values: list[ValueCount] | None = None
    date_format_observed: str | None = None
    date_min: str | None = None
    date_max: str | None = None


class ProfilingReport(BaseModel):
    source_file: str
    generated_at: datetime
    total_rows: int = Field(ge=0)
    total_columns: int = Field(ge=0)
    unique_claim_count: int = Field(ge=0)
    unique_beneficiary_count: int = Field(ge=0)
    lines_per_claim_mean: float
    lines_per_claim_median: float
    duplicate_row_count: int = Field(ge=0)
    columns: list[ColumnProfile]


class SampleManifest(BaseModel):
    output_file: str
    source_file: str
    seed: int
    target_claim_fraction: float = Field(gt=0, le=1)
    claims_included: int = Field(ge=0)
    rows_included: int = Field(ge=0)
    generated_at: datetime


class QualityIssue(str, Enum):
    DATE_FORMAT_STANDARDIZED = "date_format_standardized"
    DATE_UNPARSEABLE = "date_unparseable"
    MISSING_VALUE = "missing_value"
    DUPLICATE_ROW = "duplicate_row"
    INVALID_VALUE_NEGATIVE_AMOUNT = "invalid_value_negative_amount"
    INVALID_VALUE_DATE_OUT_OF_RANGE = "invalid_value_date_out_of_range"
    UNRECOGNIZED_CODE = "unrecognized_code"


class QualityIssueRecord(BaseModel):
    row_identifier: str
    column_name: str
    original_value: str | None
    cleaned_value: str | None
    quality_issue: QualityIssue
    detected_at: datetime


class SchemaValidationResult(BaseModel):
    passed: bool
    expected_column_count: int = Field(ge=0)
    actual_column_count: int = Field(ge=0)
    missing_columns: list[str] = Field(default_factory=list)
    unexpected_columns: list[str] = Field(default_factory=list)


class CleaningRunSummary(BaseModel):
    source_file: str
    output_file: str
    rows_in: int = Field(ge=0)
    rows_out: int = Field(ge=0)
    duplicate_rows_excluded: int = Field(ge=0)
    quality_issue_count: int = Field(ge=0)
    generated_at: datetime
