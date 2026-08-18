from datetime import datetime, timezone
from pathlib import Path

from app.quality.quality_results_log import find_check, read_quality_results, write_quality_results
from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType, QualityScoreResult

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)


def _score_result() -> QualityScoreResult:
    return QualityScoreResult(
        run_id="run-1",
        batch_source="src.csv",
        composite_score=87.5,
        weights_used={"completeness": 1.0},
        contributing_check_ids=["c1"],
        generated_at=NOW,
    )


def _check_results() -> list[ExpectationCheckResult]:
    return [
        ExpectationCheckResult(
            check_id="c1",
            suite_name="s",
            column_name="COL",
            expectation_type=ExpectationType.COMPLETENESS,
            computed_rate_or_count=1.0,
            band=Band.PASS,
            threshold_used={},
            run_id="run-1",
            evaluated_at=NOW,
        )
    ]


def test_write_then_read_round_trip(tmp_path: Path):
    write_quality_results(_score_result(), _check_results(), out_dir=tmp_path)
    result = read_quality_results(out_dir=tmp_path)
    assert result is not None
    score_result, check_results = result
    assert score_result.composite_score == 87.5
    assert len(check_results) == 1
    assert check_results[0].check_id == "c1"


def test_second_write_overwrites_not_appends(tmp_path: Path):
    write_quality_results(_score_result(), _check_results(), out_dir=tmp_path)
    write_quality_results(_score_result(), _check_results(), out_dir=tmp_path)
    _, check_results = read_quality_results(out_dir=tmp_path)
    assert len(check_results) == 1


def test_find_check_returns_none_for_unknown_id(tmp_path: Path):
    write_quality_results(_score_result(), _check_results(), out_dir=tmp_path)
    assert find_check("does-not-exist", out_dir=tmp_path) is None
    assert find_check("c1", out_dir=tmp_path) is not None


def test_read_returns_none_when_no_run_yet(tmp_path: Path):
    assert read_quality_results(out_dir=tmp_path) is None
