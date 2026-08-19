# PayerGuard — MVP Context Document

Status: In progress (v3 — 15 of 16 active specs implemented; see Section 9 for a condensed shareable status snapshot, Section 8 for the full changelog)
Last updated: 2026-08-18
Owner: AAT2

This document is the single source of truth for the PayerGuard MVP. Any human or AI agent picking up this project should be able to read this file top to bottom and understand what the project is, what data it uses, what the target architecture is, what is explicitly in and out of scope for the MVP, the order in which work should be done, and — as of v3 — exactly how much of it is actually done vs. still open (Section 9). Backend implementation is well underway via spec-driven development (`/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`); the frontend and deployment phases are not. If you only have time to read one section, read Section 9.

---

## 1. What is PayerGuard (project context)

PayerGuard is a claims quality and risk monitoring system for healthcare claims data. It takes raw insurance claims (initially CMS Medicare inpatient claims), runs them through a pipeline that:

1. Validates data quality deterministically (Great Expectations).
2. Detects statistical/behavioral anomalies in claim volume, amounts, and data quality using benchmarked anomaly-detection models.
3. Scores operational risk — specifically, the likelihood that a claim or processing window warrants human investigation — using benchmarked supervised ML models.
4. Escalates high-risk findings into structured "incidents," each carrying a computed Severity, Risk, Business Impact, and overall Priority.
5. Uses an LLM (Mistral) to investigate each incident and produce a root-cause explanation, evidence summary, business impact assessment, and a recommended (not auto-executed) fix.
6. Puts a human in the loop to accept or reject the LLM's recommendation.
7. On acceptance, runs a constrained, deterministic remediation engine against only the affected claims, then re-validates and shows before/after quality, anomaly, and risk scores.
8. Maintains full audit history of every decision (deterministic check, model score, LLM recommendation, human decision, remediation, revalidation).

The system is built to demonstrate a defensible, empirically-driven, evidence-first story: every model choice (which anomaly detector, which risk classifier) is the result of a benchmark on this project's actual data, not an assumption made in advance, and every metric the pipeline reports is either computed from real data or explicitly marked unavailable — never fabricated. Where a required signal (a field, a label, a metric) doesn't actually exist in the data, the system says so rather than inventing a plausible-looking number.

### Why this matters / the narrative
"We benchmarked HBOS vs Isolation Forest vs LOF vs an IQR baseline for anomaly detection, and Logistic Regression vs Random Forest vs XGBoost for risk prediction, and selected the production model based on validation performance on our own data. Where the data couldn't support a metric we wanted (an SLA-turnaround target, for instance), we said so and built a defensible alternative instead of faking it."

---

## 2. Dataset

### 2.1 Source
CMS Medicare **Inpatient Claims** Research Identifiable File (RIF) format — a single file, `inpatient.csv`, supplied manually by the user. This is the **only** dataset used for the MVP. There is no second dataset, no live external feed, and no additional CMS file (outpatient, carrier, etc.) in scope right now.

The file is **pipe-delimited** (`|`), not comma-delimited, despite the `.csv` extension. Any ingestion code must use `sep="|"`.

> **Naming note:** some planning material circulated for this project refers to the file as `inpatients.csv` (plural). The actual file supplied and profiled — the one sitting in `data/raw/` and referenced by every statistic in this document — is `inpatient.csv` (singular). Treat `inpatient.csv` as authoritative; if a plural reference shows up elsewhere, it's the same file.

### 2.2 Real, measured profile (from the actual file supplied)
These numbers were computed directly from `inpatient.csv` and must be treated as ground truth for baseline calculations — do not substitute assumed/synthetic numbers.

- **Rows (line-item grain):** 58,066 data rows, 197 columns.
- **Grain:** the file is at the **claim-line level**, not the claim level. Each row is one revenue-center line (`CLM_LINE_NUM`, `REV_CNTR`, `HCPCS_CD`) belonging to a claim.
- **Unique claims (`CLM_ID`):** 20,867.
- **Unique beneficiaries (`BENE_ID`):** 5,699.
- **Lines per claim:** mean 2.82, median 1, max 46 (heavily right-skewed — most claims have 1 line, a long tail has many).
- **Duplicate full rows:** 0.
- **Date range:** `CLM_FROM_DT` / `CLM_THRU_DT` / `CLM_ADMSN_DT` / `NCH_BENE_DSCHRG_DT` span **01-Apr-2015 to 31-Oct-2022**. Dates are stored as strings like `01-Apr-2015` (`DD-Mon-YYYY`), not ISO format — needs explicit parsing during standardization.
- **`CLM_PMT_AMT` (claim payment amount):** mean $13,638.31, median $1,481.72, std $35,993.91, min $62.44, max $598,716.31. Heavily right-skewed — use median/percentiles, not mean, for baselines.
- **`CLM_TOT_CHRG_AMT` (total charge amount):** identical distribution to `CLM_PMT_AMT` in this extract.
- **`PTNT_DSCHRG_STUS_CD`:** constant (100% = code `1`, "discharged home") in this extract — not usable as a variance signal, but still validated for schema conformance.
- **`CLM_DRG_CD` (diagnosis-related group):** 167 distinct values, ~5.5% missing.
- **`PRVDR_NUM` (provider number):** 4,876 distinct values, ~4.4% missing.
- **`CLM_IP_ADMSN_TYPE_CD`:** 3 categories — 1 (emergency, 43,089 rows), 3 (elective, 14,020 rows), 2 (urgent, 957 rows).
- **`PRVDR_STATE_CD`:** 51 distinct values (all US states + DC), reasonably spread.
- **`NCH_CLM_TYPE_CD`, `CLM_FREQ_CD`, `CLAIM_QUERY_CODE`, `CLM_MDCR_NON_PMT_RSN_CD`:** constant across the whole file — these are candidates for removal in Feature Selection Stage 1 (constant columns).
- **Fully-null columns (100% missing):** `OT_PHYSN_UPIN`, `OT_PHYSN_NPI`, `FI_CLM_ACTN_CD`, `FI_NUM`, `FI_CLM_PROC_DT`, `NCH_VRFD_NCVRD_STAY_FROM_DT`, `NCH_VRFD_NCVRD_STAY_THRU_DT`, `NCH_BENE_MDCR_BNFTS_EXHTD_DT_I`, `NCH_ACTV_OR_CVRD_LVL_CARE_THRU`, `CLM_UNCOMPD_CARE_PMT_AMT` — drop these outright.
- **Procedure code columns (`ICD_PRCDR_CD1`…`ICD_PRCDR_CD25` and paired `PRCDR_DTn`):** missingness increases sharply with position — `ICD_PRCDR_CD16` is already 98.3% missing, `ICD_PRCDR_CD25` is 99.9% missing. Only the first several procedure-code slots are usably populated; treat the rest as sparse/optional.
- **`ADMTG_DGNS_CD` (admitting diagnosis):** 72.2% missing. `PRNCPAL_DGNS_CD` (principal diagnosis): 0% missing — this is the more reliable diagnosis field.
- **`AT_PHYSN_NPI`, `ORG_NPI_NUM`:** 0% missing — reliable identifier fields.
- **`HCPCS_CD`:** 106 distinct procedure/service codes. **`REV_CNTR`:** only 2 distinct revenue-center codes in this extract.
- **`CLM_UTLZTN_DAY_CNT`:** mean 1.70, median 0, max 104 — utilization-day counts, mostly 0–1 with a long tail (long inpatient stays).
- **`NCH_WKLY_PROC_DT`:** 0% missing, **but this field is a fixed weekly batch-cutoff date, not an operational processing timestamp** — see Section 2.4 for why this rules it out as an SLA signal.

