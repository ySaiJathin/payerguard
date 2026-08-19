# Claude Code Prompt — PayerGuard Demo Build: Synthetic Data + Simulator + Model Swap + Page Consolidation

Copy everything below the line into Claude Code as a single prompt.

---

## Context

This is a **demo-scoped build**, not the full production hardening pass. The goal is a working, end-to-end demo of the PayerGuard claims quality / anomaly detection / SLA risk dashboard, driven by synthetic data and a simulator, using real (if lightweight) models rather than hardcoded numbers. Do not attempt to harden every backend stage — focus on making the path described below actually run, end to end, with real computation at each step.

Before changing anything, explore the repo and report back:
- Current page/route list
- Where baseline claims data currently loads from, and its schema
- Where the current quality-check logic, IQR anomaly detector, and linear regression risk model live
- Where incident generation and the incident detail text (Root Cause / Investigation / Recommended Fix) are producedcd 
- Current pipeline trigger flow (what "Refresh" currently does)

## Dashboard UI must not change

The main operations dashboard, incident cards, and their layout/copy/visual language must remain as they currently are (KPI tiles, Quality Checks by Expectation Type panel, Anomaly Detection by Injection Type panel, Claim Amount Distribution, Incident Severity Distribution, incident detail structure with What is the risk? / Root Cause / Investigation / Recommended Fix). Everything below feeds that UI with real data — it does not restyle or restructure it.

## Task 1 — Generate synthetic claims data: 3 full batches

1. Create a synthetic claims dataset generator (not a one-off static file — a reusable generator function/script) producing claims data matching the existing baseline schema (same fields as `inpatient_cleaned.csv`, including whatever produces `CLM_PMT_AMT` and the fields used by the existing quality checks: completeness, code set, range, dtype, validity, uniqueness, missing rate, duplicate rate, freshness).
2. Generate **Batch 1** as a full, clean-ish baseline batch capable of flowing through the entire pipeline (ingestion → GX validation → Isolation Forest anomaly detection → XGBoost risk scoring → incident generation) and producing at least one incident of each severity tier (Critical/High/Medium/Low) so the dashboard has representative data on first load.
3. Generate **Batch 2** and **Batch 3** as distinct batches with different injected issue profiles and different volumes, so re-running the pipeline against them produces visibly different dashboard numbers (not the same output three times). Vary things like: which quality checks fail, which anomaly injection types are present, claim volume, and claim amount distribution shape.
4. Each batch must support the existing injection-type taxonomy already shown in the UI: **Missing-value spike, Amount spike, Duplicate spike, Volume drop, Distribution shift** — build the generator so it can deliberately inject any of these into a batch, at a configurable rate, and knows the injected ground truth per row (needed for computing Recall/Precision/F1 in Task 3's Isolation Forest eval, and for the Simulator's "inject anomalies" toggle in Task 4).
5. These three batches are the data source for both the initial dashboard state and the Simulator page (Task 4) — do not build separate, disconnected demo data for each.

## Task 2 — Real models, demo-scoped (not full production hardening)

Replace the current models with real implementations. Keep this lightweight/fast enough for a live demo (small `n_estimators`, reasonable training data size) but do not fake the output — every number on the dashboard must come from these models actually running against the synthetic batches.

**2a. Data quality validation → Great Expectations (GX)**
- Build a GX Expectation Suite covering the existing expectation types: completeness, code set, range, dtype, validity, uniqueness, missing rate, duplicate rate, freshness.
- Run it against whichever batch is currently active/ingested, and compute the composite 0–100 score and per-type Pass/Warn/Critical counts from real GX validation results.
- Emit a run ID and timestamp per run, matching the current "one run retained as a snapshot" UI behavior.

**2b. Anomaly detection → Isolation Forest**
- Replace IQR with a scikit-learn `IsolationForest`, trained on clean (non-injected) data from the active batch.
- Evaluate against the injected anomalies in that batch (using the ground-truth injection labels from Task 1) and compute Recall/Precision/F1 per injection type, plus overall F1 and false-positive rate — matching the existing UI panel.
- Enforce the existing stated constraint: training data must never include injected rows; injections only appear in the evaluation split.
- Update the "PRODUCTION MODEL" label and metrics in the UI to reflect Isolation Forest's real, freshly computed values.

