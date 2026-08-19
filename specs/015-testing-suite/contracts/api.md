# API Contracts: Testing Suite

**Not applicable.** This feature adds no new backend module, router, or external interface — it is entirely test code (`backend/tests/`) plus one documentation artifact (`docs/testing/phase15_coverage_map.md`). Per the plan workflow's guidance to skip contracts for purely internal projects, no endpoint contracts are defined here.

Every capability this feature exercises is already contracted by its owning phase:
- HITL round-trips: [Phase 12 contracts](../../012-incident-management-hitl/contracts/api.md), [Phase 13 contracts](../../013-remediation-engine/contracts/api.md), [Phase 14 contracts](../../014-revalidation/contracts/api.md)
- Anomaly/Risk/LLM tests: [Phase 7](../../007-anomaly-detection-benchmark/contracts/api.md), [Phase 9](../../009-risk-model-benchmark/contracts/api.md), [Phase 11](../../011-llm-investigation/contracts/api.md) contracts
