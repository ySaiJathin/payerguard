---

description: "Task list for Incident Management & Human-in-the-Loop"
---

# Tasks: Incident Management & Human-in-the-Loop

**Input**: Design documents from `/specs/012-incident-management-hitl/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md — all present. Phase 10 (severity/business-impact/priority scoring) and Phase 11 (LLM investigation) already exist as the evidence/investigation sources this feature orchestrates. **This is the first feature to use real relational persistence** (SQLAlchemy models + a DB session) instead of the file-based JSON/CSV pattern every prior phase used — per plan.md's Storage section, incident lifecycle (multiple state transitions over time, linked feedback history) is a poor fit for flat files. Confirmed with the user: real SQLAlchemy models now, tests run against an isolated in-memory SQLite engine (no Docker/Postgres needed), production targets `DATABASE_URL` from `.env`. No Alembic migration scaffolding is added in this feature — tables are created via `Base.metadata.create_all()` at app startup, which is sufficient for the MVU; a dedicated migrations feature can formalize Alembic later without changing these models.

**Evidence-input design note**: like Phases 10/11, `POST /incidents` and `POST /hitl/{id}/recalculate` are not able to autonomously fetch a window's Phase 3/4/7/9 evidence from disk — no unified "evidence resolver" exists yet anywhere in the codebase, and building one is out of this feature's scope. Both endpoints therefore accept the same already-resolved evidence bundle shape Phase 10's `/risk/score` accepts (quality check bands, anomaly percentile, affected-claim data, risk score, baseline percentiles, weights) as request fields beyond quickstart.md's bare `{"window_id": "window-42"}` example — mirroring the additive-field pattern used in 010/011's own router request schemas.

**Tests**: Included — plan.md's Testing section names 5 test files matching the spec's Success Criteria; more are added for the same reason 008-011's tasks.md added extras: router-level and creation-time-investigation-failure paths each need their own machine-checkable assertion.

**Organization**: Tasks are grouped by user story. All three stories are P1. US1 (incident CRUD) is the foundation everything else acts on. US2 (accept/reject) depends on US1 existing. US3 (feedback + recalculation) depends on US2's reject path. This is a genuine linear dependency chain, unlike 009/010/011's more parallel structures — reflected in the phase ordering below.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (incident CRUD), US2 (accept/reject state machine), US3 (feedback + recalculation)

## Path Conventions

Backend modules: `backend/app/incidents/` and `backend/app/hitl/` (existing Phase-0 scaffolds, filled in for real), plus `backend/app/core/config.py` and `backend/app/core/database.py` (first real use of the DB infra scaffolding). Tests: `backend/tests/incidents/`, `backend/tests/hitl/`.

**Note on existing stub files**: `incidents/service.py`, `incidents/router.py`, and `hitl/router.py` already have names matching plan.md exactly — overwritten in place. `hitl/accept.py`/`hitl/reject.py` are superseded by plan.md's `accept_service.py`/`reject_service.py` naming and deleted. `backend/app/models/incidents.py` and `backend/app/models/feedback.py` (the earlier centralized-models-directory scaffold) are superseded by this feature's own `incidents/models.py`/`hitl/models.py` (one models file per owning module, matching constitution Principle VI) and deleted. `backend/tests/hitl/test_placeholder.py` is superseded by this feature's real test suite and deleted. Other `backend/app/models/*.py` stubs (claims, quality, baseline, features, risk, anomaly, windows, audit) belong to other phases and are untouched.

---

## Phase 1: Setup

**Purpose**: Real DB infrastructure (first use in this repo) and scaffold alignment.

- [x] T001 Implement `backend/app/core/config.py`: `Settings(BaseSettings)` (pydantic-settings) reading `DATABASE_URL`, `MISTRAL_API_KEY`, `MISTRAL_MODEL`, `ENVIRONMENT`, `LOG_LEVEL`, `INGESTION_WATCH_DIR` from `.env` (matching `.env.example` exactly), with `DATABASE_URL` defaulting to a local sqlite file so the app boots without a configured Postgres; `get_settings()` cached accessor
- [x] T002 Implement `backend/app/core/database.py`: `Base` (SQLAlchemy `DeclarativeBase`), a default `engine`/`SessionLocal` bound to `get_settings().database_url` (with `connect_args={"check_same_thread": False}` only for sqlite URLs), `get_db()` FastAPI dependency (yields a session, closes it after), `init_db(engine=None)` (`Base.metadata.create_all`) — callable at app startup and independently by tests against an isolated engine
- [x] T003 Delete the placeholder `backend/app/models/incidents.py`, `backend/app/models/feedback.py`, `backend/app/hitl/accept.py`, `backend/app/hitl/reject.py`, and `backend/tests/hitl/test_placeholder.py` stub files — superseded by this feature's real module files
- [x] T004 [P] Create `backend/tests/incidents/__init__.py`
- [x] T005 [P] Create `backend/tests/_db_fixtures.py` (shared, non-test-prefixed helper): `make_test_session()` — imports both `app.incidents.models` and `app.hitl.models` (so every table is registered on `Base.metadata` before creating), builds a fresh `sqlite:///:memory:` engine, calls `init_db`, and returns a bound `Session` — reused by both `tests/incidents/` and `tests/hitl/`

**Checkpoint**: DB infrastructure exists and is independently testable; module skeletons match plan.md.

---

## Phase 2: User Story 1 - Create incidents from high-priority findings and manage them (Priority: P1) 🎯 MVP

**Goal**: `Incident` CRUD backed by real Phase 10 scores and a Phase 11 investigation triggered at creation time, extensible status field, full read/list/update.

**Independent Test**: Trigger incident creation for a window/finding with real Phase 10 Priority and Phase 11 investigation data, and confirm a queryable `Incident` record exists with all of that data attached.

### Implementation for User Story 1

- [x] T006 [US1] Implement `backend/app/incidents/models.py`: SQLAlchemy `Incident` (`incident_id` PK, `window_id` indexed, `quality_score`/`anomaly_score`/`risk_score` floats, `severity_result`/`business_impact_result`/`priority_result`/`evidence_snapshot` JSON columns, `status` as a plain `String` column — not a DB-level enum, so FR-008's extensibility never needs a schema migration to add a new status value, only an update to the Python-level state machine — `current_investigation_id` nullable, `created_at`/`updated_at`)
- [x] T007 [US1] Implement `backend/app/incidents/schemas.py`: `IncidentStatus(str, Enum)` (`pending_investigation`, `ready_for_review`, `accepted`, `rejected`, `resolved`, `reopened` — the last two reserved for Phase 14, per data-model.md), `EvidenceBundle` (the shared already-resolved evidence shape: `quality_check_bands`, `anomaly_score_percentile`, `affected_claim_pct`, `affected_claims_amounts`, `risk_score`, `baseline_amount_percentiles`, `weights`), `IncidentCreate` (`window_id` + `EvidenceBundle`), `IncidentUpdate` (every field except `status` and `incident_id`, all optional), `Incident` (full read schema, `model_config = ConfigDict(from_attributes=True)` for ORM conversion)
- [x] T008 [US1] Implement `backend/app/incidents/service.py`: `create_incident(db, payload: IncidentCreate) -> Incident` — computes `SeverityResult`/`BusinessImpactResult` via Phase 10's `severity.compute_severity`/`business_impact.compute_business_impact`, `PriorityResult` via `priority.compute_priority` (propagating `MissingRiskScoreError` if `risk_score` is absent — no fabricated default, spec FR-010), builds a Phase 11 `StructuredIncidentPayload` via `payload_builder.build_payload` and calls `investigation_service.investigate`; on investigation success, persists the incident with `status="ready_for_review"` and `current_investigation_id` set, recording a `system` `IncidentStatusTransition` (`pending_investigation` → `ready_for_review`); on `MistralAPIError`/`MalformedResponseError`, still persists the incident (real Phase 10 scores exist regardless) with `status="pending_investigation"` and no transition recorded (spec Edge Cases — investigation failure doesn't block incident creation, it's reflected in status); also `get_incident(db, incident_id)`, `list_incidents(db, status=None, min_priority=None)`, `update_incident(db, incident_id, payload: IncidentUpdate)` (never touches `status` — structurally impossible since `IncidentUpdate` has no `status` field, spec contracts/api.md's Notes)
- [x] T009 [US1] Implement `backend/app/incidents/router.py`: `POST /incidents` (`201`, `422` on `MissingRiskScoreError`/`WeightConfigError`), `GET /incidents` (`status`/`min_priority` query params), `GET /incidents/{incident_id}` (`404` if missing), `PATCH /incidents/{incident_id}` (`404` if missing) per contracts/api.md, using `Depends(get_db)`
- [x] T010 [US1] Register the new `backend/app/incidents/router.py` router in `backend/app/main.py`, and call `init_db()` once at app startup (FastAPI `lifespan`), updating the "still placeholders" comment
- [x] T011 [P] [US1] `backend/tests/incidents/test_incident_crud.py`: creating an incident with a real evidence bundle produces a record carrying real Phase 10 scores and (with a mocked Phase 11 client) a linked `current_investigation_id` (SC-001); listing/reading returns real persisted data, never placeholders; `PATCH` updates a non-status field and leaves `status` untouched even if a caller tries to smuggle one in (the schema structurally has no `status` field to smuggle through); `GET /incidents/{unknown}` returns `404`
- [x] T012 [P] [US1] `backend/tests/incidents/test_investigation_failure_at_creation.py`: creating an incident with a mocked Phase 11 client that always raises `MistralAPIError` still persists the `Incident` (real Phase 10 scores intact) with `status="pending_investigation"` and `current_investigation_id=None`, rather than failing the whole creation or fabricating an investigation (spec Edge Cases)

**Checkpoint**: Incidents are creatable, readable, listable, and updatable (non-status fields), each carrying real Phase 10 scores and a best-effort Phase 11 investigation.

---

## Phase 3: User Story 2 - Accept or reject an LLM investigation's recommendation (Priority: P1)

**Goal**: An explicit, validated state machine — accept/reject only ever succeed from `ready_for_review`, every invalid transition (double-accept, reject-after-accept, accept-a-rejected-incident) is rejected with a clear `409`, never silently allowed.

**Independent Test**: Accept an incident and confirm its status transitions to a state that authorizes Phase 13; reject and confirm remediation is never authorized without an intervening accept.

### Implementation for User Story 2

- [x] T013 [US2] Implement `backend/app/hitl/state_machine.py`: `TRANSITIONS: dict[str, dict[str, set[str]]]` (`{from_status: {action: {possible_to_statuses}}}`) — `pending_investigation: {}` (no human action valid, only the `system` transition US1 already applies at creation), `ready_for_review: {accept: {accepted}, reject: {rejected}}`, `accepted: {}`, `rejected: {recalculate: {ready_for_review, pending_investigation}}` (recalculate's *actual* outcome depends on whether the new investigation succeeds — the state machine validates the *action* is legal from this status, the calling service picks which legal destination applies), `resolved: {}`, `reopened: {}` (both reserved for Phase 14); `validate_transition(current_status, action) -> set[str]` raises `InvalidTransitionError` (new, in `backend/app/hitl/errors.py`) if `action` isn't a legal move from `current_status` (research.md's explicit-transition-table decision, spec FR-007)
- [x] T014 [US2] Implement `backend/app/hitl/models.py`: SQLAlchemy `IncidentStatusTransition` (`transition_id` PK, `incident_id` FK, `from_status`/`to_status`/`action`, `reviewer_id` nullable, `occurred_at`) and `HumanFeedback` (`feedback_id` PK, `incident_id` FK, `investigation_id`, `reason_category`, `feedback_text`, `reviewer_id`, `submitted_at`) per data-model.md
- [x] T015 [US2] Implement `backend/app/hitl/schemas.py`: `ReasonCategory(str, Enum)` (`incorrect_root_cause`, `insufficient_evidence_disagreement`, `false_positive`, `other`), `AcceptRequest`/`RejectRequest` (`reviewer_id`, plus `reason_category`/`feedback_text` on reject — both required, non-empty), `HumanFeedbackRead`, `IncidentStatusTransitionRead`, `RecalculateResponse` (`incident`, `new_investigation`, `evidence_changed`)
- [x] T016 [US2] Implement `backend/app/hitl/accept_service.py`: `accept_incident(db, incident_id, reviewer_id) -> Incident` — validates the transition via `state_machine.validate_transition(incident.status, "accept")`, updates `status="accepted"`, records an `IncidentStatusTransition` (`action="accept"`, `reviewer_id` set); raises `InvalidTransitionError` for any incident not in `ready_for_review` (FR-007, SC-006)
- [x] T017 [US2] Implement `backend/app/hitl/router.py`: `POST /hitl/{incident_id}/accept` (`404` unknown incident, `409` on `InvalidTransitionError`), `POST /hitl/{incident_id}/reject` (implemented in Phase 4, wired here), `POST /hitl/{incident_id}/recalculate` (implemented in Phase 4, wired here), `GET /hitl/{incident_id}/feedback` (implemented in Phase 4, wired here) per contracts/api.md — accept path complete in this phase, the other three routes added by Phase 4's tasks editing this same file
- [x] T018 [US2] Register the new `backend/app/hitl/router.py` router in `backend/app/main.py`
- [x] T019 [P] [US2] `backend/tests/hitl/test_state_machine.py`: exhaustively covers every `(from_status, action)` pair in `TRANSITIONS` (valid ones succeed, everything else raises `InvalidTransitionError`) — double-accept, reject-after-accept, accept-a-rejected-incident-without-recalculation all explicitly covered (SC-003, SC-006, spec Acceptance Scenario 3)

**Checkpoint**: Accept transitions incidents into an authorized-for-remediation state; every invalid transition is explicitly rejected, never silently allowed.

---

## Phase 4: User Story 3 - Capture feedback on reject and support recalculation (Priority: P1)

**Goal**: Reject is impossible without feedback; every reject/feedback cycle is preserved as its own immutable record; recalculation re-invokes Phase 11 unconditionally and Phase 10 only when evidence genuinely changed, producing a new investigation without discarding history; zero automatic-retraining code path from feedback capture.

**Independent Test**: Reject with feedback text, confirm it's persisted and linked to the incident and investigation; trigger recalculation and confirm a new investigation cycle becomes available for re-review.

### Implementation for User Story 3

- [x] T020 [US3] Implement `backend/app/hitl/reject_service.py`: `reject_incident(db, incident_id, reviewer_id, reason_category, feedback_text) -> Incident` — validates the transition via `state_machine.validate_transition`, requires non-empty `feedback_text` (raises a `422`-mapped `MissingFeedbackError` otherwise — no reject without feedback is ever possible, FR-003, SC-002), updates `status="rejected"`, records the `IncidentStatusTransition` and the `HumanFeedback` (linked to the incident's `current_investigation_id`) in the same call; imports only `app.incidents`' read/update accessors and its own `hitl` module — zero import of `app.anomaly.benchmark`/`app.risk.benchmark`'s model-fitting functions (spec FR-006, SC-005, research.md's dependency-isolation decision)
- [x] T021 [US3] Implement `backend/app/hitl/recalculation_service.py`: `recalculate_incident(db, incident_id, new_evidence: EvidenceBundle | None) -> RecalculateResponse` — validates the transition via `state_machine.validate_transition(incident.status, "recalculate")`; `evidence_changed = new_evidence is not None and new_evidence != incident.evidence_snapshot` (compared as dicts — never claims evidence changed when nothing new was supplied or the new bundle is identical, spec Edge Cases); re-runs Phase 10 scoring only when `evidence_changed`, otherwise reuses the incident's stored `severity_result`/`business_impact_result`/`priority_result`; unconditionally rebuilds the Phase 11 payload and calls `investigation_service.investigate` again; on success, transitions to `ready_for_review` and updates `current_investigation_id`; on failure, transitions to `pending_investigation` (both are the two legal destinations `state_machine.py`'s table declares for the `recalculate` action) — the prior rejected `IncidentStatusTransition` and its `HumanFeedback` are never modified (FR-005, SC-004)
- [x] T022 [US3] Complete `backend/app/hitl/router.py`: `POST /hitl/{incident_id}/reject` (`422` on `MissingFeedbackError`, `409` on `InvalidTransitionError`), `POST /hitl/{incident_id}/recalculate` (`409` if not in `rejected` status), `GET /hitl/{incident_id}/feedback` (full `HumanFeedback[]` history, newest first) per contracts/api.md
- [x] T023 [P] [US3] `backend/tests/hitl/test_reject_requires_feedback.py`: reject without `feedback_text` (or whitespace-only) raises `MissingFeedbackError`/returns `422`, zero `HumanFeedback` or status-transition side effects occur (SC-002); reject with feedback persists exactly one linked `HumanFeedback` record
- [x] T024 [P] [US3] `backend/tests/hitl/test_recalculation_history.py`: recalculating a rejected incident (mocked Phase 11 client) produces a new, distinct `LLMInvestigation`/`current_investigation_id` while the prior rejected `IncidentStatusTransition` and `HumanFeedback` remain queryable and byte-identical to before (SC-004); a recalculate call with unchanged evidence reports `evidence_changed=False`, one with a genuinely different evidence bundle reports `evidence_changed=True` and updated `severity_result`/`priority_result` (research.md)
- [x] T025 [P] [US3] `backend/tests/hitl/test_no_auto_retrain.py`: statically parses (via `ast`, mirroring Phase 11's `test_write_access_boundary.py`) `backend/app/hitl/reject_service.py`'s imports and asserts none reference `app.anomaly.benchmark` or `app.risk.benchmark` (SC-005)
- [x] T026 [P] [US3] `backend/tests/hitl/test_router_hitl_flow.py`: FastAPI `TestClient` end-to-end — create (mocked LLM) → reject with feedback (`200`) → duplicate reject (`409`) → recalculate (`200`, new investigation) → accept (`200`) → duplicate accept (`409`) → `GET /hitl/{id}/feedback` returns the full preserved history

**Checkpoint**: All three user stories independently functional; Phase 13's remediation engine has a real, structurally-guarded `accepted` status to check.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T027 Run quickstart.md's manual verification steps end-to-end against a running backend, using a mocked/injected Mistral client where a real API key isn't available in this environment, and fix any drift between the contracts and the implementation
- [x] T028 [P] Review all `backend/app/incidents/*.py` and `backend/app/hitl/*.py` docstrings for consistency with the repo's per-file rationale-comment convention

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — but this is the first feature needing real DB infra, so it's larger than usual
- **User Story 1 (Phase 2)**: Depends on Setup (DB infra) — BLOCKS User Story 2 and 3 (nothing to accept/reject without an incident existing)
- **User Story 2 (Phase 3)**: Depends on User Story 1
- **User Story 3 (Phase 4)**: Depends on User Story 2 (recalculation only applies to a `rejected` incident, which only exists via US2's reject path) — unlike 009/010/011, this feature's three stories form a real linear chain, not independently parallel work
- **Polish (Phase 5)**: Depends on all three user stories

### Parallel Opportunities

- T004, T005 in parallel with each other (after T001-T003)
- T011, T012 in parallel once T006-T010 land
- T019 alongside T013-T018's completion (different file)
- T023, T024, T025, T026 in parallel once T020-T022 land
- T028 alongside T027

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup — DB infra, the one genuinely new piece of infrastructure this feature introduces)
2. Phase 2 (US1 — incident CRUD) — **this is the feature's MVP**: a durable, queryable incident record backed by real Phase 10/11 output
3. Phase 3 (US2 — accept/reject state machine) — the direct implementation of constitution Principle IV
4. Phase 4 (US3 — feedback + recalculation) — closes the human-in-the-loop cycle
5. Phase 5 (Polish)

### Incremental Delivery

Setup (DB infra) → US1 (incidents exist, MVP) → US2 (accept/reject gate remediation) → US3 (reject always captures feedback; recalculation re-reviews) → Polish.
