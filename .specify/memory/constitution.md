# PayerGuard Constitution

## Core Principles

### I. Empirical Model Selection
No model is chosen in advance because it "sounds good." Anomaly detectors
(IQR, HBOS, Isolation Forest, LOF) and risk classifiers (Logistic
Regression, Random Forest, XGBoost) are always benchmarked against real,
project-derived data before one is promoted to production use. A model
becomes the production choice only when a documented benchmark run shows
it wins on the metrics defined for that problem (anomaly: precision/
recall/F1/FPR/latency; risk: recall + PR-AUC prioritized over raw
accuracy, per MVP_CONTEXT.md Phase 11). If a benchmark contradicts the
expected outcome (e.g. HBOS does not win), the benchmark result governs,
not the plan.

### II. No Fabricated Values (NON-NEGOTIABLE)
Every threshold, baseline, score, and statistic used anywhere in the
pipeline must be computed from the real `data/raw/inpatient.csv` dataset
(or data derived from it) — never hardcoded, assumed, or invented as a
placeholder. Where a number in MVP_CONTEXT.md or this constitution looks
like a fact (e.g. "58,066 rows", "CLM_PMT_AMT median $1,481.72"), it is a
measured fact about the current dataset, provided for context — not a
constant to bake into code. If a derivation (e.g. the SLA-breach label in
Phase 8) requires a judgment call, that judgment must be written down and
justified, not silently assumed.

### III. Deterministic-First, ML-Second
Great Expectations quality checks always run before and independently of
any ML model. Deterministic validation is the floor every claim must
clear; anomaly and risk scoring augment it, they do not replace it. When
a deterministic check and a model disagree, the deterministic check's
evidence is treated as ground truth in the audit trail.

### IV. Human-in-the-Loop Before Any Write
No remediation touches claim data without an explicit human accept
decision on the LLM's investigation output. The LLM (Mistral) proposes;
it never executes. Reject decisions must capture feedback and trigger
recalculation, not be silently dropped.

### V. Constrained, Auditable Remediation
The remediation engine only performs actions with a pre-approved,
deterministic mapping (duplicate flagging, approved imputation, approved
status mapping). Anything without an approved mapping is marked "Manual
Action Required" — the system never invents a fix. Every remediation is
followed by revalidation (GX + anomaly + risk) with an explicit
before/after comparison, and every step (check, score, LLM output, human
decision, remediation, revalidation) is written to the audit log.

### VI. Modular Backend, No Monolith
The backend is organized as one module per domain (ingestion,
data_engineering, quality, baseline, features, anomaly, risk, llm,
incidents, hitl, remediation, revalidation, simulation, audit), each
owning its own models, schemas, service logic, router, and tests.
`app/main.py` only wires routers together. New functionality gets its own
file in the relevant module, not a growing addition to an existing large
file.

### VII. Temporal Integrity
This dataset spans 2015–2022 and is time-dependent. Any train/validation/
test split for the risk model uses a temporal split (older 70% / next 15%
/ latest 15%), never a random shuffle. Any window-based or baseline
comparison logic must respect chronological order — no future information
may leak into a past prediction.

## Scope Discipline

MVP_CONTEXT.md (repo root) is the single source of truth for scope. Only
`data/raw/inpatient.csv` is in scope as a dataset. Live claims streaming
is explicitly out of scope — ingestion is manual upload plus continuous/
repeated batch ingestion over the same file-based flow, never a socket or
live streaming API. Frontend implementation is deferred until the backend
pipeline is complete and the user specifies pages/UX; when built, it ships
as its own Docker container (`frontend` service in `docker-compose.yml`),
matching the backend's deployment pattern. Gemini is fully replaced by
Mistral throughout — do not reintroduce it.

## Development Workflow

Every feature (Phases 1–17 of MVP_CONTEXT.md) is worked as its own
spec-driven cycle: `/speckit.specify` → `/speckit.plan` → `/speckit.tasks`
→ `/speckit.implement`, using the templates under `.specify/templates/`.
A phase's plan must reference the relevant MVP_CONTEXT.md section instead
of restating it. Tests belonging to a phase (see MVP_CONTEXT.md Phase 16
categories: data, ML, LLM, HITL, ingestion) are written alongside that
phase's implementation, not deferred to the end.

## Governance

This constitution supersedes ad hoc practice for this repository.
Amendments require updating this file and noting the change in
`docs/architecture.md` or a dated changelog entry — silent edits are not
permitted. Any conflict between this constitution and MVP_CONTEXT.md
should be resolved in favor of MVP_CONTEXT.md for scope/data questions and
in favor of this constitution for process/engineering-discipline
questions; if genuinely ambiguous, flag it rather than guessing.

**Version**: 1.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
