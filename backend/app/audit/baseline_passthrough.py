"""`/audit/baseline` -- a direct pass-through to Phase 4 (spec FR-003, SC-003).

Every call here delegates to `app.baseline.snapshot_log`'s own readers and
returns their result unchanged. No cache, no recomputation, no second
storage location: there is deliberately no code path on which this and
Phase 4's own `GET /baseline` could return different data, which is the
only implementation that *structurally* guarantees the parity FR-003
demands rather than merely testing for it.

Note: `snapshot_log` exposes no by-id reader, so `get_baseline(snapshot_id)`
filters its history list rather than adding a function to Phase 4 -- this
feature stays strictly read-only over the baseline module (spec
Assumptions).
"""

import json

from app.baseline.schemas import BaselineSnapshot
from app.baseline.snapshot_log import _read_history, read_latest_baseline_snapshot


class BaselineNotFoundError(LookupError):
    """No baseline computed yet, or the requested snapshot_id is unknown."""


def get_baseline(snapshot_id: str | None = None) -> BaselineSnapshot:
    if snapshot_id is None:
        snapshot = read_latest_baseline_snapshot()
        if snapshot is None:
            raise BaselineNotFoundError("No baseline has been computed yet.")
        return snapshot

    for entry in _read_history():
        if entry.get("snapshot_id") == snapshot_id:
            return BaselineSnapshot.model_validate(entry)
    raise BaselineNotFoundError(f"Unknown baseline snapshot_id {snapshot_id!r}.")


def baseline_as_dict(snapshot: BaselineSnapshot) -> dict:
    """Byte-comparable form, used by the parity test to assert this and
    Phase 4's endpoint really do return identical content."""
    return json.loads(snapshot.model_dump_json())
