import math

import pandas as pd
import pytest

from app.features.claim_level.amount_ratios import compute_amount_ratios


def test_ratio_computed_from_real_values():
    df = pd.DataFrame({"CLM_PMT_AMT": [500.0], "CLM_TOT_CHRG_AMT": [1000.0]})
    result = compute_amount_ratios(df)
    assert result["payment_to_charge_ratio"].iloc[0] == pytest.approx(0.5)


def test_zero_denominator_is_null_not_divide_by_zero_error():
    df = pd.DataFrame({"CLM_PMT_AMT": [500.0], "CLM_TOT_CHRG_AMT": [0.0]})
    result = compute_amount_ratios(df)
    assert math.isnan(result["payment_to_charge_ratio"].iloc[0])


def test_missing_denominator_is_null():
    df = pd.DataFrame({"CLM_PMT_AMT": [500.0], "CLM_TOT_CHRG_AMT": [None]})
    result = compute_amount_ratios(df)
    assert math.isnan(result["payment_to_charge_ratio"].iloc[0])


def test_missing_numerator_is_null():
    df = pd.DataFrame({"CLM_PMT_AMT": [None], "CLM_TOT_CHRG_AMT": [1000.0]})
    result = compute_amount_ratios(df)
    assert math.isnan(result["payment_to_charge_ratio"].iloc[0])
