# Phase 0 Research: Continuous Ingestion

## Decision: Watched-folder mode via polling (documented interval), not filesystem-event APIs or sockets

**Decision**: `watched_folder.py` polls the configured directory on a fixed interval (default 60s) listing files and comparing against `processed_files.json`'s recorded hashes/names, rather than using OS-level filesystem-event notifications (e.g., inotify) or any socket-based mechanism.

**Rationale**: MVP_CONTEXT.md is explicit that this must never be "a live socket/stream API" — polling is the clearest, most unambiguous way to satisfy that constraint, and it's portable across the Docker Compose local-dev environment and any future container platform without relying on host-specific filesystem-event support (which behaves differently across Docker volume mount types).

**Alternatives considered**: `watchdog` library's event-based OS-level file watching (rejected as the primary mechanism — while not literally a network socket, event-based watching over Docker-mounted volumes is unreliable across platforms (well-documented `inotify` limitations with bind mounts), and simple polling is both simpler to reason about and unambiguously satisfies "not live streaming").

## Decision: Duplicate detection via SHA-256 content hash, not filename

**Decision**: `duplicate_detection.py` computes a SHA-256 hash of each uploaded/detected file's content and compares against previously-ingested batches' recorded hashes; filename is informational only, not the dedup key.

**Rationale**: Filename-based dedup would miss a genuine duplicate uploaded under a different name, and would false-positive-reject a legitimately different batch that happens to reuse a filename — content hashing is the only approach that directly matches "byte-identical duplicate" (spec FR-004).

**Alternatives considered**: Row-level duplicate detection across the whole historical dataset (rejected as the ingestion-time check — that's a much heavier operation better suited to Phase 2's existing duplicate-row detection, which still runs on the new batch's contents during cleaning; this feature's own check is specifically about "did I already ingest this exact file," a cheaper and different question).

## Decision: Overlap detection compares the new batch's `CLM_FROM_DT`/`CLM_THRU_DT` range against every existing `IngestedBatch`'s recorded range

**Decision**: `overlap_detection.py` computes the new batch's min/max claim date range and checks it against all previously-ingested batches' stored ranges (including the original historical `inpatient.csv` load, itself recorded as an `IngestedBatch` retroactively or as a designated "batch zero"); any overlap creates a `DateRangeOverlapFlag` and the batch proceeds through the pipeline but the flag is surfaced prominently rather than silently ignored.

**Rationale**: Spec Edge Cases require overlap be "detected and handled explicitly (flagged for review)," not blocked outright — a corrected resupply of a prior period is a legitimate real-world scenario (data corrections happen), so outright rejection would be too restrictive; flagging for review balances catching a likely-accidental duplicate period against not blocking a legitimate correction.

**Alternatives considered**: Hard-rejecting any overlapping batch (rejected — too restrictive for the legitimate-correction case); silently allowing overlap with no flag (rejected — directly contradicts the spec's explicit "MUST NOT silently create conflicting window/claim data" requirement).

## Decision: New-batch scoring reuses Phase 4/6's existing artifacts as read-only references; formal extension is a separate, explicitly-named action

**Decision**: `pipeline_orchestrator.py` calls Phase 2/3/5/7/9's functions using the *existing* `BaselineSnapshot` and `TemporalSplit`/`SelectedFeatureSet` as fixed reference inputs for scoring the new batch — it never calls Phase 4's `POST /baseline/compute` or Phase 6's `POST /features/select` as a side effect of ingesting one batch. Formally extending the baseline/split to include new batches as "historical" remains a distinct, explicitly-triggered action (calling those phases' own endpoints directly).

**Rationale**: Spec FR-008 and the corresponding Edge Case require this separation explicitly — silently redefining "historical" every time a new batch arrives would make the baseline a constantly-shifting target, undermining the "compare against a stable historical norm" purpose Phase 4 was built for.

**Alternatives considered**: Auto-recomputing the baseline after every N new batches (rejected as unnecessary complexity/ambiguity for the MVP — the spec explicitly wants this to be a deliberate, explicit action, not an automatic policy with its own threshold to design and justify).
