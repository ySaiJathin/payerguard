from datetime import date, datetime, timezone

from app.baseline.schemas import (
    AmountBaseline,
    BaselineSnapshot,
    DataHealthBaseline,
    LengthOfStayBaseline,
    Percentiles,
    SourceDateRange,
    VolumeBaseline,
)
from app.features.schemas import WindowFeatures
from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType, QualityScoreResult
from app.risk.dataset import row_assembly

EVALUATED_AT = datetime(2022, 1, 1, tzinfo=timezone.utc)


def _baseline() -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id="snap-1",
        source_file="inpatient.csv",
        source_row_count=100,
        source_date_range=SourceDateRange(min_date=date(2015, 4, 1), max_date=date(2022, 10, 31)),
        volume_baseline=VolumeBaseline(window_definition="daily", windows=[]),
        amount_baselines=[],
        data_health_baseline=DataHealthBaseline(
            historical_missing_rate_by_column={"COL_A": 4.0},
            historical_duplicate_rate=0.0,
            categorical_distributions={},
        ),
        length_of_stay_baseline=LengthOfStayBaseline(
            mean=0.0, median=0.0, percentiles=Percentiles(p25=0, p50=0, p75=0, p95=0, p99=0), claims_included=0,
            claims_excluded_missing_dates=0,
        ),
        computed_at=EVALUATED_AT,
    )


def _quality_results():
    checks = [
        ExpectationCheckResult(
            check_id="chk-1",
            suite_name="suite",
            column_name="COL_A",
            expectation_type=ExpectationType.COMPLETENESS,
            computed_rate_or_count=1.0,
            band=Band.CRITICAL,
            run_id="run-1",
            evaluated_at=EVALUATED_AT,
        )
    ]
    score = QualityScoreResult(
        run_id="run-1",
        batch_source="cleaned.csv",
        composite_score=80.0,
        weights_used={"completeness": 1.0},
        contributing_check_ids=[c.check_id for c in checks],
        generated_at=EVALUATED_AT,
    )
    return score, checks


def _zero_claim_window() -> WindowFeatures:
    return WindowFeatures(
        window_id="W-empty",
        start=date(2020, 6, 1),
        end=date(2020, 6, 7),
        claim_count=0,
        amount_stats={},
        missing_pct=0.0,
        duplicate_pct=0.0,
        invalid_status_pct=0.0,
        volume_deviation=-5.0,
        amount_deviation={},
        anomaly_count=0,
    )


def test_zero_claim_window_gets_genuine_zero_values_not_skipped(monkeypatch):
    windows = [_zero_claim_window()]
    monkeypatch.setattr(row_assembly, "read_window_features", lambda out_dir=None: windows)
    monkeypatch.setattr(row_assembly, "read_quality_results", lambda out_dir=None: _quality_results())
    monkeypatch.setattr(row_assembly, "read_latest_baseline_snapshot", lambda out_dir=None: _baseline())

    rows = row_assembly.assemble_rows()

    assert len(rows) == 1
    row = rows[0]
    assert row["window_id"] == "W-empty"
    assert row["claim_count"] == 0
    assert row["anomaly_frequency"] == 0.0
    assert row["anomaly_score"] == 0.0
    assert row["affected_claim_pct"] == 0.0
    # volume_deviation is carried through unchanged even though it's negative
    # -- a legitimate below-baseline reading for a real zero-claim window
    # (spec Acceptance Scenario 4), not defaulted away.
    assert row["volume_deviation"] == -5.0
