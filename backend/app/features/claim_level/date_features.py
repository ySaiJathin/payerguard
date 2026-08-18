"""Claim-level date-derived features (FR-003), extracted from the
standardized ISO CLM_ADMSN_DT produced by Phase 2.
"""

import pandas as pd

ADMISSION_DATE_COLUMN = "CLM_ADMSN_DT"


def compute_date_features(df: pd.DataFrame) -> pd.DataFrame:
    admission = pd.to_datetime(df[ADMISSION_DATE_COLUMN], errors="coerce")

    return pd.DataFrame(
        {
            "admission_day_of_week": admission.dt.dayofweek,
            "admission_month": admission.dt.month,
            "admission_year": admission.dt.year,
        },
        index=df.index,
    )
