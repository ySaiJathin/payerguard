from pathlib import Path

from app.data_engineering.schemas import ProfilingReport
from app.quality.completeness_calibration import build_calibration_table

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "quality_profiling_report.json"


def _load_report() -> ProfilingReport:
    return ProfilingReport.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def test_high_missingness_column_gets_calibration_override():
    report = _load_report()
    table = build_calibration_table(report)
    assert "OT_PHYSN_UPIN" in table
    entry = table["OT_PHYSN_UPIN"]
    assert entry.expected_max_missing_pct == 100.0
    assert "OT_PHYSN_UPIN" in entry.source_note
    assert "quality_profiling_report.json" in entry.source_note or "quality_cleaned_sample.csv" in entry.source_note


def test_low_missingness_column_gets_no_override():
    report = _load_report()
    table = build_calibration_table(report)
    assert "BENE_ID" not in table
    assert "CLM_PMT_AMT" not in table


def test_calibration_slack_is_additive_and_capped_at_100():
    report = _load_report()
    table = build_calibration_table(report, slack_pct=50.0)
    # 100% missing + 50pp slack must clamp at 100, not overflow
    assert table["OT_PHYSN_UPIN"].expected_max_missing_pct == 100.0
