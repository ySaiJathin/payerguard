"""Shared fixture builders for revalidation tests -- not a test module
itself (no `test_` prefix, so pytest doesn't collect it).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.anomaly.schemas import BenchmarkRunResult
from app.anomaly.schemas import ModelType as AnomalyModelType
from app.anomaly.schemas import ProductionModelSelection
from app.data_engineering.schemas import ColumnCategory, ProfilingReport
from app.incidents.models import Incident as IncidentORM
from app.remediation.models import ManualActionRequired as ManualActionRequiredORM
from app.remediation.models import RemediationAction as RemediationActionORM
from app.remediation.models import RemediationRun as RemediationRunORM
from app.revalidation import recompute_service
from app.revalidation.schemas import CurrentClaimState, RevalidationRunRequest
from app.risk.benchmark.schemas import ModelType as RiskModelType
from app.risk.benchmark.schemas import ProductionRiskModelSelection
from app.risk.benchmark.schemas import RiskBenchmarkRunResult

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_quality_fixtures() -> tuple[dict[str, ColumnCategory], ProfilingReport, pd.DataFrame]:
    """Reuses `tests/quality/test_suite_builder.py`'s own fixture files --
    a real, small Phase 1 categories/profiling-report/reference-data set,
    so `_recompute_quality`'s GX suite execution is genuine, not mocked."""
    categories_raw = json.loads((FIXTURES / "quality_column_categories.json").read_text(encoding="utf-8"))
    categories = {col: ColumnCategory(cat) for col, cat in categories_raw.items()}
    profiling_report = ProfilingReport.model_validate_json(
        (FIXTURES / "quality_profiling_report.json").read_text(encoding="utf-8")
    )
    reference_df = pd.read_csv(FIXTURES / "quality_reference_sample.csv", sep="|", low_memory=False)
    return categories, profiling_report, reference_df


class FakeAnomalyDetector:
    """A trivial, real-object stand-in for HBOSDetector -- `.score` is a
    genuine method call the test can spy on (SC-001), not a mock that
    merely records it "would have" been called."""

    def __init__(self, scores: list[float]):
        self._scores = scores
        self.score_call_count = 0

    def score(self, df: pd.DataFrame) -> np.ndarray:
        self.score_call_count += 1
        return np.array(self._scores[: len(df)])


class FakeRiskModel:
    """A trivial, real-object stand-in for the fitted XGBoost/sklearn
    classifier -- `.predict_proba` is a genuine method call."""

    def __init__(self, probabilities: list[float]):
        self._probabilities = probabilities
        self.predict_proba_call_count = 0

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        self.predict_proba_call_count += 1
        return np.array([[1.0 - p, p] for p in self._probabilities[: len(df)]])


def make_anomaly_artifact(scores: list[float], feature_columns: list[str], p95_threshold: float = 5.0) -> dict:
    return {
        "model": FakeAnomalyDetector(scores),
        "feature_columns": feature_columns,
        "train_medians": {col: 0.0 for col in feature_columns},
        "calibrated_thresholds": {"p95": p95_threshold},
        "model_type": "hbos",
    }


def make_risk_artifact(probabilities: list[float], feature_columns: list[str]) -> dict:
    return {
        "model": FakeRiskModel(probabilities),
        "feature_columns": feature_columns,
    }


def make_incident(
    db: Session,
    status: str = "accepted",
    incident_id: str | None = None,
    *,
    quality_score: float = 40.0,
    anomaly_score: float = 60.0,
    risk_score: float = 70.0,
    severity: float = 55.0,
    priority: float = 65.0,
    affected_claim_pct: float = 0.2,
    affected_claims_amounts: list[float] | None = None,
    baseline_amount_percentiles: dict | None = None,
) -> IncidentORM:
    now = datetime.now(timezone.utc)
    orm = IncidentORM(
        incident_id=incident_id or str(uuid4()),
        window_id="W1",
        quality_score=quality_score,
        anomaly_score=anomaly_score,
        risk_score=risk_score,
        severity_result={"severity": severity},
        business_impact_result={},
        priority_result={"priority": priority},
        evidence_snapshot={
            "affected_claim_pct": affected_claim_pct,
            "affected_claims_amounts": affected_claims_amounts or [1000.0],
            "baseline_amount_percentiles": baseline_amount_percentiles
            or {"p25": 100.0, "p50": 500.0, "p75": 1000.0, "p95": 5000.0, "p99": 10000.0},
        },
        status=status,
        current_investigation_id=None,
        created_at=now,
        updated_at=now,
    )
    db.add(orm)
    db.commit()
    db.refresh(orm)
    return orm


