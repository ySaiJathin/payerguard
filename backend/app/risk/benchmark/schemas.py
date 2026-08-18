"""Pydantic models for the risk model benchmark.

See specs/009-risk-model-benchmark/data-model.md for field definitions
and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ModelType(str, Enum):
    logistic_regression = "logistic_regression"
    random_forest = "random_forest"
    xgboost = "xgboost"


class RiskModelCandidate(BaseModel):
    model_type: ModelType
    fitted_on_split: str = "train"
    tuned_on_split: str = "validation"
    hyperparameters: dict
    artifact_path: str


class RiskBenchmarkResult(BaseModel):
    model_type: ModelType
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    calibration_brier_score: float
    false_negative_rate: float
    label_distribution_context: dict
    risk_dataset_version: str
    split_id: str


class ProductionRiskModelSelection(BaseModel):
    selected_model: ModelType
    ranking_rule: str
    pr_auc_floor_used: float
    tie_break_applied: bool
    benchmark_result_ids: list[str]
    selected_at: datetime


class RiskBenchmarkRunResult(BaseModel):
    """Matches contracts/api.md's response shape exactly, plus one
    additive field: `data_scale_warning` surfaces a data-scale limitation
    (e.g. a too-small validation split, or no model clearing the PR-AUC
    floor) as a reportable characteristic of the run -- mirroring Phase 6
    `TemporalSplit.sample_size_warning`'s precedent -- rather than a
    silent pass (spec Edge Cases).
    """

    benchmark_results: list[RiskBenchmarkResult]
    production_model_selection: ProductionRiskModelSelection
    data_scale_warning: str | None = None
