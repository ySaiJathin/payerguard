# Quickstart: Continuous Ingestion

## Upload a new batch manually

```bash
curl -X POST http://localhost:8000/ingestion/upload -F "file=@data/sampled/inpatient_sample.csv"
```

**Expected outcome**: `202 Accepted`; polling `GET /ingestion/batches/{batch_id}` eventually shows `processing_status: "completed"` with a `BatchProcessingResult`.

## Verify pipeline reuse (no duplicated logic)

Run `backend/tests/ingestion/test_pipeline_reuse_audit.py` — a static check that `pipeline_orchestrator.py` imports Phase 2/3/5/7/9's actual service functions rather than reimplementing cleaning/quality/feature/scoring logic (spec SC-001).

## Verify malformed/empty rejection

```bash
echo "" > /tmp/empty.csv
curl -X POST http://localhost:8000/ingestion/upload -F "file=@/tmp/empty.csv"
```

**Expected outcome**: `422 Unprocessable Entity`, `rejected_empty` (spec SC-002).

## Verify duplicate detection

```bash
curl -X POST http://localhost:8000/ingestion/upload -F "file=@data/sampled/inpatient_sample.csv"
```

(upload the same file again)

**Expected outcome**: `409 Conflict`, `rejected_duplicate` (spec SC-003).

## Verify the watched folder

```bash
curl -X POST http://localhost:8000/ingestion/watched-folder/start
cp data/sampled/inpatient_sample.csv data/incoming/new_batch_1.csv
```

Wait one poll interval, then:

```bash
curl http://localhost:8000/ingestion/batches?ingestion_method=watched_folder
```

**Expected outcome**: the dropped file appears as a processed `IngestedBatch` (spec SC-004).

## Verify no streaming endpoints

Run `backend/tests/ingestion/test_no_streaming_endpoints.py` — an OpenAPI-schema audit confirming no WebSocket/SSE/long-lived-connection endpoint exists in this module (spec SC-005).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
