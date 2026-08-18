"""SC-002: baseline statistics are never hardcoded constants -- every
value must change correctly when recomputed against a mutated dataset.
"""

import pandas as pd

from app.baseline.amount_baseline import compute_amount_baselines
from app.baseline.volume_baseline import compute_volume_baseline
from app.data_engineering.schemas import ColumnCategory


def test_amount_baseline_changes_when_fixture_amounts_mutate():
    df = pd.DataFrame({"CLM_PMT_AMT": [100.0, 200.0, 300.0, 400.0]})
    categories = {"CLM_PMT_AMT": ColumnCategory.AMOUNT}

    before = compute_amount_baselines(df, categories)[0]

    mutated = df.copy()
    mutated["CLM_PMT_AMT"] = mutated["CLM_PMT_AMT"] * 10
    after = compute_amount_baselines(mutated, categories)[0]

    assert after.mean != before.mean
    assert after.median != before.median
    assert after.mean == before.mean * 10
    assert after.median == before.median * 10


def test_volume_baseline_changes_when_fixture_dates_extend():
    df = pd.DataFrame({"CLM_FROM_DT": ["2026-01-01", "2026-01-01", "2026-01-02"]})
    before = compute_volume_baseline(df, window_definition="daily")

    extended = pd.concat(
        [df, pd.DataFrame({"CLM_FROM_DT": ["2026-01-03", "2026-01-03", "2026-01-03"]})],
        ignore_index=True,
    )
    after = compute_volume_baseline(extended, window_definition="daily")

    assert len(after.windows) > len(before.windows)
    after_counts = {w.window_id: w.claim_count for w in after.windows}
    assert after_counts["2026-01-03"] == 3
