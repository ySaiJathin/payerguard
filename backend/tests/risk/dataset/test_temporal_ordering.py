import random
from datetime import date, datetime, timezone

from app.baseline.schemas import (
    BaselineSnapshot,
    DataHealthBaseline,
    LengthOfStayBaseline,
    Percentiles,
    SourceDateRange,
    VolumeBaseline,
)
from app.features.schemas import WindowFeatures
from app.features.selection.schemas import DateRange, TemporalSplit
from app.features.selection.temporal_split import assign_split
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
            historical_duplicate_rate=1.0,
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


def _window(window_id: str, start: date) -> WindowFeatures:
    return WindowFeatures(
        window_id=window_id,
        start=start,
        end=start,
        claim_count=5,
        amount_stats={},
        missing_pct=0.0,
        duplicate_pct=0.0,
        invalid_status_pct=0.0,
        volume_deviation=0.0,
        amount_deviation={},
        anomaly_count=0,
    )


def test_assembled_rows_sort_to_true_chronological_window_sequence(monkeypatch):
    starts = [date(2020, 1, d) for d in (15, 3, 21, 1, 9)]
    windows = [_window(f"W{i}", start) for i, start in enumerate(starts)]
    shuffled = list(windows)
    random.Random(0).shuffle(shuffled)

    monkeypatch.setattr(row_assembly, "read_window_features", lambda out_dir=None: shuffled)
    monkeypatch.setattr(row_assembly, "read_quality_results", lambda out_dir=None: _quality_results())
    monkeypatch.setattr(row_assembly, "read_latest_baseline_snapshot", lambda out_dir=None: _baseline())

    rows = row_assembly.assemble_rows()

    assert [r["window_start"] for r in rows] == sorted(starts)


def test_rows_assign_unambiguously_to_train_validation_test(monkeypatch):
    starts = [date(2020, 1, 1), date(2020, 1, 10), date(2020, 1, 20), date(2020, 1, 25), date(2020, 2, 1)]
    windows = [_window(f"W{i}", start) for i, start in enumerate(starts)]

    monkeypatch.setattr(row_assembly, "read_window_features", lambda out_dir=None: windows)
    monkeypatch.setattr(row_assembly, "read_quality_results", lambda out_dir=None: _quality_results())
    monkeypatch.setattr(row_assembly, "read_latest_baseline_snapshot", lambda out_dir=None: _baseline())

    rows = row_assembly.assemble_rows()

    split = TemporalSplit(
        split_id="split-1",
        train_date_range=DateRange(start=date(2020, 1, 1), end=date(2020, 1, 15)),
        validation_date_range=DateRange(start=date(2020, 1, 16), end=date(2020, 1, 22)),
        test_date_range=DateRange(start=date(2020, 1, 23), end=date(2020, 2, 4)),
        train_count=1,
        validation_count=1,
        test_count=1,
        computed_at=EVALUATED_AT,
    )

    assignments = [assign_split(r["window_start"], split) for r in rows]
    assert assignments == ["train", "train", "validation", "test", "test"]
