---

description: "Task list template for feature implementation"
---

# Tasks: Revalidation

**Input**: Design documents from `/specs/014-revalidation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md (all present)

**Tests**: plan.md's Testing section explicitly names four required test files mapped to SC-001/SC-002/SC-003/SC-006 — included as required tasks, not optional additions.

**Organization**: Tasks are grouped by user story (spec.md's US1/US2/US3, all Priority P1) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Backend-only module per plan.md's Project Structure: `backend/app/revalidation/` (module code), `backend/tests/revalidation/` (tests).

## Design notes carried into every task below

**1. Caller-supplied current claim/feature state.** Mirroring 013-remediation-engine's established precedent (no live `claims` table exists; the caller supplies current state explicitly, matching `EvidenceBundle`'s own long-standing pattern): `POST /revalidation/{incident_id}/run`'s request body carries the affected claims' current raw field values (for a genuine Phase 3 GX re-check) plus current feature vectors for Phase 7's and Phase 9's saved production models (their `.score()`/`.predict_proba()` calls need real feature-shaped input, not a pass-through score — a pass-through would fail SC-001's "genuinely invoked, not skipped" requirement). Dataset-global, non-incident-specific artifacts (Phase 1's column categories/profiling report, Phase 4's baseline snapshot) are loaded internally by `recompute_service.py`, exactly as `quality/scoring_service.run_validation()` already does — only claim/incident-specific "current state" comes from the caller.

**2. Reused-from-original fields.** `affected_claim_pct` and `baseline_amount_percentiles` describe the window's static scope and Phase 4's historical reference baseline — neither changes due to remediation — so `recompute_service.py` reads them straight from the incident's already-stored `evidence_snapshot` (set at incident creation, `backend/app/incidents/models.py`) rather than asking the caller to resupply them. Only `affected_claims_amounts` may genuinely change post-remediation (e.g. an imputed `CLM_PMT_AMT`), so the caller may optionally supply updated amounts; omitting them reuses the original.

**3. Percentile-rank conversion for anomaly.** Phase 7's saved model artifact carries a single calibrated threshold (`calibrated_thresholds["p95"]`, `backend/app/anomaly/benchmark.py`'s `CALIBRATION_PERCENTILE = 95.0`), not a full distribution. `recompute_service.py` converts the fresh raw anomaly score to the `anomaly_score_percentile` (0-1) that `severity.anomaly_magnitude_score` expects via: `percentile = min(0.95, (raw_score / p95_threshold) * 0.95)` when `raw_score < p95_threshold`, else `percentile = 0.95 + min(0.05, (raw_score - p95_threshold) / p95_threshold * 0.05)` — a documented, saturating interpolation anchored at the one real calibration point available, never a fabricated band.

**4. "Before" values reuse the incident's own stored scores** (`IncidentORM.quality_score`/`anomaly_score`/`risk_score` and the `.severity`/`.priority` fields nested in its stored `severity_result`/`priority_result` JSON) — these are the exact values Phase 10 computed at incident-creation/last-recalculation time, never re-derived or guessed.

**5. "Outstanding manual actions" (FR-007) is scoped to the specific `RemediationRun` being revalidated**: since 013's `ManualActionRequired` records are immutable/append-only with no "resolved" flag (by 013's own design), "outstanding" means "this specific `remediation_run_id` has one or more `ManualActionRequired` records" — checked via `app.remediation.remediation_service.list_remediation_runs` (013's existing, already-tested function; a cross-module function call, not a raw query into remediation's tables, matching this codebase's established modular-boundary pattern, e.g. `hitl/accept_service.py` calling `app.incidents.service.get_incident_orm`). A reviewer who manually fixes the underlying issue and re-triggers remediation (013 is idempotent/resumable) produces a *new* `remediation_run_id`, which a *new* revalidation call can then clear against.

**6. FR-009's "incomplete" `RemediationRun` gate** is `RemediationRunORM.completed_at is None` (013's own definition of a not-yet-finished run), read via the same `list_remediation_runs` call as note 5.

**7. Incident-status transition.** `resolution_criteria.py` decides `resolved`/`reopened`; `revalidation_service.py` then calls `app.hitl.state_machine.validate_transition(incident.status, "revalidation_result")` and records an `IncidentStatusTransition` row (`action="revalidation_result"`), exactly mirroring `backend/app/hitl/accept_service.py`'s own pattern — this feature extends `state_machine.TRANSITIONS["accepted"]` to add that action (spec Assumptions: Phase 12's state machine is this feature's own extension point, not a new parallel one).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Clear the Phase-0 scaffold and prepare the module skeleton for this feature's actual structure.

- [X] T001 [P] Delete the mismatched Phase-0 placeholder stub file `backend/app/revalidation/service.py` (plan.md's structure uses `recompute_service.py`/`comparison_service.py`/`resolution_criteria.py`/`revalidation_service.py` instead). Keep `backend/app/revalidation/__init__.py` and `backend/app/revalidation/router.py` (both rewritten in later tasks).
- [X] T002 [P] Create `backend/tests/revalidation/__init__.py` (empty — mirrors the `backend/tests/remediation/` package convention).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schemas, ORM table, error type, and the `hitl` state-machine extension every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Rewrite the module docstring in `backend/app/revalidation/__init__.py`: remove the "STATUS: not implemented yet" placeholder text, replace with a one-paragraph description matching plan.md's Summary (genuine Phase 3/7/9/10 recomputation against a completed `RemediationRun`, honest before/after comparison, drives the incident to Resolved/Reopened).
- [X] T004 [P] Create `backend/app/revalidation/errors.py` with `IncompleteRemediationRunError(ValueError)` (FR-009, SC-006 — the targeted `RemediationRun` is unknown or its `completed_at` is still `None`; maps to `409 Conflict`) — mirror `backend/app/hitl/errors.py`'s docstring style.
- [X] T005 [P] Create `backend/app/revalidation/schemas.py` with the pydantic models: `CurrentClaimState` (`claim_id: str`, `raw_fields: dict[str, str | float | None] = {}`); `RevalidationRunRequest` (`remediation_run_id: str`, `current_claims: list[CurrentClaimState]`, `anomaly_features: dict[str, float]`, `risk_features: dict[str, float]`, `current_affected_claims_amounts: list[float] | None = None`); `RecomputedScores` (`quality_results: list[dict]`, `quality_score: float`, `anomaly_score: float`, `risk_score: float`, `severity: float`, `business_impact: float`, `priority: float`, `severity_business_impact_priority: dict`); `RevalidationRun` (`revalidation_id: str`, `incident_id: str`, `remediation_run_id: str`, `recomputed_quality_results: list[dict]`, `recomputed_anomaly_score: float`, `recomputed_risk_score: float`, `recomputed_severity_business_impact_priority: dict`, `anomaly_model_version: str`, `risk_model_version: str`, `started_at: datetime`, `completed_at: datetime | None`, `model_config = ConfigDict(from_attributes=True)`); `BeforeAfterComparison` (`revalidation_id: str`, `quality_before: float`, `quality_after: float`, `quality_delta: float`, `anomaly_before: float`, `anomaly_after: float`, `anomaly_delta: float`, `risk_before: float`, `risk_after: float`, `risk_delta: float`, `severity_before: float`, `severity_after: float`, `severity_delta: float`, `priority_before: float`, `priority_after: float`, `priority_delta: float`, `from_attributes=True`); `ResolutionOutcome(str, Enum)` (`resolved`, `reopened`); `ResolutionDetermination` (`revalidation_id: str`, `outcome: ResolutionOutcome`, `criteria_evaluated: dict`, `blocked_by_manual_actions: bool`, `from_attributes=True`); `RevalidationRunResponse` (`revalidation_run: RevalidationRun`, `comparison: BeforeAfterComparison`, `resolution: ResolutionDetermination`, `incident_status: str`) — the `POST /revalidation/{incident_id}/run` response shape per contracts/api.md.
- [X] T006 [P] Create `backend/app/revalidation/models.py` with one SQLAlchemy ORM class `RevalidationRun` (flattening `BeforeAfterComparison`/`ResolutionDetermination`'s 1:1 fields onto the same row per data-model.md's Relationships note): `revalidation_id: str` PK, `incident_id: str` indexed FK to `incidents.incident_id`, `remediation_run_id: str` indexed FK to `remediation_runs.run_id`, `recomputed_quality_results: dict` JSON, `recomputed_anomaly_score: float`, `recomputed_risk_score: float`, `recomputed_severity_business_impact_priority: dict` JSON, `anomaly_model_version: str`, `risk_model_version: str`, `started_at: datetime`, `completed_at: datetime | None`, `quality_before/after/delta: float`, `anomaly_before/after/delta: float`, `risk_before/after/delta: float`, `severity_before/after/delta: float`, `priority_before/after/delta: float`, `outcome: str`, `criteria_evaluated: dict` JSON, `blocked_by_manual_actions: bool`. Mirror `backend/app/remediation/models.py`'s append-only style (never updated/deleted, full history per FR-011/SC-005).
- [X] T007 Update `backend/tests/_db_fixtures.py` to add `import app.revalidation.models  # noqa: F401` alongside the existing model imports, so the new table registers on `Base.metadata` before `init_db()`. Depends on T006.
- [X] T008 Extend `backend/app/hitl/state_machine.py`'s `TRANSITIONS` table: add `"revalidation_result": {"resolved", "reopened"}` under the existing `"accepted"` entry (currently `{}`) — an incident only reaches `resolved`/`reopened` from `accepted` via this action, matching spec Assumptions ("this feature extends Phase 12's incident status enum... rather than introducing a separate status model"). Leave `"resolved"`/`"reopened"` themselves with no outgoing transitions (matching the existing `"pending_investigation": {}` precedent of a documented MVP limitation, not silently worked around).

