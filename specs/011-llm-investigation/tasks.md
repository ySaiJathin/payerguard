---

description: "Task list for LLM Investigation (Mistral)"
---

# Tasks: LLM Investigation (Mistral)

**Input**: Design documents from `/specs/011-llm-investigation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md — all present. Phase 3 (quality), Phase 7 (anomaly), Phase 9 (risk), and Phase 10 (severity/business-impact/priority) already exist as evidence sources. **Phase 12 (Incident CRUD) does not exist yet** — contracts/api.md's own Notes section anticipates this ("until Phase 12 ships, this endpoint can be exercised directly against a manually-constructed `StructuredIncidentPayload`"), so `payload_builder.py` (like Phase 10's scoring functions) takes already-resolved evidence values rather than fetching them from an incident store that doesn't exist, and `POST /llm/investigate` accepts an optional inline `structured_payload` for pre-Phase-12 use.

**Tests**: Included — plan.md's Testing section names 6 test files matching the spec's 6 Success Criteria; two more are added for the same reason 008/009/010's tasks.md added extras: SC-005 (re-investigation history) and the router's own contract (404/502/422 mapping) each need a dedicated, machine-checkable test.

**Organization**: Tasks are grouped by user story. All three stories are P1. US1 (produce a structured report) contains essentially all the new production code, since US2's insufficiency-handling and US3's read-only/secret-safety guarantees are structural properties of how US1's code is written (research.md: the insufficiency phrase is detected by `response_parser.py`, built in US1; the read-only boundary is the *absence* of certain imports in US1's `investigation_service.py`) rather than separate code paths — US2 and US3's phases are therefore verification-only, confirming those properties hold, mirroring how 009/010's P2/verification-only stories were structured.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (structured investigation report), US2 (insufficiency handling), US3 (read-only/secret-safety boundary)

## Path Conventions

Backend module: `backend/app/llm/` (existing Phase-0 scaffold, filled in for real). Tests: `backend/tests/llm/`.

**Note on existing `backend/app/llm/*.py` placeholders**: `investigation_service.py`, `mistral_client.py`, and `router.py` already exist as stub files with names matching plan.md's Project Structure exactly — they are overwritten in place, not deleted/recreated. `prompts.py` is superseded by plan.md's `prompt_templates.py` and deleted. `backend/tests/llm/test_placeholder.py` is superseded by this feature's real test suite and deleted.

---

## Phase 1: Setup

**Purpose**: Align the existing Phase-0 scaffold with plan.md's exact module boundary before any real code goes in.

- [x] T001 Delete the placeholder `backend/app/llm/prompts.py` and `backend/tests/llm/test_placeholder.py` stub files — superseded by this feature's real `prompt_templates.py` and test suite

**Checkpoint**: Module skeleton matches plan.md exactly; ready for real implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas and error types every user story's code depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Define `StructuredIncidentPayload`, `InvestigationDraft` (the six-field pydantic model handed to Mistral's structured-output mode: `summary`, `likely_root_cause`, `evidence`, `business_impact_narrative`, `recommended_fix`, `prevention_recommendation`, all `str`), `LLMInvestigation`, `InvestigationFailure` (data-model.md's field tables), plus `InvestigateRequest` (`incident_id: str`, `structured_payload: StructuredIncidentPayload | None = None` — additive beyond quickstart.md's bare example, needed because Phase 12 doesn't exist yet) and `InvestigationHistoryResponse` (`investigations`, `failures`) matching contracts/api.md, in `backend/app/llm/schemas.py`
- [x] T003 [P] Define `MistralAPIError` (spec FR-007, maps to `502`), `MalformedResponseError` (spec FR-004, maps to `422`), and `IncidentNotFoundError` (maps to `404` — raised when no `structured_payload` is supplied and no Phase 12 incident store exists to resolve `incident_id` against) in `backend/app/llm/errors.py`

**Checkpoint**: Foundation ready — investigation work can now begin.

---

## Phase 3: User Story 1 - Investigate a structured incident and produce a structured, evidence-grounded report (Priority: P1) 🎯 MVP

**Goal**: A structured incident payload, sent to Mistral, produces a validated six-section investigation result, persisted as a distinct, timestamped, non-overwriting record.

**Independent Test**: Feed a structured incident into the investigation service and confirm the response contains all six documented sections, each grounded in the actual evidence supplied.

### Implementation for User Story 1

- [x] T004 [US1] Implement `backend/app/llm/payload_builder.py`: `build_payload(incident_context, quality_check_results, anomaly_evidence, risk_evidence, severity_result, business_impact_result, affected_claims_sample) -> StructuredIncidentPayload` — a pure function (mirrors Phase 10's "take already-resolved inputs" pattern, since Phase 12's incident store doesn't exist to fetch from) that represents every `BusinessImpactResult` component with `status="unavailable"` as an explicit string (`"unavailable - {reason}"`), never coerced to `0` or omitted (spec FR-001, Edge Cases); `compute_evidence_snapshot_id(payload) -> str` (SHA-256 hash of the payload's own JSON content, mirroring Phase 9's `risk_dataset_version` hashing pattern) for FR-006's evidence-snapshot linkage
- [x] T005 [P] [US1] Implement `backend/app/llm/prompt_templates.py`: `INSUFFICIENCY_PHRASE = "Insufficient evidence to determine the root cause"`; `build_investigation_prompt(payload: StructuredIncidentPayload) -> str` — formats the payload into a prompt instructing Mistral to produce the six sections and to use the literal `INSUFFICIENCY_PHRASE` when evidence doesn't support a confident root-cause determination (research.md)
- [x] T006 [P] [US1] Implement `backend/app/llm/mistral_client.py`: `call_mistral(prompt, client=None, model="mistral-small-latest", timeout_s=45) -> InvestigationDraft` — constructs a real `mistralai.client.Mistral(api_key=os.environ["MISTRAL_API_KEY"])` when `client` isn't injected (test-only injection point), calls `client.chat.parse(model=model, messages=[{"role": "user", "content": prompt}], response_format=InvestigationDraft, timeout_ms=timeout_s*1000)` to get Mistral's own structured-output mode to enforce the six-field JSON shape (research.md's noted refinement over free-text parsing), retries exactly once on a transient network error (timeout/connection error only, never on a content/rate-limit error), and raises `MistralAPIError` on any failure surviving the retry (spec FR-007) — `MISTRAL_API_KEY` is read only via `os.environ`, never hardcoded (spec FR-008)
- [x] T007 [P] [US1] Implement `backend/app/llm/response_parser.py`: `validate_and_tag(draft: InvestigationDraft) -> tuple[InvestigationDraft, bool]` — raises `MalformedResponseError` if any of the six fields is empty/whitespace-only (Mistral's structured-output mode already guarantees the JSON *shape*; this enforces the *content* rule a schema alone can't express, spec FR-004); returns `insufficient_evidence = prompt_templates.INSUFFICIENCY_PHRASE.lower() in draft.likely_root_cause.lower()` (research.md)
- [x] T008 [US1] Implement `backend/app/llm/investigation_log.py`: `append_investigation`/`append_failure`/`read_investigation_history(incident_id)` persisting to `data/reports/llm_investigations.json` as an append-only history (mirrors Phase 4/9's append pattern, never overwritten — spec FR-006, SC-005)
- [x] T009 [US1] Implement `backend/app/llm/investigation_service.py`: `investigate(incident_id, payload, mistral_client=None, model_version="mistral-small-latest") -> LLMInvestigation` — computes the evidence snapshot id, builds the prompt, calls `mistral_client.call_mistral`, validates via `response_parser.validate_and_tag`, builds and persists an `LLMInvestigation` on success; on `MistralAPIError`/`MalformedResponseError`, builds and persists a distinct `InvestigationFailure` (`failure_type` = `"timeout"`/`"api_error"`/`"malformed_response"`) *before* re-raising the original exception, so the router can map it to the right HTTP status while the failure remains auditable (spec FR-006, FR-007, SC-004); imports only read-only accessors — zero import of `app.incidents` or `app.remediation` (spec FR-005, FR-009, research.md's dependency-isolation decision)
- [x] T010 [US1] Implement `backend/app/llm/router.py`: `POST /llm/investigate` (raises `IncidentNotFoundError` → `404` when `structured_payload` is omitted, since no Phase 12 incident store exists yet to resolve `incident_id`; otherwise calls `investigation_service.investigate`, mapping `MistralAPIError` → `502` and `MalformedResponseError` → `422`, response body `InvestigationFailure` in both cases) and `GET /llm/investigations/{incident_id}` (returns `InvestigationHistoryResponse` via `investigation_log.read_investigation_history`, newest first) per contracts/api.md
- [x] T011 [US1] Register the new `backend/app/llm/router.py` router in `backend/app/main.py`, updating the "still placeholders" comment
- [x] T012 [P] [US1] `backend/tests/llm/test_payload_builder.py`: asserts a fixture `BusinessImpactResult` with an unavailable component is represented as an explicit string in the built payload, never `0` or omitted (spec FR-001), and that `compute_evidence_snapshot_id` is deterministic for identical payload content
- [x] T013 [P] [US1] `backend/tests/llm/test_response_parser_sections.py`: a complete fixture `InvestigationDraft` passes `validate_and_tag` with all six sections intact (SC-001); a fixture with one empty section raises `MalformedResponseError` (FR-004)
- [x] T014 [P] [US1] `backend/tests/llm/test_api_failure_handling.py`: a mocked `mistral_client` raising a timeout on every call causes `investigation_service.investigate` to persist an `InvestigationFailure` (not a fabricated `LLMInvestigation`) and re-raise `MistralAPIError` (SC-004); a mock that fails once then succeeds confirms the single-retry behavior (research.md)
- [x] T015 [P] [US1] `backend/tests/llm/test_reinvestigation_history.py`: two successful `investigate()` calls against the same `incident_id` produce two distinct, timestamped `LLMInvestigation` records, with the first preserved unmodified (SC-005)
- [x] T016 [P] [US1] `backend/tests/llm/test_router_investigate_and_history.py`: FastAPI `TestClient` — `POST /llm/investigate` without `structured_payload` returns `404`; with a fixture `structured_payload` and a mocked Mistral client returns `200` with all six sections; `GET /llm/investigations/{incident_id}` returns the accumulated history

**Checkpoint**: `POST /llm/investigate` runs end-to-end against a mocked Mistral client and produces a complete, persisted, re-investigable report. This is the feature's MVP.

---

## Phase 4: User Story 2 - Never guess when evidence is insufficient (Priority: P1)

**Goal**: A deliberately sparse/ambiguous incident produces an explicit insufficiency statement, never a fabricated-sounding root cause.

**Independent Test**: Construct a sparse/ambiguous fixture incident and confirm the investigation response explicitly states insufficient evidence.

### Implementation for User Story 2

- [x] T017 [P] [US2] `backend/tests/llm/test_insufficient_evidence.py`: a mocked Mistral response using `prompt_templates.INSUFFICIENCY_PHRASE` in `likely_root_cause` is tagged `insufficient_evidence=True` for 100% of runs (SC-002, spec Acceptance Scenario 1); a mocked response with a substantive, specific root cause is tagged `insufficient_evidence=False` (spec Acceptance Scenario 2 — the insufficiency path isn't applied indiscriminately) — no new production code needed since `response_parser.py` (US1) already implements this detection

**Checkpoint**: Insufficiency handling is verified as a genuine, non-indiscriminate signal.

---

## Phase 5: User Story 3 - Enforce read-only, non-executing LLM access (Priority: P1)

**Goal**: A structural guarantee — not a convention — that the investigation service can never write to `claims`/`remediations`, and that `MISTRAL_API_KEY` never leaks into source, commits, or logs.

**Independent Test**: Inspect the investigation service's dependencies and confirm no write-capable import path exists; scan source for hardcoded secrets.

### Implementation for User Story 3

- [x] T018 [P] [US3] `backend/tests/llm/test_write_access_boundary.py`: statically parses (via `ast`) every `backend/app/llm/*.py` file's `import`/`from` statements and asserts none reference `app.incidents` or `app.remediation` (SC-003) — no new production code needed since this is a property of what US1's code was written to *not* import (research.md's dependency-isolation decision)
- [x] T019 [P] [US3] `backend/tests/llm/test_no_secret_leakage.py`: scans every `backend/app/llm/*.py` file's source text for a hardcoded `MISTRAL_API_KEY` string-literal assignment (as opposed to an `os.environ`/`os.getenv` read) and fails if found (SC-006, spec FR-008)

**Checkpoint**: All three user stories independently functional; the LLM investigation capability is ready for Phase 12 to call.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T020 Run quickstart.md's manual verification steps end-to-end against a running backend, using a mocked/injected Mistral client where a real API key isn't available in this environment (investigate → verify insufficient-evidence handling → verify write-access boundary → verify API-failure handling → verify re-investigation history → verify no secret leakage) and fix any drift between the contracts and the implementation
- [x] T021 [P] Review all `backend/app/llm/*.py` docstrings for consistency with the repo's per-file rationale-comment convention

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on User Story 1 (`response_parser.py` is where insufficiency detection lives) — verification-only, no new production code
- **User Story 3 (Phase 5)**: Depends on User Story 1 (the import graph and secret handling it verifies are properties of US1's own files) — verification-only, no new production code
- **Polish (Phase 6)**: Depends on all three user stories

### Parallel Opportunities

- T003 alongside T002
- T005, T006, T007 in parallel once T002-T004 land (different files)
- T012, T013, T014, T015, T016 in parallel once T004-T011 land
- T017, T018, T019 all in parallel with each other once T004-T011 land — each is independent verification against US1's already-complete code
- T021 alongside T020

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2 (setup + foundational)
2. Phase 3 (US1 — the full investigation pipeline: payload → prompt → Mistral call → parse/validate → persist → endpoints) — **this is the feature's MVP**: a real, evidence-grounded, re-investigable LLM investigation capability
3. Phase 4 + Phase 5 (US2 + US3 — verification that insufficiency-handling and the read-only/secret-safety boundary genuinely hold) can run in parallel with each other, immediately after US1

### Incremental Delivery

Setup + Foundational → US1 (full pipeline, MVP) → US2 + US3 in parallel (verification) → Polish.
