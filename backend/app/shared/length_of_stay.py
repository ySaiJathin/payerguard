"""Admission-to-discharge day-difference, shared by Phase 4's baseline and
Phase 5's claim-level feature so the two never compute length-of-stay via
two independently-maintained formulas (specs/005-feature-engineering
research.md).
"""

import pandas as pd


def compute_length_of_stay_days(admission: pd.Series, discharge: pd.Series) -> pd.Series:
    """Both inputs must already be `pd.to_datetime`-parsed (NaT for missing/
    unparseable values). Returns a float Series of day counts, NaN wherever
    either input is NaT.
    """
    return (discharge - admission).dt.days
