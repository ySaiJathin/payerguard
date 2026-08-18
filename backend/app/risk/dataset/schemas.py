"""Pydantic models for risk dataset construction.

See specs/008-risk-dataset-construction/data-model.md for field
definitions and validation rules.
"""

from datetime import date, datetime

from pydantic import BaseModel


class RiskDatasetRow(BaseModel):
    window_id: str
    window_start: date
    window_end: date
    claim_count: int
    gx_failure_count: int
    anomaly_score: float
    anomaly_frequency: float
    affected_claim_pct: float
    volume_deviation: float
    amount_deviation: float
    historical_quality_failure_rate: float
    investigation_risk_indicator: float
    investigation_risk_label: int


class InvestigationRiskLabelFormula(BaseModel):
    formula_version: str
    weights: dict[str, float]
    normalization_stats: dict[str, dict[str, float]]
    percentile_threshold: float
    rationale_text: str
    generated_at: datetime


class LabelDistributionReport(BaseModel):
    total_rows: int
    investigation_worthy_count: int
    investigation_worthy_pct: float
    not_investigation_worthy_count: int
    not_investigation_worthy_pct: float
    zero_claim_window_count: int


class RiskDatasetBuildResult(BaseModel):
    rows_built: int
    label_distribution: LabelDistributionReport
    formula_version: str
