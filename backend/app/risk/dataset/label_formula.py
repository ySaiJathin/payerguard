"""Derives and documents the investigation-risk label (spec FR-003 through
FR-006; MVP_CONTEXT.md Section 2.4).

**Why not a timing/SLA-based label**: this dataset has no genuine
claims-adjudication-turnaround field (`FI_CLM_PROC_DT` is 100% null;
`NCH_WKLY_PROC_DT` is a fixed weekly batch-cutoff date, not an operational
timestamp -- see MVP_CONTEXT.md Section 2.4). The investigation-risk
target is instead built entirely from three real, already-computed
signals: quality-failure rate, anomaly frequency, and volume/amount
deviation.

**The formula**: a continuous Investigation Risk Indicator (IRI) per
window,

    IRI = w_q * norm(historical_quality_failure_rate)
        + w_a * norm(anomaly_frequency)
        + w_d * norm(amount_deviation_scalar)

where `norm(x)` min-max normalizes each signal to [0, 1] using statistics
computed *only* on Phase 6's train-split windows (never validation/test,
to avoid leaking label-calibration information into the split that will
evaluate Phase 9's model -- constitution Principle VII), and default
weights `w_q=0.4, w_a=0.4, w_d=0.2` (quality and anomaly weighted equally
as the two most direct "something is wrong here" signals; deviation
weighted lower as a softer, more ambiguous signal -- mirroring
MVP_CONTEXT.md Section 3.3's configurable-weighting style for Severity).
`investigation_risk_label = 1` if `IRI` is at or above the 75th percentile
of `IRI` over train-split windows, `0` otherwise. Zero-claim windows
always receive `investigation_risk_label = 0` regardless of `IRI` (spec
FR-006) -- there is nothing to investigate in a window with no claims.
"""

from datetime import datetime, timezone

from app.features.selection.schemas import TemporalSplit
from app.features.selection.temporal_split import assign_split
from app.risk.dataset.schemas import InvestigationRiskLabelFormula

FORMULA_VERSION = "v1"
DEFAULT_WEIGHTS = {"w_q": 0.4, "w_a": 0.4, "w_d": 0.2}
DEFAULT_PERCENTILE_THRESHOLD = 75.0

RATIONALE_TEXT = (
    "The investigation-risk label is not an SLA-breach / processing-turnaround label: "
    "per MVP_CONTEXT.md Section 2.4, this dataset has no genuine claims-adjudication-"
    "turnaround field ('FI_CLM_PROC_DT' is 100% null; 'NCH_WKLY_PROC_DT' is a fixed "
    "weekly batch-cutoff date, not an operational timestamp). Instead, this formula "
    "combines three real, already-computed signals -- historical quality-failure rate "
    "(Phase 4), anomaly frequency (Phase 7), and the larger of volume/amount deviation "
    "from baseline (Phase 5) -- into a single, documented Investigation Risk Indicator "
    "(IRI), thresholded at the 75th percentile of IRI over Phase 6's train-split windows "
    "only, to determine which windows are investigation-worthy."
)

_SIGNAL_KEYS = ("quality_failure_rate", "anomaly_frequency", "amount_deviation")
_SIGNAL_WEIGHT_KEYS = {
    "quality_failure_rate": "w_q",
    "anomaly_frequency": "w_a",
    "amount_deviation": "w_d",
}


def _signal_values(row: dict) -> dict[str, float]:
    return {
        "quality_failure_rate": row["historical_quality_failure_rate"] / 100,
        "anomaly_frequency": row["anomaly_frequency"],
        "amount_deviation": max(abs(row["volume_deviation"]), abs(row["amount_deviation"])),
    }


def _train_rows(rows: list[dict], split: TemporalSplit) -> list[dict]:
    return [r for r in rows if assign_split(r["window_start"], split) == "train"]


