"""SC-004: near-simultaneous events retain a stable, deterministic order.

This is the failure mode `sequence_number` exists for. Sorting an audit
trail by timestamp alone means two events written in the same millisecond
can come back in either order -- and on Windows, where the clock's
resolution is coarse enough that consecutive `datetime.now()` calls
routinely return identical values, "same millisecond" is the common case,
not an edge case.
"""

from datetime import datetime, timedelta, timezone

from app.audit.aggregation_service import append_entries, append_entry
from app.audit.history_service import query_history
from tests._db_fixtures import make_test_session

SAME_INSTANT = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)


def _append(db, source_record_id: str, occurred_at: datetime, entity_id: str = "I1"):
    return append_entry(
        db,
        entity_type="incident",
        entity_id=entity_id,
        pipeline_stage="incident_status",
        source_module="hitl",
        source_record_id=source_record_id,
        occurred_at=occurred_at,
    )


def test_same_timestamp_entries_get_distinct_increasing_sequence_numbers():
    db = make_test_session()

    first = _append(db, "R1", SAME_INSTANT)
    second = _append(db, "R2", SAME_INSTANT)
    db.commit()

    assert first.occurred_at == second.occurred_at, "Precondition: this test needs a real tie."
    assert second.sequence_number > first.sequence_number


def test_repeated_queries_return_identical_ordering():
    db = make_test_session()
    _append(db, "R1", SAME_INSTANT)
    _append(db, "R2", SAME_INSTANT)
    _append(db, "R3", SAME_INSTANT)
    db.commit()

    first_query = [e.source_record_id for e in query_history(db, "incident", "I1").entries]
    second_query = [e.source_record_id for e in query_history(db, "incident", "I1").entries]

    assert first_query == second_query == ["R1", "R2", "R3"]


def test_ordering_follows_append_order_not_timestamp_order():
    """If an upstream module supplies an out-of-order timestamp, the trail
    still reflects the order events were actually recorded -- which is the
    order the pipeline really executed them in."""
    db = make_test_session()
    _append(db, "R1", SAME_INSTANT)
    _append(db, "R2", SAME_INSTANT - timedelta(seconds=30))  # earlier clock value
    db.commit()

    ordered = [e.source_record_id for e in query_history(db, "incident", "I1").entries]

    assert ordered == ["R1", "R2"]


def test_bulk_append_assigns_contiguous_increasing_numbers():
    """The batch path must not reuse or skip numbers -- reuse would break
    the unique constraint, skipping would make gaps look like lost
    entries."""
    db = make_test_session()
    entries = append_entries(
        db,
        [
            {
                "entity_type": "batch",
                "entity_id": "B1",
                "pipeline_stage": "quality",
                "source_module": "quality",
                "source_record_id": f"chk-{i}",
                "occurred_at": SAME_INSTANT,
            }
            for i in range(50)
        ],
    )
    db.commit()

    sequences = [e.sequence_number for e in entries]
    assert sequences == list(range(sequences[0], sequences[0] + 50))


def test_bulk_and_single_appends_share_one_sequence_space():
    db = make_test_session()
    first = _append(db, "R1", SAME_INSTANT)
    bulk = append_entries(
        db,
        [
            {
                "entity_type": "batch",
                "entity_id": "B1",
                "pipeline_stage": "quality",
                "source_module": "quality",
                "source_record_id": "chk-1",
                "occurred_at": SAME_INSTANT,
            }
        ],
    )
    last = _append(db, "R2", SAME_INSTANT)
    db.commit()

    assert [first.sequence_number, bulk[0].sequence_number, last.sequence_number] == [1, 2, 3]


def test_two_claims_trails_do_not_interleave():
    """Spec Edge Cases bullet 4: a claim touched by two different
    incidents must not have the other incident's entries in its trail."""
    db = make_test_session()
    _append(db, "R1", SAME_INSTANT, entity_id="I1")
    _append(db, "R2", SAME_INSTANT, entity_id="I2")
    _append(db, "R3", SAME_INSTANT, entity_id="I1")
    db.commit()

    i1 = [e.source_record_id for e in query_history(db, "incident", "I1").entries]
    i2 = [e.source_record_id for e in query_history(db, "incident", "I2").entries]

    assert i1 == ["R1", "R3"]
    assert i2 == ["R2"]
