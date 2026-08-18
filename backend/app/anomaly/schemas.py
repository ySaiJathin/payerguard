"""Pydantic models for the anomaly detection benchmark.

See specs/007-anomaly-detection-benchmark/data-model.md for field
definitions and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ModelType(str, Enum):
    iqr = "iqr"
    hbos = "hbos"
    isolation_forest = "isolation_forest"
    lof = "lof"


class InjectionType(str, Enum):
    missing_value_spike = "missing_value_spike"
    amount_spike = "amount_spike"
    duplicate_spike = "duplicate_spike"
    volume_drop = "volume_drop"
    distribution_shift = "distribution_shift"


class AnomalyModelCandidate(BaseModel):
    model_type: ModelType
    fitted_on_split: str = "train"
    calibrated_on_split: str = "validation"
    parameters: dict
    calibrated_thresholds: dict
    artifact_path: str


class InjectedAnomalyInstance(BaseModel):
    synthetic_instance_id: str
    injection_type: InjectionType
    split: str  # "validation" or "test" -- never "train" (spec FR-005)
    affected_rows: list[str]
    affected_columns: list[str]
    ground_truth_label: str = "anomaly"


class MeasurementContext(BaseModel):
    hardware: str
    python_version: str
    run_timestamp: datetime


class InjectionTypeMetrics(BaseModel):
    precision: float
    recall: float
    f1: float


class BenchmarkResult(BaseModel):
    model_type: ModelType
    precision: float
    recall: float
    f1: float
    fpr: float
    detection_latency_ms: float
    execution_time_s: float
    measurement_context: MeasurementContext
    per_injection_type_breakdown: dict[str, InjectionTypeMetrics]


class ProductionModelSelection(BaseModel):
    selected_model: ModelType
    ranking_rule: str
    tie_break_applied: bool
    benchmark_result_ids: list[str]
    selected_at: datetime


class BenchmarkRunResult(BaseModel):
    benchmark_results: list[BenchmarkResult]
    production_model_selection: ProductionModelSelection


class WindowAnomalyEnrichment(BaseModel):
    window_id: str
    anomaly_count: int
    model_used: str
    enriched_at: datetime


class EnrichWindowsResult(BaseModel):
    windows_enriched: int
    model_used: str
