import math

import pandas as pd

from app.baseline.length_of_stay_baseline import ADMISSION_DATE_COLUMN, DISCHARGE_DATE_COLUMN
from app.features.claim_level.length_of_stay import compute_length_of_stay_feature


def test_matches_shared_derivation_for_valid_dates():
    df = pd.DataFrame({ADMISSION_DATE_COLUMN: ["2026-01-01"], DISCHARGE_DATE_COLUMN: ["2026-01-06"]})
    result = compute_length_of_stay_feature(df)
    assert result.iloc[0] == 5


def test_missing_discharge_date_is_null():
    df = pd.DataFrame({ADMISSION_DATE_COLUMN: ["2026-01-01"], DISCHARGE_DATE_COLUMN: [None]})
    result = compute_length_of_stay_feature(df)
    assert math.isnan(result.iloc[0])


def test_missing_admission_date_is_null():
    df = pd.DataFrame({ADMISSION_DATE_COLUMN: [None], DISCHARGE_DATE_COLUMN: ["2026-01-06"]})
    result = compute_length_of_stay_feature(df)
    assert math.isnan(result.iloc[0])
