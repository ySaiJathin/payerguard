"""Root Cause / Investigation / Recommended Fix text (demo Task 3).

The wording is a template per detected anomaly type; every number, window
id, column name and claim count inside it is substituted from the real
run's output. Nothing here is static copy about a hypothetical incident --
if the Isolation Forest flagged 41 claims in window `2026-W07` and the
dominant injected type was an amount spike, that is what the text says.

`insufficient_evidence` is set honestly: when a window produced no flagged
claims and no failing expectations, the templates decline to name a root
cause rather than inventing one.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.demo.schemas import WindowRiskAssessment
from app.llm.schemas import LLMInvestigation

MODEL_VERSION = "payerguard-demo-templates/v1"

_TEMPLATES: dict[str, dict[str, str]] = {
    "amount_spike": {
        "risk_summary": (
            "Paid amounts in {window_id} run far above the batch baseline. Left unqueued, "
            "{anomaly_claim_count} claims worth {exposure} flow through to payment and reporting at "
            "the inflated value."
        ),
        "root_cause": (
            "An amount-mapping fault on ingestion: {anomaly_claim_count} of {claim_count} claims in "
            "{window_id} carry payment values {deviation_pct:.0f}% above the batch median, while the "
            "rest of the window is unaffected."
        ),
        "investigation": (
            "Isolation Forest flagged {anomaly_claim_count} of {claim_count} claims "
            "({anomaly_pct:.1f}% of the window) between {window_start} and {window_end}. The "
            "amount-spike detection recall for this run is {recall:.2f} at precision {precision:.2f}. "
            "Validity checks on the amount columns are {validity_state} and the window's range "
            "sub-score is {range_risk:.0f}/100."
        ),
        "recommended_fix": (
            "Quarantine the {anomaly_claim_count} flagged claims in {window_id}, re-run the amount "
            "mapping for that ingestion window, then re-validate and re-score before releasing."
        ),
        "prevention": (
            "Add an upper-bound expectation on the paid-amount columns calibrated to the batch p99 "
            "so a mapping fault fails validation at ingestion rather than at detection."
        ),
    },
    "duplicate_spike": {
        "risk_summary": (
            "Duplicate claims in {window_id} inflate both volume and payment exposure. "
            "{anomaly_claim_count} duplicated claims account for {exposure} of double-counted value."
        ),
        "root_cause": (
            "An ingestion retry replayed part of the window: the duplicate rate for {window_id} is "
            "{duplicate_risk:.0f}/100 on the duplicate sub-score, against a batch expectation of a "
            "clean claim-grain feed."
        ),
        "investigation": (
            "{anomaly_claim_count} of {claim_count} claims between {window_start} and {window_end} "
            "were flagged. Duplicate-spike recall is {recall:.2f} at precision {precision:.2f}; the "
            "batch-level uniqueness expectation is {uniqueness_state} and the window's uniqueness "
            "sub-score is {uniqueness_risk:.0f}/100."
        ),
        "recommended_fix": (
            "Deduplicate {window_id} on claim id plus source batch, confirm the claim-grain "
            "uniqueness expectation passes, and reprocess the corrected window."
        ),
        "prevention": (
            "Make ingestion idempotent on claim id per source batch so a replay is a no-op instead "
            "of a second insert."
        ),
    },
    "missing_value_spike": {
        "risk_summary": (
            "Required fields are absent across {anomaly_claim_count} claims in {window_id}. "
            "Downstream scoring silently degrades when the fields it reads are null."
        ),
        "root_cause": (
            "An upstream field-mapping or extract truncation: the window's overall missing-cell "
            "sub-score is {missing_data_risk:.0f}/100 and its business-critical null sub-score is "
            "{null_risk:.0f}/100, both well above the rest of the batch."
        ),
        "investigation": (
            "Isolation Forest flagged {anomaly_claim_count} of {claim_count} claims "
            "({anomaly_pct:.1f}%) between {window_start} and {window_end}, with missing-value-spike "
            "recall {recall:.2f} at precision {precision:.2f}. Completeness expectations are "
            "{completeness_state} for this run."
        ),
        "recommended_fix": (
            "Re-pull {window_id} from the source extract, confirm the field mapping for the affected "
            "columns, and re-run validation before the window is scored again."
        ),
        "prevention": (
            "Fail the batch at ingestion when a business-critical column's missing rate exceeds its "
            "calibrated ceiling, rather than passing partially populated rows downstream."
        ),
    },
    "volume_drop": {
        "risk_summary": (
            "{window_id} received materially fewer claims than the surrounding windows. Claims that "
            "never arrived cannot be scored, so the window looks healthier than it is."
        ),
        "root_cause": (
            "A delayed or partial batch: {claim_count} claims landed in {window_id}, and the "
            "timeliness sub-score for the window is {sla_timeliness_risk:.0f}/100 against the batch's "
            "own median processing lag."
        ),
        "investigation": (
            "Between {window_start} and {window_end} the detector flagged {anomaly_claim_count} of "
            "{claim_count} claims ({anomaly_pct:.1f}%). Volume-drop recall for this run is "
            "{recall:.2f} at precision {precision:.2f}; the window's freshness sub-score is "
            "{freshness_risk:.0f}/100."
        ),
        "recommended_fix": (
            "Check the source batch status for {window_start}..{window_end}, replay the missing "
            "records, then recompute quality, anomaly and risk for the window."
        ),
        "prevention": (
            "Alert on a window whose claim count falls below the trailing-window baseline, so a "
            "short delivery is caught before the window closes."
        ),
    },
    "distribution_shift": {
        "risk_summary": (
            "The numeric profile of {window_id} has moved away from the batch baseline across "
            "{anomaly_claim_count} claims, which biases every downstream model that assumes the "
            "prior distribution."
        ),
        "root_cause": (
            "A upstream schema, unit or population change: the window's range sub-score is "
            "{range_risk:.0f}/100 and its values sit {deviation_pct:.0f}% away from the batch median "
            "on the affected numeric columns."
        ),
        "investigation": (
            "{anomaly_claim_count} of {claim_count} claims between {window_start} and {window_end} "
            "were flagged ({anomaly_pct:.1f}%). Distribution-shift recall is {recall:.2f} at "
            "precision {precision:.2f}; the batch-level range and dtype expectations are "
            "{range_state}."
        ),
        "recommended_fix": (
            "Compare {window_id}'s numeric column profile against the batch baseline, confirm the "
            "source units and population have not changed, and re-baseline only once the cause is "
            "identified."
        ),
        "prevention": (
            "Track per-window distribution distance against the baseline snapshot so a shift raises "
            "an incident at ingestion instead of surfacing through detection."
        ),
    },
}

_NO_DOMINANT_TYPE = {
    "risk_summary": (
        "{window_id} scored {risk_score:.0f}/100 on the risk model without a single dominant anomaly "
        "type: the score is driven by the window's data-quality sub-scores rather than by one "
        "detected pattern."
    ),
    "root_cause": (
        "No single anomaly type dominates {window_id}. The largest contributing signals are "
        "{top_signals}."
    ),
    "investigation": (
        "Between {window_start} and {window_end}, {anomaly_claim_count} of {claim_count} claims were "
        "flagged ({anomaly_pct:.1f}%). Overall detection F1 for this run is {f1:.2f} at a "
        "false-positive rate of {fpr:.2f}."
    ),
    "recommended_fix": (
        "Review the top contributing sub-scores for {window_id} ({top_signals}) before treating this "
        "as a single-cause incident."
    ),
    "prevention": (
        "Keep per-window sub-scores visible alongside the composite risk score so a multi-signal "
        "window is not mistaken for one pattern."
    ),
}

_INSUFFICIENT = {
    "risk_summary": (
        "{window_id} produced no flagged claims and no failing expectations. There is not enough "
        "evidence here to describe a risk."
    ),
    "root_cause": "Insufficient evidence: nothing in {window_id} deviated from the batch baseline.",
    "investigation": (
        "{claim_count} claims between {window_start} and {window_end}; zero flagged by the detector "
        "and no expectation failures attributable to this window."
    ),
    "recommended_fix": "No remediation is indicated for {window_id}.",
    "prevention": "No preventive action is indicated from this window's evidence.",
}


def _band_state(bands: list[str], expectation_types: set[str] | None = None) -> str:
    if not bands:
        return "not evaluated"
    if "CRITICAL" in bands:
        return "failing (CRITICAL)"
    if "WARNING" in bands:
        return "in warning"
    return "passing"


def _format_currency(amount: float) -> str:
    return f"${amount:,.0f}"


def build_context(
    window: WindowRiskAssessment,
    overall_f1: float,
    overall_fpr: float,
    per_type: dict[str, dict[str, float]],
    quality_type_bands: dict[str, dict[str, int]],
) -> dict:
    injection_type = window.dominant_injection_type
    type_metrics = per_type.get(injection_type or "", {})
    sub = window.sub_scores

    def state(expectation_type: str) -> str:
        counts = quality_type_bands.get(expectation_type, {})
        if not counts:
            return "not evaluated"
        if counts.get("CRITICAL", 0):
            return f"failing ({counts['CRITICAL']} CRITICAL)"
        if counts.get("WARNING", 0):
            return f"in warning ({counts['WARNING']} WARNING)"
        return "passing"

    top_signals = ", ".join(
        f"{name.replace('_', ' ')} {value:.0f}/100"
        for name, value in sorted(
            sub.model_dump().items(), key=lambda item: item[1], reverse=True
        )[:3]
    )

    return {
        "window_id": window.window_id,
        "window_start": window.window_start,
        "window_end": window.window_end,
        "claim_count": window.claim_count,
        "anomaly_claim_count": window.anomaly_claim_count,
        "anomaly_pct": window.affected_claim_pct * 100.0,
        "risk_score": window.risk_score,
        "deviation_pct": window.deviation_pct,
        "exposure": _format_currency(sum(window.affected_claims_amounts)),
        "recall": type_metrics.get("recall", 0.0),
        "precision": type_metrics.get("precision", 0.0),
        "f1": overall_f1,
        "fpr": overall_fpr,
        "top_signals": top_signals,
        "validity_state": state("validity"),
        "uniqueness_state": state("uniqueness"),
        "completeness_state": state("completeness"),
        "range_state": state("range"),
        **{name: value for name, value in sub.model_dump().items()},
    }


def render(window: WindowRiskAssessment, context: dict) -> dict[str, str]:
    """Picks the template for the window's dominant detected anomaly type
    and fills it from the real run context."""
    if window.anomaly_claim_count == 0 and window.risk_score < 15:
        template = _INSUFFICIENT
    elif window.dominant_injection_type in _TEMPLATES:
        template = _TEMPLATES[window.dominant_injection_type]
    else:
        template = _NO_DOMINANT_TYPE

    return {key: value.format(**context) for key, value in template.items()}


def to_investigation(incident_id: str, window: WindowRiskAssessment, narrative: dict[str, str]) -> LLMInvestigation:
    """The same text, recorded through Phase 11's investigation log so the
    Investigation page and the incident detail read one source."""
    insufficient = narrative["root_cause"].startswith("Insufficient evidence")
    return LLMInvestigation(
        investigation_id=str(uuid4()),
        incident_id=incident_id,
        evidence_snapshot_id=window.window_id,
        summary=narrative["risk_summary"],
        likely_root_cause=narrative["root_cause"],
        insufficient_evidence=insufficient,
        evidence=narrative["investigation"],
        business_impact_narrative=(
            f"{window.anomaly_claim_count} of {window.claim_count} claims in {window.window_id} are "
            f"affected, carrying {_format_currency(sum(window.affected_claims_amounts))} of exposure."
        ),
        recommended_fix=narrative["recommended_fix"],
        prevention_recommendation=narrative["prevention"],
        model_version=MODEL_VERSION,
        generated_at=datetime.now(timezone.utc),
    )
