# AI-Powered Healthcare Claims Intelligence & Data Quality Platform

## Document Status
Current implementation baseline

## Purpose
Project handoff, development tracking, and AI-assisted implementation guidance

## Primary AI Coding Tools
- Claude Code
- VS Code Copilot

## Stack
- Backend: Python / FastAPI
- Frontend: React + TypeScript + Vite
- Domain: Healthcare claims, data quality, anomaly detection, risk intelligence

---

# 1. Executive Summary

This project is an AI-assisted healthcare claims intelligence platform designed to process healthcare claims data, identify data-quality problems and anomalous behavior, engineer useful features, evaluate investigation risk, support human investigation, and provide a dashboard for monitoring incidents and system behavior.

The repository contains a substantial modular backend organized around:

- Data ingestion
- Data profiling
- Data cleaning
- Data quality evaluation
- Baseline generation
- Anomaly detection
- Feature engineering
- Risk modeling
- Investigation assistance through an LLM
- Incident management
- Human-in-the-loop workflows
- Remediation
- Revalidation
- Audit/history
- Simulation/demo pipelines

The project also includes a dedicated frontend with dashboards, incident views, investigation views, live monitoring, upload functionality, simulation, history, and settings.

The repository contains trained ML artifacts, generated datasets, benchmark reports, quality reports, feature datasets, risk datasets, and automated tests, indicating that the implementation has progressed substantially beyond a basic prototype.

---

# 2. Core Problem Being Solved

Healthcare claims data can contain:

- Missing or incomplete values
- Invalid values
- Duplicate records
- Incorrect data types
- Date inconsistencies
- Unexpected distributions
- Statistical anomalies
- Behavioral anomalies
- Data-quality degradation
- Potentially high-risk claims or investigation candidates

A conventional pipeline may identify these problems but leave investigators with a large number of raw alerts.

This project attempts to create a more complete intelligence pipeline:

Raw Claims
→ Ingestion
→ Profiling
→ Cleaning / Standardization
→ Data Quality Assessment
→ Baseline Comparison
→ Feature Engineering
→ Anomaly Detection
→ Risk Scoring
→ Investigation
→ Human Review
→ Remediation
→ Revalidation
→ Audit / Historical Tracking
→ Dashboard

The key design goal is not just to detect anomalies; it is to move from:

Raw data → trustworthy data → abnormal behaviour → prioritized investigation → human decision → remediation → verification → audit trail.

---

# 3. Major System Capabilities

## 3.1 Data Ingestion
The repository contains an ingestion layer with:

- app/ingestion/router.py
- app/ingestion/service.py
- app/ingestion/watcher.py

The project also maintains raw, cleaned, processed, demo, sampled, and uploaded datasets.

---

# 4. Data Engineering Layer

The data-engineering subsystem contains functionality for:

- Categorization
- Cleaning
- Date standardization
- Data-type conversion
- Duplicate detection
- Invalid-value detection
- Profiling
- Sampling
- Standardization
- Quality issue logging
- Report generation

Relevant implementation modules include:

- app/data_engineering/categorization.py
- app/data_engineering/cleaning.py
- app/data_engineering/cleaning_service.py
- app/data_engineering/date_standardization.py
- app/data_engineering/dtype_conversion.py
- app/data_engineering/duplicate_detection.py
- app/data_engineering/invalid_value_detection.py
- app/data_engineering/profiling.py
- app/data_engineering/profiling_service.py
- app/data_engineering/quality_issue_log.py
- app/data_engineering/report_writer.py
- app/data_engineering/sampling_service.py
- app/data_engineering/standardization.py
- app/data_engineering/router.py

The repository also contains generated profiling and cleaning reports, including:

- profiling_report.json
- profiling_report.md
- cleaning_run_summary.json
- quality_issues.json
- quality_results.json

This provides strong evidence that the data-engineering stage is already substantially implemented.

---

# 5. Data Quality System

The quality subsystem contains:

- app/quality/bands.py
- app/quality/completeness_calibration.py
- app/quality/data_loader.py
- app/quality/gx_result_utils.py
- app/quality/quality_results_log.py
- app/quality/scoring_service.py
- app/quality/suite_builder.py
- app/quality/expectations/
  - completeness.py
  - freshness.py
  - range_checks.py
  - uniqueness.py
  - validity.py

