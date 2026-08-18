"""Claim-level provider-frequency feature (FR-005): how often PRVDR_NUM
appears in the configured historical scope (the dataframe passed in),
computed from real data -- a provider seen only once legitimately gets a
low, real frequency rather than an error or a fabricated zero.
"""

import pandas as pd

PROVIDER_COLUMN = "PRVDR_NUM"


def compute_provider_frequency(df: pd.DataFrame) -> pd.Series:
    provider = df[PROVIDER_COLUMN]
    counts = provider.value_counts()
    frequency = provider.map(counts) / len(provider)
    return frequency.rename("provider_frequency")
