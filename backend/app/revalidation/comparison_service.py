"""Honest before/after comparison (spec FR-005, FR-006, SC-002).

Pairs the incident's stored pre-remediation scores with the genuinely
recomputed post-remediation scores and computes real deltas. No
clamping, no `max(0, ...)`, no forced-positive logic anywhere in this
file -- a delta may be negative, meaning the signal got worse, and that
must be reported exactly as computed (remediation is never assumed
successful by default).
"""

from app.incidents.models import Incident as IncidentORM
from app.revalidation.schemas import BeforeAfterComparison, RecomputedScores


def build_comparison(revalidation_id: str, incident: IncidentORM, recomputed: RecomputedScores) -> BeforeAfterComparison:
    quality_before = incident.quality_score
    anomaly_before = incident.anomaly_score
    risk_before = incident.risk_score
    severity_before = (incident.severity_result or {}).get("severity", 0.0)
    priority_before = (incident.priority_result or {}).get("priority", 0.0)

    quality_after = recomputed.quality_score
    anomaly_after = recomputed.anomaly_score
    risk_after = recomputed.risk_score
    severity_after = recomputed.severity
    priority_after = recomputed.priority

    return BeforeAfterComparison(
        revalidation_id=revalidation_id,
        quality_before=quality_before,
        quality_after=quality_after,
        quality_delta=quality_after - quality_before,
        anomaly_before=anomaly_before,
        anomaly_after=anomaly_after,
        anomaly_delta=anomaly_after - anomaly_before,
        risk_before=risk_before,
        risk_after=risk_after,
        risk_delta=risk_after - risk_before,
        severity_before=severity_before,
        severity_after=severity_after,
        severity_delta=severity_after - severity_before,
        priority_before=priority_before,
        priority_after=priority_after,
        priority_delta=priority_after - priority_before,
    )
