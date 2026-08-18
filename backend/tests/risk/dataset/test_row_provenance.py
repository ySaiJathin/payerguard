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

RUN_ID = "run-1"
EVALUATED_AT = datetime(2022, 1, 1, tzinfo=timezone.utc)


def _percentiles() -> Percentiles:
    return Percentiles(p25=1, p50=2, p75=3, p95=4, p99=5)


def _baseline() -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id="snap-1",
        source_file="inpatient.csv",
        source_row_count=100,
        source_date_range=SourceDateRange(min_date=date(2015, 4, 1), max_date=date(2022, 10, 31)),
        volume_baseline=VolumeBaseline(window_definition="daily", windows=[]),
        amount_baselines=[
            AmountBaseline(
                column_name="CLM_PMT_AMT", mean=100.0, median=90.0, std=10.0, min=0.0, max=500.0, percentiles=_percentiles()
            )
        ],
        data_health_baseline=DataHealthBaseline(
            historical_missing_rate_by_column={"COL_A": 4.0, "COL_B": 6.0},
            historical_duplicate_rate=2.0,
            categorical_distributions={},
        ),
        length_of_stay_baseline=LengthOfStayBaseline(
            mean=3.0, median=2.0, percentiles=_percentiles(), claims_included=100, claims_excluded_missing_dates=0
        ),
        computed_at=EVALUATED_AT,
    )


def _check(band: Band, expectation_type: ExpectationType = ExpectationType.COMPLETENESS) -> ExpectationCheckResult:
    return ExpectationCheckResult(
        check_id=f"chk-{band.value}-{expectation_type.value}",
        suite_name="suite",
        column_name="COL_A",
        expectation_type=expectation_type,
        computed_rate_or_count=1.0,
        band=band,
        run_id=RUN_ID,
        evaluated_at=EVALUATED_AT,
    )


def _quality_results():
    checks = [_check(Band.CRITICAL), _check(Band.CRITICAL), _check(Band.WARNING), _check(Band.PASS)]
    score = QualityScoreResult(
        run_id=RUN_ID,
        batch_source="cleaned.csv",
        composite_score=80.0,
        weights_used={"completeness": 1.0},
        contributing_check_ids=[c.check_id for c in checks],
        generated_at=EVALUATED_AT,
    )
    return score, checks


def _window(window_id: str, claim_count: int, anomaly_count: int | None) -> WindowFeatures:
    return WindowFeatures(
        window_id=window_id,
        start=date(2020, 1, 1),
        end=date(2020, 1, 7),
        claim_count=claim_count,
        amount_stats={},
        missing_pct=5.0,
        duplicate_pct=10.0,
        invalid_status_pct=20.0,
        volume_deviation=3.0,
        amount_deviation={"CLM_PMT_AMT": -15.0, "CLM_CHRG_AMT": 25.0},
        anomaly_count=anomaly_count,
    )


def _patch(monkeypatch, windows, quality_results, baseline):
    monkeypatch.setattr(row_assembly, "read_window_features", lambda out_dir=None: windows)
    monkeypatch.setattr(row_assembly, "read_quality_results", lambda out_dir=None: quality_results)
    monkeypatch.setattr(row_assembly, "read_latest_baseline_snapshot", lambda out_dir=None: baseline)


def test_row_fields_trace_to_upstream_outputs(monkeypatch):
    windows = [_window("W1", claim_count=10, anomaly_count=2)]
    quality_results = _quality_results()
    baseline = _baseline()
    _patch(monkeypatch, windows, quality_results, baseline)

    rows = row_assembly.assemble_rows()
    assert len(rows) == 1
    row = rows[0]

    # Phase 5 pass-through fields
    assert row["window_id"] == "W1"
    assert row["window_start"] == date(2020, 1, 1)
    assert row["window_end"] == date(2020, 1, 7)
    assert row["claim_count"] == 10
    assert row["volume_deviation"] == 3.0

    # Phase 7-enriched anomaly signal
    assert row["anomaly_frequency"] == 2 / 10
    assert row["anomaly_score"] == (2 / 10) * 100

    # Phase 3: 2 CRITICAL + 1 WARNING = 3 (include_warning defaults True)
    assert row["gx_failure_count"] == 3

    # Phase 4: mean(4.0, 6.0, duplicate_rate=2.0) = 4.0
    assert row["historical_quality_failure_rate"] == (4.0 + 6.0 + 2.0) / 3

    # amount_deviation reduced to max absolute value across columns
    assert row["amount_deviation"] == 25.0


def test_gx_failure_count_excludes_warning_when_configured(monkeypatch):
    windows = [_window("W1", claim_count=10, anomaly_count=0)]
    quality_results = _quality_results()
    baseline = _baseline()
    _patch(monkeypatch, windows, quality_results, baseline)

    rows = row_assembly.assemble_rows(include_warning_in_gx_failure_count=False)
    assert rows[0]["gx_failure_count"] == 2


def test_affected_claim_pct_combines_quality_and_anomaly_signals(monkeypatch):
    windows = [_window("W1", claim_count=10, anomaly_count=2)]
    quality_results = _quality_results()
    baseline = _baseline()
    _patch(monkeypatch, windows, quality_results, baseline)

    rows = row_assembly.assemble_rows()
    row = rows[0]

    quality_issue_rate = 1 - (1 - 0.10) * (1 - 0.20)
    anomaly_frequency = 0.2
    expected = 100 * (1 - (1 - quality_issue_rate) * (1 - anomaly_frequency))
    assert row["affected_claim_pct"] == expected