### 2.3 Column categories (only columns that actually exist in this file — no invented columns)

**Identifiers:** `BENE_ID`, `CLM_ID`, `PRVDR_NUM`, `ORG_NPI_NUM`, `AT_PHYSN_NPI`, `OP_PHYSN_NPI`, `FI_NUM`

**Dates:** `CLM_FROM_DT`, `CLM_THRU_DT`, `NCH_WKLY_PROC_DT`, `FI_CLM_PROC_DT` (100% null — unusable), `CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT`, plus 25 paired `PRCDR_DTn` procedure dates

**Amounts (numerical):** `CLM_PMT_AMT`, `NCH_PRMRY_PYR_CLM_PD_AMT`, `CLM_TOT_CHRG_AMT`, `CLM_PASS_THRU_PER_DIEM_AMT`, `NCH_BENE_IP_DDCTBL_AMT`, `NCH_BENE_PTA_COINSRNC_LBLTY_AM`, `NCH_BENE_BLOOD_DDCTBL_LBLTY_AM`, `NCH_PROFNL_CMPNT_CHRG_AMT`, `NCH_IP_NCVRD_CHRG_AMT`, `NCH_IP_TOT_DDCTN_AMT`, and the `CLM_TOT_PPS_CPTL_*` / `CLM_PPS_CPTL_*` family (capital payment components)

**Utilization / duration (numerical):** `CLM_UTLZTN_DAY_CNT`, `BENE_TOT_COINSRNC_DAYS_CNT`, `BENE_LRD_USED_CNT`, `CLM_NON_UTLZTN_DAYS_CNT`, `NCH_BLOOD_PNTS_FRNSHD_QTY` — these, plus `CLM_ADMSN_DT` → `NCH_BENE_DSCHRG_DT` (length of stay), are the only genuine duration signals in this dataset (see 2.4).

**Categorical / codes:** `NCH_NEAR_LINE_REC_IDENT_CD`, `NCH_CLM_TYPE_CD`, `CLAIM_QUERY_CODE`, `CLM_FAC_TYPE_CD`, `CLM_SRVC_CLSFCTN_TYPE_CD`, `CLM_FREQ_CD`, `CLM_MDCR_NON_PMT_RSN_CD`, `NCH_PRMRY_PYR_CD`, `PRVDR_STATE_CD`, `PTNT_DSCHRG_STUS_CD`, `CLM_PPS_IND_CD`, `CLM_IP_ADMSN_TYPE_CD`, `CLM_SRC_IP_ADMSN_CD`, `NCH_PTNT_STATUS_IND_CD`, `CLM_DRG_CD`, `CLM_DRG_OUTLIER_STAY_CD`, `HCPCS_CD`, `REV_CNTR`, `CLM_LINE_NUM`

**Diagnosis / procedure codes (high-cardinality, sparse):** `ADMTG_DGNS_CD`, `PRNCPAL_DGNS_CD`, `ICD_DGNS_CD1`…`ICD_DGNS_CD25` (+ `CLM_POA_IND_SWn` present-on-admission flags), `ICD_DGNS_E_CD1`…`ICD_DGNS_E_CD12`, `ICD_PRCDR_CD1`…`ICD_PRCDR_CD25`

**Candidate targets / labels — revised, see 2.4:** there is no pre-existing risk/fraud/SLA label in this file, and (unlike the original draft of this document assumed) **no genuine operational-turnaround field exists either.** The risk model's target must instead be an "investigation-worthy" label derived from quality-failure rate, anomaly frequency, and volume deviation — all of which are real, computable signals. See Section 2.4.

Columns not listed above but present in the file (there are 197 total) should be profiled and categorized the same way as part of Phase 1/2 — this section covers the columns already confirmed relevant; the full column catalog belongs in the generated data-profiling report, not duplicated here.

### 2.4 Why there is no SLA-breach target in this dataset (important — read before Phase 8)

An earlier draft of this document proposed deriving an SLA-breach label from "processing delay between `CLM_FROM_DT`/`CLM_THRU_DT`/`FI_CLM_PROC_DT`/`NCH_WKLY_PROC_DT`." That approach doesn't hold up, for two concrete reasons discovered by actually testing it against the data:

1. `FI_CLM_PROC_DT` is 100% null (see Section 2.2) — nothing can be derived from an entirely empty column.
2. `NCH_WKLY_PROC_DT`, the other candidate, looked promising (0% missing) but turns out to be a fixed weekly batch-cutoff date, not a real operational timestamp. Computing `NCH_WKLY_PROC_DT − CLM_THRU_DT` across all 58,066 rows produces a delay of exactly 1–7 days in every row, and `NCH_WKLY_PROC_DT` itself falls on a Friday in 100% of rows with zero exceptions. This is CMS's weekly claims-processing cadence, not a signal of how long any individual claim took to adjudicate — it carries no information about claim complexity, quality, or risk.

Conclusion: **this dataset has no genuine claims-adjudication-turnaround / SLA field.** Per the project's no-fabrication principle, the risk target is therefore **not** an "SLA-breach" label. Instead, the risk model's target is reframed as **investigation-worthy risk**: whether a claim or processing window shows signs (quality-check failures, anomaly score, volume/amount deviation from baseline) that would warrant a human reviewing it. This is a defensible alternative built entirely from fields that exist and are populated, and it is what "Risk Score" refers to everywhere else in this document — the term "SLA Risk" is retired.

---

## 3. Proposed architecture (data engineering → cloud deployment)

```
inpatient.csv (manual upload, pipe-delimited)
        │
        ▼
INGESTION SERVICE  (manual upload + continuous/batch file watch — NOT a live socket stream)
        │
        ▼
DATA ENGINEERING
  Schema validation → dtype conversion → missing-value handling →
  duplicate detection → invalid-value detection → date standardization
        │
        ▼
GREAT EXPECTATIONS (deterministic quality layer) ──► Quality Score (0–100)
        │
        ▼
HISTORICAL BASELINE  (mean/median/std/percentiles per metric, computed from clean historical claims)
        │
        ▼
FEATURE ENGINEERING
  Claim-level features  +  Window-level features (5/15/30-min or N-claim batches)
        │
        ▼
FEATURE SELECTION  (remove useless → statistical filter → model-based selection)
        │
        ├──────────────► ANOMALY DETECTION (benchmarked: IQR baseline, HBOS, Isolation Forest, LOF;
        │                  train/validate/test-split with leakage discipline — see Section 3.2)
        │                        │
        │                        ▼
        │                  Selected production anomaly model + Anomaly Score (0–100)
        │
        ▼
RISK DATASET (incident/window-level rows: GX failures, anomaly score, volume deviation,
              amount deviation, quality-failure rate, claim count, derived investigation-risk label)
        │
        ▼
RISK MODEL BENCHMARK (Logistic Regression, Random Forest, XGBoost — temporal train/val/test split)
        │
        ▼
Selected production risk model + Risk Score (0–100, investigation-risk probability)
        │
        ▼
SEVERITY + BUSINESS IMPACT + PRIORITY  (see Section 3.3)
        │
        ▼
INCIDENT CREATION
        │
        ▼
LLM INVESTIGATION (Mistral)  → root cause, evidence, business impact, recommended fix
        │
        ▼
HUMAN-IN-THE-LOOP
  Accept → Remediation Engine (affected claims only) → Revalidate (GX + anomaly + risk) → Before/After
  Reject → Feedback → Recalculate → Human reviews again
        │
        ▼
AUDIT LOG (every step: check, score, LLM output, human decision, remediation, revalidation result)
```