The system is designed to evaluate several dimensions of data quality, including:

- Completeness
- Freshness
- Range validity
- Uniqueness
- General validity

The presence of scoring, calibration, expectation construction, and result logging indicates that this is intended to be a reusable quality engine rather than a collection of isolated checks.

## 5.1 Core Data Quality Metrics

The project computes file-level quality indicators as follows:

### Missing Rate

$$
\text{MissingRate} = \frac{\text{missing cells}}{\text{total cells}} \times 100
$$

### Duplicate Rate

$$
\text{DuplicateRate} = \frac{\text{duplicate rows}}{\text{total rows}} \times 100
$$

These metrics are used to evaluate the batch-level quality status before the final composite score is produced.

## 5.2 Threshold Bands

The system converts computed rates into PASS / WARNING / CRITICAL bands.

### Missing Rate Banding

$$
\text{Band} =
\begin{cases}
\text{PASS}, & \text{if } p < 2\% \\
\text{WARNING}, & \text{if } 2\% \le p < 5\% \\
\text{CRITICAL}, & \text{if } p > 5\%
\end{cases}
$$

### Duplicate Rate Banding

$$
\text{Band} =
\begin{cases}
\text{PASS}, & \text{if } p = 0\% \\
\text{WARNING}, & \text{if } 0\% < p \le 1\% \\
\text{CRITICAL}, & \text{if } p > 1\%
\end{cases}
$$

## 5.3 Total Data Quality Score

The final overall data quality score is computed using a weighted aggregate of the expectation-type averages.

Each band is mapped to a numeric score:

- PASS = 100
- WARNING = 50
- CRITICAL = 0

For each expectation type $t$:

$$
\text{typeAvg}_t = \frac{\sum \text{bandScore}}{\text{count of checks in type } t}
$$

Then the overall composite score is:

$$
\text{CompositeQuality} = \sum_t w_t \cdot \text{typeAvg}_t
$$

where $w_t$ is the weight assigned to expectation type $t$.

If no explicit weights are provided, the system defaults to equal weighting across the types present:

$$
w_t = \frac{1}{N}
$$

where $N$ is the number of expectation types currently present in the results.

The final score is also clipped to the valid range:

$$
0 \le \text{CompositeQuality} \le 100
$$

This is the project’s actual overall total-data-quality formula, implemented in the scoring engine.

---

# 6. Baseline System

The baseline subsystem contains:

- app/baseline/amount_baseline.py
- app/baseline/data_health_baseline.py
- app/baseline/length_of_stay_baseline.py
- app/baseline/volume_baseline.py
- app/baseline/snapshot_service.py
- app/baseline/snapshot_log.py
- app/baseline/window_definition.py
- app/baseline/service.py
- app/baseline/router.py

The purpose is to establish expected historical behaviour against which new data can be compared.

The repository also contains:

- data/reports/baseline_snapshot.json

This is important because anomaly detection should not depend exclusively on generic statistical thresholds.

A mature implementation should compare current observations against appropriate historical baselines.

---

# 7. Anomaly Detection

The anomaly subsystem is one of the major components.

It contains implementations for:

- HBOS
- IQR
- Isolation Forest
- Local Outlier Factor
- Model selection
- Benchmarking
- Injection testing
- Window enrichment
- Data loading
- Anomaly routing

Structure:

- app/anomaly/benchmark.py
- app/anomaly/data_loading.py
- app/anomaly/hbos.py
- app/anomaly/injection_harness.py
- app/anomaly/iqr.py
- app/anomaly/isolation_forest.py
- app/anomaly/lof.py
- app/anomaly/model_selection.py
- app/anomaly/router.py
- app/anomaly/schemas.py
- app/anomaly/window_enrichment.py

The project also contains persisted models and anomaly outputs, indicating that anomaly detection has progressed into model comparison and evaluation rather than stopping at a single algorithm.

---

# 8. Feature Engineering

The feature subsystem supports both claim-level and window-level features.

## Claim-level features
- amount_ratios.py
- categorical_encoding.py
- date_features.py
- length_of_stay.py
- provider_frequency.py

