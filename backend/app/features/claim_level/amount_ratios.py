"""Claim-level amount-ratio features (FR-001).

A zero or missing denominator produces a null ratio -- never a
divide-by-zero error or a fabricated large/default number (constitution
Principle II).
"""

import numpy as np
import pandas as pd

PAYMENT_COLUMN = "CLM_PMT_AMT"
CHARGE_COLUMN = "CLM_TOT_CHRG_AMT"


def compute_amount_ratios(df: pd.DataFrame) -> pd.DataFrame:
    payment = pd.to_numeric(df[PAYMENT_COLUMN], errors="coerce")
    charge = pd.to_numeric(df[CHARGE_COLUMN], errors="coerce")

    safe_denominator = charge.where(charge != 0)
    ratio = (payment / safe_denominator).replace([np.inf, -np.inf], np.nan)

    return pd.DataFrame({"payment_to_charge_ratio": ratio}, index=df.index)
