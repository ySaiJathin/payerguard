# Phase 0 Research: Testing Suite

## Decision: The coverage map is a checked-in Markdown table, generated once and manually maintained, with a test asserting its completeness

**Decision**: `docs/testing/phase16_coverage_map.md` is a hand-authored (during this feature's implementation) Markdown table with columns `Category | Scenario | Status | Reference`, and `test_coverage_map_completeness.py` parses it to assert every MVP_CONTEXT.md Phase 16-named scenario (hardcoded as the expected list, sourced directly from Section 5) appears with a non-empty `Reference`.

**Rationale**: FR-001/SC-001 require both a human-reviewable document and a verifiable completeness guarantee — a test that parses the checked-in table is simpler than generating the table dynamically from spec files (which would require parsing every prior spec.md's Success Criteria programmatically, a fragile approach given specs are free-form Markdown, not structured data).

**Alternatives considered**: Dynamically scanning all `specs/*/spec.md` files for scenario keywords (rejected — free-form Markdown prose isn't a reliable structured-data source to parse against; a hand-authored map, verified only for the presence of all required scenario names, is more robust and still fully auditable by a human reviewer).

## Decision: Model-stability test runs the selected anomaly model's fit+score cycle N times (default 5) on unchanged data and asserts score variance is below a documented tolerance

**Decision**: `test_model_stability.py` re-fits (or re-scores, for models like LOF that don't require fitting) the Phase 7-selected production anomaly model 5 times against the same unchanged train/test data, and asserts the resulting anomaly scores for a fixed test set vary by less than a documented tolerance (e.g., relative std dev < 5%) — flagging (per FR-008) if the model type has inherent randomness (e.g., Isolation Forest's random subsampling) requiring a documented, wider tolerance than a fully deterministic model like IQR or HBOS.

**Rationale**: "Model stability" isn't defined numerically anywhere in MVP_CONTEXT.md, so this feature must define and document a concrete, testable interpretation — repeated-run score variance is the standard, direct way to operationalize "stability."

**Alternatives considered**: Testing stability across different random seeds only for randomized models (rejected as too narrow — the test should apply uniformly across whichever model Phase 7 actually selected, with tolerance calibrated to that model's known randomness characteristics, not skipped for deterministic models).

## Decision: Drift-sensitivity test constructs a fixture with a deliberately shifted amount distribution and asserts risk scores move measurably

**Decision**: `test_drift_sensitivity.py` builds a synthetic test window (reusing Phase 7's injection-harness "distribution shift" pattern conceptually) where claim amounts are shifted well outside the historical baseline range, scores it with the Phase 9-selected production risk model, and asserts the resulting risk score differs meaningfully (beyond a documented minimum delta) from the same window's un-shifted risk score.

**Rationale**: This directly operationalizes "drift sensitivity" as "the model isn't frozen/insensitive to genuinely different input" — a concrete, testable property, and reuses Phase 7's already-designed distribution-shift injection concept rather than inventing a new drift-simulation approach from scratch.

**Alternatives considered**: Testing drift sensitivity via a formal statistical drift-detection algorithm (e.g., population stability index) — noted as a valuable future enhancement for Phase 22's actual production monitoring, but out of scope for this feature, which only needs to prove the *model* responds to drift, not implement a full drift-*detection* system (that's explicitly Phase 22's job).

## Decision: LLM evidence-grounding check cross-references cited claim IDs/values against the actual `StructuredIncidentPayload`

**Decision**: `test_evidence_grounding.py` sends a fixture incident to the (mocked, deterministic-response) LLM investigation service, then parses the `evidence` section of the resulting `LLMInvestigation` for any specific claim IDs or numeric values it cites, and asserts every cited claim ID exists in the `StructuredIncidentPayload.affected_claims_sample` and every cited numeric value is traceable to a real field in the payload (within reasonable rounding tolerance) — flagging (not failing outright) any citation that can't be verified, since this is inherently a best-effort check, per FR-007's documented limitation.

**Rationale**: This is the most concrete, automatable proxy for "hallucination"/"unsupported claims" detection available without a general-purpose fact-checking system — it directly tests whether the LLM's specific factual citations trace back to real evidence it was actually given, which is the most common and consequential form of hallucination risk for this use case (inventing a claim ID or dollar figure that was never in the evidence).

**Alternatives considered**: A separate LLM-as-judge call to evaluate the first LLM's output for hallucination (rejected for the MVP — adds a second non-deterministic dependency and cost to the test suite itself, and MVP_CONTEXT.md doesn't call for this level of sophistication; the direct citation-tracing check is simpler, deterministic, and directly testable).