## Window-level features
- deviation_features.py
- window_aggregates.py

There is also a feature-selection pipeline containing:

- stage1_structural.py
- stage2_statistical.py
- stage3_model_based.py
- temporal_split.py
- selection_service.py
- drop_decision_log.py

This suggests a multi-stage feature-selection architecture rather than simply passing every available column into the models.

Generated artifacts include:

- data/features/claim_features.csv
- data/features/window_features.csv
- data/features/selected_feature_set.json
- data/features/feature_drop_decisions.json
- data/features/temporal_split.json

---

# 9. Risk Modeling

The risk system is separate from anomaly detection.

It contains:

- app/risk/benchmark/
- app/risk/dataset/
- app/risk/scoring/

The benchmark layer includes:

- Logistic Regression
- Random Forest
- XGBoost
- Model selection
- Calibration
- Benchmark execution
- Benchmark logging

Persisted models include:

- data/models/risk/logistic_regression.pkl
- data/models/risk/random_forest.pkl
- data/models/risk/xgboost.pkl
- data/models/risk/demo_risk_xgboost.pkl

The project also stores:

- data/reports/risk_benchmark_results.json
- data/risk/risk_dataset.csv

The scoring subsystem contains:

- Business impact
- Percentile scaling
- Severity
- Priority
- Weight configuration

This implies the intended flow is:

Predictive model
→ risk score
→ severity
→ business impact
→ priority

---

# 10. LLM Investigation Layer

The project contains a dedicated LLM subsystem:

- app/llm/errors.py
- app/llm/investigation_log.py
- app/llm/investigation_service.py
- app/llm/mistral_client.py
- app/llm/payload_builder.py
- app/llm/prompt_templates.py
- app/llm/response_parser.py
- app/llm/router.py
- app/llm/schemas.py

This is a major architectural component.

The intended responsibility appears to be using an LLM to assist investigators after an anomaly or risk event has been identified.

The system is structured around:

Investigation Input
→ Payload Builder
→ LLM Client
→ Prompt Template
→ LLM Response
→ Response Parser
→ Investigation Result
→ Investigation Log

The repository also contains:

- data/reports/llm_investigations.json

---

# 11. Audit and History

The audit subsystem contains:

- app/audit/aggregation_service.py
- app/audit/baseline_passthrough.py
- app/audit/history_service.py
- app/audit/models.py
- app/audit/registry.py
- app/audit/router.py
- app/audit/schemas.py

This is important for traceability.

The system is intended to retain information about processing and decisions rather than treating each execution as an isolated operation.

---

# 12. Human-in-the-Loop System

The project explicitly contains a HITL subsystem:

- app/hitl/accept_service.py
- app/hitl/reject_service.py
- app/hitl/recalculation_service.py
- app/hitl/state_machine.py
- app/hitl/models.py
- app/hitl/schemas.py
- app/hitl/router.py

This is a key part of the intended architecture.

The system should not automatically assume that an ML or LLM result is the final decision.

Instead:

AI Detection
→ Investigation
→ Human Review
- Accept
- Reject
→ Recalculation / State Transition

---

# 13. Remediation

The remediation subsystem contains:

- app/remediation/duplicate_handler.py
- app/remediation/imputation_handler.py
- app/remediation/manual_handler.py
- app/remediation/remediation_service.py
- app/remediation/status_mapping_handler.py
- app/remediation/precedence.py
- app/remediation/models.py
- app/remediation/schemas.py
- app/remediation/config/
  - duplicate_flagging_rules.yaml
  - imputation_rules.yaml
  - status_mapping_rules.yaml

This indicates that the project goes beyond detecting data problems.

It has an explicit remediation layer for:

- Duplicate-related issues
- Imputation
- Manual remediation
- Status mapping

---

# 14. Revalidation

After remediation, the project contains a revalidation subsystem:

- app/revalidation/comparison_service.py
- app/revalidation/recompute_service.py
- app/revalidation/resolution_criteria.py
- app/revalidation/revalidation_service.py
- app/revalidation/models.py
- app/revalidation/schemas.py
- app/revalidation/router.py

