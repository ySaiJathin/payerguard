import pandas as pd

from app.data_engineering.date_standardization import standardize_date_column
from app.data_engineering.schemas import QualityIssue


def test_valid_date_reformatted_to_iso():
    series = pd.Series(["01-Apr-2015", "22-Feb-2022"], name="CLM_FROM_DT")
    result = standardize_date_column(series)

    assert result.cleaned.tolist() == ["2015-04-01", "2022-02-22"]
    assert len(result.changes) == 2
    assert result.changes[0].quality_issue == QualityIssue.DATE_FORMAT_STANDARDIZED
    assert result.changes[0].original_value == "01-Apr-2015"
    assert result.changes[0].cleaned_value == "2015-04-01"


def test_unparseable_date_flagged_not_guessed():
    series = pd.Series(["NOTADATE"], name="CLM_FROM_DT")
    result = standardize_date_column(series)

    assert result.cleaned.iloc[0] is None
    assert len(result.changes) == 1
    assert result.changes[0].quality_issue == QualityIssue.DATE_UNPARSEABLE
    assert result.changes[0].cleaned_value is None


def test_missing_value_produces_no_change_record():
    series = pd.Series([None, "01-Apr-2015"], name="CLM_FROM_DT")
    result = standardize_date_column(series)

    assert result.cleaned.iloc[0] is None
    assert len(result.changes) == 1  # only the populated cell
