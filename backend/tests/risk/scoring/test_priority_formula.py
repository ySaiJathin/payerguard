import pytest

from app.risk.scoring.errors import WeightConfigError
from app.risk.scoring.priority import affected_claims_score, compute_priority


def test_priority_matches_hand_computed_formula_with_default_weights():
    result = compute_priority(severity=80.0, risk=60.0, business_impact=40.0, affected_claims_score=20.0)
    expected = 0.40 * 80.0 + 0.30 * 60.0 + 0.20 * 40.0 + 0.10 * 20.0
    assert result.priority == pytest.approx(expected)
    assert 0.0 <= result.priority <= 100.0
    assert result.weights_used == {
        "w_severity": 0.40,
        "w_risk": 0.30,
        "w_business_impact": 0.20,
        "w_affected_claims": 0.10,
    }


def test_priority_with_non_default_weights_records_weights_used():
    weights = {"w_severity": 0.25, "w_risk": 0.25, "w_business_impact": 0.25, "w_affected_claims": 0.25}
    result = compute_priority(severity=100.0, risk=0.0, business_impact=0.0, affected_claims_score=0.0, weights=weights)
    assert result.priority == pytest.approx(25.0)
    assert result.weights_used == weights


def test_priority_rejects_malformed_weight_set():
    with pytest.raises(WeightConfigError):
        compute_priority(
            severity=50.0,
            risk=50.0,
            business_impact=50.0,
            affected_claims_score=50.0,
            weights={"w_severity": 0.4, "w_risk": 0.3, "w_business_impact": 0.2, "w_affected_claims": 0.2},  # sums to 1.1
        )


def test_affected_claims_score_scales_fraction_to_0_100():
    assert affected_claims_score(0.12) == pytest.approx(12.0)
    assert affected_claims_score(0.0) == 0.0
    assert affected_claims_score(1.0) == 100.0
