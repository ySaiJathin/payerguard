from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.quality.expectations.freshness import evaluate_freshness
from app.quality.schemas import Band, ExpectationType


def test_fresh_batch_is_pass(tmp_path: Path):
    batch = tmp_path / "batch.csv"
    batch.write_text("a,b\n1,2\n", encoding="utf-8")
    now = datetime.now(timezone.utc)
    result = evaluate_freshness(batch, run_id="run-1", now=now)
    assert result.band == Band.PASS
    assert result.expectation_type == ExpectationType.FRESHNESS
    assert result.column_name is None


def test_stale_batch_within_critical_window_is_warning(tmp_path: Path, monkeypatch):
    batch = tmp_path / "batch.csv"
    batch.write_text("a,b\n1,2\n", encoding="utf-8")
    now = datetime.now(timezone.utc) + timedelta(days=45)
    result = evaluate_freshness(batch, run_id="run-1", now=now)
    assert result.band == Band.WARNING


def test_very_stale_batch_is_critical(tmp_path: Path):
    batch = tmp_path / "batch.csv"
    batch.write_text("a,b\n1,2\n", encoding="utf-8")
    now = datetime.now(timezone.utc) + timedelta(days=200)
    result = evaluate_freshness(batch, run_id="run-1", now=now)
    assert result.band == Band.CRITICAL
