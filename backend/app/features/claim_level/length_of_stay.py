"""Claim-level length-of-stay feature (FR-002), reusing Phase 4's shared
derivation (app.shared.length_of_stay) rather than a second, potentially
divergent formula (specs/005-feature-engineering research.md).
"""

import pandas as pd

from app.shared.length_of_stay import compute_length_of_stay_days

ADMISSION_DATE_COLUMN = "CLM_ADMSN_DT"
DISCHARGE_DATE_COLUMN = "NCH_BENE_DSCHRG_DT"


def compute_length_of_stay_feature(df: pd.DataFrame) -> pd.Series:
    admission = pd.to_datetime(df[ADMISSION_DATE_COLUMN], errors="coerce")
    discharge = pd.to_datetime(df[DISCHARGE_DATE_COLUMN], errors="coerce")

    length_of_stay = compute_length_of_stay_days(admission, discharge)
    return length_of_stay.rename("length_of_stay_days")
