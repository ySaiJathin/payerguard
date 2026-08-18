import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.risk.scoring.errors import MissingRiskScoreError
from app.risk.scoring.priority import compute_priority
from app.risk.scoring.router import router as router_module


def test_compute_priority_raises_rather_than_defaulting_missing_risk():
    with pytest.raises(MissingRiskScoreError):
        compute_priority(severity=50.0, risk=None, business_impact=50.0, affected_claims_score=50.0)


def test_router_returns_422_when_risk_score_omitted():
    app = FastAPI()
    app.include_router(router_module)
    client = TestClient(app)

    response = client.post(
        "/risk/score",
        json={
            "quality_check_results": [],
            "anomaly_score": 0.1,
            "affected_claim_pct": 0.0,
            "affected_claims_amounts": [],
        },
    )
    assert response.status_code == 422