**2c. Risk prediction → XGBoost**
- Replace linear regression with an XGBoost model producing the 0–100 Risk Score used on incident cards, the Recent Incidents table's Risk column, and the Incident Severity Distribution panel.
- See Task 5 for the required input signals and severity-band mapping — build this model against that spec, not just a single blended feature.
- It's fine if this is trained on synthetic/rule-derived labels for the demo (document how you derived training labels), as long as the model itself is real and actually run at inference time.

## Task 3 — Root cause / Investigation / Recommended fix text

Keep these driven by the actual detected anomaly type and that specific incident's real stats (e.g., which injection type Isolation Forest flagged, which window, magnitude of deviation from baseline) — template-per-anomaly-type is fine for the demo, but the filled-in values (window ID, affected claim count, which distribution shifted) must come from the real run's output, not static copy.

## Task 4 — Simulator page (new)

Build a new **Simulator** page with:

1. **Fixed-interval ingestion.** A "Run Simulation" control that ingests the active batch's data in chunks, one chunk every **fixed N-second interval** (pick a sensible default, e.g. every 3–5 seconds, and hardcode it — no configurable interval needed). Each tick should feel like continuous incoming data, not one giant dump.
2. **Batch selection.** Let the user pick which of the 3 synthetic batches to run (or default to cycling through them).
3. **Anomaly injection toggle.** A control to either (a) run detection on the batch as-generated, or (b) inject anomalies on top of it at simulation time, using the same injection types from Task 1. If (b), use the generator's injection capability live rather than requiring a pre-baked "injected" file.
4. **Pipeline trigger on completion.** Once a batch finishes ingesting (all chunks streamed), automatically trigger the full pipeline — GX validation → Isolation Forest detection → XGBoost risk scoring → incident generation — and push the results to the main dashboard, exactly as if a real batch had landed.
5. **File upload, on this same page (no separate upload page).** Add an upload control directly on the Simulator page. An uploaded file must be validated against the expected schema and run through the identical ingestion → GX → Isolation Forest → XGBoost → incident pipeline as the synthetic batches. If the schema doesn't match, show a clear error rather than silently failing.
6. Show simple progress/status on this page while a simulation or upload is running (e.g., which chunk/window is currently being ingested, and when analysis kicks off) so it's demo-able live.

## Task 5 — Risk scoring: all risk categories, correctly mapped

1. Risk scoring must be computed from multiple distinct signal types, not one blended number silently averaged. At minimum, compute sub-scores for: **missing-data risk, null risk, duplicate risk, SLA/timeliness risk**, plus the existing quality dimensions already in the taxonomy (range, dtype, validity, uniqueness, freshness) and the anomaly-detection signal from Isolation Forest.
2. Feed these sub-scores into the XGBoost risk model as features (document the exact feature list you use).
3. Confirm the resulting 0–100 output correctly maps to the existing severity bands (Critical/High/Medium/Low) already shown in the Incident Severity Distribution panel and incident cards — verify the thresholds are consistent across every place a severity band is displayed (KPI tiles, incident table, incident detail, severity distribution panel).
4. In your summary, show the mapping table you used (score range → band) so it can be sanity-checked.

## Task 6 — Page removals / consolidation

1. **Remove** the standalone Settings page and the standalone Incidents (list) page entirely — routes, nav links, and any components exclusively used by them.
2. **History page**: this becomes the home for incident history (what the removed Incidents page used to show). Make sure it is fully populated with real incident data across all runs (not just the most recent), including incidents generated from Simulator runs and file uploads, not only the initial baseline batches.
3. "Investigate" actions on any incident row/card must still route to a working incident detail view — repoint any links that previously pointed to the removed Incidents page so they point to History (or directly to the incident detail route) instead.
4. Double check nothing else in the app links to the removed pages (nav bar, breadcrumbs, redirects) and clean those up too.

## Validation before finishing

1. Run all 3 synthetic batches through the pipeline once and confirm the dashboard shows different, internally consistent numbers for each (quality score, issue counts, anomaly metrics, incident counts/severities all reconcile with each other).
2. Run the Simulator end-to-end at least once with anomaly injection **on** and once **off**, and confirm incidents land in History correctly in both cases.
3. Upload a file via the Simulator page's upload control and confirm it flows through the same pipeline and produces incidents in History.
4. Confirm Settings and Incidents pages are fully gone and nothing 404s or dead-links to them.
5. In your final response, summarize: files changed/added, where the synthetic data generator lives and how to regenerate/reseed it, the real model metrics produced by each batch, the risk-score → severity mapping table, and anything ambiguous you had to make a judgment call on.