The intended flow is:

Issue Detected
→ Remediation
→ Recompute
→ Compare Before / After
→ Resolution Criteria
→ Resolved / Unresolved

---

# 15. Incident Management

The incident subsystem contains:

- app/incidents/models.py
- app/incidents/router.py
- app/incidents/schemas.py
- app/incidents/service.py

The frontend also contains a dedicated incidents page and incident-related dashboard components.

This suggests detected problems can be surfaced as operational incidents rather than remaining buried in model outputs.

---

# 16. Demo and Simulation System

The project contains a significant demonstration/simulation layer:

- app/demo/anomaly_runner.py
- app/demo/batches.py
- app/demo/column_profile.py
- app/demo/generator.py
- app/demo/narrative.py
- app/demo/pipeline.py
- app/demo/quality_runner.py
- app/demo/risk_model.py
- app/demo/simulator.py
- app/demo/upload.py

This is useful for demonstrating the complete system without requiring a live production claims source.

---

# 17. Frontend

The frontend is a React/TypeScript/Vite-style application.

The structure contains:

- frontend/src/App.tsx
- frontend/src/main.tsx
- frontend/src/components/
- frontend/src/data/
- frontend/src/hooks/
- frontend/src/layouts/
- frontend/src/pages/
- frontend/src/services/
- frontend/src/types/
- frontend/src/utils/

The application contains pages for:

- Dashboard
- History
- Incidents
- Investigation
- Live Monitor
- Settings
- Simulator
- Upload

---

# 18. Frontend Service Layer

The frontend contains service modules such as:

- claimsService.ts
- incidentService.ts
- streamSimulatorService.ts

There is also a live-stream hook:

- useLiveStream.ts

---

# 19. Data and ML Artifacts

The repository contains several categories of persisted artifacts.

## Raw data
- data/raw/inpatient.csv

## Cleaned data
- data/cleaned/inpatient_cleaned.csv

## Feature data
- data/features/

## Risk data
- data/risk/risk_dataset.csv

## ML models
- data/models/
- data/models/risk/

## Reports
- data/reports/

This means the repository already has an end-to-end artifact lifecycle rather than only source code.

---

# 20. Testing

The repository contains a large automated test structure.

Tests cover:

- anomaly detection
- audit
- baselines
- data engineering
- features
- demo workflows

This breadth of automated coverage is one of the strongest indicators that the project is considerably advanced.

---

# 21. Current Implementation Assessment

## Strongly implemented / clearly present

| Area | Status |
|---|---|
| Backend modular architecture | High |
| FastAPI application structure | High |
| Data ingestion layer | High |
| Data engineering | High |
| Data profiling | High |
| Data cleaning | High |
| Data quality framework | High |
| Baseline framework | High |
| Anomaly algorithms | High |
| Anomaly benchmarking | High |
| Feature engineering | High |
| Feature selection | High |
| Risk models | High |
| Risk benchmarking | High |
| LLM investigation layer | High |
| Audit/history architecture | High |
| HITL architecture | High |
| Remediation architecture | High |
| Revalidation architecture | High |
| Incident architecture | High |
| Demo/simulation system | High |
| React frontend structure | High |
| Dashboard UI | High |
| Automated tests | High |

---

# 22. What Is Not Safe to Claim Yet

The directory tree alone does not prove:

- Every API endpoint works correctly.
- Every frontend page is connected to the real backend.
- Every ML model performs at acceptable accuracy.
- Every integration works from a clean installation.
- Production authentication is implemented.
- Production deployment is complete.
- Database persistence is production-ready.
- LLM calls work with real credentials.
- All frontend mock data has been replaced.
- Every test currently passes.
- All features are wired together end-to-end.

These need runtime verification.

---

# 23. Practical Completion Estimate

## Architecture / implementation surface
Estimated at 85–90% complete.

The project already contains nearly all major architectural subsystems expected in the intended solution.

## Functional verification
Not yet determinable from the repository tree alone.

## Production readiness
Lower than the architectural completion percentage.

A responsible current project-status statement is:

> The project has reached an advanced prototype / pre-production stage, with the majority of core architectural components implemented. The remaining work is primarily focused on integration verification, end-to-end validation, UI/backend synchronization, robustness, deployment readiness, and final testing.

