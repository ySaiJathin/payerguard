"""End-to-end demo pipeline: ingest -> GX -> Isolation Forest -> XGBoost -> incidents.

One function, `run_pipeline`, is the single path every entry point uses --
the initial dashboard seed, each of the three synthetic batches, a
Simulator run (with or without live injection) and an uploaded file all go
through exactly this code. There is no second, easier path for demo data.

Results are written back through the *existing* phase artifacts rather than
new dashboard-specific ones:

- `quality_results_log`     -> `GET /quality/results`
- `snapshot_log`            -> `GET /baseline`
- `anomaly_benchmark_results.json` -> `GET /anomaly/results`
- the `incidents` table     -> `GET /incidents`

so the dashboard keeps reading the endpoints it already read, unchanged.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from app.baseline import snapshot_log
from app.baseline.snapshot_service import compute_baseline_snapshot
from app.data_engineering.dtype_conversion import load_column_categories
from app.demo import anomaly_runner, narrative, paths, risk_model
from app.demo.generator import CLAIM_FROM_COLUMN, NO_INJECTION, ROW_KEY_COLUMN
from app.demo.quality_runner import band_counts, band_counts_by_type, validate_batch
from app.demo.schemas import PipelineRunResult, WindowRiskAssessment
from app.incidents import service as incidents_service
from app.demo.column_profile import load_column_profile
from app.demo.generator import inject
from app.demo.schemas import InjectionCluster, InjectionPlan, InjectionType
from app.incidents.schemas import EvidenceBundle, IncidentCreate, IncidentUpdate

ACTIVE_BATCH_FILENAME = "active_batch.csv"
PAYMENT_COLUMN = "CLM_PMT_AMT"
# Below this the window is quiet enough that an incident would be noise.
# It sits inside the LOW band rather than at its ceiling, so a healthy batch
# still produces LOW incidents and the severity distribution has a floor to
# compare its CRITICAL and HIGH counts against.
INCIDENT_RISK_FLOOR = 10.0
MAX_AFFECTED_AMOUNTS = 50

# What the Simulator's "inject anomalies" toggle applies on top of the batch
# as generated: one co-located cluster (a fresh incident to find) plus a thin
# background of every type. It uses the generator's own injection code, not a
# pre-baked second copy of the batch.
LIVE_INJECTION_PLAN = InjectionPlan(
    clusters=[
        InjectionCluster(
            name="live-cluster",
            rates={
                InjectionType.missing_value_spike: 0.02,
                InjectionType.duplicate_spike: 0.015,
                InjectionType.amount_spike: 0.02,
            },
            density=1.0,
        )
    ],
    rates={
        InjectionType.volume_drop: 0.01,
        InjectionType.distribution_shift: 0.015,
    },
)


def active_batch_path() -> Path:
    return paths.demo_dir() / ACTIVE_BATCH_FILENAME


def _write_active_batch(df: pd.DataFrame) -> Path:
    """The pipeline's inputs are file-backed on purpose: the freshness
    expectation measures the batch file's mtime, and the baseline snapshot
    records the batch path as its provenance."""
    path = active_batch_path()
    df.to_csv(path, index_label=ROW_KEY_COLUMN)
    return path


def _window_assessments(
    df: pd.DataFrame,
    labels: pd.Series,
    flags: pd.Series,
    categories: dict,
    anomaly_percentile_threshold: float,
) -> list[WindowRiskAssessment]:
    context = risk_model.build_batch_context(df, categories, flags)
    windows = risk_model.assign_windows(df)
    batch_median_amount = float(pd.to_numeric(df[PAYMENT_COLUMN], errors="coerce").median() or 0.0)

    assessments: list[WindowRiskAssessment] = []
    sub_score_list = []
    for window_start, index in windows.groupby(windows).groups.items():
        window_df = df.loc[index]
        window_flags = flags.reindex(index).fillna(False)
        sub_scores = risk_model.compute_sub_scores(window_df, window_flags, context)
        sub_score_list.append(sub_scores)

        flagged_index = [row for row in index if bool(window_flags.loc[row])]
        flagged_labels = labels.reindex(flagged_index).fillna(NO_INJECTION)
        injected = flagged_labels[flagged_labels != NO_INJECTION]
        dominant = str(injected.value_counts().idxmax()) if len(injected) else None

        amounts = pd.to_numeric(window_df.loc[flagged_index, PAYMENT_COLUMN], errors="coerce").dropna()
        window_median = float(pd.to_numeric(window_df[PAYMENT_COLUMN], errors="coerce").median() or 0.0)
        deviation_pct = (
            (window_median - batch_median_amount) / batch_median_amount * 100.0
            if batch_median_amount
            else 0.0
        )

        start, end = risk_model.window_bounds(str(window_start))
        assessments.append(
            WindowRiskAssessment(
                window_id=f"W-{start}",
                window_start=start,
                window_end=end,
                claim_count=len(index),
                sub_scores=sub_scores,
                risk_score=0.0,  # filled in by the model below
                severity_band="LOW",
                anomaly_claim_count=len(flagged_index),
                dominant_injection_type=dominant,
                affected_claim_pct=len(flagged_index) / len(index) if len(index) else 0.0,
                affected_claims_amounts=[round(float(a), 2) for a in amounts.head(MAX_AFFECTED_AMOUNTS)],
                anomaly_score_percentile=anomaly_percentile_threshold,
                quality_check_bands=[],
                deviation_pct=deviation_pct,
            )
        )

    scores = risk_model.predict_risk(sub_score_list)
    for assessment, score in zip(assessments, scores):
        assessment.risk_score = score
        assessment.severity_band = risk_model.severity_band(score)

    assessments.sort(key=lambda a: a.window_start)
    return assessments


def _quality_bands_for_window(check_results, assessment: WindowRiskAssessment) -> list[str]:
    """Which expectation bands this window inherits.

    The GX suites run at batch grain, so a window inherits the batch's
    failing bands; what makes the window's severity differ is that only the
    bands whose *signal* is actually elevated in this window are carried
    over. A window with no missing-data problem does not inherit the
    batch's completeness failures.
    """
    sub = assessment.sub_scores
    signal_by_type = {
        "completeness": sub.missing_data_risk,
        "missing_rate": sub.missing_data_risk,
        "duplicate_rate": sub.duplicate_risk,
        "uniqueness": sub.uniqueness_risk,
        "validity": sub.validity_risk,
        "range": sub.range_risk,
        "dtype": sub.dtype_risk,
        "code_set": sub.null_risk,
        "freshness": sub.freshness_risk,
    }
    bands: list[str] = []
    for check in check_results:
        if check.band.value == "PASS":
            bands.append("PASS")
            continue
        if signal_by_type.get(check.expectation_type.value, 0.0) >= 20.0:
            bands.append(check.band.value)
        else:
            bands.append("PASS")
    return bands


def run_pipeline(
    db: Session,
    df: pd.DataFrame,
    labels: pd.Series,
    batch_id: str,
    batch_label: str,
    source: str,
    injection_applied: bool,
) -> PipelineRunResult:
    started_at = datetime.now(timezone.utc)
    categories = load_column_categories()

    batch_path = _write_active_batch(df)

    # --- 1. Great Expectations validation -------------------------------
    score_result, check_results = validate_batch(df, batch_path)

    # --- 2. Baseline snapshot for the active batch ----------------------
    # Runs after validation because the data-health baseline consumes the
    # persisted check results.
    snapshot = compute_baseline_snapshot(batch_path=batch_path)
    snapshot_log.write_baseline_snapshot(snapshot)

    # --- 3. Isolation Forest --------------------------------------------
    evaluation, flags = anomaly_runner.fit_and_evaluate(df, labels, categories)
    anomaly_runner.publish_benchmark_result(evaluation)

    # --- 4. XGBoost risk scoring per window ------------------------------
    assessments = _window_assessments(
        df, labels, flags, categories, anomaly_percentile_threshold=1.0 - evaluation.fpr
    )
    quality_type_bands = band_counts_by_type(check_results)
    for assessment in assessments:
        assessment.quality_check_bands = _quality_bands_for_window(check_results, assessment)

    # --- 5. Incidents -----------------------------------------------------
    incident_ids: list[str] = []
    severity_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for assessment in assessments:
        if assessment.risk_score < INCIDENT_RISK_FLOOR:
            continue
        context = narrative.build_context(
            assessment, evaluation.f1, evaluation.fpr, evaluation.per_injection_type, quality_type_bands
        )
        rendered = narrative.render(assessment, context)

        evidence = EvidenceBundle(
            quality_check_bands=assessment.quality_check_bands,
            anomaly_score_percentile=assessment.anomaly_score_percentile,
            affected_claim_pct=assessment.affected_claim_pct,
            affected_claims_amounts=assessment.affected_claims_amounts,
            risk_score=assessment.risk_score,
            baseline_amount_percentiles=(
                snapshot.amount_baselines[0].percentiles if snapshot.amount_baselines else None
            ),
            analysis_context={
                "batch_id": batch_id,
                "batch_label": batch_label,
                "source": source,
                "injection_applied": injection_applied,
                "window_start": assessment.window_start,
                "window_end": assessment.window_end,
                "claim_count": assessment.claim_count,
                "anomaly_claim_count": assessment.anomaly_claim_count,
                "detected_anomaly_type": assessment.dominant_injection_type,
                "deviation_pct": round(assessment.deviation_pct, 2),
                "risk_model": "xgboost",
                "risk_score": assessment.risk_score,
                "severity_band": assessment.severity_band,
                "sub_scores": assessment.sub_scores.model_dump(),
                "narrative": rendered,
            },
        )

        incident = incidents_service.create_incident(
            db,
            IncidentCreate(window_id=assessment.window_id, evidence=evidence),
            investigation_builder=lambda incident_id, _payload, a=assessment, r=rendered: (
                narrative.to_investigation(incident_id, a, r)
            ),
        )
        # The severity the UI bands (`severity_result.severity`) is set to the
        # XGBoost risk score, so every surface -- KPI tiles, incident table,
        # incident detail and the severity distribution panel -- bands one
        # number against one set of thresholds. Phase 10's decomposition
        # (quality-failure severity, anomaly magnitude, materiality) is kept
        # untouched underneath as the explanation of the score.
        aligned_severity = dict(incident.severity_result)
        aligned_severity["severity"] = assessment.risk_score
        aligned_severity["risk_model_severity_source"] = "xgboost"
        incident = incidents_service.update_incident(
            db, incident.incident_id, IncidentUpdate(severity_result=aligned_severity)
        )

        incident_ids.append(incident.incident_id)
        severity_counts[assessment.severity_band] += 1

    result = PipelineRunResult(
        run_id=str(uuid4()),
        source=source,
        batch_id=batch_id,
        batch_label=batch_label,
        injection_applied=injection_applied,
        rows=int(len(df)),
        claims=int(df["CLM_ID"].nunique()),
        quality_run_id=score_result.run_id,
        quality_composite_score=score_result.composite_score,
        quality_band_counts=band_counts(check_results),
        quality_type_band_counts=quality_type_bands,
        anomaly=evaluation,
        windows=assessments,
        incident_ids=incident_ids,
        incident_severity_counts=severity_counts,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )
    append_run(result)
    return result


# --------------------------------------------------------------------------
# Run history
# --------------------------------------------------------------------------


def append_run(result: PipelineRunResult) -> None:
    path = paths.pipeline_runs_path()
    runs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    runs.append(json.loads(result.model_dump_json()))
    path.write_text(json.dumps(runs, indent=2), encoding="utf-8")


def read_runs() -> list[PipelineRunResult]:
    path = paths.pipeline_runs_path()
    if not path.exists():
        return []
    return [PipelineRunResult.model_validate(entry) for entry in json.loads(path.read_text(encoding="utf-8"))]


def run_batch(db: Session, batch_id: str, inject_extra: bool = False, source: str = "batch") -> PipelineRunResult:
    """Runs one of the three synthetic batches. `inject_extra` layers a
    second round of live injections on top of the batch as generated --
    the Simulator's "inject anomalies" toggle, using the generator's own
    injection capability rather than a pre-baked injected file."""
    from app.demo import batches

    spec = batches.spec_for(batch_id)
    df, labels = batches.load_batch(batch_id)

    if inject_extra:
        df, labels = inject(df, labels, LIVE_INJECTION_PLAN, load_column_profile(), seed=spec.seed + 7)
        df = df.sort_values(CLAIM_FROM_COLUMN, kind="stable")
        labels = labels.loc[df.index]

    return run_pipeline(
        db,
        df,
        labels,
        batch_id=spec.batch_id,
        batch_label=spec.label,
        source=source,
        injection_applied=inject_extra,
    )
