import pandas as pd

from app.data_engineering.invalid_value_detection import ReferenceStats
from app.data_engineering.schemas import ColumnCategory
from app.features.window_level.window_aggregates import compute_window_aggregates

CATEGORIES = {
    "CLM_FROM_DT": ColumnCategory.DATE,
    "CLM_PMT_AMT": ColumnCategory.AMOUNT,
    "PTNT_DSCHRG_STUS_CD": ColumnCategory.CATEGORICAL_CODE,
}


def _reference_stats():
    return ReferenceStats(date_min=None, date_max=None, known_values={"PTNT_DSCHRG_STUS_CD": {"01", "02"}})


def test_every_window_including_zero_claim_gets_a_complete_row():
    df = pd.DataFrame(
        {
            "CLM_FROM_DT": ["2026-01-01", "2026-01-01", "2026-01-04"],
            "CLM_PMT_AMT": [100.0, 200.0, 50.0],
            "PTNT_DSCHRG_STUS_CD": ["01", "02", "01"],
        }
    )
    rows = compute_window_aggregates(df, CATEGORIES, _reference_stats(), "daily")
    window_ids = [r["window_id"] for r in rows]
    assert window_ids == ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]

    by_id = {r["window_id"]: r for r in rows}
    assert by_id["2026-01-01"]["claim_count"] == 2
    assert by_id["2026-01-02"]["claim_count"] == 0
    assert by_id["2026-01-02"]["missing_pct"] == 0.0
    assert by_id["2026-01-02"]["duplicate_pct"] == 0.0
    assert by_id["2026-01-02"]["invalid_status_pct"] == 0.0
    assert by_id["2026-01-01"]["amount_stats"]["CLM_PMT_AMT"]["mean"] == 150.0


def test_invalid_status_pct_reflects_unknown_reference_codes():
    df = pd.DataFrame(
        {
            "CLM_FROM_DT": ["2026-01-01", "2026-01-01"],
            "CLM_PMT_AMT": [100.0, 200.0],
            "PTNT_DSCHRG_STUS_CD": ["01", "99"],
        }
    )
    rows = compute_window_aggregates(df, CATEGORIES, _reference_stats(), "daily")
    assert rows[0]["invalid_status_pct"] == 50.0