---

# 24. Recommended Remaining Work

## Phase 1 — Establish a Known-Good Baseline
Before adding anything:

1. Run backend tests.
2. Run frontend build.
3. Start backend.
4. Start frontend.
5. Verify API connectivity.
6. Verify dashboard.
7. Verify upload.
8. Verify simulation.
9. Verify incident flow.
10. Verify investigation flow.
11. Record every failure.

---

## Phase 2 — End-to-End Pipeline Verification
Verify:

Upload
→ Ingestion
→ Profiling
→ Cleaning
→ Quality
→ Baseline
→ Features
→ Anomaly
→ Risk
→ Investigation
→ Incident
→ HITL
→ Remediation
→ Revalidation
→ Audit

---

## Phase 3 — Frontend Integration
The next implementation task should be to determine exactly which screens are:

1. fully API-backed
2. partially API-backed
3. simulation-backed
4. still mock-data-backed

---

## Phase 4 — API Contract Validation
Document every backend route.

For each endpoint record:

- Endpoint
- HTTP method
- Request schema
- Response schema
- Authentication requirement
- Database/data source
- Frontend consumer
- Error cases
- Test coverage

---

## Phase 5 — ML Validation
For each model record:

- Model
- Input features
- Training dataset
- Target
- Train/test strategy
- Metrics
- Benchmark result
- Calibration
- Known limitations
- Saved artifact
- Inference path

---

## Phase 6 — LLM Safety and Reliability
The LLM layer should be treated as an investigation assistant rather than the source of truth.

Recommended architecture:

Deterministic Evidence
→ Structured Prompt
→ LLM
→ Structured Response
→ Validation
→ Investigator

---

## Phase 7 — Production Hardening
Remaining production-level areas should include:

- Authentication
- Authorization
- Secret management
- Environment configuration
- Logging
- Error handling
- Rate limiting
- Input validation
- File validation
- Database migration strategy
- Monitoring
- Deployment configuration
- CORS configuration
- Secure LLM credentials
- Backup/recovery
- Model versioning

---

# 25. Definition of Done

The project should be considered functionally complete only when:

- Backend starts from a clean environment.
- Frontend builds from a clean environment.
- Automated tests pass.
- Data upload works.
- Profiling works.
- Cleaning works.
- Data-quality scoring works.
- Baseline creation/comparison works.
- Anomaly detection works.
- Risk scoring works.
- Investigation works.
- Incidents are created correctly.
- HITL accept/reject works.
- Remediation works.
- Revalidation works.
- Audit/history works.
- Dashboard displays backend-derived information.
- Live monitor works.
- Simulator works.
- Error cases are handled.
- Documentation matches the implementation.
- No critical secrets are committed.
- Production configuration is documented.

---

# 26. Master AI Development Prompt

Use the following prompt as the primary context for Claude Code or VS Code Copilot.

## MASTER PROJECT PROMPT

You are working inside an existing healthcare claims intelligence and data-quality platform.

Your job is to CONTINUE the existing implementation, not redesign the entire application.

### Project Purpose
The system processes healthcare claims/inpatient-style data and provides:

1. Data ingestion
2. Data profiling
3. Data cleaning
4. Data quality evaluation
5. Historical baselines
6. Anomaly detection
7. Feature engineering
8. Feature selection
9. Risk modeling
10. LLM-assisted investigation
11. Incident management
12. Human-in-the-loop decisions
13. Remediation
14. Revalidation
15. Audit/history
16. Simulation/demo workflows
17. Operational dashboard

### Existing Backend Domains
The backend contains modules for:

- anomaly
- audit
- baseline
- core
- data_engineering
- demo
- features
- hitl
- incidents
- ingestion
- llm
- models
- quality
- remediation
- revalidation
- risk
- simulation
- shared

### Existing Frontend Domains
The frontend contains:

- Dashboard
- History
- Incidents
- Investigation
- Live Monitor
- Settings
- Simulator
- Upload

### Important Rule
DO NOT rewrite the application from scratch.

DO NOT replace the architecture simply because you prefer another architecture.