### 3.1 Formulas & thresholds (initial defaults — all configurable, calibrate on validation data)

**Data quality:**
```
MissingRate = (MissingRecords / TotalRecords) × 100
  < 2%   → PASS
  2–5%   → WARNING
  > 5%   → CRITICAL

DuplicateRate = (DuplicateRecords / TotalRecords) × 100
  0%     → PASS
  0–1%   → WARNING
  > 1%   → CRITICAL
```
Quality Score (0–100) is computed dynamically from the weighted proportion of PASS/WARNING/CRITICAL results across all Great Expectations checks — never a hardcoded number. Weights per check category are configurable.

**Anomaly detection — IQR baseline:**
```
IQR = Q3 - Q1
Lower Bound = Q1 - 1.5 × IQR
Upper Bound = Q3 + 1.5 × IQR
```
Values outside these bounds are anomaly candidates.

**Anomaly detection — HBOS:**
```
For feature j: Hj(x) = -log(Pj(x) + ε)
Overall:       HBOS(x) = Σ Hj(x)
```
Higher score = more anomalous. Initial calibration (recalibrate on validation data, do not treat as universal):
```
< 95th percentile     → NORMAL
95th–99th percentile  → WARNING
> 99th percentile     → CRITICAL CANDIDATE
```

**Risk classification bands (initial, configurable):**
```
0–30%    → LOW
31–60%   → MEDIUM
61–80%   → HIGH
81–100%  → CRITICAL
```

### 3.2 Anomaly model train/validation/test discipline (no data leakage)

The risk model already had a mandated chronological split (Section 5, Phase 9). The anomaly models need the same discipline, made explicit here because it was previously undocumented:

```
TRAIN       → fit the anomaly model (IQR / HBOS / Isolation Forest / LOF) on clean training data only
VALIDATION  → tune model parameters; calibrate anomaly thresholds (the 95th/99th percentile bands above)
TEST        → evaluate the final, calibrated configuration exactly once, on untouched test data
```
Synthetic anomaly injection (missing-value spike, duplicate spike, numerical-value spike, distribution shift, volume change, invalid value) — used because this dataset has no ground-truth anomaly labels — is applied **only to validation and test copies**. Training data must never be contaminated with injected anomalies. This mirrors the general leakage rule in Section 5.5 (Feature Selection): any learned transformation (imputation, scaling, encoding, feature selection, anomaly thresholds, model parameters) is fit on training data only.

### 3.3 Severity, Business Impact, and Priority

Four distinct, non-overlapping signals feed the Priority formula. Each measures something different so nothing gets double-counted:

- **Quality Score (0–100):** batch-level data soundness (Great Expectations).
- **Anomaly Score (0–100):** how statistically unusual this specific claim/window is (HBOS).
- **Risk Score (0–100):** the model's predicted probability that this incident is investigation-worthy (XGBoost or the empirically-selected winner — see 2.4 for why this replaced "SLA Risk").
- **Severity (0–100), newly defined here:** the magnitude of the incident itself — how bad this specific finding is, independent of whether it turns out to be a true risk or what it costs. Computed as:
  ```
  Severity = wq × QualityFailureSeverity + wa × AnomalyMagnitudeScore + wm × MaterialityScore
  ```
  where `QualityFailureSeverity` weights the Great Expectations checks that failed for the affected claim(s) (CRITICAL=100, WARNING=50, PASS=0 per check, averaged), `AnomalyMagnitudeScore` maps the HBOS percentile onto 0–100 using the same 95th/99th-percentile calibration as Section 3.1 (so severity scales continuously with how extreme the anomaly is, not a flat yes/no), and `MaterialityScore` measures the actual scale of the incident — percentage of claims affected within the window and/or the dollar-amount percentile of `CLM_PMT_AMT`/`CLM_TOT_CHRG_AMT` for affected claims relative to baseline. Initial illustrative weights: `wq=0.4, wa=0.4, wm=0.2` — configurable, to be revisited once real incidents are running through the pipeline.
- **Business Impact (0–100):** dollar/operational consequence, computed **only** from measurable fields — claim-amount-based components (total charge, payment amount, affected-claim dollar exposure) are computable from this dataset; components like member-harm or provider-reputation impact are **not** present in the data and must be explicitly marked unavailable rather than fabricated, per the project's no-fabrication principle.

Priority formula (unchanged from the original plan, now with all four inputs precisely defined):
```
Priority = 0.40 × Severity + 0.30 × Risk + 0.20 × Business Impact + 0.10 × Affected Claims Score
```
Weights are configurable.

### Backend architecture (modular, not a monolith)
Backend is a single deployable service for the MVP, but the codebase is split into one module per feature/domain (own files, own router, own service, own tests) rather than one large file. Target module boundaries:

`ingestion` · `data_engineering` (profiling/cleaning/standardization) · `quality` (Great Expectations) · `baseline` · `features` (claim-level, window-level, selection) · `anomaly` (iqr, hbos, isolation_forest, lof, benchmark) · `risk` (logistic, random_forest, xgboost, benchmark, scoring) · `llm` (Mistral client, prompts, investigation service) · `incidents` · `hitl` (accept/reject) · `remediation` (duplicate/missing/invalid-status/manual handlers) · `revalidation` · `simulation` (window batching over uploaded/continuously-ingested files — not a live stream) · `audit`

Each module owns its own database models, Pydantic schemas, service logic, and API router; `app/main.py` only wires routers together.

### Database (core tables — same as full plan)
`claims`, `claim_batches`, `baseline_metrics`, `quality_results`, `anomaly_results`, `features`, `risk_predictions`, `incidents`, `llm_investigations`, `human_feedback`, `remediations`, `revalidation_results`, `stream_windows` (repurposed as ingestion/processing windows, not live-stream windows), `audit_logs`.

### Cloud target (post-MVP, not built yet)
CloudFront → ALB → ECS/Fargate running two containers (frontend, backend) → RDS PostgreSQL + S3 (claims/models/logs) → ECR (both images) → CloudWatch (monitoring) → managed secrets store for `MISTRAL_API_KEY` / `DATABASE_URL`. The frontend is containerized the same way as the backend (its own Dockerfile, its own image in ECR) rather than shipped as a static S3/CloudFront bundle. This is documented for planning purposes only; no cloud resources are provisioned as part of the MVP, and AWS deployment does not start until the Docker validation step in Phase 18 is complete (see that phase for the sequencing note).

---

## 4. What is included in this MVP (and what is explicitly deferred)

