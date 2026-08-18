"""Spec SC-002 / US2 Acceptance Scenarios 1-2: `comparison_service.
build_comparison` reports the real delta in whichever direction the
recomputed values actually land -- unfavorable (worse) included.
"""

from app.revalidation.comparison_service import build_comparison
from app.revalidation.schemas import RecomputedScores
from tests._db_fixtures import make_test_session
from tests.revalidation._fixtures import make_incident


def _recomputed(**overrides) -> RecomputedScores:
    defaults = dict(
        quality_results=[],
        quality_score=80.0,
        anomaly_score=20.0,
        anomaly_score_percentile=0.2,
        risk_score=30.0,
        severity=25.0,
        business_impact=10.0,
        priority=35.0,
        severity_business_impact_priority={},
        anomaly_model_version="hbos",
        risk_model_version="xgboost",
    )
    defaults.update(overrides)
    return RecomputedScores(**defaults)


def test_unfavorable_risk_and_anomaly_deltas_are_reported_positive_not_clamped():
    db = make_test_session()
    incident = make_incident(db, quality_score=80.0, anomaly_score=20.0, risk_score=30.0, severity=25.0, priority=35.0)

    # Remediation didn't help -- recomputed risk/anomaly are *worse* than
    # the stored pre-remediation values.
    recomputed = _recomputed(anomaly_score=50.0, risk_score=60.0)

    comparison = build_comparison("reval-1", incident, recomputed)

    assert comparison.anomaly_delta == 30.0  # worse, reported as a positive delta, not 0 or negated
    assert comparison.risk_delta == 30.0
    assert comparison.anomaly_delta > 0
    assert comparison.risk_delta > 0


def test_favorable_quality_delta_reported_in_the_real_direction():
    db = make_test_session()
    incident = make_incident(db, quality_score=20.0, anomaly_score=80.0, risk_score=80.0, severity=75.0, priority=75.0)

    # Remediation genuinely improved quality and reduced anomaly/risk.
    recomputed = _recomputed(quality_score=90.0, anomaly_score=10.0, risk_score=15.0, severity=10.0, priority=15.0)

    comparison = build_comparison("reval-2", incident, recomputed)

    assert comparison.quality_delta == 70.0
    assert comparison.quality_delta > 0
    assert comparison.anomaly_delta == -70.0
    assert comparison.anomaly_delta < 0
    assert comparison.risk_delta == -65.0
    assert comparison.risk_delta < 0