DO NOT introduce a new framework unless explicitly requested.

DO NOT delete existing modules because they appear unused.

DO NOT replace working functionality with mock implementations.

DO NOT modify unrelated modules while implementing a requested feature.

---

# 27. AI Working Protocol

## Before changing code:

### Step 1 — Understand
Inspect:
- repository structure
- relevant source files
- schemas
- routers
- services
- models
- tests
- frontend consumers
- configuration

### Step 2 — Trace
For the requested feature, trace:

Frontend
→ API
→ Router
→ Service
→ Model / Pipeline
→ Persistence / Artifact
→ Response
→ Frontend

### Step 3 — Identify existing implementation
Search the repository before creating anything.

If functionality already exists:
Extend it instead of duplicating it.

### Step 4 — Identify contracts
Before modifying code, determine:
- request schema
- response schema
- internal service interface
- database/artifact interface
- frontend TypeScript type
- existing tests

### Step 5 — Implement minimally
Change the smallest number of files necessary.

### Step 6 — Test
After implementation:
1. Run relevant unit tests.
2. Run integration tests.
3. Run type checking.
4. Run frontend build if frontend changed.
5. Verify the actual API response.
6. Verify the UI if applicable.

### Step 7 — Report
At the end provide:

- IMPLEMENTED
- FILES CHANGED
- TESTS RUN
- TEST RESULTS
- KNOWN ISSUES
- NEXT RECOMMENDED STEP

---

# 28. AI Rules for This Project

## Rule 1 — Inspect before editing
Never make assumptions about how a feature works. Search first.

## Rule 2 — Preserve architecture
Use existing routers, services, schemas, models, logging, configuration, and utilities where appropriate.

## Rule 3 — No duplicate implementations
Before creating new service, router, model, or schema files, search for an existing equivalent.

## Rule 4 — No fake completion
Never say “this is fully implemented” unless the implementation has actually been tested.

## Rule 5 — No hidden fallback
Do not silently fall back from real API data to mock data unless the existing architecture explicitly requires it.

## Rule 6 — Do not destroy mock/demo functionality
The simulator and demo system are intentional project components.

## Rule 7 — Preserve auditability
Any meaningful processing decision should remain traceable.

## Rule 8 — ML changes require validation
If changing features, models, thresholds, labels, scoring, or training logic, run the relevant tests and benchmark where possible.

## Rule 9 — LLM output is not ground truth
LLM-generated conclusions must be based on supplied evidence.

## Rule 10 — Frontend changes must respect backend contracts
Do not create arbitrary frontend fields that do not exist in backend responses.

---

# 29. When Implementing a New Feature

Use this sequence:

1. Understand requirement
2. Search repository
3. Find existing implementation
4. Identify affected modules
5. Identify API contract
6. Identify frontend consumers
7. Identify tests
8. Implement smallest change
9. Run tests
10. Fix failures
11. Run build
12. Verify end-to-end
13. Document change

---

# 30. Bug-Fix Protocol

When fixing a bug:

1. Reproduce it.
2. Record expected and actual results.
3. Identify the root cause.
4. Fix the root cause, not only the symptom.
5. Add a regression test.
6. Verify the original failure is fixed.
7. Run related tests.

---

# 31. Frontend Development Rules

When modifying React:

- Preserve existing component structure.
- Reuse existing UI components.
- Reuse layout patterns.
- Reuse formatting utilities.
- Reuse existing types.
- Avoid unnecessary state duplication.
- Avoid hard-coded API responses.
- Do not introduce mock data into production paths.
- Keep loading/error/empty states.
- Preserve responsive behavior.
- Run TypeScript checks.
- Run the production build.

---

# 32. Backend Development Rules

When modifying Python/FastAPI:

- Follow existing router/service/schema separation.
- Keep business logic out of routers where possible.
- Reuse existing models.
- Preserve validation.
- Preserve logging.
- Preserve error handling.
- Add tests for new behavior.
- Avoid global mutable state.
- Avoid hard-coded paths.
- Use existing configuration mechanisms.

---

# 33. Data and ML Development Rules

When modifying the ML pipeline:

Raw data
→ Validated data
→ Features
→ Train/test split
→ Model
→ Evaluation
→ Calibration
→ Artifact
→ Inference

