"""SC-003: `/audit/baseline` returns data identical to Phase 4's own
`GET /baseline`.

The pass-through is designed so the two *cannot* diverge (same function
call, no cache), but that is the claim being verified rather than assumed
-- a future "optimisation" that introduced a copy is exactly what this
test exists to catch.
"""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.router import router as audit_router
from app.baseline import snapshot_log
from app.baseline.router import router as baseline_router
from app.baseline.schemas import (
    AmountBaseline,
    BaselineSnapshot,
    DataHealthBaseline,
    LengthOfStayBaseline,
    Percentiles,
    SourceDateRange,
    VolumeBaseline,
    VolumeWindow,
)
from datetime import date, datetime, timezone


def _snapshot(snapshot_id: str, median: float = 500.0) -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id=snapshot_id,
        source_file="data/cleaned/inpatient_cleaned.csv",
        source_row_count=58066,
        source_date_range=SourceDateRange(min_date=date(2015, 4, 1), max_date=date(2022, 10, 31)),
        volume_baseline=VolumeBaseline(
            window_definition="monthly",
            windows=[VolumeWindow(window_id="W1", start=date(2015, 4, 1), end=date(2015, 4, 30), claim_count=10)],
        ),
        amount_baselines=[
            AmountBaseline(
                column_name="CLM_PMT_AMT",
                mean=600.0,
                median=median,
                std=100.0,
                min=10.0,
                max=9000.0,
                percentiles=Percentiles(p25=100.0, p50=median, p75=1000.0, p95=5000.0, p99=10000.0),
            )
        ],
        data_health_baseline=DataHealthBaseline(
            historical_missing_rate_by_column={},
            historical_duplicate_rate=0.0,
            categorical_distributions={},
        ),
        length_of_stay_baseline=LengthOfStayBaseline(
            mean=4.0,
            median=3.0,
            percentiles=Percentiles(p25=2.0, p50=3.0, p75=5.0, p95=12.0, p99=25.0),
            claims_included=10,
            claims_excluded_missing_dates=0,
        ),
        computed_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    )


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(snapshot_log, "reports_dir", lambda: tmp_path)
    app = FastAPI()
    app.include_router(baseline_router)
    app.include_router(audit_router)
    return TestClient(app)


def test_audit_baseline_matches_phase_4_baseline_exactly(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    snapshot_log.write_baseline_snapshot(_snapshot("snap-1"), tmp_path)

    phase4 = client.get("/baseline")
    audit = client.get("/audit/baseline")

    assert phase4.status_code == 200
    assert audit.status_code == 200
    assert audit.json() == phase4.json(), "The pass-through diverged from Phase 4's own baseline."


def test_specific_historical_snapshot_is_retrievable_by_id(tmp_path, monkeypatch):
    """US2 acceptance scenario 3: 'what baseline was in effect when this
    incident was scored' needs the older snapshot, not just the latest."""
    client = _client(tmp_path, monkeypatch)
    snapshot_log.write_baseline_snapshot(_snapshot("snap-1", median=500.0), tmp_path)
    snapshot_log.write_baseline_snapshot(_snapshot("snap-2", median=750.0), tmp_path)

    latest = client.get("/audit/baseline")
    assert latest.json()["snapshot_id"] == "snap-2"

    historical = client.get("/audit/baseline", params={"snapshot_id": "snap-1"})
    assert historical.status_code == 200
    assert historical.json()["snapshot_id"] == "snap-1"
    assert historical.json()["amount_baselines"][0]["median"] == 500.0


def test_unknown_snapshot_id_returns_404(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    snapshot_log.write_baseline_snapshot(_snapshot("snap-1"), tmp_path)

    assert client.get("/audit/baseline", params={"snapshot_id": "nope"}).status_code == 404


def test_no_baseline_computed_yet_returns_404(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    assert client.get("/audit/baseline").status_code == 404


def test_passthrough_does_not_cache_a_stale_copy(tmp_path, monkeypatch):
    """A cached copy is the specific failure FR-003 warns about: the two
    endpoints would agree at first and silently drift after a recompute."""
    client = _client(tmp_path, monkeypatch)
    snapshot_log.write_baseline_snapshot(_snapshot("snap-1", median=500.0), tmp_path)

    first = client.get("/audit/baseline").json()
    assert first["amount_baselines"][0]["median"] == 500.0

    snapshot_log.write_baseline_snapshot(_snapshot("snap-2", median=750.0), tmp_path)

    second = client.get("/audit/baseline").json()
    assert second["amount_baselines"][0]["median"] == 750.0
    assert second == json.loads(client.get("/baseline").text)
