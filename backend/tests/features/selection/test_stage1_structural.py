import pandas as pd

from app.data_engineering.schemas import ColumnCategory
from app.features.schemas import AmountStats, ClaimFeatures, WindowFeatures, deferred_window_feature_fields
from app.features.selection.stage1_structural import apply_stage1

CATEGORIES = {
    "CLM_ID": ColumnCategory.IDENTIFIER,
    "BENE_ID": ColumnCategory.IDENTIFIER,
    "PRVDR_NUM": ColumnCategory.IDENTIFIER,
    "FI_NUM": ColumnCategory.IDENTIFIER,
    "OT_PHYSN_UPIN": ColumnCategory.IDENTIFIER,
    "NCH_CLM_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_FREQ_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLAIM_QUERY_CODE": ColumnCategory.CATEGORICAL_CODE,
    "CLM_MDCR_NON_PMT_RSN_CD": ColumnCategory.CATEGORICAL_CODE,
    "PTNT_DSCHRG_STUS_CD": ColumnCategory.CATEGORICAL_CODE,
    "PRVDR_STATE_CD": ColumnCategory.CATEGORICAL_CODE,  # varies -- keeps CATEGORICAL_CODE from being wiped out entirely
    "CLM_PMT_AMT": ColumnCategory.AMOUNT,
}


def _cleaned_df(n: int = 200) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CLM_ID": [f"C{i}" for i in range(n)],
            "BENE_ID": [f"B{i % 50}" for i in range(n)],
            "PRVDR_NUM": [f"P{i % 10}" for i in range(n)],
            "FI_NUM": [None] * n,
            "OT_PHYSN_UPIN": [None] * n,
            "NCH_CLM_TYPE_CD": ["60"] * n,
            "CLM_FREQ_CD": ["1"] * n,
            "CLAIM_QUERY_CODE": ["1"] * n,
            "CLM_MDCR_NON_PMT_RSN_CD": [None] * n,
            "PTNT_DSCHRG_STUS_CD": ["01"] * n,
            "PRVDR_STATE_CD": [f"S{i % 5}" for i in range(n)],
            "CLM_PMT_AMT": [100.0 + i for i in range(n)],
            "INCIDENT_OUTCOME_FLAG": [i % 2 for i in range(n)],  # synthetic leakage-pattern column, deliberately varying
        }
    )


def _claim_features(n: int = 200) -> list[ClaimFeatures]:
    return [
        ClaimFeatures(
            claim_id=f"C{i}",
            payment_to_charge_ratio=0.5 + (i % 10) * 0.01,
            length_of_stay_days=i % 7,
            provider_frequency=float(i % 10),
        )
        for i in range(n)
    ]


def _window_features(n: int = 5) -> list[WindowFeatures]:
    return [
        WindowFeatures(
            window_id=f"W{i}",
            start=f"2020-01-{i + 1:02d}",
            end=f"2020-01-{i + 2:02d}",
            claim_count=40 + i,
            amount_stats={"CLM_PMT_AMT": AmountStats(mean=100.0 + i, median=95.0, std=10.0)},
            missing_pct=0.01 * i,
            duplicate_pct=0.0,
            invalid_status_pct=0.0,
            volume_deviation=float(i),
            amount_deviation={"CLM_PMT_AMT": 1.0 * i},
            anomaly_count=None,
        )
        for i in range(n)
    ]


def test_documented_constant_columns_are_dropped_with_reason():
    surviving, decisions = apply_stage1(_cleaned_df(), _claim_features(), _window_features(), CATEGORIES)
    by_name = {d.feature_name: d for d in decisions}

    for col in ("NCH_CLM_TYPE_CD", "CLM_FREQ_CD", "CLAIM_QUERY_CODE", "PTNT_DSCHRG_STUS_CD"):
        assert col in by_name, f"{col} should have been dropped"
        assert "constant" in by_name[col].reason
        assert col not in surviving["claim"]


def test_documented_fully_null_columns_dropped_as_high_missingness():
    surviving, decisions = apply_stage1(_cleaned_df(), _claim_features(), _window_features(), CATEGORIES)
    by_name = {d.feature_name: d for d in decisions}

    for col in ("OT_PHYSN_UPIN", "FI_NUM", "CLM_MDCR_NON_PMT_RSN_CD"):
        assert col in by_name
        assert "high-missingness" in by_name[col].reason
        assert col not in surviving["claim"]


def test_raw_identifier_columns_dropped():
    surviving, decisions = apply_stage1(_cleaned_df(), _claim_features(), _window_features(), CATEGORIES)
    by_name = {d.feature_name: d for d in decisions}

    for col in ("CLM_ID", "BENE_ID", "PRVDR_NUM"):
        assert col in by_name
        assert "raw identifier" in by_name[col].reason
        assert col not in surviving["claim"]


def test_leakage_pattern_column_dropped_with_leakage_reason():
    surviving, decisions = apply_stage1(_cleaned_df(), _claim_features(), _window_features(), CATEGORIES)
    by_name = {d.feature_name: d for d in decisions}

    assert "INCIDENT_OUTCOME_FLAG" in by_name
    assert "leakage" in by_name["INCIDENT_OUTCOME_FLAG"].reason
    assert "INCIDENT_OUTCOME_FLAG" not in surviving["claim"]


def test_anomaly_count_never_dropped_for_missingness_when_exempted():
    exempt = deferred_window_feature_fields()
    surviving, decisions = apply_stage1(
        _cleaned_df(), _claim_features(), _window_features(), CATEGORIES, exempt_fields=exempt
    )
    dropped_names = {d.feature_name for d in decisions}

    assert "anomaly_count" not in dropped_names
    assert "anomaly_count" in surviving["window"]


def test_non_flagged_columns_survive():
    surviving, _ = apply_stage1(_cleaned_df(), _claim_features(), _window_features(), CATEGORIES)
    assert "CLM_PMT_AMT" in surviving["claim"]
    assert "payment_to_charge_ratio" in surviving["claim"]
