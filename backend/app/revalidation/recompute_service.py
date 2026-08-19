"""Genuine Phase 3/7/9/10 recomputation against caller-supplied current
(post-remediation) claim/feature state (spec FR-001-FR-004).

Never reads a cached/stale pre-remediation `ExpectationCheckResult` or
anomaly/risk score -- every value here comes from actually invoking
Phase 3's GX suites, Phase 7's/Phase 9's saved production model
artifacts, and Phase 10's scoring functions fresh (research.md's
"genuine recomputation enforced by calling ... functions with fresh
current-state inputs, never cached values" decision; spec SC-001).
"""

import pickle
from datetime import datetime, timezone
from uuid import uuid4

import great_expectations as gx
import pandas as pd

from app.anomaly.benchmark import read_benchmark_run_result
from app.baseline.schemas import Percentiles
from app.data_engineering.dtype_conversion import load_column_categories
from app.data_engineering.invalid_value_detection import build_reference_stats
from app.data_engineering.paths import models_dir, raw_inpatient_csv
from app.data_engineering.profiling_service import load_source_csv
from app.data_engineering.report_writer import read_profiling_report
from app.incidents.models import Incident as IncidentORM
from app.quality.completeness_calibration import build_calibration_table
from app.quality.expectations.range_checks import bounds_with_slack
from app.quality.schemas import ExpectationCheckResult
from app.quality.scoring_service import compute_composite_score, compute_file_level_checks, run_category_suites
from app.quality.suite_builder import build_suites
from app.revalidation.schemas import CurrentClaimState, RecomputedScores, RevalidationRunRequest
from app.risk.benchmark import benchmark_log
from app.risk.scoring import business_impact as business_impact_module
from app.risk.scoring import priority as priority_module
from app.risk.scoring import severity as severity_module

# Design Note 3 (tasks.md): the saved anomaly artifact only carries a
# single calibrated threshold (the p95 cutoff), not a full distribution,
# so the raw-score-to-percentile conversion is this documented,
# saturating interpolation anchored at that one real calibration point.
_ANOMALY_NORMAL_BAND_CEILING = 0.95
_ANOMALY_PERCENTILE_HEADROOM = 1.0 - _ANOMALY_NORMAL_BAND_CEILING


class NoProductionAnomalyModelError(RuntimeError):
    """Raised when Phase 7 hasn't produced a `ProductionModelSelection`
    (or its pickled artifact) yet -- distinct from FR-009's incomplete-
    remediation-run gate."""


class NoProductionRiskModelError(RuntimeError):
    """Raised when Phase 9 hasn't produced a `ProductionRiskModelSelection`
    (or its pickled artifact) yet -- distinct from FR-009's incomplete-
    remediation-run gate."""


def _claims_to_dataframe(current_claims: list[CurrentClaimState]) -> pd.DataFrame:
    rows = [{"CLM_ID": claim.claim_id, **claim.raw_fields} for claim in current_claims]
    return pd.DataFrame(rows)


def _recompute_quality(current_claims: list[CurrentClaimState]) -> tuple[list[ExpectationCheckResult], float]:
    """Genuinely re-executes Phase 3's GX suites against the current
    (post-remediation) raw field values for exactly the claims supplied
    -- a real, smaller-N GX batch, not a full-file run (FR-001)."""
    df = _claims_to_dataframe(current_claims)
    run_id = str(uuid4())
    evaluated_at = datetime.now(timezone.utc)

    categories = load_column_categories()
    profiling_report = read_profiling_report()
    raw_df = load_source_csv(raw_inpatient_csv(), expected_column_count=None)
    reference_stats = build_reference_stats(raw_df, categories)
    known_code_values = {col: sorted(values) for col, values in reference_stats.known_values.items()}
    date_bounds = bounds_with_slack(reference_stats.date_min, reference_stats.date_max)
    calibration = build_calibration_table(profiling_report) if profiling_report is not None else {}

    context = gx.get_context(mode="ephemeral")
    suite_runs = build_suites(
        context,
        df,
        categories,
        calibration,
        known_code_values,
        # Uniqueness here is scoped to *this* small revalidation batch,
        # not the full dataset's profiling_report.unique_claim_count --
        # every claim_id supplied should be unique within the batch
        # we're actually checking.
        expected_unique_claim_count=len(current_claims),
        reference_date_bounds=date_bounds,
    )

    check_results = run_category_suites(suite_runs, run_id, evaluated_at)
    check_results += compute_file_level_checks(df, run_id, evaluated_at)

    score_result = compute_composite_score(
        check_results, weights=None, run_id=run_id, batch_source="revalidation:current_claims", generated_at=evaluated_at
    )
    return check_results, score_result.composite_score


def _load_pickled_artifact(path):
    with path.open("rb") as f:
        return pickle.load(f)


