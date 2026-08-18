import pandas as pd
import pytest

from app.baseline.length_of_stay_baseline import compute_length_of_stay_baseline


def test_claims_with_missing_dates_excluded_and_counted():
    df = pd.DataFrame(
        {
            "CLM_ADMSN_DT": ["2026-01-01", None, "2026-01-05", "2026-01-10"],
            "NCH_BENE_DSCHRG_DT": ["2026-01-03", "2026-01-04", None, "2026-01-15"],
        }
    )
    baseline = compute_length_of_stay_baseline(df)

    # row0: valid, 2 days. row1: missing admsn -> excluded. row2: missing dschrg -> excluded.
    # row3: valid, 5 days.
    assert baseline.claims_included == 2
    assert baseline.claims_excluded_missing_dates == 2
    assert baseline.claims_included + baseline.claims_excluded_missing_dates == len(df)
    assert baseline.mean == pytest.approx((2 + 5) / 2)
    assert baseline.median == pytest.approx((2 + 5) / 2)


def test_all_valid_dates_none_excluded():
    df = pd.DataFrame(
        {
            "CLM_ADMSN_DT": ["2026-01-01", "2026-01-02"],
            "NCH_BENE_DSCHRG_DT": ["2026-01-04", "2026-01-06"],
        }
    )
    baseline = compute_length_of_stay_baseline(df)
    assert baseline.claims_excluded_missing_dates == 0
    assert baseline.claims_included == 2


def test_all_missing_dates_produces_empty_stats_with_full_exclusion():
    df = pd.DataFrame({"CLM_ADMSN_DT": [None, None], "NCH_BENE_DSCHRG_DT": [None, None]})
    baseline = compute_length_of_stay_baseline(df)
    assert baseline.claims_included == 0
    assert baseline.claims_excluded_missing_dates == 2
