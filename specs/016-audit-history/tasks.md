---

description: "Task list template for feature implementation"
---

# Tasks: Audit & History

**Input**: Design documents from `/specs/016-audit-history/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Explicitly requested — plan.md's Testing section names five test files mapped to SC-001 through SC-005, and FR-008/SC-005 require the completeness guarantee be enforced *by a failing test*, not documentation. Test tasks are therefore included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend module: `backend/app/audit/`
- Backend tests: `backend/tests/audit/`
- Call sites in already-complete phases: `backend/app/{data_engineering,quality,anomaly,risk,incidents,hitl,remediation,revalidation}/`

## Pre-Implementation Finding 1: `ingestion` cannot be an audited module

research.md's `EXPECTED_AUDITED_MODULES` lists `"ingestion"`, but `backend/app/ingestion/` is still the untouched Phase-0 placeholder — the continuous-ingestion feature that would have built it was removed 2026-08-18 (commit `6dd9ad2`) and its phase number retired. There is no write path to instrument, so an `ingestion` entry in the expected list would make `test_registry_completeness.py` fail permanently, training readers to ignore a red test.

**Resolution (user-confirmed)**: `"ingestion"` is dropped from `EXPECTED_AUDITED_MODULES`, with an inline comment at the constant and a note in the module docstring recording why and when. Re-adding it is a one-line change once ingestion is re-scoped. This is a deliberate, documented deviation from research.md's literal list.

## Pre-Implementation Finding 2: research.md's registry list omits `data_engineering`, but FR-001 requires it

research.md's `EXPECTED_AUDITED_MODULES` starts at `"quality"`, omitting `data_engineering`. But FR-001 explicitly names "Phase 2's `QualityIssueRecord`" as an aggregated source, and **User Story 1's first acceptance scenario is entirely about a Phase 2 cleaning correction appearing in a claim's audit trail**. Following research.md's list literally would leave the feature unable to satisfy its own P1 acceptance scenario.

**Resolution (user-confirmed)**: `data_engineering` is included in `EXPECTED_AUDITED_MODULES`. Spec Assumptions exclude "Phase 1's profiling, Phase 5 feature engineering, Phase 6 feature selection" as pure-computation modules — Phase 2 cleaning is *not* in that exclusion list, and it does produce a decision-like output (a recorded correction per cell), so including it matches the Assumptions' own "modules producing decisions/scores/actions" framing.

## Pre-Implementation Finding 3: two classes of write path, only one of which already has a DB session

`audit_logs` is a relational table, so `append_entry` needs a `Session`. The write paths split cleanly:

| Seam | Session today? | How it gets audited |
|---|---|---|
| `incidents.create_incident(db, …)` | ✅ yes | direct — and it also wraps Phase 10 scoring and the Phase 11 `investigate()` call, so `risk.scoring` and `llm` are auditable from this one seam without touching either module |
| `hitl` accept/reject/recalculate services | ✅ yes | direct |
| `remediation.run_remediation(db, …)` | ✅ yes | direct |
| `revalidation.run_revalidation(db, …)` | ✅ yes | direct |
| `data_engineering` cleaning, `quality`, `anomaly`, `risk.benchmark` | ❌ no | their routers gain `db: Session = Depends(get_db)` and pass it down — small additive change, no signature break for existing callers/tests |

**Resolution (user-confirmed)**: full wiring per FR-001. The batch-module changes are additive (`db` is threaded from the router into an optional service parameter), so every existing test that calls those services directly keeps working unchanged.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Replace the three mismatched Phase-0 placeholder stubs with the module skeleton plan.md's structure specifies, and create the test package.

- [X] T001 [P] Delete `backend/app/audit/service.py` — plan.md's structure splits its responsibilities across `registry.py`/`aggregation_service.py`/`history_service.py`/`baseline_passthrough.py`, mirroring the mismatched-Phase-0-stub cleanup precedent set by 014's T001 and 015's T001.
- [X] T002 [P] Rewrite the module docstring in `backend/app/audit/__init__.py`: remove the "STATUS: not implemented yet" placeholder text, replace with a one-paragraph description matching plan.md's Summary (audit-source registry + aggregation layer over Phases 2-14's own persisted records, `GET /history` with pagination/filtering and deterministic ordering, `GET /baseline` pass-through to Phase 4, completeness check). State explicitly that this module **references, never duplicates** other modules' facts (FR-001, FR-009).
- [X] T003 [P] Create `backend/tests/audit/__init__.py` (empty — mirrors the existing `backend/tests/<module>/__init__.py` convention).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The ORM table, schemas, registry, and the `append_entry` utility every call site and both user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Create `backend/app/audit/schemas.py` with the pydantic models per data-model.md: `EntityType(str, Enum)` (`claim`, `incident`, `batch`); `PipelineStage(str, Enum)` (`cleaning`, `quality`, `anomaly`, `risk`, `severity_scoring`, `llm_investigation`, `incident_status`, `human_feedback`, `remediation`, `revalidation`) — note `ingestion` is omitted per Pre-Implementation Finding 1, with an inline comment saying so; `AuditTrailEntry` (`entry_id: str`, `entity_type: EntityType`, `entity_id: str`, `pipeline_stage: PipelineStage`, `source_module: str`, `source_record_id: str`, `baseline_snapshot_id_used: str | None = None`, `sequence_number: int`, `occurred_at: datetime`, `model_config = ConfigDict(from_attributes=True)`); `AuditSourceRegistryEntry` (`module_name: str`, `record_types_contributed: list[str]`, `registered: bool`); `HistoryQueryResult` (`entity_type: str`, `entity_id: str`, `entries: list[AuditTrailEntry]`, `page: int`, `page_size: int`, `total_count: int`, `found: bool`).
- [X] T005 [P] Create `backend/app/audit/models.py` with one SQLAlchemy ORM class `AuditLog` (`__tablename__ = "audit_logs"`, the name MVP_CONTEXT.md Section 3's core-tables list uses): `entry_id: str` PK, `entity_type: str` indexed, `entity_id: str` indexed, `pipeline_stage: str` indexed, `source_module: str`, `source_record_id: str`, `baseline_snapshot_id_used: str | None`, `sequence_number: int` unique+indexed, `occurred_at: datetime` indexed. Mirror `backend/app/revalidation/models.py`'s append-only style — rows are never updated or deleted (FR-009). Add a composite index on `(entity_type, entity_id, sequence_number)` since that is the exact shape every `/history` query filters and orders by.
- [X] T006 Update `backend/tests/_db_fixtures.py` to add `import app.audit.models  # noqa: F401` alongside the existing model imports, so `audit_logs` registers on `Base.metadata` before `init_db()`. Depends on T005.
- [X] T007 Create `backend/app/audit/registry.py` with `EXPECTED_AUDITED_MODULES: dict[str, list[str]]` mapping each decision-producing module to the record types it contributes: `data_engineering` → `["QualityIssueRecord"]`, `quality` → `["ExpectationCheckResult"]`, `anomaly` → `["BenchmarkRunResult"]`, `risk` → `["RiskBenchmarkRunResult"]`, `risk.scoring` → `["SeverityResult", "BusinessImpactResult", "PriorityResult"]`, `llm` → `["LLMInvestigation"]`, `incidents` → `["Incident"]`, `hitl` → `["IncidentStatusTransition", "HumanFeedback"]`, `remediation` → `["RemediationAction", "ManualActionRequired"]`, `revalidation` → `["RevalidationRun"]`. Include a prominent comment recording that `ingestion` is deliberately absent (Pre-Implementation Finding 1: module retired 2026-08-18, no write path exists to instrument) and that `data_engineering` is deliberately present (Finding 2: FR-001 and US1 acceptance scenario 1 require it despite research.md's list omitting it). Add `check_registry_completeness(db) -> list[AuditSourceRegistryEntry]` returning one entry per expected module with `registered=True` iff at least one real `AuditLog` row exists with that `source_module`.
- [X] T008 Create `backend/app/audit/aggregation_service.py` with `append_entry(db: Session, *, entity_type: str, entity_id: str, pipeline_stage: str, source_module: str, source_record_id: str, baseline_snapshot_id_used: str | None = None, occurred_at: datetime | None = None) -> AuditTrailEntry` (research.md's append-at-write-time model). It assigns `sequence_number` as `max(existing) + 1` computed inside the same transaction via `SELECT COALESCE(MAX(sequence_number), 0) + 1` so near-simultaneous appends can never collide (FR-004, SC-004 — a timestamp alone is not sufficient, which is the whole point of the field); defaults `occurred_at` to `datetime.now(timezone.utc)`; `db.add(...)`s the row **without committing**, so the caller's existing transaction stays atomic — an audit entry must never be durable for a fact whose own write was rolled back. Keep this module free of imports from any other pipeline-stage module (research.md's no-circular-dependency decision): it takes only plain values and a `Session`. Depends on T004, T005.

**Checkpoint**: Table, schemas, registry, and the append utility exist — call-site wiring and both read endpoints can now proceed.

---

## Phase 3: User Story 1 - See a complete audit trail across every pipeline stage (Priority: P1) 🎯 MVP

**Goal**: Every decision/score/action-producing stage appends a referencing audit entry at the moment it persists its own record, so an incident's or claim's full cross-module history is reconstructable in correct order.

**Independent Test**: Run a fixture incident through create → accept → remediate → revalidate, then query `AuditLog` rows for that incident and confirm each stage appears exactly once, in correct `sequence_number` order, each `source_record_id` resolving to a real row in its owning module's own table.

### Implementation for User Story 1

- [X] T009 [US1] Wire `append_entry` into `backend/app/incidents/service.py`'s `create_incident`: after `db.add(incident_orm)`, append one entry for the incident itself (`entity_type="incident"`, `pipeline_stage="incident_status"`, `source_module="incidents"`, `source_record_id=incident_id`) and one for Phase 10's scoring (`pipeline_stage="severity_scoring"`, `source_module="risk.scoring"`, `source_record_id=incident_id` — the incident row is where `severity_result`/`business_impact_result`/`priority_result` are actually persisted, so it is the honest source reference). When `investigation_id` is not `None`, append a third entry (`pipeline_stage="llm_investigation"`, `source_module="llm"`, `source_record_id=investigation_id`). Do **not** append an llm entry when the investigation failed — a failed investigation produced no `LLMInvestigation` record to reference, and inventing one would violate FR-001/SC-002. Set `baseline_snapshot_id_used` from `evidence.baseline_amount_percentiles`' originating snapshot when the evidence bundle carries one, else `None` (FR-005).
- [X] T010 [P] [US1] Wire `append_entry` into `backend/app/hitl/accept_service.py`'s `accept_incident` and `backend/app/hitl/reject_service.py`'s `reject_incident`: one entry per persisted `IncidentStatusTransition` (`pipeline_stage="incident_status"`, `source_module="hitl"`, `source_record_id=<transition_id>`), plus, in the reject path, one for the persisted `HumanFeedback` row (`pipeline_stage="human_feedback"`, `source_record_id=<feedback_id>`). Depends on T008.
- [X] T011 [P] [US1] Wire `append_entry` into `backend/app/hitl/recalculation_service.py`'s `recalculate_incident`: one entry for the status transition it records, plus one `llm_investigation` entry when recalculation produced a new `LLMInvestigation` (matching T009's rule — no entry when investigation failed). Depends on T008.
- [X] T012 [P] [US1] Wire `append_entry` into `backend/app/remediation/remediation_service.py`'s `run_remediation`: one entry per persisted `RemediationAction` (`entity_type="claim"`, `entity_id=<claim_id>`, `pipeline_stage="remediation"`, `source_record_id=<action_id>`) and one per `ManualActionRequired` record, plus one incident-scoped entry for the `RemediationRun` itself so the incident's own trail shows the run. Claim-scoped entries are what make US1's "audit trail for a claim" answerable, and scoping each action to its own `claim_id` is what keeps two incidents touching the same claim from conflating (spec Edge Cases bullet 4). Depends on T008.
- [X] T013 [P] [US1] Wire `append_entry` into `backend/app/revalidation/revalidation_service.py`'s `run_revalidation`: one entry for the persisted `RevalidationRun` (`pipeline_stage="revalidation"`, `source_record_id=<revalidation_id>`) and one for the resulting status transition it records via `hitl`. Depends on T008.
- [X] T014 [US1] Add an optional `db: Session | None = None` parameter to `backend/app/data_engineering/cleaning_service.py`'s `run_cleaning` and, when supplied, append one `cleaning` entry per persisted `QualityIssueRecord` (`entity_type="claim"`, `entity_id=<the record's claim/row id>`, `source_module="data_engineering"`, `source_record_id=<record id>`) — satisfying US1 acceptance scenario 1. Then add `db: Session = Depends(get_db)` to `backend/app/data_engineering/router.py`'s `run_clean` endpoint and pass it through. The parameter is optional and defaults to `None` specifically so every existing direct-call test in `backend/tests/data_engineering/` keeps passing unchanged. Depends on T008.
- [X] T015 [P] [US1] Same additive pattern for `backend/app/quality/scoring_service.py`'s `run_validation` (optional `db`, one `quality` entry per persisted `ExpectationCheckResult`, `entity_type="batch"`) and `backend/app/quality/router.py`'s `validate` endpoint (`Depends(get_db)`). Depends on T008.
- [X] T016 [P] [US1] Same additive pattern for `backend/app/anomaly/router.py`'s `benchmark`/`enrich` endpoints and `backend/app/risk/benchmark/router.py`'s `benchmark` endpoint — one `anomaly`/`risk` entry per persisted benchmark run result (`entity_type="batch"`, `source_record_id=<the run's own id/version>`). Depends on T008.
- [X] T017 [US1] Create `backend/tests/audit/_fixtures.py` (no `test_` prefix) with shared builders: a `run_full_incident_lifecycle(db, monkeypatch) -> incident_id` helper that drives a fixture incident through the real create → accept → remediate → revalidate path (reusing `tests.revalidation._fixtures`' `make_incident`/`make_remediation_run`/`patch_recompute_dependencies` and `tests.llm._fixtures`' fake Mistral client), returning the incident id plus the ids of every record created along the way, so provenance assertions have real upstream ids to resolve against.
- [X] T018 [US1] Create `backend/tests/audit/test_full_pipeline_trail.py` (SC-001): drives `_fixtures.run_full_incident_lifecycle`, queries `AuditLog` for that incident, and asserts every stage the incident actually passed through appears as a distinct entry in strictly increasing `sequence_number` order; asserts the stage set matches exactly what the fixture exercised — **no extra stages and no missing ones** (an audit trail that over-reports is as wrong as one that under-reports). Depends on T009-T013, T017.
- [X] T019 [US1] Create `backend/tests/audit/test_provenance.py` (SC-002): for every `AuditLog` row produced by the lifecycle fixture, resolve `source_record_id` against `source_module`'s own table/store and assert the referenced record genuinely exists; additionally assert the `AuditLog` row does **not** carry a copy of the upstream record's payload fields (only the reference), enforcing FR-001's "never duplicates" clause structurally rather than by convention. Depends on T017, T018.
- [X] T020 [US1] Create `backend/tests/audit/test_deterministic_ordering.py` (SC-004, spec Edge Cases bullet 3): append two entries with an identical explicitly-passed `occurred_at` (same millisecond), then query history twice and assert both queries return them in the same order, and that their `sequence_number`s differ. Add a second case asserting two claims' remediation entries never interleave into each other's trail (Edge Cases bullet 4). Depends on T008.

**Checkpoint**: Every pipeline stage contributes real, referencing, deterministically-ordered audit entries — independently verifiable without either endpoint existing yet.

---

## Phase 4: User Story 2 - Expose `/history` and `/baseline` read endpoints (Priority: P1)

**Goal**: A stable, documented read surface over Story 1's aggregated trail, plus a baseline pass-through that structurally cannot diverge from Phase 4's own data.

**Independent Test**: `GET /history/incident/{id}` returns the fixture incident's full ordered trail with `found: true`; an unknown id returns `found: false`; `GET` the audit baseline and Phase 4's baseline and confirm identical content.

### Implementation for User Story 2

- [X] T021 [US2] Create `backend/app/audit/history_service.py` with `query_history(db, entity_type, entity_id, *, page=1, page_size=50, stage=None, start_date=None, end_date=None) -> HistoryQueryResult`: filters `AuditLog` by entity, optionally by `pipeline_stage` and `occurred_at` range, orders by `sequence_number` (never by `occurred_at` — FR-004's whole purpose), paginates, and sets `found=False` **only when the entity has zero entries at all**, distinct from a valid page beyond the end of a non-empty history (FR-006/SC-006 — a normal empty page must not masquerade as "no history"). Returns `total_count` as the unpaginated match count. Depends on T004, T005.
- [X] T022 [P] [US2] Create `backend/app/audit/baseline_passthrough.py` with `get_baseline(snapshot_id: str | None = None)`: with no id, returns `app.baseline.snapshot_log.read_latest_baseline_snapshot()`; with an id, scans `read_baseline_history()`/the persisted snapshots for that `snapshot_id` and returns the full `BaselineSnapshot`. Calls Phase 4's own functions directly and returns their result unchanged — no caching, no recomputation, no second code path that could diverge (research.md's decision, FR-003/SC-003). Note in the docstring that `snapshot_log` currently exposes no by-id reader, so this module filters the history list rather than adding a function to Phase 4 (keeping this feature read-only over Phase 4, per the Assumptions).
- [X] T023 [US2] Create `backend/app/audit/router.py`: `GET /history/{entity_type}/{entity_id}` (query params `page`, `page_size`, `stage`, `start_date`, `end_date`; `response_model=HistoryQueryResult`) calling `query_history` — returns `200` in both the found and not-found cases, distinguished by the `found` flag per contracts/api.md (**not** a 404, which the contract deliberately does not specify for this endpoint). `GET /audit/baseline` (query param `snapshot_id`; `response_model=BaselineSnapshot`) calling `baseline_passthrough`, mapping "no baseline computed yet" and "unknown snapshot_id" to `404`. **Path note**: contracts/api.md names this `GET /baseline`, but Phase 4's router already owns the `/baseline` prefix on the same app — registering a duplicate would let FastAPI silently serve whichever router was included first, and the resulting endpoint would depend on include order rather than intent. It is mounted at `/audit/baseline` instead, with the deviation recorded here and in T027's contract update. Expose no write endpoint of any kind (FR-009). Depends on T021, T022.
- [X] T024 [US2] Wire the new router into `backend/app/main.py`: import `audit_router` from `app.audit.router`, add it to the `app.include_router` loop, and update the trailing comment (which currently says "ingestion, simulation, audit" are still placeholders) to drop `audit` and note that `ingestion`/`simulation` remain retired/unimplemented. Depends on T023.
- [X] T025 [P] [US2] Create `backend/tests/audit/test_baseline_parity.py` (SC-003): writes a fixture `BaselineSnapshot` via Phase 4's own `snapshot_log.write_baseline_snapshot`, then asserts `audit`'s baseline endpoint and Phase 4's `GET /baseline` return identical content for the same snapshot; adds a by-id case asserting a specific historical snapshot is retrievable (US2 acceptance scenario 3) and an unknown-id case returning `404`. Depends on T022, T023.
- [X] T026 [US2] Create `backend/tests/audit/test_history_endpoint.py` (SC-006, FR-007): end-to-end `TestClient` test mirroring `backend/tests/revalidation/test_router_revalidation_flow.py`'s pattern — seeds the lifecycle fixture, asserts `GET /history/incident/{id}` returns `200` with `found: true` and the full ordered trail; asserts an unknown id returns `200` with `found: false` and `entries: []`; asserts a `stage` filter returns only that stage; asserts a `start_date`/`end_date` filter returns only in-range entries; asserts pagination returns the right slice with a correct unpaginated `total_count`, and that a page past the end still reports `found: true` (the FR-006 distinction from T021). Depends on T017, T023.

**Checkpoint**: Both read endpoints work end-to-end over real data, with the baseline structurally guaranteed to match Phase 4's.

---

## Phase 5: User Story 3 - Guarantee audit completeness (Priority: P2)

**Goal**: Make it impossible for a new or modified pipeline stage to silently skip auditing — enforced by an executable failing test, not documentation.

**Independent Test**: `test_registry_completeness.py` passes against the real wired modules, and deliberately fails when a mock module is added to the expected list without any audit source.

### Implementation for User Story 3

- [X] T027 [US3] Create `backend/tests/audit/test_registry_completeness.py` (SC-005, FR-008): drives the lifecycle fixture plus the batch-module call sites so every expected module has appended at least one entry, then asserts `check_registry_completeness(db)` reports `registered=True` for **every** entry in `EXPECTED_AUDITED_MODULES`. Add the negative case the spec actually demands: monkeypatch `EXPECTED_AUDITED_MODULES` to include a `"mock_new_stage"` module with no audit source and assert the check reports it unregistered — proving the guarantee is enforced rather than vacuous. Include an explicit assertion that `"ingestion"` is **not** in the expected list, with a comment pointing at Pre-Implementation Finding 1, so the deliberate omission is visible in the test rather than looking like an oversight. Depends on T007, T009-T016.
- [X] T028 [US3] Update `specs/016-audit-history/contracts/api.md` to record the `/audit/baseline` path (T023's documented deviation from the originally-specified `/baseline`, forced by Phase 4's existing ownership of that prefix), and to note that `GET /history` returns `200` with `found: false` rather than `404` for an unknown entity. Depends on T023.

**Checkpoint**: All three user stories functional; the completeness guarantee is executable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across the whole feature and the phases it touched.

- [X] T029 [P] Run `pytest backend/tests/audit/ -v`, then the **full** backend suite (`pytest backend/tests/ -q`). The full run matters more than usual here: this feature adds call sites inside eight already-complete, already-passing phases, so a regression would most likely surface in *their* tests, not audit's. Fix any regressions found.
- [X] T030 [P] Manually validate every command in `specs/016-audit-history/quickstart.md` against a locally running `uvicorn app.main:app`, and update quickstart.md wherever it no longer matches what was built — specifically its `/baseline` `diff` example (now `/audit/baseline`) and its claim that `test_registry_completeness.py` "registers a mock new pipeline-stage module", which T027 implements via monkeypatching the expected list.
- [X] T031 Update `MVP_CONTEXT.md`'s Phase 16 entry, Section 9.4's status table row for `016-audit-history`, and Section 9.5's task 6 to reflect completion, and add a v5 changelog entry in Section 8 recording this feature plus its three documented deviations (no `ingestion` audit source; `data_engineering` added to the registry; `/audit/baseline` path). Do **not** rewrite earlier changelog entries — they are historical records.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **BLOCKS all user stories** — nothing can append or query without the table, schemas, and `append_entry`.
- **User Story 1 (Phase 3)**: Depends on Foundational. Independent of US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational for the schemas/table; its *tests* (T026) additionally depend on US1's call-site wiring (T017's fixture) to have a trail worth querying. T021-T025 can be written before US1 lands.
- **User Story 3 (Phase 5)**: Depends on Foundational (T007) and on US1's wiring (T009-T016) being complete, since the positive half of the completeness check asserts every real module registered.
- **Polish (Phase 6)**: Depends on all three stories.

### User Story Dependencies

- **US1 (P1)**: The MVP. No dependency on US2/US3.
- **US2 (P1)**: Implementation is independent of US1; only its end-to-end test needs US1's data.
- **US3 (P2)**: Genuinely depends on US1 — a completeness check over unwired modules would fail by construction.

### Within Each User Story

- T009 is not marked [P]: it touches `incidents/service.py`, and T010/T011 touch `hitl/` — different files, but T009 establishes the entry-shape conventions (entity scoping, the no-entry-on-failed-investigation rule) the others follow, so it should land first.
- T010-T013 and T015-T016 are [P] — different modules, no shared files.
- T014 is not [P]: it changes both `cleaning_service.py` and `data_engineering/router.py`.
- T018/T019 depend on the wiring tasks; T019 depends on T018's fixture usage pattern.

### Parallel Opportunities

- Setup: T001-T003 all [P].
- Foundational: T004 and T005 [P] (different files); T007 and T008 both depend on them.
- US1: T010, T011, T012, T013 in parallel after T009; T015 and T016 in parallel with those.
- US2: T022 [P] with T021; T025 [P] once T023 lands.
- Polish: T029 and T030 [P].

---

## Parallel Example: Phase 3 (User Story 1 call-site wiring)

```bash
# After T009 sets the conventions, wire the remaining modules together:
Task: "Wire append_entry into backend/app/hitl/accept_service.py and reject_service.py"
Task: "Wire append_entry into backend/app/remediation/remediation_service.py"
Task: "Wire append_entry into backend/app/revalidation/revalidation_service.py"
Task: "Wire append_entry into backend/app/quality/scoring_service.py and router.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup.
2. Phase 2: Foundational (CRITICAL — blocks everything).
3. Phase 3: User Story 1 — every stage appends a real, referencing, ordered entry.
4. **STOP and VALIDATE**: `pytest backend/tests/audit/ backend/tests/ -q` — the trail is complete and provenance holds, even before any endpoint exists.

### Incremental Delivery

1. Setup + Foundational → table, schemas, registry, `append_entry`.
2. Add US1 → the audit trail is genuinely populated across all ten modules → MVP.
3. Add US2 → `/history` and `/audit/baseline` expose it.
4. Add US3 → the completeness guarantee becomes executable and regression-proof.
5. Polish → full-suite regression pass (critical — eight other phases were touched), quickstart validation, MVP_CONTEXT.md sync.

### Parallel Team Strategy

Once Foundational is done: Developer A takes US1's wiring (T009-T016), Developer B takes US2's services/endpoints (T021-T025) against the schemas alone, Developer C prepares US3's test (T027) and waits on A. The only real coordination point is `_fixtures.py` (T017), which both A's and B's tests consume.

---

## Notes

- **[P] tasks** = different files, no dependencies. **[Story] label** maps each task to its user story.
- `append_entry` deliberately does **not** commit — it joins the caller's transaction so an audit entry can never outlive a rolled-back write. Every call site must therefore already be inside a transaction that commits (all ten are).
- This feature adds **no new write path for pipeline facts** — `audit_logs` holds only references (`source_record_id`), never copies (FR-001, FR-009, SC-002).
- Three deviations from the design docs are recorded above rather than silently applied: no `ingestion` audit source (retired module), `data_engineering` added to the registry (FR-001/US1-AS1 require it), and `/audit/baseline` instead of `/baseline` (Phase 4 owns that prefix).
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