def make_remediation_run(
    db: Session, incident_id: str, *, completed: bool = True, with_manual_action: bool = False, claim_id: str = "CLM1001"
) -> str:
    """Persists a minimal 013 `RemediationRun`/`RemediationAction`/
    `ManualActionRequired` row set directly at the ORM layer, bypassing
    013's actual engine -- revalidation tests only care about the run's
    `completed_at`/outstanding-manual-action shape, not how it got there."""
    now = datetime.now(timezone.utc)
    run_id = str(uuid4())
    db.add(
        RemediationRunORM(
            run_id=run_id,
            incident_id=incident_id,
            started_at=now,
            completed_at=now if completed else None,
        )
    )
    if with_manual_action:
        db.add(
            ManualActionRequiredORM(
                record_id=str(uuid4()),
                run_id=run_id,
                incident_id=incident_id,
                claim_id=claim_id,
                description="No approved handler matched.",
                reason_code="no_matching_rule",
                flagged_at=now,
            )
        )
    else:
        db.add(
            RemediationActionORM(
                action_id=str(uuid4()),
                run_id=run_id,
                incident_id=incident_id,
                claim_id=claim_id,
                rule_id="dup-001",
                before_value=None,
                after_value="DUPLICATE_FLAGGED",
                applied_at=now,
            )
        )
    db.commit()
    return run_id


def patch_recompute_dependencies(monkeypatch, anomaly_artifact: dict, risk_artifact: dict) -> None:
    """Patches `recompute_service`'s I/O boundaries (Phase 1's category/
    profiling-report loaders, Phase 7's/Phase 9's benchmark-result
    readers, and the pickled-artifact loader) to return small, real
    fixture objects -- leaving every actual *compute* call
    (`run_category_suites`, `detector.score`, `model.predict_proba`,
    Phase 10's functions) as genuine, unmocked invocations. Shared by
    every revalidation test that needs `recompute_service.recompute` to
    run end to end without touching the real repo `data/` directory."""
    categories, profiling_report, reference_df = load_quality_fixtures()
    monkeypatch.setattr(recompute_service, "load_column_categories", lambda: categories)
    monkeypatch.setattr(recompute_service, "read_profiling_report", lambda: profiling_report)
    monkeypatch.setattr(recompute_service, "load_source_csv", lambda *a, **k: reference_df)

    anomaly_run_result = BenchmarkRunResult(
        benchmark_results=[],
        production_model_selection=ProductionModelSelection(
            selected_model=AnomalyModelType.hbos,
            ranking_rule="test",
            tie_break_applied=False,
            benchmark_result_ids=[],
            selected_at=profiling_report.generated_at,
        ),
    )
    monkeypatch.setattr(recompute_service, "read_benchmark_run_result", lambda: anomaly_run_result)

    risk_run_result = RiskBenchmarkRunResult(
        benchmark_results=[],
        production_model_selection=ProductionRiskModelSelection(
            selected_model=RiskModelType.xgboost,
            ranking_rule="test",
            pr_auc_floor_used=0.0,
            tie_break_applied=False,
            benchmark_result_ids=[],
            selected_at=profiling_report.generated_at,
        ),
    )
    monkeypatch.setattr(recompute_service.benchmark_log, "read_latest_run_result", lambda: risk_run_result)

    def _fake_load_pickled_artifact(path):
        return risk_artifact if "risk" in str(path) else anomaly_artifact

    monkeypatch.setattr(recompute_service, "_load_pickled_artifact", _fake_load_pickled_artifact)


def make_revalidation_request(remediation_run_id: str, claim_id: str = "1001") -> RevalidationRunRequest:
    """A standard `RevalidationRunRequest` built from the same reference
    claim `load_quality_fixtures()`'s data represents -- shared across
    tests that don't care about the specific raw field values, only that
    a real GX-checkable claim row is supplied."""
    return RevalidationRunRequest(
        remediation_run_id=remediation_run_id,
        current_claims=[
            CurrentClaimState(
                claim_id=claim_id,
                raw_fields={
                    "BENE_ID": "5001",
                    "CLM_FROM_DT": "2015-04-01",
                    "CLM_THRU_DT": "2015-04-05",
                    "CLM_PMT_AMT": 1200.50,
                    "CLM_IP_ADMSN_TYPE_CD": "1",
                    "PRNCPAL_DGNS_CD": "I10",
                    "OT_PHYSN_UPIN": "UPIN001",
                    "CLM_LINE_NUM": "1",
                },
            )
        ],
        anomaly_features={"f1": 1.0, "f2": 2.0},
        risk_features={"f1": 1.0, "f2": 2.0},
    )
