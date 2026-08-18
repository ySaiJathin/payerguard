"""Assembles one ClaimFeatures row per claim from every claim-level
computer (FR-010: never a fabricated value for a claim missing the
relevant input).
"""

import math

import pandas as pd

from app.data_engineering.schemas import ColumnCategory
from app.features.claim_level.amount_ratios import compute_amount_ratios
from app.features.claim_level.categorical_encoding import apply_encoding_scheme, fit_encoding_scheme
from app.features.claim_level.date_features import compute_date_features
from app.features.claim_level.length_of_stay import compute_length_of_stay_feature
from app.features.claim_level.provider_frequency import compute_provider_frequency
from app.features.schemas import ClaimFeatures

CLAIM_ID_COLUMN = "CLM_ID"


def _clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def _clean_int(value):
    cleaned = _clean(value)
    return int(cleaned) if cleaned is not None else None


def compute_claim_features(df: pd.DataFrame, categories: dict[str, ColumnCategory]) -> list[ClaimFeatures]:
    amount_ratios = compute_amount_ratios(df)
    length_of_stay = compute_length_of_stay_feature(df)
    date_features = compute_date_features(df)
    provider_frequency = compute_provider_frequency(df)

    schemes = fit_encoding_scheme(df, categories)
    encoded = apply_encoding_scheme(df, schemes)

    rows: list[ClaimFeatures] = []
    for idx in df.index:
        length_of_stay_value = _clean(length_of_stay.loc[idx])
        rows.append(
            ClaimFeatures(
                claim_id=str(df.at[idx, CLAIM_ID_COLUMN]),
                payment_to_charge_ratio=_clean(amount_ratios.at[idx, "payment_to_charge_ratio"]),
                length_of_stay_days=int(length_of_stay_value) if length_of_stay_value is not None else None,
                admission_day_of_week=_clean_int(date_features.at[idx, "admission_day_of_week"]),
                admission_month=_clean_int(date_features.at[idx, "admission_month"]),
                admission_year=_clean_int(date_features.at[idx, "admission_year"]),
                encoded_categoricals={col: _clean(encoded.at[idx, col]) for col in encoded.columns},
                provider_frequency=_clean(provider_frequency.loc[idx]),
            )
        )
    return rows
