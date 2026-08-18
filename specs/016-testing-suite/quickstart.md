# Quickstart: Testing Suite

## Verify the coverage map is complete

```bash
pytest backend/tests/coverage_map/test_coverage_map_completeness.py -v
```

**Expected outcome**: pass — every MVP_CONTEXT.md Phase 16 named scenario has a `CoverageMapEntry` (spec SC-001).

## Run the new gap-filling tests

```bash
pytest backend/tests/anomaly/test_model_stability.py backend/tests/risk/test_drift_sensitivity.py backend/tests/llm/test_evidence_grounding.py -v
```

**Expected outcome**: pass, or an explicit, documented data-scale-limitation report — never a silent skip (spec SC-002, SC-006).

## Run the HITL integration tests

```bash
pytest backend/tests/integration/test_hitl_accept_remediate_revalidate.py backend/tests/integration/test_hitl_reject_feedback_recalculate.py -v
```

**Expected outcome**: both pass against real (non-mocked) Phase 12-14 module boundaries (spec SC-003).

## Run the ingestion integration tests

```bash
pytest backend/tests/integration/test_ingestion_large_file.py backend/tests/integration/test_ingestion_malformed_batch.py backend/tests/integration/test_ingestion_repeated_uploads.py -v
```

**Expected outcome**: all three pass against the real Phase 15 pipeline (spec SC-004).

## Run the consolidated Data-category suite

```bash
pytest backend/tests/data_suite/test_data_category_suite.py -v
```

**Expected outcome**: pass, running Phase 1/2/3's existing tests by reference — verify via `backend/tests/data_suite/test_data_category_suite.py`'s own imports that no test logic is duplicated (spec SC-005).

Full documentation reference: [docs/testing/phase16_coverage_map.md](../../../docs/testing/phase16_coverage_map.md) (created by this feature's implementation). Entity definitions: [data-model.md](./data-model.md).
