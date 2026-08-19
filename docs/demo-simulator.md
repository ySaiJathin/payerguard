# PayerGuard demo build: synthetic data, simulator, and real models

This document covers the demo-scoped build under `backend/app/demo/`: where
the synthetic data comes from, how to regenerate it, which models actually
run, and how a 0–100 risk score becomes a severity band on the dashboard.

Everything described here is real computation. No dashboard number is
hardcoded: Great Expectations really validates each batch, scikit-learn's
`IsolationForest` is fitted and scored per run, and the risk score on every
incident card is an `XGBRegressor.predict` call.

---

## 1. Where the data lives

| Path | What it is |
|---|---|
| `data/demo/synthetic/column_profile.json` | Per-column statistical profile learned from `data/cleaned/inpatient_cleaned.csv` — value pools, log-normal amount fits, measured missing rates. The generator samples from this, so synthetic rows share the real extract's schema, code sets and structural sparsity. |
| `data/demo/synthetic/batch-{1,2,3}.csv` | The three generated batches, at claim grain, carrying all 197 columns. |
| `data/demo/synthetic/batch-{1,2,3}_ground_truth.csv` | Per-row injection label (`none` or one of the five types). Drives the per-injection-type recall/precision/F1 the dashboard shows. |
| `data/demo/synthetic/manifest.json` | Row counts, injected counts by type, date ranges, amount stats per batch. |
| `data/demo/synthetic/active_batch.csv` | Whatever the last pipeline run ingested. The freshness expectation reads its mtime and the baseline snapshot records it as provenance. |
| `data/demo/synthetic/pipeline_runs.json` | Every pipeline run ever performed, whatever the source. |
| `data/demo/synthetic/uploads/` | Files accepted through the Simulator's upload control. |
| `data/models/risk/demo_risk_xgboost.pkl` | The fitted risk regressor. |

`data/demo/batch_XX_*.csv` (no `synthetic/`) are unrelated date slices of the
real extract from an earlier experiment; nothing here reads them.

### Regenerating / reseeding

```bash
cd backend
.venv/Scripts/python.exe -m app.demo.batches      # rewrites all three batches + manifest
```

or `POST /demo/batches/regenerate`. Generation is deterministic: each batch
draws from one seeded `numpy.random.Generator`, so the same spec always
produces the same batch. Changing a spec in `app/demo/batches.py` and
rerunning is the supported way to reshape the demo.

To rebuild the column profile after the cleaned source batch changes, delete
`column_profile.json` (it is rebuilt on next use) or call
`app.demo.column_profile.build_column_profile()`.

---

## 2. The three batches

| | batch-1 · Steady state | batch-2 · Data quality degradation | batch-3 · Payment anomaly surge |
|---|---|---|---|
| Claims requested | 3 000 | 4 800 | 1 900 |
| Amount distribution | source shape | 0.85× centre, 0.9× spread | 1.9× centre, 1.45× spread |
| Structural degradation | none | +9 pp missing, 3.5% duplicate rows | +0.5 pp missing |
| Injection emphasis | one severe multi-failure cluster, one truncated-replay cluster, one payment cluster, one short delivery | extract truncation + replayed batch | mapping fault + late delivery |

Injections are **clustered in time**, not sprinkled: a real bad ingestion is
localised and usually breaks several things at once, and a window only
reaches the upper severity bands when several signals fire together.
Spreading them uniformly produced twelve indistinguishable middling windows,
which is the opposite of a demo. `InjectionCluster` in
`app/demo/schemas.py` is what expresses this.

---

## 3. The models

### 3a. Data quality → Great Expectations

`app/demo/quality_runner.py` reuses Phase 3's own suite builder, extractors,
file-level checks and composite-score formula — none of that logic is
reimplemented — and only swaps out where the DataFrame comes from, so an
arbitrary batch can be validated instead of the fixed cleaned path.

Coverage is identical to production: completeness, code set, range, dtype
(ISO date format), validity, uniqueness, missing rate, duplicate rate,
freshness. Each run mints a run id and timestamp and persists through
`quality_results_log`, preserving the "one run retained as a snapshot"
behaviour the UI expects.

