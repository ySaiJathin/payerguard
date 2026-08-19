"""Fixed-interval chunked ingestion, with the pipeline firing on completion.

A simulation run streams the selected batch in chunks, one chunk every
`CHUNK_INTERVAL_SECONDS`, so the Simulator page shows claims arriving
continuously rather than one instantaneous dump. When the last chunk has
landed, the run triggers the full pipeline -- GX validation, Isolation
Forest, XGBoost risk scoring, incident generation -- against exactly the
claims that were ingested, and the dashboard picks the results up on its
next load, the same way it would after a real batch.

Run state lives in this module's `_RUNS` dict. It is deliberately in-process
and non-durable: a simulation is a live demo action, not a record. What the
run *produces* -- the quality results, the baseline snapshot, the benchmark
result, the incidents -- is persisted through the normal artifacts, and the
run's own summary is appended to `pipeline_runs.json`, so nothing of
substance is lost when the process restarts.
"""

import threading
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from app.core.database import SessionLocal
from app.demo import batches, pipeline
from app.demo.generator import CLAIM_FROM_COLUMN
from app.demo.schemas import SimulationStatus

# Hardcoded on purpose (the interval is not configurable): fast enough that a
# run finishes inside a demo, slow enough to watch.
CHUNK_INTERVAL_SECONDS = 4.0
CHUNK_COUNT = 8
MAX_RETAINED_RUNS = 20

_RUNS: dict[str, SimulationStatus] = {}
_LOCK = threading.Lock()


def _put(status: SimulationStatus) -> None:
    with _LOCK:
        _RUNS[status.run_id] = status
        if len(_RUNS) > MAX_RETAINED_RUNS:
            oldest = sorted(_RUNS.values(), key=lambda s: s.started_at)[: len(_RUNS) - MAX_RETAINED_RUNS]
            for stale in oldest:
                _RUNS.pop(stale.run_id, None)


def get_status(run_id: str) -> SimulationStatus | None:
    with _LOCK:
        return _RUNS.get(run_id)


def list_runs() -> list[SimulationStatus]:
    with _LOCK:
        return sorted(_RUNS.values(), key=lambda s: s.started_at, reverse=True)


def _update(run_id: str, **fields) -> None:
    with _LOCK:
        status = _RUNS.get(run_id)
        if status is None:
            return
        for key, value in fields.items():
            setattr(status, key, value)
        status.updated_at = datetime.now(timezone.utc)


def _chunks(df: pd.DataFrame, count: int) -> list[pd.DataFrame]:
    ordered = df.sort_values(CLAIM_FROM_COLUMN, kind="stable")
    size = max(len(ordered) // count, 1)
    parts = [ordered.iloc[i : i + size] for i in range(0, len(ordered), size)]
    # Fold any remainder into the last chunk rather than dropping it -- the
    # progress readout has to end on the batch's real claim count, because
    # the pipeline then runs on all of it.
    while len(parts) > count:
        parts[-2] = pd.concat([parts[-2], parts.pop()])
    return parts or [ordered]


def _run(run_id: str, batch_id: str, inject_anomalies: bool, stop: threading.Event) -> None:
    db = SessionLocal()
    try:
        df, labels = batches.load_batch(batch_id)
        if inject_anomalies:
            _update(run_id, message="Applying live anomaly injection to the batch...")
            from app.demo.column_profile import load_column_profile
            from app.demo.generator import inject

            df, labels = inject(
                df,
                labels,
                pipeline.LIVE_INJECTION_PLAN,
                load_column_profile(),
                seed=batches.spec_for(batch_id).seed + 7,
            )
            df = df.sort_values(CLAIM_FROM_COLUMN, kind="stable")
            labels = labels.loc[df.index]

        parts = _chunks(df, CHUNK_COUNT)
        _update(
            run_id,
            state="ingesting",
            chunk_total=len(parts),
            claims_total=int(len(df)),
            message="Ingesting claims...",
        )

        ingested = 0
        for index, part in enumerate(parts, start=1):
            if stop.wait(CHUNK_INTERVAL_SECONDS):
                _update(run_id, state="failed", error="Run cancelled.")
                return
            ingested += len(part)
            window_dates = pd.to_datetime(part[CLAIM_FROM_COLUMN], errors="coerce")
            _update(
                run_id,
                chunk_index=index,
                claims_ingested=ingested,
                current_window=(
                    f"{window_dates.min().date()} .. {window_dates.max().date()}"
                    if window_dates.notna().any()
                    else None
                ),
                message=f"Ingested chunk {index} of {len(parts)} ({ingested} of {len(df)} claims).",
            )

        _update(
            run_id,
            state="analyzing",
            current_window=None,
            message="All chunks ingested -- running GX validation, Isolation Forest, XGBoost and incident generation.",
        )
        spec = batches.spec_for(batch_id)
        result = pipeline.run_pipeline(
            db,
            df,
            labels,
            batch_id=batch_id,
            batch_label=spec.label,
            source="simulator",
            injection_applied=inject_anomalies,
        )
        _update(
            run_id,
            state="complete",
            result=result,
            message=(
                f"Complete: quality {result.quality_composite_score:.1f}, "
                f"detection F1 {result.anomaly.f1:.2f}, {len(result.incident_ids)} incident(s) created."
            ),
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced to the UI, not swallowed
        _update(run_id, state="failed", error=f"{type(exc).__name__}: {exc}", message="Simulation failed.")
    finally:
        db.close()


def start(batch_id: str, inject_anomalies: bool) -> SimulationStatus:
    spec = batches.spec_for(batch_id)
    now = datetime.now(timezone.utc)
    status = SimulationStatus(
        run_id=str(uuid4()),
        batch_id=batch_id,
        batch_label=spec.label,
        inject_anomalies=inject_anomalies,
        state="queued",
        chunk_index=0,
        chunk_total=CHUNK_COUNT,
        chunk_interval_seconds=CHUNK_INTERVAL_SECONDS,
        claims_ingested=0,
        claims_total=0,
        current_window=None,
        message="Preparing batch...",
        started_at=now,
        updated_at=now,
    )
    _put(status)

    stop = threading.Event()
    thread = threading.Thread(
        target=_run, args=(status.run_id, batch_id, inject_anomalies, stop), daemon=True
    )
    thread.start()
    return status


def next_batch_id(previous: str | None) -> str:
    """Default cycling order for the batch picker."""
    ids = [spec.batch_id for spec in batches.BATCH_SPECS]
    if previous not in ids:
        return ids[0]
    return ids[(ids.index(previous) + 1) % len(ids)]