**Checkpoint**: Foundation ready — schemas, ORM table, and the state-machine extension all exist; user story implementation can now begin.

---

## Phase 3: User Story 1 - Recompute quality, anomaly, and risk signals on remediated claims (Priority: P1) 🎯 MVP

**Goal**: Genuinely re-invoke Phase 3's GX suites, Phase 7's saved production anomaly model, Phase 9's saved production risk model, and Phase 10's Severity/Business Impact/Priority functions against the caller-supplied current post-remediation claim/feature state — never a cached/reused pre-remediation value.

**Independent Test**: Call `recompute_service.recompute` directly with a fixture claim whose `raw_fields` show a resolved duplicate/corrected value, and confirm (via monkeypatch/spy on the real Phase 3/7/9/10 functions) that each was actually invoked with the fresh data and produced a new result — not a value copied from the incident's stored `evidence_snapshot`.

### Implementation for User Story 1

- [X] T009 [US1] Create `backend/app/revalidation/recompute_service.py` with `_recompute_quality(current_claims: list[CurrentClaimState]) -> tuple[list[ExpectationCheckResult], float]`: builds a `pd.DataFrame` from `current_claims`' `raw_fields`; loads Phase 1's `categories` (`app.data_engineering.dtype_conversion.load_column_categories`), `profiling_report` (`app.data_engineering.report_writer.read_profiling_report`), and reference stats/known-code-values/date-bounds exactly as `quality/scoring_service.run_validation()` does; calls `app.quality.suite_builder.build_suites` and `app.quality.scoring_service.run_category_suites`/`compute_file_level_checks` against that small DataFrame (real GX execution on the current claims' current state, not the full-file batch); folds the results through `app.quality.scoring_service.compute_composite_score` to get a fresh `composite_score`; returns `(check_results, composite_score)`.
- [X] T010 [US1] Add `_recompute_anomaly(anomaly_features: dict[str, float]) -> tuple[float, float, str]` to `recompute_service.py`: reads `app.anomaly.benchmark.read_benchmark_run_result()` (raises `IncompleteRemediationRunError`... no — raises a clear `RuntimeError` if `None`, since this is "no production anomaly model selected yet", a distinct precondition from FR-009's remediation-run check); loads the pickled artifact from `models_dir() / f"{selected_model}.pkl"` exactly as `app.anomaly.window_enrichment._load_selected_artifact` does; builds a one-row `pd.DataFrame` from `anomaly_features` restricted to `artifact["feature_columns"]`, filling any missing columns from `artifact["train_medians"]`; calls the real `detector.score(...)` (genuine invocation, SC-001); converts the raw score to a 0-1 percentile via the Design Note 3 formula using `artifact["calibrated_thresholds"]["p95"]`; calls `app.risk.scoring.severity.anomaly_magnitude_score(percentile)` for the 0-100 scale matching `IncidentORM.anomaly_score`'s own scale; returns `(anomaly_magnitude_score_0_100, percentile, run_result.production_model_selection.selected_model.value)`.
- [X] T011 [US1] Add `_recompute_risk(risk_features: dict[str, float]) -> tuple[float, str]` to `recompute_service.py`: reads `app.risk.benchmark.benchmark_log.read_latest_run_result()`, raising a clear `RuntimeError` if `None`; loads the pickled artifact from `models_dir() / "risk" / f"{selected_model}.pkl"` (same pickle shape as `benchmark_runner.run_benchmark` writes: `model`, `feature_columns`); builds a one-row `pd.DataFrame` from `risk_features` restricted to `feature_columns`; calls the real `model.predict_proba(...)[:, 1][0]` (genuine invocation, SC-001), scaled `* 100.0` to match `IncidentORM.risk_score`'s 0-100 scale (documented scaling choice, MVP_CONTEXT.md Section 3.3); returns `(risk_score_0_100, run_result.production_model_selection.selected_model.value)`.
- [X] T012 [US1] Add `recompute(incident: IncidentORM, request: RevalidationRunRequest) -> RecomputedScores` to `recompute_service.py`, composing T009-T011: calls each `_recompute_*` helper; reads `affected_claim_pct` and `baseline_amount_percentiles` from `incident.evidence_snapshot` (Design Note 2); uses `request.current_affected_claims_amounts` if supplied, else `incident.evidence_snapshot["affected_claims_amounts"]`; derives `quality_check_bands` from the fresh `check_results`' `.band` values (T009); calls `app.risk.scoring.severity.compute_severity`, `app.risk.scoring.business_impact.compute_business_impact`, and `app.risk.scoring.priority.compute_priority` (Phase 10's real functions, FR-004) with these genuinely recomputed inputs; returns a fully-populated `RecomputedScores`.
- [X] T013 [P] [US1] Create `backend/tests/revalidation/_fixtures.py` (no `test_` prefix) with shared builders: `make_incident_with_evidence(db, ...) -> IncidentORM` (an `accepted`-status incident with a realistic `evidence_snapshot` including `affected_claim_pct`/`affected_claims_amounts`/`baseline_amount_percentiles`); `make_remediation_run(db, incident_id, *, completed=True, with_manual_action=False) -> str` (persists a minimal `app.remediation.models.RemediationRun`/`RemediationAction`/`ManualActionRequired` row set directly via 013's ORM, returning the `run_id`, for revalidation tests that need a specific remediation state without running 013's full engine); fixture anomaly/risk model artifacts (a fitted `HBOSDetector`/a trivial fitted `LogisticRegression`, pickled to a `tmp_path`) plus a matching `BenchmarkRunResult`/`RiskBenchmarkRunResult` written via `app.anomaly.benchmark`/`app.risk.benchmark.benchmark_log`'s own writer functions, so tests exercise the real read/load/score path end to end rather than mocking it away entirely.
- [X] T014 [US1] Create `backend/tests/revalidation/test_genuine_recomputation.py` (spec SC-001): using `_fixtures.py`'s real fitted-artifact fixtures, monkeypatch/spy on `app.quality.scoring_service.run_category_suites`, the fixture detector's `.score`, and the fixture risk model's `.predict_proba` to assert each is actually called by `recompute_service.recompute(...)`; assert the returned `RecomputedScores` values differ from (are not equal to / not simply copied from) the incident's stored pre-remediation `quality_score`/`anomaly_score`/`risk_score` in the fixture's constructed scenario.

**Checkpoint**: At this point, genuine Phase 3/7/9/10 recomputation is fully functional and independently testable — zero cached/reused pre-remediation values anywhere in the result.

---

## Phase 4: User Story 2 - Produce an honest before/after comparison (Priority: P1)

**Goal**: Pair the incident's stored pre-remediation scores with Story 1's genuinely recomputed post-remediation scores, computing real deltas that may be positive, negative, or zero — never assumed to improve.

**Independent Test**: Feed `comparison_service.build_comparison` a fixture incident's stored scores and a Story 1 `RecomputedScores` where the risk score is deliberately worse than before, and confirm the resulting `BeforeAfterComparison.risk_delta` is positive (worse) rather than clamped/forced non-negative.

### Implementation for User Story 2

- [X] T015 [US2] Create `backend/app/revalidation/comparison_service.py` with `build_comparison(revalidation_id: str, incident: IncidentORM, recomputed: RecomputedScores) -> BeforeAfterComparison`: reads `quality_before = incident.quality_score`, `anomaly_before = incident.anomaly_score`, `risk_before = incident.risk_score`, `severity_before = incident.severity_result["severity"]`, `priority_before = incident.priority_result["priority"]` (Design Note 4); pairs each with `recomputed`'s corresponding `_after` value; computes `*_delta = after - before` for all five signals, with **no clamping, no `max(0, ...)`, no forced-positive logic anywhere** (spec FR-005, SC-002 — a delta may be negative, meaning the signal got worse) — this is the one function in the module where a "the number came out wrong" instinct must NOT be resolved by changing the formula.
- [X] T016 [P] [US2] Create `backend/tests/revalidation/test_unfavorable_delta.py` (spec SC-002) covering spec.md US2 Acceptance Scenarios 1-2: a fixture where recomputed risk/anomaly are worse than the stored pre-remediation values asserts `risk_delta > 0` and `anomaly_delta > 0` (both "worse", not clamped to 0 or negated); a fixture where recomputed quality genuinely improved asserts `quality_delta > 0` in the expected (favorable) direction — confirming the comparison logic reports whichever direction the real numbers produce, never a fixed sign.

**Checkpoint**: At this point, before/after comparisons are honest and independently testable in both the favorable and unfavorable direction.

---

## Phase 5: User Story 3 - Mark the incident Resolved or Reopened based on real revalidation results (Priority: P1)

**Goal**: Wire recomputation + comparison into the full orchestrator: refuse an incomplete `RemediationRun`, evaluate documented resolution criteria, block "Resolved" while manual actions remain outstanding, transition the incident via `hitl`'s state machine, persist full history, and expose it over HTTP.

**Independent Test**: Two fixtures — one where recomputed signals clear every resolution criterion with zero outstanding manual actions (expect `resolved`), one where a CRITICAL quality check or elevated risk/anomaly remains, or a manual action is still outstanding (expect `reopened`) — confirm `resolution_criteria.determine_resolution` and the full `revalidation_service.run_revalidation` orchestrator agree with the real recomputed evidence in both cases.

### Implementation for User Story 3

- [X] T017 [US3] Create `backend/app/revalidation/resolution_criteria.py` with `determine_resolution(revalidation_id: str, check_results: list[ExpectationCheckResult], anomaly_score_percentile: float, risk_score_0_100: float, risk_threshold: float, has_outstanding_manual_actions: bool) -> ResolutionDetermination`: evaluates `no_critical_gx = not any(r.band == Band.CRITICAL for r in check_results)`, `anomaly_in_normal_band = anomaly_score_percentile < 0.95` (research.md's NORMAL-band definition), `risk_below_threshold = risk_score_0_100 < risk_threshold`, `no_outstanding_manual_actions = not has_outstanding_manual_actions`; sets `outcome = resolved` only if all four are `True` (data-model.md's validation rule, FR-007/SC-003), else `reopened`; sets `blocked_by_manual_actions = has_outstanding_manual_actions and (no_critical_gx and anomaly_in_normal_band and risk_below_threshold)` (True only when manual actions were the *sole* reason Resolved was withheld, per data-model.md's field note). Document the `risk_threshold` default as the investigation-worthy threshold research.md references (Section 3.1's risk bands) as a module-level constant, overridable by the caller.
- [X] T018 [US3] Create `backend/app/revalidation/revalidation_service.py` with `run_revalidation(db: Session, incident_id: str, request: RevalidationRunRequest) -> RevalidationRunResponse`: looks up the incident via `app.incidents.service.get_incident_orm`, raising `LookupError` if unknown; calls `app.remediation.remediation_service.list_remediation_runs(db, incident_id)` and locates `request.remediation_run_id` among them, raising `IncompleteRemediationRunError` if not found or if its `completed_at` is `None` (FR-009, SC-006, Design Note 6); computes `has_outstanding_manual_actions = bool(matched_run.manual_actions_required)` (Design Note 5); calls `recompute_service.recompute(incident, request)` (US1); calls `comparison_service.build_comparison(...)` (US2); calls `resolution_criteria.determine_resolution(...)` (US3); calls `app.hitl.state_machine.validate_transition(incident.status, "revalidation_result")` and picks the destination matching the determined `outcome`; records an `app.hitl.models.IncidentStatusTransition` row (`action="revalidation_result"`) and updates `incident.status`; persists one `RevalidationRun` ORM row with every recomputed/comparison/resolution field flattened onto it (T006); commits; returns the assembled `RevalidationRunResponse`. Depends on T004, T006-T008, T012, T015, T017.
- [X] T019 [US3] Add `list_revalidation_runs(db: Session, incident_id: str) -> list[RevalidationRunResponse]` to `revalidation_service.py`: queries all `RevalidationRun` ORM rows for `incident_id` ordered by `started_at`, reconstructing each into its `RevalidationRunResponse` triple (no incident-status re-derivation needed -- read the incident's *current* status once for all rows, since revalidation history doesn't retroactively change what the incident's status was at each point). Depends on T018.
- [X] T020 [US3] Create `backend/app/revalidation/router.py`: `POST /revalidation/{incident_id}/run` (body: `RevalidationRunRequest`, `response_model=RevalidationRunResponse`) calling `run_revalidation`, mapping `LookupError`→`404` and `IncompleteRemediationRunError`→`409` (contracts/api.md); `GET /revalidation/{incident_id}` (`response_model=list[RevalidationRunResponse]`) calling `list_revalidation_runs`, raising `404` when empty (matching 013's `remediation/router.py` pattern exactly). Depends on T018, T019.
- [X] T021 [US3] Wire the new router into `backend/app/main.py`: import `revalidation_router` from `app.revalidation.router`, add it to the `app.include_router` loop, remove `revalidation` from the trailing comment listing modules whose routers are still placeholders. Depends on T020.
- [X] T022 [P] [US3] Create `backend/tests/revalidation/test_resolved_blocked_by_manual_action.py` (spec SC-003, US3 Acceptance Scenario 3): a fixture remediation run with zero `ManualActionRequired` records and recomputed signals that clear every criterion asserts `outcome == "resolved"`; the same recomputed signals but with the fixture remediation run carrying one outstanding `ManualActionRequired` record asserts `outcome != "resolved"` (`reopened`) and `blocked_by_manual_actions is True`, exercised through the full `run_revalidation` orchestrator (not just `resolution_criteria` in isolation), asserting the incident's status actually transitions accordingly.
- [X] T023 [P] [US3] Create `backend/tests/revalidation/test_incomplete_remediation_refused.py` (spec SC-006, Edge Cases bullet 1): `run_revalidation` against a `remediation_run_id` whose fixture `RemediationRun` row has `completed_at=None` is refused (`IncompleteRemediationRunError`/`409`) with zero `RevalidationRun` rows persisted; the same call against a completed run succeeds.
- [X] T024 [P] [US3] Create `backend/tests/revalidation/test_router_revalidation_flow.py`: an end-to-end `TestClient` test (mirroring `backend/tests/remediation/test_router_remediation_flow.py`'s pattern) that seeds an accepted incident + a completed 013 `RemediationRun` fixture, POSTs a `RevalidationRunRequest` to `/revalidation/{id}/run`, asserts `200` with `revalidation_run`/`comparison`/`resolution`/`incident_status` all present and `incident_status` matching the persisted incident's new status; `GET /revalidation/{id}` then returns that run in history; re-running against the same `remediation_run_id` produces a second, distinct `RevalidationRun` record (FR-011/SC-005) rather than overwriting the first.

**Checkpoint**: All three user stories are now independently functional and wired end-to-end over HTTP.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across the whole feature.

- [X] T025 [P] Run `pytest backend/tests/revalidation/` (and the full backend suite) and fix any regressions surfaced by cross-file integration between the phases above.
- [X] T026 [P] Manually validate every curl example in `specs/014-revalidation/quickstart.md` against a locally running `uvicorn app.main:app` instance (200 with the full response shape, 409 on an incomplete remediation run), confirming they match this implementation's actual behavior.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion.
  - US1 (Phase 3) has no dependency on US2/US3 and can be built/tested first.
  - US2 (Phase 4) depends on US1's `RecomputedScores` shape (T012) to build comparisons against.
  - US3 (Phase 5) depends on both US1's `recompute` (T012) and US2's `build_comparison` (T015) to assemble the full orchestrator — so while all three stories are P1, they build in this sequence in practice (US1 → US2 → US3), matching 013's own precedent for this kind of layered, single-orchestrator feature.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Recomputation helpers (T009-T011) before the composing `recompute` function (T012).
- `recompute` (US1) before `build_comparison` (US2) before `determine_resolution`/`run_revalidation` (US3).
- Service logic before the router; router before `main.py` wiring.
- Tests for a story follow that story's implementation tasks (verifying already-built behavior, per plan.md's Testing section).

### Parallel Opportunities

- T001-T002 (Setup) can run in parallel.
- Within Foundational, T003-T006 (four independent new/rewritten files) can run in parallel; T007 depends on T006, T008 is independent of T003-T007.
- Within US1, T009-T011 touch the same new file (`recompute_service.py`) so run sequentially; T013 can run in parallel with T009-T012.
- Within US3, T022-T024 (three independent test files) can run in parallel once T017-T021 are done.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch independent foundational files together:
Task: "Create backend/app/revalidation/errors.py with IncompleteRemediationRunError"
Task: "Create backend/app/revalidation/schemas.py with RevalidationRun/BeforeAfterComparison/etc."
Task: "Create backend/app/revalidation/models.py with the flattened RevalidationRun ORM table"
Task: "Extend backend/app/hitl/state_machine.py with the revalidation_result transition"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1 — genuine Phase 3/7/9/10 recomputation.
4. **STOP and VALIDATE**: `pytest backend/tests/revalidation/test_genuine_recomputation.py`.

### Incremental Delivery

1. Setup + Foundational → schemas/ORM/state-machine extension ready.
2. US1 → recomputation is genuine and independently testable (via spy/mock on the real Phase 3/7/9 functions).
3. US2 → before/after deltas are honest in both directions (testable standalone against fixture score pairs).
4. US3 → the safety boundary (complete-run gate, manual-action block, resolved/reopened transition) wraps US1+US2 into the real HTTP-facing engine — deploy/demo here.

### Notes

- Because US2's `build_comparison` and US3's `run_revalidation` each wrap the previous story's logic, "independently testable" for US2/US3 means testable via direct function calls against fixtures (per each phase's Independent Test above), not that US3 can be built before US1/US2 exist.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
- Avoid: any code path that returns a cached/pre-remediation value dressed up as "recomputed" (FR-012, SC-001); clamping/forcing a delta's sign in `comparison_service.py` (FR-005, SC-002); marking an incident "resolved" while `resolution_criteria.py`'s four-criteria check has any `False` (FR-007, SC-003).