### 3b. Anomaly detection → Isolation Forest

`app/demo/anomaly_runner.py`. IQR is no longer the production detector; the
run publishes an `isolation_forest` production-model selection to
`anomaly_benchmark_results.json`, which is what the dashboard's "PRODUCTION
MODEL" label and per-injection-type panel read.

**Leakage guard.** The training set is a seeded random 60% of the batch's
*clean* rows. Injected rows are excluded before the split is drawn, so no
injection can reach `fit`, and the function asserts that rather than trusting
it. The decision threshold is calibrated from train scores alone. Evaluation
is the remaining clean rows plus every injected row.

The split is random over clean rows rather than a date cut because the
generator clusters injections in time — a chronological cut pushed whole
injection types into the train range, where they were correctly dropped and
then never evaluated, leaving their per-type breakdown blank.

**Feature space.** Seven engineered features, one measurable signal per
failure mode:

| feature | isolates |
|---|---|
| `row_missing_count` | missing-value spike |
| `is_repeat_of_earlier_row` | duplicate spike |
| `claims_on_same_day` | volume drop |
| `payment_zscore` | amount spike |
| `amount_profile_deviation` | amount spike, distribution shift |
| `negative_amount_count` | distribution shift |
| `length_of_stay_days` | general claim-shape outliers |

Feeding the ~30 raw amount columns instead makes the forest a one-trick
detector: those columns span seven orders of magnitude and move together, so
random axis splits isolate an amount spike immediately while a row extreme in
one of thirty dimensions is diluted away. Measured on batch-1 that cost the
other four types nearly all their recall (0.02–0.11).

The threshold sits at the 92nd percentile of clean train scores. At 97.5 the
detector holds precision ≈ 0.82 but reaches only ≈ 0.36 recall; at 92 it runs
near precision 0.78 / recall 0.66 with FPR ≈ 0.07. For a monitoring queue a
missed bad window costs more than a reviewed good one.

### 3c. Risk prediction → XGBoost

`app/demo/risk_model.py`. Ten distinct sub-scores per window, not one blended
number:

| feature | measured from |
|---|---|
| `missing_data_risk` | excess null-cell rate over the batch baseline |
| `null_risk` | excess null rate in the business-critical columns |
| `duplicate_risk` | exact duplicate rows in the window |
| `sla_timeliness_risk` | claim-through → weekly-cutoff lag vs the batch median |
| `range_risk` | rows outside the batch p1–p99 numeric envelope |
| `dtype_risk` | date cells failing the ISO-8601 expectation |
| `validity_risk` | rows carrying a negative amount |
| `uniqueness_risk` | repeated claim ids beyond claim-grain expectation |
| `freshness_risk` | window staleness against the batch's latest claim date |
| `anomaly_risk` | share of the window's claims flagged by Isolation Forest |

Sub-scores are expressed as **excess over the batch's own baseline** where a
structural floor exists. This extract is legitimately sparse — dozens of
columns are 100% null in every batch — so an absolute missing-cell rate
saturates every window at 100 and carries no information. Measures whose
healthy baseline is genuinely zero behave identically either way.

`sla_timeliness_risk` is a timeliness signal derived from `NCH_WKLY_PROC_DT`,
a weekly batch cutoff rather than an adjudication timestamp. It is labelled
as such and never presented as a contractual SLA breach; the dataset has no
such field.

**Training labels** are rule-derived and documented, because no ground-truth
"true risk" for a window exists:

```
base        = Σ weight_i × sub_score_i        (weights below, sum to 1.0)
interaction = 12 × (anomaly_risk/100) × (missing_data_risk/100)
label       = clip(base + interaction, 0, 100)
```

| feature | weight | | feature | weight |
|---|---|---|---|---|
| `missing_data_risk` | 0.16 | | `dtype_risk` | 0.06 |
| `null_risk` | 0.10 | | `validity_risk` | 0.10 |
| `duplicate_risk` | 0.12 | | `uniqueness_risk` | 0.08 |
| `sla_timeliness_risk` | 0.10 | | `freshness_risk` | 0.05 |
| `range_risk` | 0.08 | | `anomaly_risk` | 0.15 |

