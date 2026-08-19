"""Audit trail across the whole pipeline (Phase 16).

An audit-source registry and aggregation layer over every prior phase's
own persisted records (Phases 2-14): each owning module calls
`aggregation_service.append_entry` at the moment it writes its own record,
building an ordered `audit_logs` index incrementally rather than
reconstructing history retroactively from ten different tables' timestamps.
On top of that sit `GET /history` (paginated, filterable, deterministically
ordered) and `GET /audit/baseline` (a direct pass-through to Phase 4's own
baseline data), plus a completeness check that fails if a decision-producing
module has no registered audit source.

This module **references, never duplicates**: an `audit_logs` row carries
the owning module's `source_record_id` and nothing of its payload, so
there is no second copy of any fact to drift out of sync (FR-001, SC-002).
It exposes no write endpoint -- entries originate only from other modules'
own write paths, never from a caller-supplied record (FR-009).
"""