**In scope:**
- Single dataset: `inpatient.csv` (CMS inpatient claims, pipe-delimited), ingested via manual upload.
- Continuous/repeated file ingestion (the user or a script can keep dropping/uploading batches over time), processed as discrete batches — **not** a live streaming API or claims simulator.
- Full data engineering pipeline: profiling, cleaning, standardization, keeping `original_value` / `cleaned_value` / `quality_issue` alongside cleaned data (never silently delete bad records).
- Great Expectations deterministic quality layer with a real, computed 0–100 quality score using the MissingRate/DuplicateRate formulas in Section 3.1.
- Historical baseline computed from real cleaned data (no static/assumed baseline numbers).
- Claim-level and window-level feature engineering, three-stage feature selection.
- Anomaly detection benchmark: IQR baseline vs HBOS vs Isolation Forest vs LOF, with a proper train/validate/test split and leakage discipline (Section 3.2), synthetic anomaly injection restricted to validation/test copies, scored on precision/recall/F1/FPR/latency/runtime. Production model selected empirically.
- Risk dataset built at incident/window grain with a derived, documented **investigation-risk** label (not an SLA-breach label — see Section 2.4 for why), temporal train/val/test split.
- Risk model benchmark: Logistic Regression vs Random Forest vs XGBoost, evaluated primarily on recall + PR-AUC (false negatives are the costly error), production model selected empirically.
- Severity, Business Impact, Risk, and Quality computed as four distinct, non-overlapping signals (Section 3.3), combined into a composite Priority score.
- LLM investigation using **Mistral** (not Gemini) — root cause, evidence, impact, recommendation only; the LLM never executes fixes or touches the database directly.
- Human-in-the-loop accept/reject flow, feedback capture for future retraining.
- Constrained remediation engine (duplicate flagging, approved imputations, approved status mappings only; anything else becomes "Manual Action Required").
- Revalidation with before/after comparison using real computed values, never demonstration numbers.
- Full audit trail across the whole pipeline.
- Backend built as modular Python service, containerized with Docker/Docker Compose (backend + Postgres) for local development.
- Repo structure, Docker/dev environment scaffolding, and speckit installation (already delivered — see Section 7).
- Frontend, once built, will also ship as its own Docker container (own Dockerfile, added as a service in `docker-compose.yml`) rather than a separately-hosted static bundle — confirmed by the user, scaffolded as a placeholder now, wired up for real once frontend implementation starts.

**Explicitly deferred / out of scope for this MVP pass:**
- No live claims-stream ingestion API/socket — this is replaced by manual + continuous file-based ingestion.
- No frontend implementation yet — see the frontend reality-check below; a UI shell exists but has no real source code and no backend wiring.
- No CI/CD pipeline, no cloud deployment, no container registry push — infra planning only, documented for later phases. AWS deployment specifically does not start until local Docker validation is complete (Phase 18/20).
- No production secrets, no real Mistral API key committed anywhere (use `.env`, gitignored).
- Gemini is fully replaced by Mistral throughout — no dual-LLM support needed.
- No second dataset (outpatient, carrier, DME, etc.) — single-file scope only for now.
- No SLA-breach modeling of any kind — the dataset does not support it (Section 2.4); do not reintroduce it without a new, verified source field.

**Spec 015-continuous-ingestion removed (2026-08-18).** The user decided a live/continuous ingestion pipeline is out of scope and had this spec folder deleted; specs `016-*`→`015-*` and `017-*`→`016-*` were renumbered down to close the gap (see Section 8 changelog). This leaves an open question, flagged rather than assumed: `backend/app/ingestion/router.py` is still an unimplemented placeholder, and no spec currently exists for it. It is unclear whether the deleted spec's content was entirely about live streaming (in which case nothing in-scope was lost) or also covered the still-in-scope "manual + repeated batch upload" ingestion flow described above (in which case that capability now has no spec and needs a new one, e.g. a re-scoped `017-batch-ingestion`). **Needs a decision before Phase 13+ implementation planning treats ingestion as covered.**

### 4.1 Frontend reality-check (2026-08-18)

A `frontend/` folder exists (package name `cognizant` in `package.json`) with a real `package.json`/`index.html`/config scaffold (React 19, Vite 8, Tailwind CSS 4, React Router 7, lucide-react) and a **pre-built, minified `dist/` bundle**, but no `frontend/src/` — it was never committed to git and does not exist on disk. Findings from inspecting the compiled bundle directly (no source, no sourcemap, so this is reverse-engineered from strings, not read from real code):

- **8 routes exist**: `/dashboard`, `/incidents`, `/investigation/:id`, `/upload`, `/history`, `/simulator`, `/stream`, `/settings`.
- **Zero API integration.** No `fetch`-to-backend calls, no `axios`, no `import.meta.env`/`VITE_API_*` usage, no `Authorization`/`Bearer` handling found anywhere in the bundle. Every incident, auditor, payer, and batch shown when the UI is run is hardcoded mock data baked into the JS — not wired to any backend, real or otherwise.
- **Route-to-backend readiness**, checked against the actual implemented routers:
  - Backend-ready today: `/dashboard` (would aggregate `quality`/`anomaly`/`risk` endpoints), `/incidents` (incidents CRUD + HITL), `/investigation/:id` (`llm` router).
  - Backend not implemented yet: `/upload` (ingestion), `/history` (audit), `/simulator` (simulation) — all placeholder routers, specs 013/014/015/016 not done.
  - **Conflicts with a scope decision already made**: `/stream` implies live streaming, which was explicitly ruled out (see 015-continuous-ingestion removal above). This page needs to be dropped or reinterpreted as repeated-batch ingestion, not built as designed.
- **Reusable as-is**: the route/page list, the Tailwind dark theme (slate-950/cyan-500) and fonts already wired in `index.html`, the icon set.
- **Not reusable**: any component code (no source exists to recover) or any of the mock data (fake, not a real data contract).

No frontend implementation work has started as a result of this finding — this is a documentation-only update, per explicit instruction, pending the user's review and go-ahead.

---

## 5. High-level task breakdown (build order)

**Status legend used below: ✅ Implemented and complete · ⚠️ Implemented, one item pending · 🔲 Not started.**

**Phase 0 — Environment & repo (delivered)**
Repo structure, Docker Compose (backend + Postgres) scaffolding, `.env.example`, `requirements.txt`, `data/` folder convention, `inpatient.csv` placed under `data/raw/`, speckit vendored under `.specify/` and `.claude/skills/`.

**Phase 1 — Data engineering foundation** ✅ Implemented (spec `001-data-profiling-foundation`, 002-cleaning-standardization — all tasks complete)
1.1 Full data profiling of `inpatient.csv` (row/col counts, dtypes, missingness, cardinality, duplicates, numeric/categorical distributions, date columns) → written report.
1.2 Column categorization (identifiers / dates / numerical / categorical / diagnosis-procedure codes) confirmed against the real columns above.
1.3 Sampling strategy for fast local iteration (keep raw file intact under `data/raw/`, generate a working sample under `data/sampled/`).

**Phase 2 — Cleaning & standardization** ✅ Implemented (spec `002-cleaning-standardization`, 18/18 tasks)
Schema validation → dtype conversion → missing-value handling → duplicate detection → invalid-value detection → date standardization (`DD-Mon-YYYY` → ISO). Preserve `original_value` / `cleaned_value` / `quality_issue` for every correction.

**Phase 3 — Great Expectations quality layer** ✅ Implemented (spec `003-quality-validation-layer`, 24/24 tasks)
Define expectation suites per column category (completeness, uniqueness on `CLM_ID`, validity of amounts ≥ 0, dtype checks, range checks, valid code-set checks, date validity, freshness). Compute the 0–100 composite quality score using the MissingRate/DuplicateRate formulas and PASS/WARNING/CRITICAL bands from Section 3.1.

**Phase 4 — Historical baseline** ✅ Implemented (spec `004-historical-baseline`, 25/25 tasks)
Compute baseline statistics (claim volume per window, amount mean/median/std/percentiles, missingness rates, duplicate rate, status distribution) from the cleaned historical data — all real, computed values. (Processing-time distribution is dropped from this list — see Section 2.4 on why no genuine processing-time field exists; length-of-stay, from `CLM_ADMSN_DT`→`NCH_BENE_DSCHRG_DT`, is tracked instead where a duration baseline is needed.)

**Phase 5 — Feature engineering** ✅ Implemented (spec `005-feature-engineering`, 30/30 tasks)
Claim-level features (amount ratios, length-of-stay, date-derived features, encoded categoricals, provider frequency) and window-level features (claim count, amount stats, missingness %, duplicate %, invalid-status %, volume/amount deviation vs baseline, anomaly count per window).

