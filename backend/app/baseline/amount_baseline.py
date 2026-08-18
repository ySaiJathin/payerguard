"""Amount distribution baseline: mean/median/std/min/max/percentiles for
every amount-category column (FR-002).

Every amount column is computed independently -- CLM_PMT_AMT and
CLM_TOT_CHRG_AMT happening to be identical in the current extract
(MVP_CONTEXT.md 2.2) is not assumed to hold for future data.
"""

import pandas as pd

from app.baseline.schemas import AmountBaseline, Percentiles
from app.data_engineering.schemas import ColumnCategory

_PERCENTILE_LEVELS = (0.25, 0.50, 0.75, 0.95, 0.99)


def compute_amount_baselines(
    df: pd.DataFrame, categories: dict[str, ColumnCategory]
) -> list[AmountBaseline]:
    amount_columns = [col for col, cat in categories.items() if cat == ColumnCategory.AMOUNT and col in df.columns]

    baselines: list[AmountBaseline] = []
    for column in amount_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue

        quantiles = series.quantile(_PERCENTILE_LEVELS)
        baselines.append(
            AmountBaseline(
                column_name=column,
                mean=float(series.mean()),
                median=float(series.median()),
                std=float(series.std()),
                min=float(series.min()),
                max=float(series.max()),
                percentiles=Percentiles(
                    p25=float(quantiles.loc[0.25]),
                    p50=float(quantiles.loc[0.50]),
                    p75=float(quantiles.loc[0.75]),
                    p95=float(quantiles.loc[0.95]),
                    p99=float(quantiles.loc[0.99]),
                ),
            )
        )
    return baselines
