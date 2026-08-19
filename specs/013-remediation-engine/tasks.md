---

description: "Task list template for feature implementation"
---

# Tasks: Remediation Engine

**Input**: Design documents from `/specs/013-remediation-engine/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md (all present)

**Tests**: plan.md's Testing section and Project Structure explicitly name required test files mapped to specific success criteria (SC-002, SC-004, SC-005, SC-006) and FR-010 — these are included as required tasks, not optional additions.

**Organization**: Tasks are grouped by user story (spec.md's US1/US2/US3, all Priority P1) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Backend-only module per plan.md's Project Structure: `backend/app/remediation/` (module code), `backend/tests/remediation/` (tests).

## Design note carried into every task below

Phase 12's `Incident` model (`backend/app/incidents/models.py`) has no persisted "affected claims" list, and no `claims` table exists yet (`backend/app/models/claims.py` is still a Phase-0 placeholder). Per user decision, the caller supplies the affected claims — each claim's `claim_id` plus the specific field values handlers need (duplicate flag, column values for status-mapping/imputation preconditions) — explicitly in the `POST /remediation/{incident_id}/run` request body. This matches the established pattern elsewhere in this codebase (`EvidenceBundle` in `incidents/schemas.py`: "neither `incidents` nor `hitl` can autonomously fetch... evidence from disk, so the caller supplies it explicitly"). Because remediation only ever iterates over the claims present in that request, FR-003's "never touch a claim outside the documented affected set" is structurally guaranteed, not something requiring a separate runtime check.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Clear the Phase-0 scaffold and prepare the module skeleton for this feature's actual structure.

- [X] T001 [P] Delete the mismatched Phase-0 placeholder stub files under `backend/app/remediation/` that don't match this feature's plan.md file structure: `backend/app/remediation/duplicate_handler.py`, `backend/app/remediation/engine.py`, `backend/app/remediation/invalid_status_handler.py`, `backend/app/remediation/manual_action.py`, `backend/app/remediation/missing_value_handler.py`. Keep `backend/app/remediation/__init__.py` (rewritten in T005).
- [X] T002 [P] Add `pyyaml` to `backend/requirements.txt` (already transitively available via `great_expectations` in the dev environment, but `remediation_service.py`/`precedence.py` will import it directly, so pin it explicitly as a direct dependency).
- [X] T003 [P] Create the `backend/app/remediation/config/` directory (holds the three versioned rule-table YAML files added in Phase 2).
- [X] T004 [P] Create `backend/tests/remediation/__init__.py` (empty — mirrors the `backend/tests/hitl/` and `backend/tests/incidents/` package convention so pytest discovers the directory as a package).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schemas, ORM tables, error types, and the three versioned rule tables that every user story's handlers/service/tests depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 [P] Rewrite the module docstring in `backend/app/remediation/__init__.py`: remove the "STATUS: not implemented yet" placeholder text and replace it with a one-paragraph description matching plan.md's Summary (three deterministic handlers driven by versioned config, gated on Phase 12's "accepted" status, zero LLM involvement at execution).
- [X] T006 [P] Create `backend/app/remediation/errors.py` with `NotAcceptedIncidentError(ValueError)` — raised when remediation is attempted against an incident whose status is not `"accepted"` (spec FR-002), mapped to `409 Conflict` in the router. Mirror the docstring style of `backend/app/hitl/errors.py`'s `InvalidTransitionError`.
- [X] T007 [P] Create `backend/app/remediation/schemas.py` with the pydantic models: `HandlerType(str, Enum)` (`duplicate_flagging`, `approved_imputation`, `approved_status_mapping`); `ReasonCode(str, Enum)` (`no_matching_rule`, `precondition_invalidated`, `concurrent_incident_conflict`); `RemediationRule` (`rule_id: str`, `handler_type: HandlerType`, `precondition: dict`, `to_value: str | float | None`, `precedence_rank: int`, `rule_table_version: str`); `AffectedClaimInput` (`claim_id: str`, `is_duplicate: bool = False`, `fields: dict[str, str | float | None] = {}`) — the caller-supplied per-claim data described in the Design note above; `RemediationRunRequest` (`affected_claims: list[AffectedClaimInput]`) — the `POST /remediation/{incident_id}/run` request body; `RemediationAction` (`action_id: str`, `incident_id: str`, `claim_id: str`, `rule_id: str`, `before_value: str | None`, `after_value: str | None`, `applied_at: datetime`, `model_config = ConfigDict(from_attributes=True)`); `ManualActionRequired` (`record_id: str`, `incident_id: str`, `claim_id: str`, `description: str`, `reason_code: ReasonCode`, `flagged_at: datetime`, `from_attributes=True`); `RemediationRun` (`run_id: str`, `incident_id: str`, `actions: list[RemediationAction]`, `manual_actions_required: list[ManualActionRequired]`, `started_at: datetime`, `completed_at: datetime | None`).
- [X] T008 [P] Create `backend/app/remediation/models.py` with SQLAlchemy ORM classes (mirroring `backend/app/hitl/models.py`'s append-only style): `RemediationRun` (`run_id: str` PK, `incident_id: str` indexed FK to `incidents.incident_id`, `started_at: datetime`, `completed_at: datetime | None`); `RemediationAction` (`action_id: str` PK, `run_id: str` indexed FK to the run table, `incident_id: str` indexed, `claim_id: str` indexed, `rule_id: str`, `before_value: str | None`, `after_value: str | None`, `applied_at: datetime`, plus `UniqueConstraint("incident_id", "claim_id", "rule_id")` — the idempotency key from data-model.md); `ManualActionRequired` (`record_id: str` PK, `run_id: str` indexed FK, `incident_id: str` indexed, `claim_id: str` indexed, `description: str`, `reason_code: str`, `flagged_at: datetime`).
- [X] T009 Update `backend/tests/_db_fixtures.py` to add `import app.remediation.models  # noqa: F401` alongside the existing `app.hitl.models`/`app.incidents.models` imports, so the three new tables register on `Base.metadata` before `init_db()` runs in every test using `make_test_session()`. Depends on T008.
- [X] T010 [P] Create `backend/app/remediation/config/duplicate_flagging_rules.yaml`: top-level `version: "1.0.0"`, one illustrative rule (`rule_id: dup-001`, `precondition: {}`, `precedence_rank: 1`) with a comment explaining that duplicate flagging needs no field-level precondition beyond Phase 2's `is_duplicate` flag on the affected claim.
- [X] T011 [P] Create `backend/app/remediation/config/status_mapping_rules.yaml`: top-level `version: "1.0.0"`, one illustrative rule (`rule_id: stat-001`, `precondition: {column: "PTNT_DSCHRG_STUS_CD", from_value: "01"}`, `to_value: "1"`, `precedence_rank: 2`), documented in a YAML comment as a leading-zero formatting-variant correction (not a clinical equivalence claim), noting that real production entries require the config-management/clinical review the spec's Assumptions section places outside this feature's scope.
- [X] T012 [P] Create `backend/app/remediation/config/imputation_rules.yaml`: top-level `version: "1.0.0"`, one illustrative rule (`rule_id: imp-001`, `precondition: {column: "ADMTG_DGNS_CD", condition: "missing"}`, `to_value: "UNKNOWN"`, `precedence_rank: 3`), documented in a YAML comment as a narrow, pre-approved sentinel-value policy — never a fabricated/guessed clinical value — with the same review-required note as T011.

