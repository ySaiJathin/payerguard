from datetime import date

import pytest

from app.features.schemas import WindowFeatures
from app.risk.dataset import row_assembly
from app.risk.dataset.errors import AnomalyEnrichmentIncompleteError


def _window(window_id: str, anomaly_count: int | None) -> WindowFeatures:
    return WindowFeatures(
        window_id=window_id,
        start=date(2020, 1, 1),
        end=date(2020, 1, 7),
        claim_count=5,
        amount_stats={},
        missing_pct=0.0,
        duplicate_pct=0.0,
        invalid_status_pct=0.0,
        volume_deviation=0.0,
        amount_deviation={},
        anomaly_count=anomaly_count,
    )


def test_unenriched_window_raises_before_touching_quality_or_baseline(monkeypatch):
    windows = [_window("W1", anomaly_count=1), _window("W2", anomaly_count=None)]
    monkeypatch.setattr(row_assembly, "read_window_features", lambda out_dir=None: windows)

    def _fail(*args, **kwargs):
        raise AssertionError("must not read Phase 3/4 outputs before the enrichment guard")

    monkeypatch.setattr(row_assembly, "read_quality_results", _fail)
    monkeypatch.setattr(row_assembly, "read_latest_baseline_snapshot", _fail)

    with pytest.raises(AnomalyEnrichmentIncompleteError, match="W2"):
        row_assembly.assemble_rows()
