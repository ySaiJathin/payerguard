# Phase 0 Research: Revalidation

## Decision: Resolution criteria — no CRITICAL GX checks, anomaly score in NORMAL band, risk below the investigation threshold

**Decision**: `resolution_criteria.py` marks an incident eligible for "Resolved" when, for its affected claims/window: (a) zero remaining CRITICAL Phase 3 expectation results, (b) the Phase 7 anomaly score falls in the Section 3.1 NORMAL band (below the 95th percentile), and (c) the Phase 9 risk score falls below the configured investigation-worthy threshold (Section 3.1's risk bands, LOW/below-MEDIUM) — all three must hold, plus zero outstanding `ManualActionRequired` records.

**Rationale**: This directly reuses the exact bands MVP_CONTEXT.md Section 3.1 already defines for quality/anomaly/risk, rather than inventing new resolution-specific thresholds — consistent with the project's pattern of reusing already-documented, already-justified thresholds instead of introducing new unexplained ones.

**Alternatives considered**: A single composite "improved enough" score (e.g., Priority dropped by X%) — rejected as less directly tied to whether the underlying problem is actually fixed; a claim could have a much lower Priority while still failing a CRITICAL quality check, which shouldn't count as "Resolved."

## Decision: Genuine recomputation enforced by calling Phase 3/7/9/10's existing functions with fresh current-state inputs, never cached values

**Decision**: `recompute_service.py` reads the affected claims' *current* state (post-remediation, from the claims store) and passes it through Phase 3's suite-execution function, Phase 7's selected-model scoring function, and Phase 9's selected-model scoring function fresh — it never reads a cached/stale `ExpectationCheckResult` or anomaly/risk score from before remediation.

**Rationale**: SC-001 requires verifying recomputation functions were "actually invoked, not skipped" — the only way to guarantee this is to structurally have no code path that returns a pre-remediation cached value as if it were current; calling the real functions with current data by construction cannot return stale results.

**Alternatives considered**: Diffing before/after by reading two different historical snapshots without re-executing anything (rejected — this would only be valid if Phase 3/7/9 already re-ran independently after remediation, which isn't guaranteed; explicit re-invocation from this feature is the only way to guarantee freshness on demand).

## Decision: Model-version recording via a `model_version` field already present on Phase 7/9's `ProductionModelSelection`/`ProductionRiskModelSelection`

**Decision**: `recompute_service.py` captures `ProductionModelSelection.selected_model`+`selected_at` (Phase 7) and `ProductionRiskModelSelection.selected_model`+`selected_at` (Phase 9) at revalidation time and stores them on the `RevalidationRun` record.

**Rationale**: FR-010/SC-004 require recording which model version was used; both upstream phases already expose exactly this information (they didn't need new fields added), so this feature simply reads and persists it alongside its own results — no upstream spec changes needed.

**Alternatives considered**: Adding a new model-versioning system specific to this feature (rejected — unnecessary duplication; Phase 7/9 already own and expose this information as the authoritative source).

## Decision: Revalidation trigger is an explicit endpoint call, not an automatic post-remediation hook

**Decision**: `POST /revalidation/{incident_id}/run` is called explicitly (by a reviewer action or an orchestration script), not automatically fired the instant Phase 13's remediation completes.

**Rationale**: Spec Assumptions explicitly defer the exact trigger mechanism to later phases/frontend UX; an explicit endpoint keeps this feature's own scope minimal and testable in isolation, while still being trivially wireable to an automatic trigger later (Phase 12's `hitl` module or Phase 18's frontend could call this endpoint immediately after remediation without any change to this feature).

**Alternatives considered**: An automatic in-process call from `remediation_service.py` directly into `recompute_service.py` (rejected — would couple the `remediation` and `revalidation` modules' internals together, violating the modular-boundary principle; an explicit HTTP call between modules keeps the boundary clean, matching how every other cross-module reference in this build order has been handled).