Always check for:

- leakage
- temporal leakage
- inconsistent preprocessing
- missing values
- feature mismatch
- train/inference mismatch
- model serialization compatibility

---

# 34. Current Priority Order

Unless the user explicitly gives a different priority, work in this order:

1. Get the entire existing system running reliably.
2. Verify backend ↔ frontend integration.
3. Remove accidental mock-data dependencies.
4. Verify complete end-to-end pipeline.
5. Fix failing tests.
6. Improve reliability and error handling.
7. Improve production readiness.
8. Only then perform cosmetic/refactoring work.

---

# 35. AI Response Format

Every time you finish a task, respond using:

## Task
<what was requested>

## Analysis
<what already existed>

## Changes
<exact changes>

## Files Changed
<list>

## Tests
<commands/tests executed>

## Result
<PASS / PARTIAL / FAIL>

## Remaining Issues
<issues>

## Next Step
<recommended next action>

---

# 36. Special Instruction for Claude Code

Claude Code has permission to inspect and modify the repository.

Before making substantial modifications:

1. Inspect the repository.
2. Read the relevant implementation.
3. Read relevant tests.
4. Explain the planned change briefly.
5. Make the change.
6. Test it.
7. Show the result.

---

# 37. Special Instruction for VS Code Copilot

When generating code suggestions:

- Prefer existing project abstractions.
- Search nearby modules for patterns.
- Match naming conventions.
- Match existing schema conventions.
- Match existing error handling.
- Match existing API patterns.
- Match existing TypeScript types.
- Do not generate an entirely new architecture.

---

# 38. Project Handoff Summary

The project is not a simple anomaly detector.

Its intended architecture is a complete claims intelligence and data-quality workflow:

Claims Data
→ Ingestion
→ Profiling & Cleaning
→ Data Quality
→ Historical Baseline
→ Feature Engineering
→ Anomaly Detection
→ Risk Scoring
→ LLM Investigation
→ Incidents
→ Human-in-the-Loop
→ Remediation
→ Revalidation
→ Audit / History
→ Operational Dashboard

---

# 39. Final Development Principle

The AI coding agent must behave as a careful senior engineer joining an existing team, not as a code generator starting a new project.

The priority is:

Understand → Preserve → Extend → Test → Verify → Document

Not:

Rewrite → Hope → Break → Patch

The existing repository already contains substantial implementation across the backend, ML pipeline, data pipeline, investigation workflow, remediation workflow, frontend, artifacts, and tests. The next stage should focus on integration, verification, correctness, and production hardening, rather than rebuilding the foundation.

---

## Key Formula Summary

This is the most important formula cluster to retain:

$$
\text{MissingRate} = \frac{\text{missing cells}}{\text{total cells}} \times 100
$$

$$
\text{DuplicateRate} = \frac{\text{duplicate rows}}{\text{total rows}} \times 100
$$

$$
\text{Band} =
\begin{cases}
\text{PASS}, & p < 2\% \\
\text{WARNING}, & 2\% \le p < 5\% \\
\text{CRITICAL}, & p > 5\%
\end{cases}
\quad \text{for MissingRate}
$$

$$
\text{Band} =
\begin{cases}
\text{PASS}, & p = 0\% \\
\text{WARNING}, & 0\% < p \le 1\% \\
\text{CRITICAL}, & p > 1\%
\end{cases}
\quad \text{for DuplicateRate}
$$

$$
\text{CompositeQuality} = \sum_t w_t \cdot \text{typeAvg}_t
$$

$$
\text{typeAvg}_t = \frac{\sum \text{bandScore}}{\text{count of checks in type } t}
$$

with band scores:

- PASS = 100
- WARNING = 50
- CRITICAL = 0

---

# 40. Final Notes

This document is intended to serve as a structured project master document, implementation status baseline, and AI handoff reference. It should be treated as a working engineering brief rather than a final production specification.

It is suitable for:

- technical handoff
- onboarding
- project planning
- AI coding guidance
- implementation review
- status reporting

The next practical step is to validate the live system and confirm which parts of the architecture are fully working versus still requiring integration and runtime verification.
