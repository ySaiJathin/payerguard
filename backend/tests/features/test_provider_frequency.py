import math

import pandas as pd
import pytest

from app.features.claim_level.provider_frequency import compute_provider_frequency


def test_frequency_reflects_real_occurrence_rate():
    df = pd.DataFrame({"PRVDR_NUM": ["A", "A", "B", "A"]})
    result = compute_provider_frequency(df)
    assert result.iloc[0] == pytest.approx(3 / 4)
    assert result.iloc[2] == pytest.approx(1 / 4)


def test_rare_provider_gets_real_low_frequency_not_error():
    df = pd.DataFrame({"PRVDR_NUM": ["A", "A", "A", "RARE"]})
    result = compute_provider_frequency(df)
    assert result.iloc[3] == pytest.approx(1 / 4)


def test_missing_provider_is_null():
    df = pd.DataFrame({"PRVDR_NUM": ["A", None]})
    result = compute_provider_frequency(df)
    assert math.isnan(result.iloc[1])
