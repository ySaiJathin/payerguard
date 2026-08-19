"""Continuous ingestion: watches an inbox folder for new claim batches and enqueues them for processing.

STATUS: not implemented, and deliberately out of scope. Spec
`015-continuous-ingestion` (folder-watching / live-pipeline ingestion) was
removed on 2026-08-18 -- the project's scope is manual + repeated-batch
upload only (`POST /claims/upload`, see `app.ingestion.router`), never a
watched folder or a live/streaming source. Spec `017-batch-file-ingestion`
(FR-008) reaffirms this boundary explicitly. This file remains a
placeholder as a deliberate scope marker, not an oversight; do not
implement folder-watching here without a new, separately-scoped spec.
"""