**Phase 6 — Feature selection** ✅ Implemented (spec `006-feature-selection`, 20/20 tasks)
Stage 1 (drop constant/near-constant/duplicate/raw-ID/high-missingness/leakage columns — several already identified above), Stage 2 (correlation, mutual information, variance, cardinality, missingness thresholds), Stage 3 (XGBoost importance, permutation importance, RFE if needed). Feature selection is fit on training/validation data only — never on test data.

**Phase 7 — Anomaly detection benchmark** ⚠️ Implemented, 28/29 tasks — **T028 still open**: run `specs/007-anomaly-detection-benchmark/quickstart.md`'s manual end-to-end verification (benchmark → results → selection-matches-F1 check → enrich-windows → idempotency diff) against a running backend and fix any contract/implementation drift found. Needs a running backend + real dependencies, which this planning environment cannot provide — do this from wherever the backend actually runs.
Implement IQR baseline, HBOS, Isolation Forest, LOF using the train/validate/test discipline in Section 3.2. Build an anomaly-injection harness (missing-value spike, amount spike, duplicate spike, volume drop, distribution shift) applied only to validation/test copies. Evaluate precision/recall/F1/FPR/detection latency/execution time. Select production model empirically (expected HBOS, but only if the benchmark confirms it).

**Phase 8 — Risk dataset construction** ✅ Implemented (spec `008-risk-dataset-construction`, 24/24 tasks)
Build incident/window-grain rows (GX failure count, anomaly score, affected-claim %, volume deviation, amount deviation, historical quality-failure rate, anomaly frequency, claim count). Define and document the **investigation-risk label** derivation explicitly, per Section 2.4: this dataset has no genuine SLA/processing-turnaround field, so the target is built from quality-failure rate + anomaly frequency + volume/amount deviation rather than a fabricated timing-based label.

**Phase 9 — Risk model benchmark** ✅ Implemented (spec `009-risk-model-benchmark`, 23/23 tasks)
Logistic Regression (baseline) vs Random Forest vs XGBoost. Temporal 70/15/15 train/val/test split (no random shuffling — this is time-dependent data spanning 2015–2022). Evaluate accuracy/precision/recall/F1/ROC-AUC/PR-AUC/calibration/false-negative rate, prioritizing recall + PR-AUC. Select production model empirically.

**Phase 10 — Severity, Business Impact, and Priority scoring** ✅ Implemented (spec `010-severity-impact-priority-scoring`, 19/19 tasks)
Compute Severity using the formula in Section 3.3 (quality-failure severity + anomaly magnitude + materiality). Compute Business Impact only from measurable claim-amount fields, explicitly marking any non-computable component (e.g. member-harm impact) as unavailable. Combine Quality + Anomaly + Risk + Severity + Business Impact into Final Incident Priority (`0.40×Severity + 0.30×Risk + 0.20×Business Impact + 0.10×Affected Claims Score`, weights configurable).

**Phase 11 — LLM investigation (Mistral)** ✅ Implemented (spec `011-llm-investigation`, 21/21 tasks)
Structured incident → Mistral → incident summary, likely root cause, evidence, business impact, recommended fix, prevention recommendation. LLM has read-only access to structured evidence; it never executes remediation. If evidence is insufficient, it must say so explicitly ("Insufficient evidence to determine the root cause") rather than guess.

**Phase 12 — Incident management & HITL** ✅ Implemented (spec `012-incident-management-hitl`, 28/28 tasks)
Incident CRUD, accept/reject endpoints, feedback capture on reject, recalculation loop. Human feedback is stored for future retraining but never triggers automatic retraining from a single event.

**Phase 13 — Remediation engine** ✅ Implemented (spec `013-remediation-engine`, 33/33 tasks)
Deterministic handlers only: duplicate flagging, approved imputation, approved status mapping. Anything unhandled → "Manual Action Required." No LLM-invented fixes.

**Phase 14 — Revalidation** ✅ Implemented (spec `014-revalidation`, 26/26 tasks)
Re-run GX + anomaly + risk on affected claims after remediation; produce before/after comparison using real recomputed values; mark incident Resolved or Reopened.

**Phase 15 (retired number) — Continuous ingestion — REMOVED (2026-08-18)**
~~Support repeated manual uploads / a watched-folder pattern...~~ Deleted per the user's explicit decision: no live/continuous pipeline is in scope. The spec folder (`015-continuous-ingestion`) was removed and later specs renumbered down to close the gap (see Section 4.1 and Section 8). **Open gap, not yet resolved:** basic ingestion (`POST /claims/upload` and repeated batch upload, which Section 4 still lists as in-scope) has no active spec and no implementation — `backend/app/ingestion/router.py` is still a placeholder. This phase number is intentionally left retired rather than reused, so history stays traceable; a replacement ingestion spec should get the next free number when scoped.

**Phase 15 — Testing** ✅ Implemented (spec `015-testing-suite`, 19/19 tasks; renumbered from `016-testing-suite`)
Broken out explicitly per category (previously bundled into one line). Coverage against these named scenarios is tracked in `docs/testing/phase15_coverage_map.md`, which `backend/tests/coverage_map/` parses to assert none goes unaccounted for — 13 covered by prior phases, 8 new tests, 3 (the Ingestion row below) recorded as documented limitations because the pipeline they need was retired with the phase above:
- *Data:* missing values, duplicates, invalid types/values/dates, missing columns, empty files.
- *Anomaly:* injected-anomaly detection accuracy, false positives, false negatives, detection latency, model stability.
- *Risk:* data-leakage test (verify no test/validation information reached training), temporal-split-correctness test (verify chronological ordering was respected), false negatives, model calibration, drift sensitivity.
- *LLM:* hallucination, unsupported claims, insufficient-evidence handling, incorrect-recommendation detection (distinct from hallucination).
- *HITL:* accept → fix → revalidate; reject → feedback → recalculate → re-review.
- *Ingestion:* large files, malformed batches, repeated/continuous uploads.

**Phase 16 — Audit & history** ✅ Implemented (spec `016-audit-history`, 31/31 tasks; renumbered from `017-audit-history`)
Full audit log across every pipeline stage; `/history` and `/audit/baseline` read endpoints. Ten decision-producing modules call `audit.append_entry` at their own write sites, so the trail is built at write time rather than reconstructed retroactively; entries reference (never copy) the owning module's record. The baseline endpoint is a direct pass-through to Phase 4 and is mounted at `/audit/baseline` because Phase 4's router already owns `/baseline` — a duplicate would have been silently shadowed. `ingestion` is deliberately absent from the audit-source registry (its phase was retired; no write path exists).

**Phase 17 — Frontend (deferred)** 🔲 Not started for real, but not a blank slate either — see Section 4.1's frontend reality-check: a UI scaffold + compiled mockup bundle exists with no source and no backend wiring. When implementation starts, it gets its own Dockerfile and is added to `docker-compose.yml` as a `frontend` service — same containerized-deployment pattern as the backend, confirmed by the user.

**Phase 18 — Dockerization & local dev**
The `Dockerfile` and `docker-compose.yml` already in the repo (Phase 0) are structural scaffolding only — empty-service skeletons with no application code running yet. Actual containerization work (build the image, run it, verify DB/API connectivity, verify model loading, verify Mistral integration end-to-end) happens only after the backend pipeline (Phases 1–14) is functionally complete and tested locally without Docker. Do not treat the existing Docker files as "containerization done." A `frontend` service and Dockerfile are added to the same Compose file once Phase 17 produces real frontend code.

