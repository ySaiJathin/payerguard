"""Orchestrates an accepted upload through the existing Phase 2-12
pipeline (spec FR-003).

**Shared-state note, read before changing this file.** Only the raw
upload itself is batch-scoped storage (`app.ingestion.paths.batch_upload_path`).
Everything downstream -- Phase 2's cleaned batch, Phase 3's quality
results, Phase 5's feature log, Phase 7's anomaly enrichment -- is read
and written through each phase's own *default*, shared, single-current-
batch locations, exactly as their own routers already call them. This is
not a shortcut this feature introduced: `anomaly.window_enrichment`'s
default inputs (`load_benchmark_inputs`/`load_claim_window_map`) have no
per-batch override at all, so batch-scoped isolation everywhere else in
the chain would be inconsistent with what Phase 7 can actually honor.
Practically, this means an ingested batch becomes "the current batch"
system-wide the same way re-running any phase's router already does --
and a batch's `quality_result_id`/`anomaly_result_id`/`risk_result_id`
are reliable only until a *later* batch's run supersedes them, same
limitation `app.demo.pipeline` already lives with for the identical
reason (see its own module docstring).

Baseline is **not** recomputed per batch. `compute_features` (Phase 5)
already reads whatever baseline currently exists via
`read_latest_baseline_snapshot()` -- recomputing it here would compare
this batch against itself, making every deviation trivially zero.
Refreshing the baseline to fold new data into history is Phase 4's own
separate, explicit operation, out of scope for a single ingestion call.
"""

from pathlib import Path

from sqlalchemy.orm import Session

from app.anomaly.window_enrichment import enrich_windows
from app.data_engineering.cleaning_service import run_cleaning
from app.features import features_log
from app.features.features_service import compute_features
from app.ingestion import batch_service
from app.ingestion.schemas import BatchStatus
from app.incidents.schemas import EvidenceBundle, IncidentCreate
from app.incidents.service import create_incident
from app.quality.quality_results_log import read_quality_results
from app.quality.scoring_service import run_validation
from app.risk.dataset.row_assembly import assemble_rows
from app.risk.scoring.inference import score_window

# MVP default (mirrors app.demo.pipeline's identical constant and
# rationale): below this a window is quiet enough that an incident would
# be noise. Configurable, not silently assumed permanent.
INCIDENT_RISK_FLOOR = 10.0


class PipelineRunError(RuntimeError):
    """Raised when a stage fails after the upload was accepted; the caller
    (router) still returns 201 for the *upload*, but the batch's own
    `status` (set to `failed` before this is raised) is the honest signal
    of pipeline outcome (spec FR-007, SC-004)."""


def run(db: Session, batch_id: str, raw_path: Path) -> None:
    # `last_completed_stage` is reported on failure -- deliberately not the
    # stage that was *about to* run when the exception hit. Conflating the
    # two was an actual bug caught by
    # tests/ingestion/test_partial_failure_status.py: reporting "quality"
    # for a batch that never got past cleaning would itself be a
    # fabricated claim about what completed (constitution Principle II).
    last_completed_stage: str | None = None
    try:
        batch_service.update_batch_status(db, batch_id, status=BatchStatus.processing)

        run_cleaning(source_path=raw_path, db=db)
        last_completed_stage = "cleaning"
        batch_service.update_batch_status(
            db, batch_id, status=BatchStatus.processing, pipeline_stage_reached=last_completed_stage
        )

        quality_result = run_validation()
        last_completed_stage = "quality"
        batch_service.update_batch_status(
            db,
            batch_id,
            status=BatchStatus.processing,
            pipeline_stage_reached=last_completed_stage,
            quality_result_id=quality_result.run_id,
        )

        claim_features, window_features = compute_features()
        features_log.write_claim_features(claim_features)
        features_log.write_window_features(window_features)
        last_completed_stage = "features"
        batch_service.update_batch_status(
            db, batch_id, status=BatchStatus.processing, pipeline_stage_reached=last_completed_stage
        )

        enrich_result = enrich_windows()
        last_completed_stage = "anomaly"
        batch_service.update_batch_status(
            db,
            batch_id,
            status=BatchStatus.processing,
            pipeline_stage_reached=last_completed_stage,
            # No per-run anomaly result id exists upstream (Phase 7 has no
            # persisted-with-its-own-id record for one enrichment pass) --
            # recording which model was used is the honest alternative to
            # inventing one (constitution Principle II).
            anomaly_result_id=enrich_result.model_used,
        )

        rows = assemble_rows()
        quality_payload = read_quality_results()
        quality_check_bands = [c.band.value for c in quality_payload[1]] if quality_payload else []

        incident_ids: list[str] = []
        risk_model_used: str | None = None
        for row in rows:
            risk_score = score_window(row)
            risk_model_used = risk_model_used or "production"
            if risk_score < INCIDENT_RISK_FLOOR:
                continue
            evidence = EvidenceBundle(
                quality_check_bands=quality_check_bands,
                anomaly_score_percentile=row["anomaly_score"],
                affected_claim_pct=row["affected_claim_pct"],
                # Per-claim affected-amount detail requires joining
                # claim-level payment amounts to this window's anomaly
                # flags, which no existing service function currently
                # exposes -- left empty and honestly marked "unavailable"
                # by compute_business_impact rather than fabricated
                # (constitution Principle II). A documented simplification,
                # not an oversight.
                affected_claims_amounts=[],
                risk_score=risk_score,
                baseline_amount_percentiles=None,
            )
            incident = create_incident(db, IncidentCreate(window_id=row["window_id"], evidence=evidence))
            incident_ids.append(incident.incident_id)

        batch_service.update_batch_status(
            db,
            batch_id,
            status=BatchStatus.completed,
            pipeline_stage_reached="incidents",
            risk_result_id=risk_model_used,
            incident_ids=incident_ids,
        )
    except Exception as exc:
        # Deliberately broad: every stage above can raise a different,
        # phase-owned exception type (CleaningError,
        # QualityInputUnavailableError, FeaturesInputUnavailableError,
        # AnomalyEnrichmentIncompleteError, NoProductionRiskModelError,
        # RiskDatasetInputUnavailableError, ...). The batch's own `status`
        # is the thing that must never lie about a mid-pipeline failure
        # (FR-007, SC-004) -- narrowing this to a specific exception list
        # would risk a stage's new/changed error type silently bypassing
        # the honest-failure guarantee this function exists to provide.
        batch_service.update_batch_status(
            db, batch_id, status=BatchStatus.failed, pipeline_stage_reached=last_completed_stage
        )
        raise PipelineRunError(
            f"Batch {batch_id} failed after last completing stage {last_completed_stage!r}: {exc}"
        ) from exc
