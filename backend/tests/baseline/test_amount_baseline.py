import pandas as pd
import pytest

from app.baseline.amount_baseline import compute_amount_baselines
from app.data_engineering.schemas import ColumnCategory


def _categories():
    return {
        "CLM_PMT_AMT": ColumnCategory.AMOUNT,
        "CLM_TOT_CHRG_AMT": ColumnCategory.AMOUNT,
        "BENE_ID": ColumnCategory.IDENTIFIER,
    }


def test_amount_stats_hand_computed():
    df = pd.DataFrame(
        {
            "CLM_PMT_AMT": [10.0, 20.0, 30.0, 40.0],
            "CLM_TOT_CHRG_AMT": [100.0, 100.0, 100.0, 100.0],
            "BENE_ID": ["a", "b", "c", "d"],
        }
    )
    baselines = {b.column_name: b for b in compute_amount_baselines(df, _categories())}

    pmt = baselines["CLM_PMT_AMT"]
    assert pmt.mean == pytest.approx(25.0)
    assert pmt.median == pytest.approx(25.0)
    assert pmt.min == pytest.approx(10.0)
    assert pmt.max == pytest.approx(40.0)
    assert pmt.std == pytest.approx(df["CLM_PMT_AMT"].std())


def test_only_amount_category_columns_are_computed():
    df = pd.DataFrame(
        {
            "CLM_PMT_AMT": [10.0, 20.0],
            "CLM_TOT_CHRG_AMT": [5.0, 5.0],
            "BENE_ID": ["a", "b"],
        }
    )
    baselines = compute_amount_baselines(df, _categories())
    column_names = {b.column_name for b in baselines}
    assert column_names == {"CLM_PMT_AMT", "CLM_TOT_CHRG_AMT"}


def test_pmt_and_chrg_amt_computed_independently_even_when_identical():
    df = pd.DataFrame(
        {
            "CLM_PMT_AMT": [100.0, 200.0, 300.0],
            "CLM_TOT_CHRG_AMT": [100.0, 200.0, 300.0],
        }
    )
    baselines = {b.column_name: b for b in compute_amount_baselines(df, _categories())}
    assert baselines["CLM_PMT_AMT"] is not baselines["CLM_TOT_CHRG_AMT"]
    assert baselines["CLM_PMT_AMT"].mean == baselines["CLM_TOT_CHRG_AMT"].mean == pytest.approx(200.0)


def test_percentiles_present():
    df = pd.DataFrame({"CLM_PMT_AMT": list(range(1, 101))})
    baselines = {b.column_name: b for b in compute_amount_baselines(df, {"CLM_PMT_AMT": ColumnCategory.AMOUNT})}
    pct = baselines["CLM_PMT_AMT"].percentiles
    assert pct.p50 == pytest.approx(50.5, abs=1.0)
    assert pct.p99 > pct.p95 > pct.p75 > pct.p50 > pct.p25