**Phase 19 — CI/CD (deferred)**
GitHub Actions pipeline (lint → unit tests → ML tests → build → scan → push → deploy) — documented, not implemented yet.

**Phase 20 — AWS backend deployment (deferred)**
Starts only after Phase 18's local Docker validation is complete. Covers: Docker image, AWS compute/service selection (ECS/Fargate), database (RDS PostgreSQL), storage (S3), environment variables, secrets management, networking, logging (CloudWatch), health checks, and basic scaling considerations. Frontend deployment is not part of this phase. Cloud architecture target documented in Section 3; not provisioned yet.

**Phase 21 — Model & data monitoring, retraining (deferred)**
Broken out explicitly per the three signal groups:
- *Anomaly model:* anomaly rate, false-positive rate, detection latency, score distribution.
- *Risk model:* precision, recall, F1, PR-AUC, calibration, false-negative rate.
- *Data:* missing rate, volume changes, feature distribution, categorical distribution, drift.

Escalation path on significant drift: model review → retraining candidate → validation against held-out data → compare against current production model → deploy only if better (never automatic replacement from a single retraining run). Human feedback from Phase 12 becomes future training data through this same gated path.

---

## 6. Final ML stack (target, pending benchmark confirmation)

| Problem | Method | Status |
|---|---|---|
| Data quality | Great Expectations | Deterministic, always on |
| Anomaly baseline | IQR / percentile | Benchmark baseline |
| Anomaly candidate | Isolation Forest | Benchmarked |
| Anomaly candidate | LOF | Benchmarked |
| **Anomaly production** | **HBOS (pending benchmark)** | Selected only if validated on this data |
| Risk baseline | Logistic Regression | Benchmarked |
| Risk candidate | Random Forest | Benchmarked |
| **Risk production** | **XGBoost (pending benchmark)** | Selected only if validated on this data; target is investigation-risk, not SLA-breach (Section 2.4) |
| Root cause / recommendation | **Mistral** (replaces Gemini) | Investigation only, no execution |

No model is hard-selected in advance. Selection happens after Phases 7 and 9 run on the real `inpatient.csv`-derived datasets.

---

## 7. Tooling notes for whoever implements this

- Intended implementation approach: spec-driven development (speckit) inside this repo.
- **speckit is fully installed in this repo, ready to use.** `.specify/` has `memory/constitution.md` (PayerGuard-specific principles, already filled in, not a blank template), `templates/` (spec/plan/tasks/checklist templates + the raw `speckit.*` command templates), and `scripts/bash/` (the helper scripts those commands call). `.claude/skills/speckit-*/SKILL.md` (10 skills: specify, plan, tasks, implement, clarify, analyze, checklist, constitution, converge, taskstoissues) back the `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement` etc. slash commands in Claude Code — start using them immediately.
  - Provenance note for whoever continues this: the scaffolding session ran in a sandbox with no PyPI/apt access, so it couldn't run the real `specify` CLI. `.specify/` was vendored verbatim from https://github.com/github/spec-kit, and `.claude/skills/*/SKILL.md` was hand-reconstructed by reading the CLI's actual generation code and reimplementing it — verified for valid frontmatter, correct argument-hints, and correct `.specify/`-rewritten script paths, but not a byte-for-byte guarantee against the official output. `bash scripts/bootstrap_speckit.sh` re-runs the official `specify init --here --ai claude` (needs `uv`/`uvx` and real internet) if exact CLI parity ever matters; it will not touch `.specify/memory/constitution.md`.
