# Quickstart: Testing Suite

## Verify the coverage map is complete

```bash
pytest backend/tests/coverage_map/test_coverage_map_completeness.py -v
```

**Expected outcome**: pass — every MVP_CONTEXT.md Phase 15 named scenario has a `CoverageMapEntry` (spec SC-001).

## Run the new gap-filling tests

```bash
pytest backend/tests/anomaly/test_model_stability.py backend/tests/risk/test_drift_sensitivity.py backend/tests/llm/test_evidence_grounding.py backend/tests/data_engineering/test_empty_file_handling.py -v
```

**Expected outcome**: pass, or an explicit, documented data-scale-limitation report — never a silent skip (spec SC-002, SC-006).

## Run the HITL integration tests

```bash
pytest backend/tests/integration/ backend/tests/hitl/test_router_hitl_flow.py -v
```

**Expected outcome**: both round-trips pass against real (non-mocked) Phase 12-14 module boundaries (spec SC-003).

Note there is no `test_hitl_reject_feedback_recalculate.py`. The
reject → feedback → recalculate → re-review round-trip is already covered
end-to-end over real HTTP by Phase 12's
`backend/tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow`,
so spec FR-009 (no duplicated coverage) means this feature cites it
rather than adding a second copy. Only the genuinely uncovered
accept → remediate → revalidate round-trip got a new file.

## Ingestion category — no tests to run

The three Ingestion scenarios (large files, malformed batches,
repeated/continuous uploads) are recorded as `limitation_documented`
rather than tested. `015-continuous-ingestion` — the feature that would
have built the pipeline they exercise — was removed as out-of-scope in
commit `6dd9ad2`, and `backend/app/ingestion/` remains an unimplemented
Phase-0 placeholder. Testing them would require either adding production
code this feature must not add, or mocking the very pipeline the test
exists to prove is real (spec FR-008/FR-009).

See `docs/testing/phase15_coverage_map.md` and
`backend/tests/ingestion/test_placeholder.py` for the full record.

## Run the consolidated Data-category suite

```bash
pytest backend/tests/data_suite/test_data_category_suite.py -v
```

**Expected outcome**: pass, running Phase 1/2/3's existing tests by reference — verify via `backend/tests/data_suite/test_data_category_suite.py`'s own imports that no test logic is duplicated (spec SC-005).

Full documentation reference: [docs/testing/phase15_coverage_map.md](../../../docs/testing/phase15_coverage_map.md) (created by this feature's implementation). Entity definitions: [data-model.md](./data-model.md).