def _normalize(value: float, stats: dict[str, float]) -> float:
    lo, hi = stats["min"], stats["max"]
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def compute_formula(
    rows: list[dict],
    split: TemporalSplit,
    weights: dict[str, float] | None = None,
    percentile_threshold: float = DEFAULT_PERCENTILE_THRESHOLD,
    generated_at: datetime | None = None,
) -> InvestigationRiskLabelFormula:
    """Computes normalization stats from train-split rows only and returns
    the documented, versioned formula (spec FR-003, FR-004)."""
    weights = weights or DEFAULT_WEIGHTS
    train_rows = _train_rows(rows, split)
    if not train_rows:
        raise ValueError("No train-split rows available to calibrate the label formula against.")

    normalization_stats: dict[str, dict[str, float]] = {}
    for key in _SIGNAL_KEYS:
        values = [_signal_values(r)[key] for r in train_rows]
        normalization_stats[key] = {"min": min(values), "max": max(values)}

    return InvestigationRiskLabelFormula(
        formula_version=FORMULA_VERSION,
        weights=weights,
        normalization_stats=normalization_stats,
        percentile_threshold=percentile_threshold,
        rationale_text=RATIONALE_TEXT,
        generated_at=generated_at or datetime.now(timezone.utc),
    )


def _compute_iri(row: dict, formula: InvestigationRiskLabelFormula) -> float:
    signals = _signal_values(row)
    weights = formula.weights
    return sum(
        weights[_SIGNAL_WEIGHT_KEYS[key]] * _normalize(signals[key], formula.normalization_stats[key])
        for key in _SIGNAL_KEYS
    )


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    frac = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * frac


def apply_formula(
    rows: list[dict], formula: InvestigationRiskLabelFormula, split: TemporalSplit
) -> list[dict]:
    """Applies `formula` to every row, adding `investigation_risk_indicator`
    and `investigation_risk_label`. Reproducible by construction: a pure
    function of each row's own stored input fields plus the formula's own
    persisted weights/stats/threshold (spec FR-005, SC-002)."""
    train_rows = _train_rows(rows, split)
    train_iris = [_compute_iri(r, formula) for r in train_rows]
    threshold = _percentile(train_iris, formula.percentile_threshold)

    labeled_rows = []
    for row in rows:
        iri = _compute_iri(row, formula)
        label = 1 if (row["claim_count"] > 0 and iri >= threshold) else 0
        labeled_rows.append({**row, "investigation_risk_indicator": iri, "investigation_risk_label": label})
    return labeled_rows


def render_formula_markdown(formula: InvestigationRiskLabelFormula) -> str:
    """Renders `formula` as a standalone, human-reviewable Markdown
    artifact (spec FR-003, FR-004 -- "not only embedded in code")."""
    lines = [
        "# Investigation Risk Label Formula",
        "",
        f"**Version**: `{formula.formula_version}`",
        f"**Generated at**: {formula.generated_at.isoformat()}",
        "",
        "## Formula",
        "",
        "```",
        "IRI = w_q * norm(historical_quality_failure_rate)",
        "    + w_a * norm(anomaly_frequency)",
        "    + w_d * norm(max(|volume_deviation|, |amount_deviation|))",
        "",
        "investigation_risk_label = 1 if IRI >= percentile_threshold(IRI over train-split windows)",
        "                           else 0",
        "Zero-claim windows always receive investigation_risk_label = 0.",
        "```",
        "",
        "## Weights",
        "",
    ]
    for key, value in formula.weights.items():
        lines.append(f"- `{key}` = {value}")
    lines += ["", "## Normalization statistics (train-split windows only)", ""]
    for key, stats in formula.normalization_stats.items():
        lines.append(f"- `{key}`: min={stats['min']}, max={stats['max']}")
    lines += [
        "",
        f"## Percentile threshold: {formula.percentile_threshold}",
        "",
        "## Rationale",
        "",
        formula.rationale_text,
        "",
    ]
    return "\n".join(lines)
