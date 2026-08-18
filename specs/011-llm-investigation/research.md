# Phase 0 Research: LLM Investigation (Mistral)

## Decision: Structured output via a strict, validated response schema, not free-text parsing

**Decision**: The prompt instructs Mistral to respond in a fixed structure (e.g., JSON or clearly delimited sections matching `summary`/`likely_root_cause`/`evidence`/`business_impact`/`recommended_fix`/`prevention_recommendation`), and `response_parser.py` validates the response against a pydantic schema before accepting it as a successful `LLMInvestigation`.

**Rationale**: FR-004 requires detecting malformed/incomplete responses rather than presenting a partial result as complete — a strict schema validation step is the only reliable way to guarantee this rather than best-effort free-text scraping, which risks silently accepting a response missing a section.

**Alternatives considered**: Free-text response with regex-based section extraction (rejected — fragile, more likely to silently produce a false "complete" parse when a section is actually missing or malformed); relying on Mistral's own function-calling/JSON-mode feature if available (worth using during implementation if Mistral's API supports structured output natively — reduces parsing risk further, noted as an implementation refinement, not a spec requirement).

## Decision: Insufficiency handling is instructed explicitly in the prompt, then verified post-hoc for consistency

**Decision**: The prompt template explicitly instructs Mistral to respond with the literal phrase "Insufficient evidence to determine the root cause" (or a close documented variant) when the structured evidence doesn't support a confident determination, and `response_parser.py` checks whether the `likely_root_cause` section contains this phrase to tag the investigation as `insufficient_evidence: true/false` for downstream filtering (e.g., Phase 13's remediation engine treating insufficient-evidence incidents as "Manual Action Required" candidates).

**Rationale**: MVP_CONTEXT.md's phrasing ("it must say so explicitly... rather than guess") is itself the instruction to give the model — the clearest way to get consistent, detectable insufficiency statements is to ask for a specific, recognizable phrase rather than hoping the model naturally hedges in a parseable way.

**Alternatives considered**: A separate boolean "confidence" field the model self-reports (rejected as primary mechanism — self-reported confidence scores from LLMs are notoriously unreliable/uncalibrated; the explicit-phrase instruction is more directly testable and matches MVP_CONTEXT.md's own literal wording); relying purely on downstream human judgment to notice weak investigations (rejected — defeats the purpose of FR-003's structural guarantee, and doesn't give Phase 12/13 a machine-readable signal to act on).

## Decision: Read-only enforcement via dependency isolation, not just documentation

**Decision**: `investigation_service.py` (and everything it imports) has zero import-time dependency on `app.incidents`' or `app.remediation`'s write-capable service functions — it only imports read-only accessor functions from `app.quality`, `app.baseline`, `app.anomaly`, `app.risk`, and its own `llm` module's persistence. A test (`test_write_access_boundary.py`) statically inspects the module's import graph to assert this.

**Rationale**: FR-005/SC-003 require this to be a structural guarantee, not a convention — the prompt-injection edge case (spec Edge Cases) specifically anticipates that a malicious evidence string might try to get the LLM to "instruct" the system to mutate data. Since the investigation service has no write-capable dependency to call even if it wanted to, the LLM's output text cannot cause a mutation no matter what it says — the enforcement lives in the Python dependency graph, not in trusting the LLM to behave.

**Alternatives considered**: Runtime permission checks (e.g., a role/scope check before any write) — considered as defense-in-depth but not sufficient alone, since it still requires the write-capable code path to exist and be reachable; import-graph isolation removes the capability entirely, which is a stronger guarantee for this specific risk.

## Decision: `mistralai` official client with an explicit, documented timeout

**Decision**: Use Mistral's official Python client library where available, wrapped in `mistral_client.py` with an explicit request timeout (default 45s) and a single retry on transient network errors only (not on rate-limit or content errors) before surfacing an `InvestigationFailure`.

**Rationale**: FR-007 requires a clear, distinguishable failure state without silently retrying indefinitely — one bounded retry for genuinely transient failures balances resilience against the "never silently retry indefinitely" requirement.

**Alternatives considered**: No retry at all (rejected — a single transient network blip would unnecessarily surface as a failure requiring manual re-investigation); unlimited/exponential-backoff retry (rejected — directly contradicts FR-007's "without silently retrying indefinitely").