def _recompute_anomaly(anomaly_features: dict[str, float]) -> tuple[float, float, str]:
    """Loads Phase 7's *currently selected* production model artifact and
    genuinely re-scores the caller-supplied current feature vector
    (FR-002, FR-010). Returns (anomaly_magnitude_score_0_100,
    anomaly_score_percentile, model_version)."""
    run_result = read_benchmark_run_result()
    if run_result is None:
        raise NoProductionAnomalyModelError(
            "No ProductionModelSelection exists yet -- run POST /anomaly/benchmark first."
        )

    model_type = run_result.production_model_selection.selected_model
    artifact_path = models_dir() / f"{model_type.value}.pkl"
    try:
        artifact = _load_pickled_artifact(artifact_path)
    except FileNotFoundError as exc:
        raise NoProductionAnomalyModelError(f"Selected anomaly model artifact not found at {artifact_path}.") from exc

    detector = artifact["model"]
    feature_columns: list[str] = artifact["feature_columns"]
    train_medians = artifact["train_medians"]
    p95_threshold = artifact["calibrated_thresholds"]["p95"]

    row = pd.DataFrame([{col: anomaly_features.get(col, train_medians.get(col)) for col in feature_columns}])
    raw_score = float(detector.score(row)[0])

    if raw_score < p95_threshold:
        percentile = min(_ANOMALY_NORMAL_BAND_CEILING, (raw_score / p95_threshold) * _ANOMALY_NORMAL_BAND_CEILING)
    else:
        excess_ratio = min(1.0, (raw_score - p95_threshold) / p95_threshold) if p95_threshold else 1.0
        percentile = _ANOMALY_NORMAL_BAND_CEILING + excess_ratio * _ANOMALY_PERCENTILE_HEADROOM

    anomaly_score_0_100 = severity_module.anomaly_magnitude_score(percentile)
    return anomaly_score_0_100, percentile, model_type.value


def _recompute_risk(risk_features: dict[str, float]) -> tuple[float, str]:
    """Loads Phase 9's *currently selected* production model artifact and
    genuinely re-scores the caller-supplied current window feature vector
    (FR-003, FR-010). Returns (risk_score_0_100, model_version)."""
    run_result = benchmark_log.read_latest_run_result()
    if run_result is None:
        raise NoProductionRiskModelError("No ProductionRiskModelSelection exists yet -- run POST /risk/benchmark first.")

    model_type = run_result.production_model_selection.selected_model
    artifact_path = models_dir() / "risk" / f"{model_type.value}.pkl"
    try:
        artifact = _load_pickled_artifact(artifact_path)
    except FileNotFoundError as exc:
        raise NoProductionRiskModelError(f"Selected risk model artifact not found at {artifact_path}.") from exc

    model = artifact["model"]
    feature_columns: list[str] = artifact["feature_columns"]

    row = pd.DataFrame([{col: risk_features.get(col, 0.0) for col in feature_columns}])
    risk_proba = float(model.predict_proba(row)[:, 1][0])
    # MVP_CONTEXT.md Section 3.3 states Risk Score on a 0-100 scale,
    # matching IncidentORM.risk_score's own stored scale (spec Assumptions
    # -- this feature's own documented scaling choice, not a new
    # invented threshold).
    return risk_proba * 100.0, model_type.value


def recompute(incident: IncidentORM, request: RevalidationRunRequest) -> RecomputedScores:
    check_results, quality_score = _recompute_quality(request.current_claims)
    anomaly_score, anomaly_percentile, anomaly_model_version = _recompute_anomaly(request.anomaly_features)
    risk_score, risk_model_version = _recompute_risk(request.risk_features)

    evidence = incident.evidence_snapshot or {}
    affected_claim_pct = evidence.get("affected_claim_pct", 0.0)
    # Stored as a plain JSON dict on evidence_snapshot; Phase 10's
    # severity/business-impact functions expect the real Percentiles
    # model (attribute access), not a dict.
    raw_baseline_percentiles = evidence.get("baseline_amount_percentiles")
    baseline_amount_percentiles = Percentiles(**raw_baseline_percentiles) if raw_baseline_percentiles else None
    affected_claims_amounts = (
        request.current_affected_claims_amounts
        if request.current_affected_claims_amounts is not None
        else evidence.get("affected_claims_amounts", [])
    )

    quality_check_bands = [result.band.value for result in check_results]

    severity_result = severity_module.compute_severity(
        quality_check_bands=quality_check_bands,
        anomaly_score_percentile=anomaly_percentile,
        affected_claim_pct=affected_claim_pct,
        affected_claims_amounts=affected_claims_amounts,
        baseline_amount_percentiles=baseline_amount_percentiles,
    )
    business_impact_result = business_impact_module.compute_business_impact(
        affected_claims_amounts=affected_claims_amounts,
        baseline_amount_percentiles=baseline_amount_percentiles,
    )
    priority_result = priority_module.compute_priority(
        severity=severity_result.severity,
        risk=risk_score,
        business_impact=business_impact_result.business_impact,
        affected_claims_score=priority_module.affected_claims_score(affected_claim_pct),
    )

    return RecomputedScores(
        quality_results=[result.model_dump(mode="json") for result in check_results],
        quality_score=quality_score,
        anomaly_score=anomaly_score,
        anomaly_score_percentile=anomaly_percentile,
        risk_score=risk_score,
        severity=severity_result.severity,
        business_impact=business_impact_result.business_impact,
        priority=priority_result.priority,
        severity_business_impact_priority={
            "severity_result": severity_result.model_dump(mode="json"),
            "business_impact_result": business_impact_result.model_dump(mode="json"),
            "priority_result": priority_result.model_dump(mode="json"),
        },
        anomaly_model_version=anomaly_model_version,
        risk_model_version=risk_model_version,
    )
