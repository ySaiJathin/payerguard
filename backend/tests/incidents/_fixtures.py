"""Shared fixture builders for incidents/hitl tests -- not a test module
itself (no `test_` prefix, so pytest doesn't collect it)."""

from app.incidents.schemas import EvidenceBundle, IncidentCreate


def make_evidence(
    quality_check_bands: list[str] | None = None,
    anomaly_score_percentile: float = 0.9,
    affected_claim_pct: float = 0.2,
    risk_score: float | None = 0.6,
) -> EvidenceBundle:
    return EvidenceBundle(
        quality_check_bands=quality_check_bands if quality_check_bands is not None else ["CRITICAL", "WARNING"],
        anomaly_score_percentile=anomaly_score_percentile,
        affected_claim_pct=affected_claim_pct,
        affected_claims_amounts=[],
        risk_score=risk_score,
    )


def make_incident_create(window_id: str = "W1", **evidence_kwargs) -> IncidentCreate:
    return IncidentCreate(window_id=window_id, evidence=make_evidence(**evidence_kwargs))
