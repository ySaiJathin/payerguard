import pandas as pd

from app.data_engineering.schemas import ColumnCategory
from app.features.claim_level.categorical_encoding import (
    UNKNOWN_BUCKET,
    apply_encoding_scheme,
    fit_encoding_scheme,
)


def test_unseen_category_maps_to_unknown_bucket_without_error():
    fit_df = pd.DataFrame({"CLM_IP_ADMSN_TYPE_CD": ["1", "2", "1", "3"]})
    categories = {"CLM_IP_ADMSN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE}
    schemes = fit_encoding_scheme(fit_df, categories)

    new_df = pd.DataFrame({"CLM_IP_ADMSN_TYPE_CD": ["9"]})
    encoded = apply_encoding_scheme(new_df, schemes)

    assert encoded.loc[0, "CLM_IP_ADMSN_TYPE_CD=1"] == 0.0
    assert encoded.loc[0, "CLM_IP_ADMSN_TYPE_CD=2"] == 0.0
    assert encoded.loc[0, "CLM_IP_ADMSN_TYPE_CD=3"] == 0.0
    assert encoded.loc[0, f"CLM_IP_ADMSN_TYPE_CD={UNKNOWN_BUCKET}"] == 1.0


def test_known_category_does_not_set_unknown_bucket():
    fit_df = pd.DataFrame({"CLM_IP_ADMSN_TYPE_CD": ["1", "2", "1", "3"]})
    categories = {"CLM_IP_ADMSN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE}
    schemes = fit_encoding_scheme(fit_df, categories)

    encoded = apply_encoding_scheme(fit_df, schemes)
    assert encoded.loc[0, "CLM_IP_ADMSN_TYPE_CD=1"] == 1.0
    assert encoded.loc[0, f"CLM_IP_ADMSN_TYPE_CD={UNKNOWN_BUCKET}"] == 0.0


def test_high_cardinality_column_uses_frequency_encoding_and_unseen_is_zero():
    fit_df = pd.DataFrame({"CLM_DRG_CD": [str(i) for i in range(150)] + ["1"]})
    categories = {"CLM_DRG_CD": ColumnCategory.CATEGORICAL_CODE}
    schemes = fit_encoding_scheme(fit_df, categories)
    assert schemes["CLM_DRG_CD"].strategy == "frequency"

    new_df = pd.DataFrame({"CLM_DRG_CD": ["not-seen-before"]})
    encoded = apply_encoding_scheme(new_df, schemes)
    assert encoded.loc[0, "CLM_DRG_CD"] == 0.0


def test_missing_value_stays_null_not_unknown():
    fit_df = pd.DataFrame({"CLM_IP_ADMSN_TYPE_CD": ["1", "2"]})
    categories = {"CLM_IP_ADMSN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE}
    schemes = fit_encoding_scheme(fit_df, categories)

    new_df = pd.DataFrame({"CLM_IP_ADMSN_TYPE_CD": [None]})
    encoded = apply_encoding_scheme(new_df, schemes)
    assert encoded.loc[0].isna().all()
