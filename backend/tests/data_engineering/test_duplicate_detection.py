from pathlib import Path

import pandas as pd

from app.data_engineering.duplicate_detection import detect_and_exclude_duplicates
from app.data_engineering.paths import raw_inpatient_csv
from app.data_engineering.schemas import QualityIssue

DIRTY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "inpatient_dirty_sample.csv"


def _row_ids(df: pd.DataFrame) -> dict:
    return (df["CLM_ID"].astype(str) + ":" + df["CLM_LINE_NUM"].astype(str)).to_dict()


def test_exact_duplicate_excluded_and_flagged():
    df = pd.read_csv(DIRTY_FIXTURE, sep="|")
    row_ids = _row_ids(df)

    deduped, records = detect_and_exclude_duplicates(df, row_ids)

    assert len(deduped) == len(df) - 1  # the fixture has exactly one duplicate pair
    assert len(records) == 1
    assert records[0].quality_issue == QualityIssue.DUPLICATE_ROW
    # The excluded row's identity is still recoverable via the record.
    assert records[0].original_value == "1002:1"


def test_no_row_physically_deleted_from_source_file():
    before = DIRTY_FIXTURE.read_bytes()
    df = pd.read_csv(DIRTY_FIXTURE, sep="|")
    detect_and_exclude_duplicates(df, _row_ids(df))

    assert DIRTY_FIXTURE.read_bytes() == before


def test_real_file_has_zero_duplicates():
    raw_path = raw_inpatient_csv()
    if not raw_path.exists():
        return  # matches profiling's real-data test skip convention
    df = pd.read_csv(raw_path, sep="|", low_memory=False)
    _, records = detect_and_exclude_duplicates(df, _row_ids(df))

    assert len(records) == 0
