"""Spec SC-001 / US1: `recompute_service.recompute` genuinely invokes
Phase 3's GX suites and Phase 7's/Phase 9's saved production models,
rather than reusing/copying the incident's stored pre-remediation
values.
"""

from unittest.mock import MagicMock

from app.revalidation import recompute_service
from tests._db_fixtures import make_test_session
from tests.revalidation._fixtures import (
    make_anomaly_artifact,
    make_incident,
    make_revalidation_request,
    make_risk_artifact,
    patch_recompute_dependencies,
)


def test_recompute_genuinely_invokes_phase3_phase7_phase9(monkeypatch):
    anomaly_artifact = make_anomaly_artifact(scores=[1.0], feature_columns=["f1", "f2"], p95_threshold=5.0)
    risk_artifact = make_risk_artifact(probabilities=[0.1], feature_columns=["f1", "f2"])
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    spy = MagicMock(wraps=recompute_service.run_category_suites)
    monkeypatch.setattr(recompute_service, "run_category_suites", spy)

    incident = make_incident(
        db=make_test_session(),
        quality_score=10.0,
        anomaly_score=90.0,
        risk_score=95.0,
        severity=80.0,
        priority=85.0,
    )
    request = make_revalidation_request(remediation_run_id="run-1")

    result = recompute_service.recompute(incident, request)

    # Phase 3's real GX execution was actually invoked, not skipped.
    spy.assert_called_once()
    # Phase 7's/Phase 9's real model objects were actually invoked.
    assert anomaly_artifact["model"].score_call_count == 1
    assert risk_artifact["model"].predict_proba_call_count == 1

    # The recomputed values are genuinely new, not copies of the
    # incident's stored pre-remediation scores.
    assert result.quality_score != incident.quality_score
    assert result.anomaly_score != incident.anomaly_score
    assert result.risk_score != incident.risk_score