The interaction term is what makes this more than a weighted average: a
window that is both anomalous *and* structurally incomplete is worse than
either alone, and a linear blend cannot express that.

The model is fitted on a 12 000-row three-part sweep — 60% low-skewed Beta
(most real windows are quiet), 25% uniform, 15% high-skewed Beta. The last
part matters: a low-skewed sweep alone never produces the corner where many
signals are simultaneously maxed, and the model then extrapolates badly
exactly where it counts — a genuine five-alarm window came back at 62 when
the formula put it at 81. Fitted mean absolute error against the formula is
≈ 0.5 points.

At inference the dashboard's number is a real `predict` call, clipped to
0–100.

---

## 4. Risk score → severity band

| score | band |
|---|---|
| > 80 | CRITICAL |
| 60 < s ≤ 80 | HIGH |
| 30 < s ≤ 60 | MEDIUM |
| ≤ 30 | LOW |

These are the thresholds the UI's `bandForScore` already applied, unchanged.

To make every surface agree, the pipeline writes the XGBoost risk score into
the incident's `severity_result.severity` after creation (marked with
`risk_model_severity_source: "xgboost"`). Phase 10's decomposition —
quality-failure severity, anomaly magnitude, materiality — is kept underneath
as the explanation of the score. Without this the KPI tiles and incident
table would band `risk_score` while the severity distribution panel banded a
different number computed from different inputs.

Windows scoring below **10** do not become incidents; below that a window is
quiet enough that an incident would be noise. The floor sits inside the LOW
band rather than at its ceiling, so a healthy batch still produces LOW
incidents.

---

## 5. Incident narrative

`app/demo/narrative.py` holds one template per detected anomaly type, plus a
no-dominant-type variant and an insufficient-evidence variant. The wording is
templated; every number, window id, column name and claim count inside it is
substituted from the real run — which type Isolation Forest flagged, how many
claims in which window, that type's measured recall and precision, and
whether the relevant expectations are passing, warning or failing.

The rendered text is stored twice, deliberately: on the incident's
`evidence_snapshot.analysis_context.narrative` (so the dashboard card is
self-describing without a second request) and through Phase 11's
investigation log with `model_version: payerguard-demo-templates/v1` (so the
Investigation page reads one source). `insufficient_evidence` is set honestly
when a window produced no flagged claims and no failing expectations.

---

## 6. The Simulator

`POST /demo/simulation/start` streams the selected batch in **8 chunks, one
every 4 seconds** (hardcoded — the interval is not configurable), then fires
the full pipeline on the claims that were ingested. Run state is in-process
and non-durable; what the run *produces* is persisted through the normal
artifacts and `pipeline_runs.json`.

The "inject anomalies" toggle calls the generator's own `inject()` live —
one co-located cluster plus a thin background of every type — rather than
loading a pre-baked injected file.

Upload lives on the same page. An uploaded file is checked against the
expected schema first and rejected with the specific columns that are wrong;
if accepted it goes through `pipeline.run_pipeline`, the identical function
the synthetic batches use. Uploaded files carry no injection ground truth, so
detection still runs but the per-injection-type breakdown is honestly empty.

### API

| endpoint | purpose |
|---|---|
| `GET /demo/batches` | the three batches (generated on first call) |
| `POST /demo/batches/regenerate` | reseed from the specs |
| `POST /demo/pipeline/run?batch_id=&inject_anomalies=` | synchronous full run |
| `GET /demo/pipeline/runs` | every run, newest first |
| `POST /demo/simulation/start` | chunked run |
| `GET /demo/simulation/{run_id}` | live progress |
| `POST /demo/upload` | multipart claims file |

---

## 7. Pages

`/dashboard`, `/simulator`, `/history`, `/investigation/:id`.

`/settings` and `/incidents` were removed outright — Settings configured
nothing the backend reads, and the Incidents list is now History, which shows
incidents from every run rather than only the latest. `/upload` folded into
`/simulator`. Anything still pointing at a removed path lands on
`/dashboard` via the catch-all rather than 404ing.
