import pandas as pd

from app.data_engineering.invalid_value_detection import build_reference_stats, detect_invalid_values
from app.data_engineering.schemas import ColumnCategory, QualityIssue

CATEGORIES = {
    "CLM_ID": ColumnCategory.IDENTIFIER,
    "CLM_LINE_NUM": ColumnCategory.CATEGORICAL_CODE,
    "CLM_PMT_AMT": ColumnCategory.AMOUNT,
    "CLM_FROM_DT": ColumnCategory.DATE,
    "CLM_IP_ADMSN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
}

# Reference stats are built from raw-format (DD-Mon-YYYY) values, mirroring
# real usage where the reference dataframe is pre-conversion.
REFERENCE_DF = pd.DataFrame(
    {
        "CLM_ID": ["1", "2"],
        "CLM_LINE_NUM": ["1", "1"],
        "CLM_PMT_AMT": [100.0, 200.0],
        "CLM_FROM_DT": ["01-Jan-2020", "02-Jan-2020"],
        "CLM_IP_ADMSN_TYPE_CD": ["1", "2"],
    }
)

# The dataframe under validation is post-conversion (ISO dates, numeric amounts).
CANDIDATE_DF = pd.DataFrame(
    {
        "CLM_ID": ["1", "2", "3"],
        "CLM_LINE_NUM": ["1", "1", "1"],
        "CLM_PMT_AMT": [-50.0, 200.0, 300.0],
        "CLM_FROM_DT": ["2020-01-01", "2020-01-02", "1900-01-01"],
        "CLM_IP_ADMSN_TYPE_CD": ["1", "2", "9"],
    }
)


def _row_ids(df: pd.DataFrame) -> dict:
    return df["CLM_ID"].astype(str).to_dict()


def test_negative_amount_flagged_but_value_not_corrected():
    stats = build_reference_stats(REFERENCE_DF, CATEGORIES)
    records = detect_invalid_values(CANDIDATE_DF, CATEGORIES, _row_ids(CANDIDATE_DF), stats)

    negative = [r for r in records if r.quality_issue == QualityIssue.INVALID_VALUE_NEGATIVE_AMOUNT]
    assert len(negative) == 1
    assert negative[0].row_identifier == "1"
    assert negative[0].original_value == "-50.0"
    assert negative[0].cleaned_value == "-50.0"


def test_date_far_outside_observed_range_plus_slack_flagged():
    stats = build_reference_stats(REFERENCE_DF, CATEGORIES)
    records = detect_invalid_values(CANDIDATE_DF, CATEGORIES, _row_ids(CANDIDATE_DF), stats)

    out_of_range = [r for r in records if r.quality_issue == QualityIssue.INVALID_VALUE_DATE_OUT_OF_RANGE]
    assert len(out_of_range) == 1
    assert out_of_range[0].row_identifier == "3"
    assert out_of_range[0].original_value == "1900-01-01"


def test_unrecognized_categorical_code_flagged():
    stats = build_reference_stats(REFERENCE_DF, CATEGORIES)
    records = detect_invalid_values(CANDIDATE_DF, CATEGORIES, _row_ids(CANDIDATE_DF), stats)

    unrecognized = [r for r in records if r.quality_issue == QualityIssue.UNRECOGNIZED_CODE]
    assert len(unrecognized) == 1
    assert unrecognized[0].row_identifier == "3"
    assert unrecognized[0].original_value == "9"


def test_known_values_within_range_not_flagged():
    stats = build_reference_stats(REFERENCE_DF, CATEGORIES)
    records = detect_invalid_values(CANDIDATE_DF, CATEGORIES, _row_ids(CANDIDATE_DF), stats)

    flagged_row_ids = {r.row_identifier for r in records}
    assert "2" not in flagged_row_ids
