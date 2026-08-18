# Implementation Plan: LLM Investigation (Mistral)

**Branch**: `011-llm-investigation` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-llm-investigation/spec.md`

## Summary

Build the `llm` module: a Mistral client, a structured-payload builder (Phase 3/4/7/9/10 evidence → `StructuredIncidentPayload`), a response parser enforcing the six-section structure and insufficiency-handling contract, and an `LLMInvestigation`/`InvestigationFailure` persistence layer — with a hard, structural read-only boundary (no write access to `claims`/`remediations`).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: `mistralai` (official Mistral Python client) or `httpx` for direct REST calls; pydantic for response-schema validation

**Storage**: `llm_investigations` table (MVP_CONTEXT.md Section 3 core tables) — this feature is the first to genuinely need incident-linked persistence beyond files, since investigations must survive and be queryable across HITL review cycles (Phase 12); file-based fallback (`data/reports/llm_investigations.json`) acceptable for MVP if DB wiring isn't yet complete, consistent with the file-first precedent, but the DB table is the intended home per Section 3

**Testing**: pytest with a mocked Mistral client — a six-section-completeness test (SC-001); a sparse-evidence insufficiency test (SC-002); a write-access-boundary static/dependency-audit test (SC-003); a simulated API-failure test (SC-004); a secret-scan test (SC-006)

**Target Platform**: Same as prior phases; external network call to Mistral's API is new for this feature (all prior phases were local computation)

**Project Type**: Backend module — new `backend/app/llm/` module (Section 3's `llm (Mistral client, prompts, investigation service)` boundary)

**Performance Goals**: No phase-specific numeric target; a single Mistral call's latency is bounded by the external API, not this feature's own logic — document a reasonable timeout (e.g., 30-60s) rather than blocking indefinitely

**Constraints**: Zero write access to mutating tables (FR-005, SC-003); `MISTRAL_API_KEY` never hardcoded/logged (FR-008, SC-006); insufficiency handling never silently upgraded to a fabricated conclusion (FR-003)

**Scale/Scope**: One investigation per incident-creation or recalculation event (Phase 12-triggered), not a batch job

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — Mistral is fixed by MVP_CONTEXT.md ("Mistral, not Gemini"), not a benchmarked choice among candidates | PASS |
| II. No Fabricated Values | Applies — FR-001 (accurate payload including `unavailable` markers), FR-003 (no fabricated root cause) | PASS |
| III. Deterministic-First, ML-Second | Applies — the LLM investigates only after Phase 3's deterministic floor and Phase 7/9's empirical benchmarks have already run; it doesn't replace them | PASS |
| IV. Human-in-the-Loop | This feature **is** the direct implementation of "The LLM (Mistral) proposes; it never executes" | PASS |
| V. Constrained, Auditable Remediation | Related — this feature's output feeds Phase 13's remediation engine, but this feature itself performs zero remediation (FR-009) | PASS |
| VI. Modular Backend, No Monolith | Applies — new `llm` module matching Section 3's boundary exactly | PASS |
| VII. Temporal Integrity | Not directly applicable | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-llm-investigation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md   # /speckit.tasks — not created here
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── llm/
│       ├── __init__.py
│       ├── mistral_client.py       # thin, read-only-capable API wrapper; timeout handling (FR-007)
│       ├── payload_builder.py      # FR-001 — Phase 3/4/7/9/10 -> StructuredIncidentPayload
│       ├── prompt_templates.py     # six-section prompt structure, insufficiency instruction
│       ├── response_parser.py      # FR-002, FR-003, FR-004 — validates six sections
│       ├── investigation_service.py # orchestrates build -> call -> parse -> persist; NO write access elsewhere (FR-005, FR-009)
│       ├── schemas.py              # StructuredIncidentPayload, LLMInvestigation, InvestigationFailure
│       └── router.py               # POST /llm/investigate, GET /llm/investigations/{incident_id}
└── tests/
    └── llm/
        ├── test_payload_builder.py
        ├── test_response_parser_sections.py   # SC-001
        ├── test_insufficient_evidence.py       # SC-002
        ├── test_write_access_boundary.py       # SC-003 (static import/dependency check)
        ├── test_api_failure_handling.py         # SC-004
        └── test_no_secret_leakage.py             # SC-006
```

**Structure Decision**: New `llm` module matching Section 3's exact naming. `test_write_access_boundary.py` statically verifies (e.g., via import-graph inspection or a dependency-injection audit) that `investigation_service.py` never imports/calls anything from `claims` or `remediation` write paths — enforcing FR-005 at test time, not just by convention.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