- Reference skills/tooling the user wants applied during implementation (fetch and review before use, don't assume behavior):
  - `anthropics/skills` → `frontend-design` (for when frontend work starts)
  - `anthropics/skills` → `web-artifacts-builder` (for when frontend/artifact work starts)
  - `obra/superpowers` (general tooling to pull in during implementation)
  - `massgen/MassGen` (for efficient multi-file/codebase search during implementation)
- Backend language/stack: Python (FastAPI implied by the API design in Section 3), Postgres, Docker Compose for local dev.
- Secrets: `MISTRAL_API_KEY`, `DATABASE_URL` via `.env` (gitignored), never committed.
- Do not hardcode static thresholds, baseline numbers, or scores anywhere in the implementation — every number in Sections 2–6 that looks like a placeholder must instead be computed from the real data at build time. The numbers in Section 2.2 are measured facts about the current `inpatient.csv` and are provided so implementers know what to expect, not values to hardcode into the pipeline. This applies with particular force to Section 2.4: do not resurrect an SLA-breach label from a field that hasn't been independently re-verified against the data.

---

## 8. Changelog from v1

This section records what changed from the first version of this document and why, so anyone diffing the two understands the reasoning without re-deriving it.

1. **SLA-breach target removed and replaced.** v1 proposed deriving it from `CLM_FROM_DT`/`CLM_THRU_DT`/`FI_CLM_PROC_DT`/`NCH_WKLY_PROC_DT`. Testing showed `FI_CLM_PROC_DT` is 100% null and `NCH_WKLY_PROC_DT` is a fixed weekly batch date (always a Friday, always 1–7 days after `CLM_THRU_DT`), not a real operational signal. Replaced throughout with an **investigation-risk** target built from quality-failure rate, anomaly frequency, and volume/amount deviation. See Section 2.4.
2. **Formulas and thresholds added.** MissingRate/DuplicateRate formulas and PASS/WARNING/CRITICAL bands, IQR bounds, HBOS formula and percentile calibration, risk classification bands — all added to Section 3.1, previously undocumented.
3. **Anomaly model leakage discipline added.** Section 3.2 — train/validate/test split and injection-into-val/test-only rule, previously only specified for the risk model.
4. **Severity formally defined.** Section 3.3 — a three-component formula (quality-failure severity + anomaly magnitude + materiality) designed to be distinct from Quality, Anomaly, and Risk scores so the Priority formula doesn't double-count evidence. Previously undefined in both source documents.
5. **Business Impact non-fabrication clause added.** Section 3.3 — explicit statement that only measurable claim-amount components are computed; anything else is marked unavailable.
6. **Testing phase (16) broken out by category** instead of one bundled line, adding explicit data-leakage and temporal-split-correctness tests.
7. **Monitoring phase (22) broken out by the three signal groups** (anomaly / risk / data) with their specific metrics, instead of one summary sentence.
8. **Docker sequencing clarified.** Phase 19 now states explicitly that the existing `Dockerfile`/`docker-compose.yml` are scaffolding only, not a validated build — actual containerization happens after the backend pipeline works locally.
9. **Filename discrepancy noted.** Section 2.1 — some circulated planning material says `inpatients.csv`; the real, profiled file is `inpatient.csv`. No data was renamed.

**v3 (2026-08-18) — implementation-status sync:**
10. **Spec 015-continuous-ingestion removed.** Live/continuous pipeline confirmed out of scope by the user; the spec folder was deleted and `016-testing-suite`→`015-testing-suite`, `017-audit-history`→`016-audit-history` renumbered to close the gap. Phase numbering in Section 5 updated to match, with the retired Phase 15 slot left visibly marked rather than silently reused. See Section 4.1 for the open ingestion-coverage question this left behind.
11. **Section 5 annotated with real implementation status** per spec (✅/⚠️/🔲), read directly from each spec's `tasks.md` — specs 001–012 complete (28/29 for 007, see next item), specs 013–016 not started.
12. **T028 flagged as the one open item in an otherwise-complete spec.** `specs/007-anomaly-detection-benchmark/tasks.md` T028 (manual `quickstart.md` end-to-end verification against a running backend) is still unchecked — needs a real running backend + dependencies to execute, which isn't available from this planning environment.
13. **Section 4.1 (new) — frontend reality-check.** The `frontend/` folder has a real scaffold (Vite/React 19/Tailwind 4/React Router 7) and a compiled `dist/` bundle, but no `src/` — never committed, doesn't exist on disk. Reverse-engineered from the compiled bundle's strings: 8 routes exist, but zero API integration of any kind was found, and all visible data is hardcoded mock content. One route (`/stream`) conflicts with the continuous-ingestion removal above and needs to be dropped or reinterpreted. Section 9 (new) gives a shareable status snapshot including this.

**v4 (2026-08-19) — spec renumbering completed repo-wide; 013/014/015 implemented:**

14. **Statuses corrected for specs 013, 014, and 015.** All three are implemented and passing (33/33, 26/26, 19/19), not "not started" as v3 recorded — v3's entry 11 was accurate when written and is left as-is rather than rewritten. Section 5, Section 9.4's table, and Section 9.5's task list now reflect the real state. Backend suite: 362 passed / 3 skipped.
15. **v3's renumbering propagated into every artifact it had missed.** v3 renumbered Section 5's phase headings but not the ~33 spec/doc/source files that referenced the old numbers. All forward references were remapped in a single pass (16→15, 17→16, 18→17, 19→18, 20→19, 21→20, 22→21), including ranges (`Phase 1-17`→`1-16`, `Phases 18-22`→`17-21`).
16. **Empty deferred-phase spec folders renumbered to match.** `018-frontend`→`017-frontend`, `019-dockerization-local-dev`→`018-…`, `020-cicd`→`019-cicd`, `021-aws-backend-deployment`→`020-…`, `022-model-data-monitoring-retraining`→`021-…`. Spec directory numbers now map 1:1 onto Section 5's phase numbers with no gaps.
17. **References to the retired Phase 15 annotated, not renumbered.** ~30 sites across specs 001–004/007/008/009/012/016 and a few `backend/app/` docstrings referred to the removed continuous-ingestion phase (e.g. "as Phase 15 adds more batches"). Renumbering them would have pointed at Testing; each was reworded to keep its design rationale while stating the descoping explicitly.
18. **One unsatisfiable requirement dropped.** `016-audit-history` FR-001 required aggregating `Phase 15`'s `IngestedBatch` record into the audit trail. That record type died with the retired ingestion phase, so the requirement could never be met; it was removed from the list rather than left as a spec demanding a module read a record that will never exist.
19. **Two pre-existing test failures fixed** (both unrelated to the above, both confirmed present before spec 014's commit): pandas 3.x's default string dtype was coercing genuine `None` into a float `NaN` in `date_standardization.py`, and `investigation_log.py`'s "newest first" ordering had no tiebreaker for entries sharing a timestamp at the host clock's resolution.

**v5 (2026-08-19) — spec 016 implemented; backend pipeline complete:**

20. **Spec 016 (audit & history) implemented**, 31/31 tasks. `audit_logs` is built at write time: ten decision-producing modules call `audit.append_entry` inside their own transaction, so an audit entry can never become durable for a fact that was rolled back. Entries store only a `source_record_id` reference; a test asserts the table has no column capable of holding a copy of upstream content. Phases 1-16 are now functionally complete (396 tests passing).
21. **Three deviations from spec 016's design documents, each decided explicitly rather than drifted into.** (a) `ingestion` was dropped from `EXPECTED_AUDITED_MODULES` — its phase was retired and there is no write path to instrument, so keeping it would ship a permanently failing completeness check, which trains people to ignore red tests. (b) `data_engineering` was *added* to that list, which research.md had omitted, because FR-001 and User Story 1's first acceptance scenario both require Phase 2 cleaning corrections in a claim's trail. (c) The baseline endpoint is mounted at `/audit/baseline`, not `/baseline`: Phase 4's router already owns that path, and a duplicate registration is silently shadowed by whichever router was included first (verified empirically, not assumed).
22. **FR-005's baseline-snapshot provenance is resolved by matching, not by stamping.** `EvidenceBundle` carries baseline percentile *values* but no snapshot id, so the link is genuinely absent upstream. Rather than record "whatever the current baseline is" and hope, an incident's `baseline_snapshot_id_used` is set only when the supplied percentiles exactly match a persisted snapshot's own — otherwise it stays null. Guessing would have violated Principle II.
23. **Cleaning audit entries are per-claim, not per-`QualityIssueRecord`.** The real 58,066-row x 197-column file produces on the order of millions of individual records; one audit row each would dwarf the rest of the trail while answering no question the claim-level entry doesn't. Every individual record stays resolvable in the same run's `quality_issues.json`. A bulk `append_entries` path was added at the same time, since a per-entry `MAX(sequence_number)` lookup would otherwise have been one database round trip per record.

---

## 9. MVP status snapshot & completion plan (shareable handoff doc)

**Purpose of this section:** everything above (Sections 1–8) is the full, detailed spec history. This section is a self-contained condensed version — if you hand *only this section* to another person or LLM, they should know what the project is, what data it uses, the architecture, what's actually done vs. still open, and a concrete task list to close out the MVP. No implementation should start from this section alone without reading Sections 3.1/3.2/3.3 (the exact formulas) and the relevant spec's `data-model.md`/`contracts/api.md` first — this is an orientation doc, not a replacement for the specs.

### 9.1 What is the project

PayerGuard is a healthcare claims quality and risk monitoring system. It ingests raw insurance claims, deterministically validates their data quality (Great Expectations), scores statistical anomalies (benchmarked unsupervised models) and operational risk (benchmarked supervised models — specifically, likelihood a claim/window needs human investigation), escalates high-risk findings into structured "incidents" with a computed Severity/Risk/Business-Impact/Priority, has an LLM (Mistral) investigate each incident (root cause, evidence, impact, recommended fix — read-only, never auto-executes), puts a human in the loop to accept/reject that recommendation, runs a constrained deterministic remediation engine only on acceptance, revalidates before/after, and keeps a full audit trail of every step. The governing principle (see `.specify/memory/constitution.md`): **no fabricated values, ever** — every threshold, score, and label is computed from the real dataset or explicitly marked unavailable; models are chosen empirically by benchmark, never assumed in advance.

### 9.2 Dataset and proposed architecture

**Dataset:** exactly one file, `data/raw/inpatient.csv` — CMS Medicare Inpatient Claims (RIF format), pipe-delimited (`sep="|"`), 58,066 claim-line rows / 197 columns / 20,867 unique claims / 5,699 beneficiaries, spanning 01-Apr-2015 to 31-Oct-2022. No other dataset is in scope. Full measured profile: Section 2.2. Manual upload is the ingestion mechanism; there is no live streaming source (see 9.4 on why "continuous ingestion" was removed as a live-pipeline concept but manual/repeated-batch upload remains in scope and is a gap — see Section 4.1).

**Proposed full architecture (target state, not all built yet):**
- **Backend:** modular Python/FastAPI service, one module per domain (`ingestion`, `data_engineering`, `quality`, `baseline`, `features`, `anomaly`, `risk`, `llm`, `incidents`, `hitl`, `remediation`, `revalidation`, `simulation`, `audit`) — each owns its own models/schemas/service/router. `app/main.py` only wires routers together.
- **Data layer:** Postgres for relational state (incidents, feedback, audit log); flat files (`data/raw` → `sampled` → `processed` → `baseline` → `features`) for the pipeline stages; trained model artifacts under `ml/artifacts/` (gitignored).
- **ML:** Great Expectations for deterministic quality (always-on floor); IQR/HBOS/Isolation Forest/LOF benchmarked for anomaly detection; Logistic Regression/Random Forest/XGBoost benchmarked for risk (temporal 70/15/15 split, never random shuffle — this is time-series data). Production model for each = whichever wins its benchmark on this actual data, not a preset choice.
- **LLM:** Mistral only (Gemini fully replaced), structured-output investigation, read-only access to evidence, never writes to the database.
- **Frontend:** its own Docker container (own Dockerfile, added as a `docker-compose.yml` service), same containerized-deployment pattern as the backend — not a separately-hosted static bundle. Current state: scaffold + mockup only, no real implementation (Section 4.1).
- **Deployment target (post-MVP, not provisioned):** CloudFront → ALB → ECS/Fargate (frontend + backend containers) → RDS PostgreSQL + S3 → ECR → CloudWatch, secrets via a managed secrets store.
- **Dev environment:** Docker Compose (backend + Postgres) for local dev; speckit (`.specify/` + `.claude/skills/speckit-*`) for spec-driven development of every phase.

### 9.3 What's included in this MVP

In scope, per Section 4: the full pipeline above end-to-end on `inpatient.csv` only — profiling → cleaning → GX quality scoring → historical baseline → feature engineering/selection → anomaly benchmark+scoring → risk dataset+benchmark+scoring → severity/business-impact/priority → LLM investigation → incident management/HITL → constrained remediation → revalidation → audit trail. Manual + repeated-batch file ingestion (not live streaming). Backend containerized with Docker Compose. Repo/speckit scaffolding.

Explicitly out of scope for this MVP pass: live claims-stream ingestion (any socket/streaming API), a finished frontend, CI/CD, cloud deployment, a second dataset, and any SLA-breach-timing model (the data doesn't support one — Section 2.4).

### 9.4 Current implementation status (as of 2026-08-18)

| Spec | Phase | Status |
|---|---|---|
| 001-data-profiling-foundation | 1 | ✅ 17/17 |
| 002-cleaning-standardization | 2 | ✅ 18/18 |
| 003-quality-validation-layer | 3 | ✅ 24/24 |
| 004-historical-baseline | 4 | ✅ 25/25 |
| 005-feature-engineering | 5 | ✅ 30/30 |
| 006-feature-selection | 6 | ✅ 20/20 |
| 007-anomaly-detection-benchmark | 7 | ⚠️ 28/29 — **T028 open** (manual quickstart verification against a running backend) |
| 008-risk-dataset-construction | 8 | ✅ 24/24 |
| 009-risk-model-benchmark | 9 | ✅ 23/23 |
| 010-severity-impact-priority-scoring | 10 | ✅ 19/19 |
| 011-llm-investigation | 11 | ✅ 21/21 |
| 012-incident-management-hitl | 12 | ✅ 28/28 |
| 013-remediation-engine | 13 | ✅ 33/33 |
| 014-revalidation | 14 | ✅ 26/26 |
| 015-testing-suite | 15 | ✅ 19/19 — see `docs/testing/phase15_coverage_map.md`; 3 Ingestion scenarios are `limitation_documented`, not tested (retired pipeline) |
| 016-audit-history | 16 | ✅ 31/31 — `/history` + `/audit/baseline`; audit-source registry covers 10 modules (`ingestion` excluded, phase retired) |
| *(015-continuous-ingestion)* | *(retired)* | Deleted — live pipeline out of scope; left an open ingestion-coverage gap, see below |
| Frontend | 17 | 🔲 Scaffold + compiled mockup only, no real source, zero backend wiring (Section 4.1) |
| Dockerization/CI-CD/AWS/Monitoring | 18–21 | 🔲 Not started — deliberately deferred until the backend pipeline is functionally complete |

**All 16 active specs complete, 1 of them with a single open manual task (007's T028, which needs a running backend), plus a frontend that's visually designed but has zero real implementation.** The backend pipeline (Phases 1-16) is functionally done. The backend test suite runs 396 passed / 3 skipped (the 3 skips are a deliberate hand-off between two complementary HITL state-machine tests, not gaps).

### 9.5 High-level tasks to finish by tomorrow (for review before any building starts)

This is a priority-ordered task list, not a promise every item fits in one day — use it to decide what actually gets attempted. Nothing here should be built until reviewed and approved.

1. **Close out spec 007.** Run T028 (`specs/007-anomaly-detection-benchmark/quickstart.md`'s manual end-to-end verification) against a real running backend; fix any drift found. Still open — it needs a running backend with real dependencies, which the planning environment can't provide.
2. **Resolve the ingestion gap.** Partly answered in practice: specs 013–015 were implemented successfully with `ingestion` still a placeholder, so it is not a hard blocker. But the gap is real and now has a visible cost — three Phase 15 Ingestion test scenarios could not be written at all (see `docs/testing/phase15_coverage_map.md`), and Section 4 still lists manual + repeated-batch upload as in-scope. A re-scoped ingestion spec (manual/repeated-batch only, explicitly not live streaming) should get the next free spec number when scoped.
3. ~~**Implement spec 013 (remediation engine)**~~ ✅ **Done** — 33/33 tasks. Deterministic-only handlers (duplicate flagging, approved imputation, approved status mapping); anything unmapped becomes "Manual Action Required."
4. ~~**Plan/tasks/implement spec 014 (revalidation)**~~ ✅ **Done** — 26/26 tasks. Re-runs GX + anomaly + risk on affected claims post-remediation, honest before/after comparison (deltas are never clamped to look favourable), Resolved/Reopened status.
5. ~~**Plan/tasks/implement spec 015 (testing suite)**~~ ✅ **Done** — 19/19 tasks. Two scope conflicts were found and resolved rather than papered over: the Ingestion category's three scenarios are recorded as `limitation_documented` (the pipeline they test was retired with the old Phase 15), and the reject→feedback→recalculate→re-review round-trip is cited to Phase 12's existing test rather than duplicated. Coverage is tracked in `docs/testing/phase15_coverage_map.md`.
6. ~~**Plan/tasks/implement spec 016 (audit & history)**~~ ✅ **Done** — 31/31 tasks. Full audit log across ten pipeline-stage modules, `/history` with pagination/filtering and deterministic ordering, `/audit/baseline` pass-through, and an executable registry-completeness check. Its FR-001 previously required aggregating a `Phase 15 IngestedBatch` record; that record type died with the retired ingestion phase and was dropped from the requirement.

**Remaining work now that Phases 1-16 are complete:** 007's T028 manual verification (needs a running backend), the ingestion re-scoping decision in item 2 above, and then the deferred Phases 17-21 (frontend, Docker validation, CI/CD, AWS, monitoring).
7. **Decide on the frontend's fate before doing anything with it**: the existing `frontend/` folder is a mockup, not a partial implementation (Section 4.1). Decide whether to rebuild it from scratch against real endpoints (reusing its route list and Tailwind theme only), and resolve the `/stream` route conflict with the continuous-ingestion removal, before any frontend coding starts.
8. **Only after 1–6 are functionally complete locally (no Docker):** validate `docker compose up --build` actually works end-to-end (Phase 18) — this has never been build-tested in this project so far.

**Revisit after this MVP pass (do not pull forward without a separate decision):** CI/CD pipeline, AWS deployment, a second CMS dataset (outpatient/carrier/DME), model/data monitoring + retraining loop, and a real frontend build. All are already marked deferred in Section 4/5 — listed here again because they're the items most likely to get scope-crept into "the MVP" if this snapshot is shared without the rest of the document.
