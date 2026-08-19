# Quickstart: Batch File Ingestion

## Upload a real (or realistically-shaped) claims file

```bash
curl -X POST "http://localhost:8000/claims/upload" \
  -F "file=@data/raw/inpatient.csv"
```

**Expected outcome**: `201 Created`, `IngestedBatch` with `status = completed`, and `quality_result_id`/`anomaly_result_id`/`risk_result_id` populated with real references — confirmed by then fetching those phases' own existing endpoints (`GET /quality/results`, `GET /anomaly/results`, `GET /incidents`) and finding this batch's data reflected there (spec SC-001). These references reflect the *most recently processed* batch specifically: quality/anomaly results live in each phase's own shared, single-current-batch store (unchanged by this feature), so a later upload's run supersedes an earlier batch's references the same way re-running any phase's own router already does — see `pipeline_runner.py`'s module docstring.

## Verify a malformed file is rejected before anything runs

```bash
curl -X POST "http://localhost:8000/claims/upload" -F "file=@/dev/null"
curl -X POST "http://localhost:8000/claims/upload" -F "file=@some_wrong_schema.csv"
```

**Expected outcome**: `422 Unprocessable Entity` in both cases, with a `reason_code` and `detail` naming exactly what's wrong (empty file; missing/unexpected columns) — never a downstream pipeline error (spec SC-002).

```bash
pytest backend/tests/ingestion/test_upload_validation.py -v
```

## Verify repeated uploads never collide

```bash
for i in 1 2 3 4 5; do
  curl -s -X POST "http://localhost:8000/claims/upload" -F "file=@data/raw/inpatient.csv" | jq -r .batch_id
done
curl -s "http://localhost:8000/claims/batches" | jq '.batches | length'
```

**Expected outcome**: five distinct `batch_id` values, five independently-listable `IngestedBatch` records, none overwritten (spec SC-003).

```bash
pytest backend/tests/ingestion/test_repeated_upload.py -v
```

## Verify honest status on a partial failure

```bash
pytest backend/tests/ingestion/test_partial_failure_status.py -v
```

Deliberately breaks a downstream stage (e.g., a malformed row that passes upload validation but fails cleaning) and asserts the resulting `IngestedBatch.status` is `failed` with `pipeline_stage_reached` naming the last stage that actually completed — never silently reported as `completed` (spec SC-004, constitution Principle II).

## Verify ingestion is now part of the audit trail

```bash
curl "http://localhost:8000/history/batch/<batch_id>"
pytest backend/tests/ingestion/test_audit_coverage.py -v
```

**Expected outcome**: every accepted and rejected upload has a corresponding `AuditTrailEntry` with `pipeline_stage = ingestion` (spec SC-005).

**Note**: implementing this feature required flipping an already-existing Phase 16 test that asserted the *absence* of ingestion coverage — `backend/tests/audit/test_registry_completeness.py::test_ingestion_is_deliberately_absent_from_the_expected_list` checked `"ingestion" not in EXPECTED_AUDITED_MODULES`; it is now `test_ingestion_is_present_now_that_a_real_write_path_exists`. The same file's positive completeness test (`test_every_expected_module_registers_when_its_stage_runs`) was extended with a `_drive_ingestion` helper so it actually exercises this feature's own audit-append call, not just asserts the registry entry's presence. Both were deliberate, expected updates during implementation, not regressions.

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).

---

This closes MVP_CONTEXT.md Section 5's Phase 17. Phases 18–22 (frontend, Dockerization, CI/CD, AWS, monitoring) remain explicitly deferred.
