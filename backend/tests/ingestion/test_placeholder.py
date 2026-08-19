"""Ingestion tests: large files, malformed batches, repeated/continuous
uploads (Phase 15 Ingestion category).

STATUS: intentionally not implemented. `015-continuous-ingestion` -- the
feature that would have built the actual pipeline these scenarios need
(a watched-folder pattern processing repeated batches through the same
windowing logic used for the historical baseline) -- was removed as
out-of-scope in commit `6dd9ad2` before this testing-suite feature
(015-testing-suite) was renumbered into its old slot. `app/ingestion/`
remains the untouched Phase-0 placeholder: no router, no service, no
watcher logic, and no benchmark/model artifacts exist on disk to exercise.

Rather than fabricate production code this feature is explicitly
forbidden from adding, or write an integration test that mocks the very
module boundary it's supposed to prove is real, all three Ingestion
scenarios are recorded honestly as `limitation_documented` in
docs/testing/phase15_coverage_map.md, citing this same explanation
(spec 015-testing-suite FR-008/FR-009). See that file for the
authoritative record.
"""
