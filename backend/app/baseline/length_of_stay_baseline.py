"""Length-of-stay distribution baseline (FR-005): the duration signal
that replaces a processing-time/SLA baseline (MVP_CONTEXT.md 2.4).

Claims with a missing or unparseable CLM_ADMSN_DT/NCH_BENE_DSCHRG_DT are
excluded from the statistics -- never assigned a fabricated duration --
and the exclusion count is reported as a first-class output field
(FR-005, SC-004). This module MUST NOT read NCH_WKLY_PROC_DT or
FI_CLM_PROC_DT (FR-006).
"""

import pandas as pd

from app.baseline.schemas import LengthOfStayBaseline, Percentiles
from app.shared.length_of_stay import compute_length_of_stay_days

ADMISSION_DATE_COLUMN = "CLM_ADMSN_DT"
DISCHARGE_DATE_COLUMN = "NCH_BENE_DSCHRG_DT"
_PERCENTILE_LEVELS = (0.25, 0.50, 0.75, 0.95, 0.99)


def compute_length_of_stay_baseline(df: pd.DataFrame) -> LengthOfStayBaseline:
    admission = pd.to_datetime(df[ADMISSION_DATE_COLUMN], errors="coerce")
    discharge = pd.to_datetime(df[DISCHARGE_DATE_COLUMN], errors="coerce")

    valid_mask = admission.notna() & discharge.notna()
    length_of_stay = compute_length_of_stay_days(admission[valid_mask], discharge[valid_mask])

    claims_included = int(valid_mask.sum())
    claims_excluded = int((~valid_mask).sum())

    if length_of_stay.empty:
        return LengthOfStayBaseline(
            mean=0.0,
            median=0.0,
            percentiles=Percentiles(p25=0.0, p50=0.0, p75=0.0, p95=0.0, p99=0.0),
            claims_included=0,
            claims_excluded_missing_dates=claims_excluded,
        )

    quantiles = length_of_stay.quantile(_PERCENTILE_LEVELS)
    return LengthOfStayBaseline(
        mean=float(length_of_stay.mean()),
        median=float(length_of_stay.median()),
        percentiles=Percentiles(
            p25=float(quantiles.loc[0.25]),
            p50=float(quantiles.loc[0.50]),
            p75=float(quantiles.loc[0.75]),
            p95=float(quantiles.loc[0.95]),
            p99=float(quantiles.loc[0.99]),
        ),
        claims_included=claims_included,
        claims_excluded_missing_dates=claims_excluded,
    )
