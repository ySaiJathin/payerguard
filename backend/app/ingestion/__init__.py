"""Manual + repeated-batch upload of the raw CMS claims extract (spec 017-batch-file-ingestion).

Validates an uploaded file against the raw, pre-cleaning 197-column
schema profiled in Phase 1 (pipe-delimited, `sep="|"`) -- not the
already-cleaned schema -- then drives it synchronously through the
existing Phase 2-12 pipeline (cleaning, quality, baseline, features,
anomaly, risk, incident creation) by calling each phase's own service
functions, never re-implementing them. Every upload attempt, accepted or
rejected, is persisted as its own `IngestedBatch` row and appended to the
Phase 16 audit trail.

This module is unrelated to `app.demo`'s `POST /demo/upload`: that
endpoint accepts the already-cleaned/synthetic schema for demo and
simulation purposes and skips cleaning entirely. The two coexist
permanently; neither supersedes the other (see
specs/017-batch-file-ingestion/research.md's first decision).
"""
