import pandas as pd

from app.baseline.volume_baseline import compute_volume_baseline


def test_every_window_present_including_zero_claim_gap():
    # 2026-01-01, 2026-01-02, then a gap on 2026-01-03 (zero claims), then 2026-01-04
    df = pd.DataFrame(
        {
            "CLM_FROM_DT": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-02",
                "2026-01-04",
            ]
        }
    )
    baseline = compute_volume_baseline(df, window_definition="daily")

    assert baseline.window_definition == "daily"
    window_ids = [w.window_id for w in baseline.windows]
    assert window_ids == ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]

    counts = {w.window_id: w.claim_count for w in baseline.windows}
    assert counts["2026-01-01"] == 2
    assert counts["2026-01-02"] == 1
    assert counts["2026-01-03"] == 0
    assert counts["2026-01-04"] == 1


def test_windows_are_chronologically_ordered():
    df = pd.DataFrame({"CLM_FROM_DT": ["2026-01-05", "2026-01-01", "2026-01-03"]})
    baseline = compute_volume_baseline(df, window_definition="daily")
    starts = [w.start for w in baseline.windows]
    assert starts == sorted(starts)