**Checkpoint**: Foundation ready — schemas, ORM tables, and rule-table config all exist; user story implementation can now begin.

---

## Phase 3: User Story 1 - Apply only pre-approved, deterministic remediation actions (Priority: P1) 🎯 MVP

**Goal**: Implement the three deterministic handlers and the precedence logic that selects among them, with zero LLM involvement at execution time.

**Independent Test**: Call each handler's `matches`/`apply` functions and `precedence.select_rule` directly against `AffectedClaimInput` fixtures matching Phase 2's duplicate-detection output, an approved-imputation condition, and an approved-status-mapping condition — confirm exactly the right handler is selected and applied per case, and confirm (via static import-graph inspection) that no file under `backend/app/remediation/` imports Phase 11's LLM client.

### Implementation for User Story 1

- [X] T013 [P] [US1] Create `backend/app/remediation/duplicate_handler.py` with `matches(claim: AffectedClaimInput, rule: RemediationRule) -> bool` (returns `claim.is_duplicate is True`), `verify_precondition = matches` (re-verification at execution time re-runs the identical check, FR-006), and `apply(claim, rule) -> tuple[str | None, str]` (returns `(None, "DUPLICATE_FLAGGED")` — a fixed marker, since flagging doesn't invent a value).
- [X] T014 [P] [US1] Create `backend/app/remediation/status_mapping_handler.py` with `matches(claim, rule) -> bool` (reads `rule.precondition["column"]`/`rule.precondition["from_value"]` and compares against `claim.fields.get(column)`), `verify_precondition = matches`, and `apply(claim, rule) -> tuple[str, str]` (returns `(rule.precondition["from_value"], rule.to_value)`).
- [X] T015 [P] [US1] Create `backend/app/remediation/imputation_handler.py` with `matches(claim, rule) -> bool` (returns `True` when `claim.fields.get(rule.precondition["column"])` is `None`/missing), `verify_precondition = matches`, and `apply(claim, rule) -> tuple[None, str]` (returns `(None, rule.to_value)`).
- [X] T016 [US1] Create `backend/app/remediation/precedence.py` with: `HANDLER_MODULES: dict[HandlerType, module]` mapping each `HandlerType` to its handler module (T013–T015); `load_rule_tables() -> dict[HandlerType, list[RemediationRule]]` that reads the three YAML files under `backend/app/remediation/config/` via `yaml.safe_load`, parses each `rules` entry into a `RemediationRule` (attaching the file's top-level `version` as `rule_table_version`), and returns them keyed by `HandlerType`; `select_rule(claim: AffectedClaimInput, rule_tables) -> RemediationRule | None` that collects every rule across all three tables whose handler's `matches(claim, rule)` returns `True`, then returns the one with the lowest `precedence_rank` (or `None` if no candidates) — implements FR-007's documented, invasiveness-based precedence order (duplicate flagging → status mapping → imputation) from research.md. Depends on T007, T010–T015.
- [X] T017 [P] [US1] Create `backend/tests/remediation/_fixtures.py` (no `test_` prefix, not collected as a test module) with `make_claim(claim_id: str, is_duplicate: bool = False, fields: dict | None = None) -> AffectedClaimInput`, a shared builder for the remaining test files.
- [X] T018 [US1] Create `backend/tests/remediation/test_handler_selection.py` covering spec.md US1 Acceptance Scenarios 1–3 and FR-007: a claim with `is_duplicate=True` selects the `dup-001` rule via `precedence.select_rule`; a claim missing `ADMTG_DGNS_CD` selects `imp-001`; a claim with `PTNT_DSCHRG_STUS_CD="01"` selects `stat-001`; and a claim satisfying both the duplicate-flagging and status-mapping preconditions simultaneously selects `dup-001` (lower `precedence_rank` wins). Depends on T016, T017.
- [X] T019 [P] [US1] Create `backend/tests/remediation/test_no_llm_dependency.py` (spec SC-004, US1 Acceptance Scenario 4): a static import-graph check — parse each `backend/app/remediation/*.py` file's AST (or inspect `sys.modules`/`importlib`) and assert none imports `app.llm.mistral_client` or any other Phase 11 LLM-client symbol. Depends on T013–T016.

**Checkpoint**: At this point, handler selection and application are fully functional and independently testable — no LLM call anywhere in the remediation execution path.

---

## Phase 4: User Story 2 - Escalate anything unhandled as "Manual Action Required" (Priority: P1)

**Goal**: Any affected-claim condition matching no approved handler, or whose precondition no longer holds at execution time, is explicitly marked "Manual Action Required" — without blocking remediation of other, handleable conditions.

**Independent Test**: Call the claim-processing function directly with a claim matching no rule at all, and separately with a batch mixing matching and non-matching claims — confirm the unmatched claim(s) produce an explicit `ManualActionRequired` record while matched claims still produce their `RemediationAction`.

### Implementation for User Story 2

- [X] T020 [P] [US2] Create `backend/app/remediation/manual_handler.py` with `flag_manual_action(incident_id: str, claim_id: str, reason_code: ReasonCode, description: str) -> ManualActionRequired` — a factory that generates `record_id=str(uuid4())` and `flagged_at=datetime.now(timezone.utc)`. Depends on T007.
- [X] T021 [US2] Create `backend/app/remediation/remediation_service.py` with `_process_claim(claim: AffectedClaimInput, rule_tables: dict, incident_id: str) -> RemediationAction | ManualActionRequired`: calls `precedence.select_rule(claim, rule_tables)`; if `None`, returns `manual_handler.flag_manual_action(incident_id, claim.claim_id, ReasonCode.no_matching_rule, f"No approved handler matches the current condition for claim {claim.claim_id}.")`; otherwise immediately re-verifies the selected rule's handler `verify_precondition(claim, rule)` before applying (FR-006) — if it no longer holds, returns `manual_handler.flag_manual_action(incident_id, claim.claim_id, ReasonCode.precondition_invalidated, f"Handler {rule.rule_id} was selected for claim {claim.claim_id} but its precondition no longer held at execution time.")`; otherwise calls `handler.apply(claim, rule)` and returns a `RemediationAction` (`action_id=str(uuid4())`, `before_value`/`after_value` from `apply()`, `applied_at=now`). This function does not touch the DB or the accepted-status gate — those are added by `run_remediation` in Phase 5. Depends on T016, T020.
- [X] T022 [P] [US2] Create `backend/tests/remediation/test_manual_action_fallback.py` covering spec.md US2 Acceptance Scenarios 1–2: a claim matching no rule produces `ManualActionRequired(reason_code=no_matching_rule)` with a description naming the claim; a batch of claims mixing matching and non-matching conditions, run through `_process_claim` per claim, produces `RemediationAction` for the matching ones and `ManualActionRequired` for the rest, with neither blocking the other. Depends on T021.
- [X] T023 [P] [US2] Create `backend/tests/remediation/test_precondition_revalidation.py` (spec SC-006): build a claim whose fields initially satisfy the status-mapping (or imputation) rule's precondition, confirm `precedence.select_rule` selects it, then mutate the claim's fields so the precondition no longer holds before calling `_process_claim` again on the same claim/rule_tables — assert the result is `ManualActionRequired(reason_code=precondition_invalidated)`, never an incorrectly-applied `RemediationAction`. Depends on T021.

**Checkpoint**: At this point, every affected-claim condition — handled or not — produces an explicit, traceable outcome from `_process_claim`.

---

## Phase 5: User Story 3 - Remediate only accepted incidents, and only affected claims (Priority: P1)

**Goal**: Wire the handler/manual-fallback layer into the full orchestrator: refuse non-"accepted" incidents, scope strictly to the caller-supplied affected claims, detect cross-incident claim conflicts, persist results idempotently, and expose it over HTTP.

**Independent Test**: Attempt to trigger remediation on a non-accepted incident and confirm it's refused with `409`; run remediation twice on the same accepted incident and confirm no duplicate `RemediationAction` rows; run remediation on two accepted incidents sharing one affected claim and confirm the second run flags a conflict instead of double-applying.

### Implementation for User Story 3

- [X] T024 [US3] Extend `backend/app/remediation/remediation_service.py` with `run_remediation(db: Session, incident_id: str, affected_claims: list[AffectedClaimInput]) -> RemediationRun`: looks up the incident via `app.incidents.service.get_incident_orm`, raising `LookupError` if unknown; raises `NotAcceptedIncidentError` if `incident.status != "accepted"` (FR-002, SC-002); creates a `RemediationRun` ORM row (`run_id=str(uuid4())`, `started_at=now`); for each affected claim — first checks for a conflicting `RemediationAction` row from a *different* `incident_id` on the same `claim_id` (FR-010) and, if found, persists `ManualActionRequired(reason_code=concurrent_incident_conflict)` instead of processing further; otherwise calls `precedence.select_rule`, and if a rule is selected, checks for an existing `RemediationAction` row keyed on `(incident_id, claim_id, rule_id)` (FR-008/SC-005 idempotency) — if found, reuses it instead of re-applying; otherwise runs `_process_claim`'s precondition-reverify-and-apply-or-manual logic and persists the resulting row tagged with the new `run_id`; sets `completed_at=now`, commits, and returns the assembled `RemediationRun` pydantic model (every affected claim appears in exactly one of `actions`/`manual_actions_required`, FR-009/SC-003). Depends on T006, T008, T009, T021.
- [X] T025 [US3] Add `list_remediation_runs(db: Session, incident_id: str) -> list[RemediationRun]` to `backend/app/remediation/remediation_service.py`: queries all `RemediationRun` ORM rows for `incident_id` ordered by `started_at`, and for each assembles its `RemediationAction`/`ManualActionRequired` rows filtered by `run_id`; returns `[]` if no runs exist. Depends on T024.
- [X] T026 [US3] Create `backend/app/remediation/router.py`: `POST /remediation/{incident_id}/run` (body: `RemediationRunRequest`, `response_model=RemediationRun`) calling `run_remediation`, mapping `LookupError`→`404` and `NotAcceptedIncidentError`→`409` (per contracts/api.md); `GET /remediation/{incident_id}` (`response_model=list[RemediationRun]`) calling `list_remediation_runs`, raising `404` when the result is empty. Depends on T024, T025.
- [X] T027 [US3] Wire the new router into `backend/app/main.py`: import `remediation_router` from `app.remediation.router`, add it to the `app.include_router` loop, and remove `remediation` from the trailing comment listing modules whose routers are still placeholders. Depends on T026.
- [X] T028 [P] [US3] Create `backend/tests/remediation/test_accepted_gate.py` (spec SC-002, US3 Acceptance Scenario 1): `run_remediation` (or `POST /remediation/{id}/run`) against incidents in `pending_investigation`/`ready_for_review`/`rejected` status is refused (`NotAcceptedIncidentError`/`409`) with zero `RemediationAction` rows created; the same call against an `accepted` incident succeeds. Depends on T024 (or T026 for the HTTP variant).
- [X] T029 [P] [US3] Create `backend/tests/remediation/test_idempotency.py` (spec SC-005, Edge Cases bullet 3): run remediation twice on the same accepted incident with the same affected claims and assert the second run produces zero duplicate `RemediationAction` rows for already-completed `(incident_id, claim_id, rule_id)` triples, while still completing any claims left unresolved by a simulated partial first run. Depends on T024.
- [X] T030 [P] [US3] Create `backend/tests/remediation/test_concurrent_claim_conflict.py` (spec FR-010, Edge Cases bullet 5): create two accepted incidents that both list the same `claim_id` as affected; run remediation for the first incident (the claim gets a `RemediationAction`), then run remediation for the second incident and assert that same claim now receives `ManualActionRequired(reason_code=concurrent_incident_conflict)` instead of a second action, while any other claims unique to the second incident remediate normally. Depends on T024.
- [X] T031 [P] [US3] Create `backend/tests/remediation/test_router_remediation_flow.py`: an end-to-end `TestClient` test (mirroring `backend/tests/hitl/test_router_hitl_flow.py`'s pattern) that creates an incident via `POST /incidents`, accepts it via `POST /hitl/{id}/accept`, then POSTs a `RemediationRunRequest` with a mix of duplicate/status-mapping/imputation/unhandled claims to `POST /remediation/{id}/run` and asserts every affected claim appears in the response's `actions` or `manual_actions_required` (SC-003); `GET /remediation/{id}` then returns that same run in its history; `GET` on an incident with no runs yet returns `404`. Depends on T026, T027.

**Checkpoint**: All three user stories are now independently functional and wired end-to-end over HTTP.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across the whole feature.

- [X] T032 [P] Run `pytest backend/tests/remediation/` (and the full backend suite) and fix any regressions surfaced by cross-file integration between the phases above.
- [X] T033 [P] Manually validate every curl example in `specs/013-remediation-engine/quickstart.md` against a locally running `uvicorn app.main:app` instance (accepted-gate `409`, idempotent re-run producing no duplicate actions, `GET` history), confirming they match this implementation's actual behavior.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion.
  - US1 (Phase 3) has no dependency on US2/US3 and can be built/tested first.
  - US2 (Phase 4) depends on US1's `precedence.py` (T016) to build `_process_claim`.
  - US3 (Phase 5) depends on US2's `_process_claim` (T021) to build the full `run_remediation` orchestrator — so while all three stories are P1, they build in this sequence in practice (US1 → US2 → US3), not in parallel, because each orchestrator layer wraps the previous one.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Handlers/config before precedence selection.
- Precedence selection before the manual-fallback wrapper (`_process_claim`).
- `_process_claim` before the full gated/persisted orchestrator (`run_remediation`).
- Service logic before the router; router before `main.py` wiring.
- Tests for a story follow that story's implementation tasks (tests are listed after implementation here since this feature's tests verify already-built behavior per plan.md's Testing section, rather than a TDD red-green flow).

### Parallel Opportunities

- All Setup tasks (T001–T004) can run in parallel.
- Within Foundational, T005–T008 (four independent new/rewritten files) can run in parallel; T010–T012 (three independent YAML files) can run in parallel with each other and with T005–T008. T009 depends on T008.
- Within US1, T013–T015 (the three handlers) can run in parallel; T017 can run in parallel with T016.
- Within US2, T022 and T023 can run in parallel once T021 is done.
- Within US3, T028–T031 (four independent test files) can run in parallel once T024–T027 are done.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch independent foundational files together:
Task: "Create backend/app/remediation/errors.py with NotAcceptedIncidentError"
Task: "Create backend/app/remediation/schemas.py with RemediationRule/RemediationAction/etc."
Task: "Create backend/app/remediation/models.py with RemediationRun/RemediationAction/ManualActionRequired ORM tables"
Task: "Create backend/app/remediation/config/duplicate_flagging_rules.yaml"
Task: "Create backend/app/remediation/config/status_mapping_rules.yaml"
Task: "Create backend/app/remediation/config/imputation_rules.yaml"
```

## Parallel Example: User Story 1

```bash
# Launch the three handlers together (each is a separate file, no shared state):
Task: "Implement backend/app/remediation/duplicate_handler.py"
Task: "Implement backend/app/remediation/status_mapping_handler.py"
Task: "Implement backend/app/remediation/imputation_handler.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1 — the three deterministic handlers, precedence selection, and the no-LLM-dependency guarantee.
4. **STOP and VALIDATE**: `pytest backend/tests/remediation/test_handler_selection.py backend/tests/remediation/test_no_llm_dependency.py`.

### Incremental Delivery

1. Setup + Foundational → schemas/ORM/config ready.
2. US1 → handler selection is correct and LLM-free (testable standalone).
3. US2 → unhandled conditions are never silently skipped (testable standalone via `_process_claim`).
4. US3 → the safety boundary (accepted-only, scoped, idempotent, conflict-aware) wraps US1+US2 into the real HTTP-facing engine — deploy/demo here.

### Notes

- Because US2's `_process_claim` and US3's `run_remediation` each wrap the previous story's logic, "independently testable" for US2/US3 means testable via direct function calls against fixtures (per each phase's Independent Test above), not that US3 can be built before US1/US2 exist.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
- Avoid: inline magic values in handlers (all precondition/target values come from the YAML rule tables per FR-001), same-file conflicts between parallel tasks, and any import from `backend/app/remediation/` into `app.llm.mistral_client` (FR-005).
