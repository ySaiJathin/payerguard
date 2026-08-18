import pytest

from app.risk.scoring.errors import WeightConfigError
from app.risk.scoring.severity import compute_severity


def test_severity_matches_hand_computed_formula_with_default_weights():
    bands = ["CRITICAL", "WARNING", "PASS"]  # avg = (100+50+0)/3 = 50.0
    result = compute_severity(
        quality_check_bands=bands,
        anomaly_score_percentile=0.5,  # < 0.95 => (0.5/0.95)*50
        affected_claim_pct=0.20,  # => 20.0 (no amounts/baseline supplied)
    )

    expected_qfs = 50.0
    expected_ams = (0.5 / 0.95) * 50.0
    expected_ms = 20.0
    expected_severity = 0.4 * expected_qfs + 0.4 * expected_ams + 0.2 * expected_ms

    assert result.quality_failure_severity == expected_qfs
    assert result.anomaly_magnitude_score == pytest.approx(expected_ams)
    assert result.materiality_score == expected_ms
    assert result.severity == pytest.approx(expected_severity)
    assert result.weights_used == {"wq": 0.4, "wa": 0.4, "wm": 0.2}


def test_severity_with_non_default_weights_reproduces_by_hand():
    weights = {"wq": 0.5, "wa": 0.3, "wm": 0.2}
    result = compute_severity(
        quality_check_bands=["CRITICAL", "CRITICAL"],
        anomaly_score_percentile=0.99,
        affected_claim_pct=0.5,
        weights=weights,
    )
    expected = weights["wq"] * 100.0 + weights["wa"] * 90.0 + weights["wm"] * 50.0
    assert result.severity == pytest.approx(expected)
    assert result.weights_used == weights


def test_severity_rejects_malformed_weight_set():
    with pytest.raises(WeightConfigError):
        compute_severity(
            quality_check_bands=["PASS"],
            anomaly_score_percentile=0.1,
            affected_claim_pct=0.0,
            weights={"wq": 0.5, "wa": 0.5, "wm": 0.5},  # sums to 1.5
        )


def test_anomaly_magnitude_score_is_continuous_across_bands():
    from app.risk.scoring.severity import anomaly_magnitude_score

    just_below_95 = anomaly_magnitude_score(0.9499)
    just_above_95 = anomaly_magnitude_score(0.9501)
    just_below_99 = anomaly_magnitude_score(0.9899)
    just_above_99 = anomaly_magnitude_score(0.9901)
    at_max = anomaly_magnitude_score(1.0)

    assert just_below_95 == pytest.approx(50.0, abs=0.1)
    assert just_above_95 == pytest.approx(50.0, abs=0.1)
    assert just_below_99 == pytest.approx(90.0, abs=0.1)
    assert just_above_99 == pytest.approx(90.0, abs=0.1)
    assert at_max == pytest.approx(100.0)


def test_quality_failure_severity_empty_checks_is_zero_not_error():
    from app.risk.scoring.severity import quality_failure_severity

    assert quality_failure_severity([]) == 0.0
